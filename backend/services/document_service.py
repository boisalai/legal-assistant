"""
Document Service - Business logic for document management.

Handles CRUD operations, file management, and document metadata for courses.
"""

import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

from config.settings import settings
from services.surreal_service import get_surreal_service
from models.document_models import DocumentResponse, DocusaurusSource
from utils.file_utils import calculate_file_hash, get_file_extension, get_mime_type

logger = logging.getLogger(__name__)


class DocumentService:
    """Service for document operations."""

    def __init__(self):
        """Initialize the document service."""
        self.surreal_service = get_surreal_service()

    async def list_documents(
        self,
        course_id: str,
        verify_files: bool = True,
        auto_remove_missing: bool = True,
        include_derived: bool = True
    ) -> List[DocumentResponse]:
        """
        List all documents for a course.

        Args:
            course_id: Course ID (normalized to "course:xxx")
            verify_files: Check if files exist on disk
            auto_remove_missing: Remove documents with missing files
            include_derived: Include derived documents (transcriptions, etc.)

        Returns:
            List of DocumentResponse objects
        """
        try:
            if not self.surreal_service.db:
                await self.surreal_service.connect()

            # Normalize course ID
            if not course_id.startswith("course:"):
                course_id = f"course:{course_id}"

            # Query documents
            legacy_course_id = course_id.replace("course:", "course:")

            if include_derived:
                result = await self.surreal_service.query(
                    "SELECT * FROM document WHERE course_id IN [$course_id, $legacy_course_id] ORDER BY created_at DESC",
                    {"course_id": course_id, "legacy_course_id": legacy_course_id}
                )
            else:
                result = await self.surreal_service.query(
                    "SELECT * FROM document WHERE course_id IN [$course_id, $legacy_course_id] AND is_derived != true ORDER BY created_at DESC",
                    {"course_id": course_id, "legacy_course_id": legacy_course_id}
                )

            # Unwrap SurrealDB result
            items = []
            if result and len(result) > 0:
                first_result = result[0]
                if isinstance(first_result, dict) and "result" in first_result:
                    items = first_result["result"]
                elif isinstance(result, list):
                    items = result

            documents = []
            docs_to_remove = []

            for item in items:
                file_path = item.get("file_path", "")
                file_exists = True

                # Verify file existence
                if verify_files and file_path:
                    file_exists = Path(file_path).exists()
                    if not file_exists and auto_remove_missing:
                        docs_to_remove.append(str(item.get("id", "")))
                        continue

                # Build response
                linked_source_data = item.get("linked_source")
                docusaurus_source_data = item.get("docusaurus_source")

                doc_response = DocumentResponse(
                    id=str(item.get("id", "")),
                    course_id=item.get("course_id", course_id),
                    filename=item.get("nom_fichier", ""),
                    file_type=item.get("type_fichier", ""),
                    mime_type=item.get("type_mime", ""),
                    size=item.get("taille", 0),
                    file_path=file_path,
                    created_at=item.get("created_at", ""),
                    extracted_text=item.get("texte_extrait"),
                    file_exists=file_exists,
                    source_document_id=item.get("source_document_id"),
                    is_derived=item.get("is_derived", False),
                    derivation_type=item.get("derivation_type"),
                    source_type=item.get("source_type", "upload"),
                    linked_source=linked_source_data,
                    docusaurus_source=DocusaurusSource(**docusaurus_source_data) if docusaurus_source_data else None,
                    indexed=item.get("indexed", False)
                )

                documents.append(doc_response)

            # Remove missing documents if requested
            if docs_to_remove:
                for doc_id in docs_to_remove:
                    await self.delete_document(doc_id)
                logger.info(f"Removed {len(docs_to_remove)} documents with missing files")

            return documents

        except Exception as e:
            logger.error(f"Error listing documents: {e}", exc_info=True)
            raise

    async def get_document(self, document_id: str) -> Optional[DocumentResponse]:
        """
        Get a single document by ID.

        Args:
            document_id: Document ID

        Returns:
            DocumentResponse or None if not found
        """
        try:
            if not self.surreal_service.db:
                await self.surreal_service.connect()

            # Normalize document ID
            if not document_id.startswith("document:"):
                document_id = f"document:{document_id}"

            result = await self.surreal_service.query(
                f"SELECT * FROM {document_id}"
            )

            if not result or len(result) == 0:
                return None

            # Unwrap result
            doc_data = result[0]
            if isinstance(doc_data, dict):
                if "result" in doc_data and isinstance(doc_data["result"], list):
                    if len(doc_data["result"]) == 0:
                        return None
                    doc_data = doc_data["result"][0]

            # Check file existence
            file_path = doc_data.get("file_path", "")
            file_exists = Path(file_path).exists() if file_path else False

            # Build response
            linked_source_data = doc_data.get("linked_source")
            docusaurus_source_data = doc_data.get("docusaurus_source")

            return DocumentResponse(
                id=str(doc_data.get("id", document_id)),
                course_id=doc_data.get("course_id", ""),
                filename=doc_data.get("nom_fichier", ""),
                file_type=doc_data.get("type_fichier", ""),
                mime_type=doc_data.get("type_mime", ""),
                size=doc_data.get("taille", 0),
                file_path=file_path,
                created_at=doc_data.get("created_at", ""),
                extracted_text=doc_data.get("texte_extrait"),
                file_exists=file_exists,
                source_document_id=doc_data.get("source_document_id"),
                is_derived=doc_data.get("is_derived", False),
                derivation_type=doc_data.get("derivation_type"),
                source_type=doc_data.get("source_type", "upload"),
                linked_source=linked_source_data,
                docusaurus_source=DocusaurusSource(**docusaurus_source_data) if docusaurus_source_data else None,
                indexed=doc_data.get("indexed", False)
            )

        except Exception as e:
            logger.error(f"Error getting document {document_id}: {e}", exc_info=True)
            raise

    async def create_document(
        self,
        course_id: str,
        filename: str,
        file_path: str,
        file_size: int,
        file_type: Optional[str] = None,
        mime_type: Optional[str] = None,
        extracted_text: Optional[str] = None,
        source_type: str = "upload",
        source_document_id: Optional[str] = None,
        is_derived: bool = False,
        derivation_type: Optional[str] = None,
        linked_source: Optional[Dict[str, Any]] = None,
        docusaurus_source: Optional[Dict[str, Any]] = None
    ) -> DocumentResponse:
        """
        Create a new document record.

        Args:
            course_id: Course ID
            filename: Original filename
            file_path: Absolute path to file
            file_size: File size in bytes
            file_type: File extension (auto-detected if None)
            mime_type: MIME type (auto-detected if None)
            extracted_text: Extracted text content
            source_type: "upload", "linked", or "docusaurus"
            source_document_id: ID of parent document if derived
            is_derived: True if this is a derived file
            derivation_type: Type of derivation (transcription, pdf_extraction, tts)
            linked_source: Metadata for linked directory source
            docusaurus_source: Metadata for Docusaurus source

        Returns:
            Created DocumentResponse
        """
        try:
            if not self.surreal_service.db:
                await self.surreal_service.connect()

            # Normalize course ID
            if not course_id.startswith("course:"):
                course_id = f"course:{course_id}"

            # Auto-detect file type and mime type if not provided
            if not file_type:
                file_type = get_file_extension(filename)
            if not mime_type:
                mime_type = get_mime_type(filename)

            # Generate document ID (remove hyphens for SurrealDB compatibility)
            doc_id = f"document:{uuid.uuid4().hex[:16]}"

            # Prepare document data
            # Note: Don't include "id" in doc_data - it's specified in the CREATE statement
            doc_data = {
                "course_id": course_id,
                "nom_fichier": filename,
                "type_fichier": file_type,
                "type_mime": mime_type,
                "taille": file_size,
                "file_path": file_path,
                "created_at": datetime.utcnow().isoformat(),
                "source_type": source_type,
                "indexed": False
            }

            # Add optional fields
            if extracted_text:
                doc_data["texte_extrait"] = extracted_text
            if source_document_id:
                doc_data["source_document_id"] = source_document_id
            if is_derived:
                doc_data["is_derived"] = is_derived
            if derivation_type:
                doc_data["derivation_type"] = derivation_type
            if linked_source:
                doc_data["linked_source"] = linked_source
            if docusaurus_source:
                doc_data["docusaurus_source"] = docusaurus_source

            # Insert into database
            result = await self.surreal_service.query(
                f"CREATE {doc_id} CONTENT $data",
                {"data": doc_data}
            )

            logger.info(f"Created document {doc_id} for course {course_id}")

            # Return created document
            return await self.get_document(doc_id)

        except Exception as e:
            logger.error(f"Error creating document: {e}", exc_info=True)
            raise

    async def delete_document(self, document_id: str, delete_file: bool = True) -> bool:
        """
        Delete a document and optionally its file.

        Args:
            document_id: Document ID
            delete_file: If True, also delete the file from disk

        Returns:
            True if successful
        """
        try:
            if not self.surreal_service.db:
                await self.surreal_service.connect()

            # Normalize document ID
            if not document_id.startswith("document:"):
                document_id = f"document:{document_id}"

            # Get document to find file path
            doc = await self.get_document(document_id)
            if not doc:
                logger.warning(f"Document {document_id} not found for deletion")
                return False

            # Delete from database
            await self.surreal_service.query(f"DELETE {document_id}")

            # Delete file if requested
            if delete_file and doc.file_path:
                try:
                    file_path = Path(doc.file_path)
                    if file_path.exists():
                        file_path.unlink()
                        logger.info(f"Deleted file: {doc.file_path}")
                except Exception as e:
                    logger.error(f"Error deleting file {doc.file_path}: {e}")

            # Delete associated embeddings
            try:
                await self.surreal_service.query(
                    "DELETE FROM embedding WHERE document_id = $doc_id",
                    {"doc_id": document_id}
                )
                logger.info(f"Deleted embeddings for document {document_id}")
            except Exception as e:
                logger.error(f"Error deleting embeddings for {document_id}: {e}")

            logger.info(f"Deleted document {document_id}")
            return True

        except Exception as e:
            logger.error(f"Error deleting document {document_id}: {e}", exc_info=True)
            raise

    async def get_derived_documents(self, source_document_id: str) -> List[DocumentResponse]:
        """
        Get all derived documents from a source document.

        Args:
            source_document_id: Source document ID

        Returns:
            List of derived DocumentResponse objects
        """
        try:
            if not self.surreal_service.db:
                await self.surreal_service.connect()

            # Normalize document ID
            if not source_document_id.startswith("document:"):
                source_document_id = f"document:{source_document_id}"

            result = await self.surreal_service.query(
                "SELECT * FROM document WHERE source_document_id = $source_id ORDER BY created_at DESC",
                {"source_id": source_document_id}
            )

            # Unwrap result
            items = []
            if result and len(result) > 0:
                first_result = result[0]
                if isinstance(first_result, dict) and "result" in first_result:
                    items = first_result["result"]
                elif isinstance(result, list):
                    items = result

            documents = []
            for item in items:
                doc = await self._build_document_response(item)
                if doc:
                    documents.append(doc)

            return documents

        except Exception as e:
            logger.error(f"Error getting derived documents: {e}", exc_info=True)
            raise

    async def update_document_text(
        self,
        document_id: str,
        extracted_text: str
    ) -> DocumentResponse:
        """
        Update the extracted text of a document.

        Args:
            document_id: Document ID
            extracted_text: New extracted text

        Returns:
            Updated DocumentResponse
        """
        try:
            if not self.surreal_service.db:
                await self.surreal_service.connect()

            # Normalize document ID
            if not document_id.startswith("document:"):
                document_id = f"document:{document_id}"

            # Update document
            await self.surreal_service.query(
                f"UPDATE {document_id} SET texte_extrait = $text",
                {"text": extracted_text}
            )

            logger.info(f"Updated text for document {document_id}")

            # Return updated document
            return await self.get_document(document_id)

        except Exception as e:
            logger.error(f"Error updating document text: {e}", exc_info=True)
            raise

    async def _build_document_response(self, item: Dict[str, Any]) -> Optional[DocumentResponse]:
        """
        Build a DocumentResponse from a database item.

        Args:
            item: Database document data

        Returns:
            DocumentResponse or None
        """
        try:
            file_path = item.get("file_path", "")
            file_exists = Path(file_path).exists() if file_path else False

            linked_source_data = item.get("linked_source")
            docusaurus_source_data = item.get("docusaurus_source")

            return DocumentResponse(
                id=str(item.get("id", "")),
                course_id=item.get("course_id", ""),
                filename=item.get("nom_fichier", ""),
                file_type=item.get("type_fichier", ""),
                mime_type=item.get("type_mime", ""),
                size=item.get("taille", 0),
                file_path=file_path,
                created_at=item.get("created_at", ""),
                extracted_text=item.get("texte_extrait"),
                file_exists=file_exists,
                source_document_id=item.get("source_document_id"),
                is_derived=item.get("is_derived", False),
                derivation_type=item.get("derivation_type"),
                source_type=item.get("source_type", "upload"),
                linked_source=linked_source_data,
                docusaurus_source=DocusaurusSource(**docusaurus_source_data) if docusaurus_source_data else None,
                indexed=item.get("indexed", False)
            )
        except Exception as e:
            logger.error(f"Error building document response: {e}")
            return None


# Singleton instance
_document_service: Optional[DocumentService] = None


def get_document_service() -> DocumentService:
    """Get the singleton document service instance."""
    global _document_service
    if _document_service is None:
        _document_service = DocumentService()
    return _document_service
