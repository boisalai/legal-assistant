"""
Automatic synchronization service for linked directories.

This service runs in the background and periodically synchronizes
all linked directories to detect:
- New files (add and index)
- Modified files (reindex)
- Deleted files (remove from index)
"""

import asyncio
import logging
import traceback
import uuid
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Optional

from services.surreal_service import get_surreal_service
from services.document_indexing_service import DocumentIndexingService
from utils.file_utils import calculate_file_hash
from utils.linked_directory_utils import (
    scan_directory,
    extract_text_from_file,
    normalize_linked_source,
)

logger = logging.getLogger(__name__)


class AutoSyncService:
    """Singleton service for automatic synchronization of linked directories."""

    _instance: Optional["AutoSyncService"] = None
    _task: Optional[asyncio.Task] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._running = False
        self._interval_seconds = 300  # 5 minutes by default
        self._task = None

    @property
    def interval_seconds(self) -> int:
        """Synchronization interval in seconds."""
        return self._interval_seconds

    @interval_seconds.setter
    def interval_seconds(self, value: int):
        """Set the synchronization interval (minimum 60 seconds)."""
        self._interval_seconds = max(60, value)
        logger.info(f"Auto-sync interval set to {self._interval_seconds} seconds")

    @property
    def is_running(self) -> bool:
        """Check if the service is running."""
        return self._running and self._task is not None and not self._task.done()

    async def start(self):
        """Start automatic synchronization in the background."""
        if self.is_running:
            logger.warning("Auto-sync service is already running")
            return

        self._running = True
        self._task = asyncio.create_task(self._sync_loop())
        logger.info(
            f"Auto-sync service started (interval: {self._interval_seconds}s)"
        )

    async def stop(self):
        """Gracefully stop automatic synchronization."""
        if not self._running:
            return

        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        logger.info("Auto-sync service stopped")

    async def _sync_loop(self):
        """Main synchronization loop."""
        # Wait a bit at startup to allow the DB to connect
        await asyncio.sleep(10)

        while self._running:
            try:
                await self._sync_all_linked_directories()
            except Exception as e:
                logger.error(f"Error in auto-sync loop: {e}")
                logger.debug(traceback.format_exc())

            # Wait for interval before next sync
            try:
                await asyncio.sleep(self._interval_seconds)
            except asyncio.CancelledError:
                break

    async def _sync_all_linked_directories(self):
        """Synchronize all linked directories from all courses."""
        try:
            service = get_surreal_service()
            if not service.db:
                logger.debug("Database not connected, skipping auto-sync")
                return

            # Retrieve all linked documents (all courses)
            query = """
                SELECT * FROM document
                WHERE source_type = 'linked'
                AND linked_source IS NOT NONE
            """
            result = await service.db.query(query)
            linked_docs = result if result else []

            if not linked_docs:
                logger.debug("No linked directories found, skipping sync")
                return

            # Group by course_id then by link_id
            by_course = defaultdict(lambda: defaultdict(list))
            for doc in linked_docs:
                course_id = doc.get("course_id", "")
                linked_source = normalize_linked_source(doc.get("linked_source"))
                link_id = linked_source.get("link_id")
                if course_id and link_id:
                    by_course[course_id][link_id].append(doc)

            # Global statistics
            global_stats = {
                "courses_synced": 0,
                "added": 0,
                "updated": 0,
                "removed": 0,
                "unchanged": 0,
                "errors": 0,
            }

            # Synchronize each course
            for course_id, links in by_course.items():
                try:
                    stats = await self._sync_course_directories(
                        service, course_id, links
                    )
                    global_stats["courses_synced"] += 1
                    global_stats["added"] += stats["added"]
                    global_stats["updated"] += stats["updated"]
                    global_stats["removed"] += stats["removed"]
                    global_stats["unchanged"] += stats["unchanged"]
                except Exception as e:
                    global_stats["errors"] += 1
                    logger.error(f"Error syncing course {course_id}: {e}")

            # Log only if changes occurred
            changes = (
                global_stats["added"]
                + global_stats["updated"]
                + global_stats["removed"]
            )
            if changes > 0:
                logger.info(
                    f"Auto-sync completed: {global_stats['courses_synced']} courses, "
                    f"+{global_stats['added']} -{global_stats['removed']} "
                    f"~{global_stats['updated']} ={global_stats['unchanged']}"
                )
            else:
                logger.debug(
                    f"Auto-sync: no changes detected in {global_stats['courses_synced']} courses"
                )

        except Exception as e:
            logger.error(f"Error in _sync_all_linked_directories: {e}")
            logger.debug(traceback.format_exc())

    async def _sync_course_directories(
        self, service, course_id: str, links: dict
    ) -> dict:
        """Synchronize linked directories for a specific course."""
        stats = {"added": 0, "updated": 0, "removed": 0, "unchanged": 0}
        indexing_service = DocumentIndexingService()
        now = datetime.utcnow().isoformat()

        for link_id, docs in links.items():
            try:
                # Get the base path
                first_doc_linked_source = normalize_linked_source(
                    docs[0].get("linked_source")
                )
                directory_path = first_doc_linked_source.get("base_path")

                if not directory_path:
                    absolute_path = first_doc_linked_source.get("absolute_path", "")
                    if not absolute_path:
                        continue
                    directory_path = str(Path(absolute_path).parent)

                # Verify the directory still exists
                if not Path(directory_path).exists():
                    logger.warning(
                        f"Linked directory no longer exists: {directory_path}"
                    )
                    continue

                # Scan the directory
                try:
                    scan_result = scan_directory(directory_path)
                except Exception as e:
                    logger.error(f"Cannot scan {directory_path}: {e}")
                    continue

                # Index of existing files
                existing_files = {doc["file_path"]: doc for doc in docs}
                scanned_files = {
                    str(f.absolute_path): f for f in scan_result.files
                }

                # Get user_id from first document for new files
                user_id = docs[0].get("user_id", "system")

                # 1. Detect deleted files
                for file_path, doc in existing_files.items():
                    if file_path not in scanned_files:
                        doc_id = doc["id"]
                        await service.delete(doc_id)
                        stats["removed"] += 1
                        logger.info(f"Auto-sync: removed {Path(file_path).name}")

                # 2. Detect new files and modifications
                for file_path, file_info in scanned_files.items():
                    source_file = Path(file_path)

                    if file_path not in existing_files:
                        # New file
                        try:
                            await self._add_new_file(
                                service,
                                indexing_service,
                                source_file,
                                file_info,
                                scan_result,
                                course_id,
                                link_id,
                                user_id,
                                now,
                            )
                            stats["added"] += 1
                            logger.info(f"Auto-sync: added {source_file.name}")
                        except Exception as e:
                            logger.error(f"Error adding {file_path}: {e}")
                    else:
                        # Existing file - check for modifications
                        existing_doc = existing_files[file_path]
                        existing_linked_source = normalize_linked_source(
                            existing_doc.get("linked_source")
                        )
                        old_hash = existing_linked_source.get("source_hash", "")
                        old_mtime = existing_linked_source.get("source_mtime", 0)

                        new_hash = calculate_file_hash(source_file)

                        if (
                            new_hash != old_hash
                            or file_info.modified_time != old_mtime
                        ):
                            # Modified file
                            try:
                                await self._update_modified_file(
                                    service,
                                    indexing_service,
                                    existing_doc,
                                    existing_linked_source,
                                    source_file,
                                    file_info,
                                    new_hash,
                                    course_id,
                                    now,
                                )
                                stats["updated"] += 1
                                logger.info(f"Auto-sync: updated {source_file.name}")
                            except Exception as e:
                                logger.error(f"Error updating {file_path}: {e}")
                        else:
                            stats["unchanged"] += 1

            except Exception as e:
                logger.error(f"Error syncing link_id {link_id}: {e}")

        return stats

    async def _add_new_file(
        self,
        service,
        indexing_service,
        source_file: Path,
        file_info,
        scan_result,
        course_id: str,
        link_id: str,
        user_id: str,
        now: str,
    ):
        """Add a newly detected file."""
        doc_id = str(uuid.uuid4())[:8]
        content = extract_text_from_file(source_file)
        file_hash = calculate_file_hash(source_file)

        linked_source = {
            "absolute_path": str(source_file),
            "relative_path": file_info.relative_path,
            "parent_folder": file_info.parent_folder,
            "link_id": link_id,
            "base_path": scan_result.base_path,
            "last_sync": now,
            "source_hash": file_hash,
            "source_mtime": file_info.modified_time,
        }

        mime_types = {
            "md": "text/markdown",
            "mdx": "text/markdown",
            "txt": "text/plain",
            "pdf": "application/pdf",
            "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "doc": "application/msword",
        }
        type_mime = mime_types.get(file_info.extension, "application/octet-stream")

        document_data = {
            "course_id": course_id,
            "nom_fichier": source_file.name,
            "type_fichier": file_info.extension,
            "type_mime": type_mime,
            "taille": file_info.size,
            "file_path": str(source_file),
            "user_id": user_id,
            "created_at": now,
            "source_type": "linked",
            "linked_source": linked_source,
            "texte_extrait": (
                content if content and not content.startswith("[Contenu") else None
            ),
            "indexed": False,
        }

        await service.create("document", document_data, record_id=doc_id)

        # Index if content is available
        if content and not content.startswith("[Contenu"):
            try:
                result = await indexing_service.index_document(
                    document_id=f"document:{doc_id}",
                    course_id=course_id,
                    text_content=content,
                )
                if result.get("success"):
                    await service.merge(f"document:{doc_id}", {"indexed": True})
            except Exception as e:
                logger.error(f"Error indexing document:{doc_id}: {e}")

    async def _update_modified_file(
        self,
        service,
        indexing_service,
        existing_doc: dict,
        existing_linked_source: dict,
        source_file: Path,
        file_info,
        new_hash: str,
        course_id: str,
        now: str,
    ):
        """Update a modified file."""
        content = extract_text_from_file(source_file)
        doc_id = existing_doc["id"]

        updated_linked_source = existing_linked_source.copy()
        updated_linked_source["source_hash"] = new_hash
        updated_linked_source["source_mtime"] = file_info.modified_time
        updated_linked_source["last_sync"] = now

        update_data = {
            "linked_source": updated_linked_source,
            "texte_extrait": (
                content if content and not content.startswith("[Contenu") else None
            ),
            "taille": file_info.size,
            "indexed": False,
        }

        await service.merge(doc_id, update_data)

        # Reindex if content is available
        if content and not content.startswith("[Contenu"):
            try:
                result = await indexing_service.index_document(
                    document_id=doc_id,
                    course_id=course_id,
                    text_content=content,
                )
                if result.get("success"):
                    await service.merge(doc_id, {"indexed": True})
            except Exception as e:
                logger.error(f"Error re-indexing {doc_id}: {e}")


# Global service instance
_auto_sync_service: Optional[AutoSyncService] = None


def get_auto_sync_service() -> AutoSyncService:
    """Return the singleton auto-sync service instance."""
    global _auto_sync_service
    if _auto_sync_service is None:
        _auto_sync_service = AutoSyncService()
    return _auto_sync_service


async def start_auto_sync(interval_seconds: int = 300):
    """Start the automatic synchronization service."""
    service = get_auto_sync_service()
    service.interval_seconds = interval_seconds
    await service.start()


async def stop_auto_sync():
    """Stop the automatic synchronization service."""
    service = get_auto_sync_service()
    await service.stop()
