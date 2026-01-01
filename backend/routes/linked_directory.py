"""
Routes pour la liaison de répertoires locaux dans Legal Assistant.

Endpoints:
- POST /api/linked-directory/scan - Scanne un répertoire et retourne les statistiques
- POST /api/courses/{course_id}/link-directory - Lie et indexe les fichiers d'un répertoire
- POST /api/linked-directory/{link_id}/refresh - Rafraîchit les fichiers d'un répertoire lié
"""

import logging
import os
import uuid
import traceback
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict
from collections import defaultdict

from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import json

from config.settings import settings
from services.surreal_service import get_surreal_service
from services.document_indexing_service import DocumentIndexingService
from models.document_models import DocumentResponse
from auth.helpers import require_auth, get_current_user_id
from utils.file_utils import calculate_file_hash, LINKABLE_EXTENSIONS
from utils.linked_directory_utils import (
    FileInfo,
    DirectoryScanResult,
    scan_directory,
    extract_text_from_file,
    normalize_linked_source,
    SUPPORTED_EXTENSIONS,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["Linked Directory"])


# ============================================================================
# Pydantic Models
# ============================================================================

class ScanDirectoryRequest(BaseModel):
    """Requête pour scanner un répertoire."""
    directory_path: str


class LinkDirectoryRequest(BaseModel):
    """Requête pour lier un répertoire."""
    directory_path: str
    file_paths: Optional[List[str]] = None  # Si None, importe tous les fichiers trouvés
    auto_extract_markdown: bool = False  # Si True, extrait automatiquement PDF/DOCX/Audio en markdown
    module_id: Optional[str] = None  # Si fourni, assigne tous les fichiers à ce module


class LinkedDirectoryMetadata(BaseModel):
    """Métadonnées d'un répertoire lié."""
    base_path: str
    linked_at: str
    total_files: int
    total_size: int
    last_refresh: Optional[str] = None


# ============================================================================
# Helper Functions
# ============================================================================
# Note: scan_directory, extract_text_from_file, normalize_linked_source
# are imported from utils.linked_directory_utils


async def create_markdown_from_file(
    service,
    source_file: Path,
    course_id: str,
    user_id: str,
    link_id: str,
    linked_source_metadata: dict,
    module_id: Optional[str] = None
) -> Optional[tuple[str, str]]:
    """
    Extrait un fichier (PDF, Word, Audio) et crée un fichier Markdown dérivé.

    Args:
        service: Instance de SurrealService
        source_file: Chemin du fichier source
        course_id: ID du cours
        user_id: ID de l'utilisateur
        link_id: ID de liaison du répertoire
        linked_source_metadata: Métadonnées de la source liée

    Returns:
        Tuple (document_id, texte_extrait) ou None si l'extraction a échoué
    """
    from services.document_extraction_service import get_extraction_service

    extraction_service = get_extraction_service()
    extension = source_file.suffix.lower()

    # Extraire le contenu
    try:
        extraction_result = await extraction_service.extract(
            file_path=source_file,
            language="fr"
        )

        if not extraction_result.success or not extraction_result.text:
            logger.warning(f"Extraction failed for {source_file.name}: {extraction_result.error}")
            return None

        # Créer le fichier markdown dans le même répertoire que le fichier source
        markdown_filename = source_file.stem + ".md"
        markdown_path = source_file.parent / markdown_filename

        # Écrire le fichier markdown
        with open(markdown_path, "w", encoding="utf-8") as f:
            f.write(extraction_result.text)

        # Créer l'enregistrement dans SurrealDB
        now = datetime.utcnow().isoformat()
        doc_id = str(uuid.uuid4())[:8]

        # Déterminer le type de dérivation
        derivation_type = "pdf_extraction" if extension == ".pdf" else \
                         "word_extraction" if extension in [".doc", ".docx"] else \
                         "audio_transcription"

        # Créer les métadonnées de liaison pour le fichier markdown
        md_linked_source = linked_source_metadata.copy()
        md_linked_source["absolute_path"] = str(markdown_path)
        md_linked_source["relative_path"] = str(Path(linked_source_metadata["relative_path"]).parent / markdown_filename)
        md_linked_source["derived_from"] = str(source_file)
        md_linked_source["last_sync"] = now
        md_linked_source["source_hash"] = calculate_file_hash(markdown_path)
        md_linked_source["source_mtime"] = markdown_path.stat().st_mtime

        document_data = {
            "course_id": course_id,
            "nom_fichier": markdown_filename,
            "type_fichier": "md",
            "type_mime": "text/markdown",
            "taille": len(extraction_result.text.encode('utf-8')),
            "file_path": str(markdown_path),
            "user_id": user_id,
            "created_at": now,
            "source_type": "linked",
            "linked_source": md_linked_source,
            "texte_extrait": extraction_result.text,
            "indexed": False,
            "is_derived": True,
            "derivation_type": derivation_type,
            "is_transcription": extraction_result.is_transcription,
        }

        # Ajouter module_id si spécifié
        if module_id:
            document_data["module_id"] = module_id

        await service.create("document", document_data, record_id=doc_id)
        logger.info(f"Created markdown document {doc_id} from {source_file.name}")

        return (f"document:{doc_id}", extraction_result.text)

    except Exception as e:
        logger.error(f"Error creating markdown from {source_file.name}: {e}")
        return None


# ============================================================================
# Endpoints
# ============================================================================

@router.post("/linked-directory/scan", response_model=DirectoryScanResult)
async def scan_directory_endpoint(
    request: ScanDirectoryRequest,
    user_id: Optional[str] = Depends(get_current_user_id)
):
    """
    Scanne un répertoire et retourne les statistiques des fichiers supportés.

    Fichiers supportés : .md, .mdx, .pdf, .txt, .docx, .doc
    """
    try:
        result = scan_directory(request.directory_path)
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Erreur lors du scan du répertoire: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/courses/{course_id}/link-directory")
async def link_directory_endpoint(
    course_id: str,
    request: LinkDirectoryRequest,
    user_id: str = Depends(require_auth)
):
    """
    Lie un répertoire à un cours et indexe tous les fichiers.

    Utilise Server-Sent Events (SSE) pour envoyer la progression en temps réel.

    Events:
    - progress: {"indexed": 5, "total": 32, "current_file": "contrat.pdf"}
    - complete: {"success": true, "total_indexed": 32}
    - error: {"error": "message d'erreur"}
    """
    try:
        service = get_surreal_service()
        if not service.db:
            await service.connect()

        # Normaliser l'ID du cours
        if not course_id.startswith("course:"):
            course_id = f"course:{course_id}"

        # Scanner le répertoire
        scan_result = scan_directory(request.directory_path)

        # Déterminer les fichiers à indexer
        files_to_index = scan_result.files
        if request.file_paths:
            # Filtrer uniquement les fichiers sélectionnés
            selected_paths = set(request.file_paths)
            files_to_index = [f for f in files_to_index if f.absolute_path in selected_paths]

        async def generate_progress():
            """Générateur SSE pour la progression."""
            total = len(files_to_index)
            indexed = 0
            now = datetime.utcnow().isoformat()

            # Normaliser le module_id si fourni
            target_module_id = None
            if request.module_id:
                target_module_id = request.module_id
                if not target_module_id.startswith("module:"):
                    target_module_id = f"module:{target_module_id}"

            # Créer une entrée pour le répertoire lié
            link_id = str(uuid.uuid4())[:8]
            link_metadata = {
                "base_path": scan_result.base_path,
                "linked_at": now,
                "total_files": total,
                "total_size": sum(f.size for f in files_to_index),
                "last_refresh": now
            }

            # Envoyer l'événement "started" avec le link_id pour permettre l'annulation
            started_data = {
                "link_id": link_id,
                "total": total,
                "message": "Indexation démarrée"
            }
            yield f"event: started\ndata: {json.dumps(started_data)}\n\n"

            try:
                indexing_service = DocumentIndexingService()

                for file_info in files_to_index:
                    try:
                        source_file = Path(file_info.absolute_path)

                        # Générer un ID unique pour le document
                        doc_id = str(uuid.uuid4())[:8]

                        # Extraire le contenu
                        content = extract_text_from_file(source_file)

                        # Calculer le hash
                        file_hash = calculate_file_hash(source_file)

                        # Créer les métadonnées de liaison
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

                        # Déterminer le type MIME
                        mime_types = {
                            "md": "text/markdown",
                            "mdx": "text/markdown",
                            "txt": "text/plain",
                            "pdf": "application/pdf",
                            "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                            "doc": "application/msword"
                        }
                        type_mime = mime_types.get(file_info.extension, "application/octet-stream")

                        # Créer le document dans SurrealDB
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
                            "texte_extrait": content if content and not content.startswith("[Contenu") else None,
                            "indexed": False
                        }

                        # Ajouter module_id si spécifié
                        if target_module_id:
                            document_data["module_id"] = target_module_id

                        await service.create("document", document_data, record_id=doc_id)

                        # Si auto_extract_markdown est activé et le fichier est PDF/DOCX/Audio
                        markdown_result = None
                        if request.auto_extract_markdown and file_info.extension in ["pdf", "docx", "doc", "mp3", "m4a", "wav", "mp4", "webm", "ogg"]:
                            markdown_result = await create_markdown_from_file(
                                service=service,
                                source_file=source_file,
                                course_id=course_id,
                                user_id=user_id,
                                link_id=link_id,
                                linked_source_metadata=linked_source,
                                module_id=target_module_id
                            )

                        # Déterminer quel contenu indexer
                        content_to_index = None
                        doc_id_to_index = None

                        if markdown_result:
                            # Si markdown créé avec succès, indexer le markdown
                            doc_id_to_index, content_to_index = markdown_result
                        elif content and not content.startswith("[Contenu"):
                            # Sinon, indexer le fichier source si contenu disponible
                            content_to_index = content
                            doc_id_to_index = f"document:{doc_id}"

                        # Indexer si contenu disponible
                        if content_to_index and doc_id_to_index:
                            try:
                                result = await indexing_service.index_document(
                                    document_id=doc_id_to_index,
                                    course_id=course_id,
                                    text_content=content_to_index
                                )

                                if result.get("success"):
                                    await service.merge(
                                        doc_id_to_index,
                                        {"indexed": True}
                                    )
                            except Exception as e:
                                logger.error(f"Erreur lors de l'indexation du document:{doc_id_to_index}: {e}")

                        indexed += 1

                        # Envoyer la progression
                        progress_data = {
                            "indexed": indexed,
                            "total": total,
                            "current_file": source_file.name,
                            "percentage": round((indexed / total) * 100, 1)
                        }
                        yield f"event: progress\ndata: {json.dumps(progress_data)}\n\n"

                    except Exception as e:
                        logger.error(f"Erreur lors du traitement du fichier {file_info.absolute_path}: {e}")
                        continue

                # Envoyer le message de complétion
                complete_data = {
                    "success": True,
                    "total_indexed": indexed,
                    "link_id": link_id
                }
                yield f"event: complete\ndata: {json.dumps(complete_data)}\n\n"

            except Exception as e:
                logger.error(f"Erreur lors de la liaison du répertoire: {e}")
                error_data = {"error": str(e)}
                yield f"event: error\ndata: {json.dumps(error_data)}\n\n"

        return StreamingResponse(
            generate_progress(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no"
            }
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Erreur lors de la liaison du répertoire: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/courses/{course_id}/sync-linked-directories")
async def sync_linked_directories_endpoint(
    course_id: str,
    user_id: str = Depends(require_auth)
):
    """
    Synchronise tous les répertoires liés d'un cours.

    Pour chaque répertoire lié:
    - Détecte les nouveaux fichiers (ajoute et indexe)
    - Détecte les fichiers modifiés (réindexe)
    - Détecte les fichiers supprimés (retire de la BD)

    Returns:
        {
            "added": 3,
            "updated": 2,
            "removed": 1,
            "unchanged": 20
        }
    """
    try:
        service = get_surreal_service()
        if not service.db:
            await service.connect()

        # Normaliser l'ID du cours
        if not course_id.startswith("course:"):
            course_id = f"course:{course_id}"

        # Récupérer tous les documents liés pour ce cours
        query = """
            SELECT * FROM document
            WHERE course_id = $course_id
            AND source_type = 'linked'
            AND linked_source IS NOT NONE
        """
        result = await service.db.query(query, {"course_id": course_id})
        # Note: result est directement la liste de documents, pas result[0]
        linked_docs = result if result else []

        if not linked_docs:
            return {
                "added": 0,
                "updated": 0,
                "removed": 0,
                "unchanged": 0,
                "message": "Aucun répertoire lié trouvé"
            }

        # Grouper par link_id
        by_link_id = defaultdict(list)
        for doc in linked_docs:
            linked_source = normalize_linked_source(doc.get("linked_source"))
            link_id = linked_source.get("link_id")
            if link_id:
                by_link_id[link_id].append(doc)

        # Compteurs
        total_added = 0
        total_updated = 0
        total_removed = 0
        total_unchanged = 0

        indexing_service = DocumentIndexingService()
        now = datetime.utcnow().isoformat()

        # Pour chaque répertoire lié
        for link_id, docs in by_link_id.items():
            # Obtenir le chemin de base depuis le premier document
            first_doc_linked_source = normalize_linked_source(docs[0].get("linked_source"))

            # Essayer d'abord le base_path stocké (nouveaux documents)
            directory_path = first_doc_linked_source.get("base_path")

            # Fallback pour les anciens documents (avant la correction)
            if not directory_path:
                absolute_path = first_doc_linked_source.get("absolute_path", "")
                if not absolute_path:
                    logger.warning(f"Chemin de base introuvable pour link_id {link_id}")
                    continue
                directory_path = str(Path(absolute_path).parent)

            # Re-scanner le répertoire
            try:
                scan_result = scan_directory(directory_path)
            except Exception as e:
                logger.error(f"Impossible de scanner {directory_path}: {e}")
                continue

            # Créer un index des fichiers existants par chemin absolu
            existing_files = {doc["file_path"]: doc for doc in docs}
            scanned_files = {str(f.absolute_path): f for f in scan_result.files}

            # 1. Détecter les fichiers supprimés (dans BD mais pas sur disque)
            for file_path, doc in existing_files.items():
                if file_path not in scanned_files:
                    # Fichier supprimé - retirer de la BD
                    doc_id = doc["id"]
                    await service.delete(doc_id)
                    total_removed += 1
                    logger.info(f"Document {doc_id} supprimé (fichier absent)")

            # 2. Détecter les nouveaux fichiers et fichiers modifiés
            for file_path, file_info in scanned_files.items():
                source_file = Path(file_path)

                if file_path not in existing_files:
                    # Nouveau fichier - ajouter et indexer
                    try:
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
                            "doc": "application/msword"
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
                            "texte_extrait": content if content and not content.startswith("[Contenu") else None,
                            "indexed": False
                        }

                        await service.create("document", document_data, record_id=doc_id)

                        # Indexer si contenu disponible
                        if content and not content.startswith("[Contenu"):
                            try:
                                result = await indexing_service.index_document(
                                    document_id=f"document:{doc_id}",
                                    course_id=course_id,
                                    text_content=content
                                )

                                if result.get("success"):
                                    await service.merge(
                                        f"document:{doc_id}",
                                        {"indexed": True}
                                    )
                            except Exception as e:
                                logger.error(f"Erreur lors de l'indexation du document:{doc_id}: {e}")

                        total_added += 1
                        logger.info(f"Nouveau fichier ajouté: {file_path}")

                    except Exception as e:
                        logger.error(f"Erreur lors de l'ajout de {file_path}: {e}")

                else:
                    # Fichier existant - vérifier s'il a été modifié
                    existing_doc = existing_files[file_path]
                    existing_linked_source = normalize_linked_source(existing_doc.get("linked_source"))
                    old_hash = existing_linked_source.get("source_hash", "")
                    old_mtime = existing_linked_source.get("source_mtime", 0)

                    # Calculer le nouveau hash
                    new_hash = calculate_file_hash(source_file)

                    # Vérifier si le fichier a changé (hash ou mtime différent)
                    if new_hash != old_hash or file_info.modified_time != old_mtime:
                        # Fichier modifié - réindexer
                        try:
                            content = extract_text_from_file(source_file)
                            doc_id = existing_doc["id"]

                            # Mettre à jour l'objet linked_source complet
                            updated_linked_source = existing_linked_source.copy()
                            updated_linked_source["source_hash"] = new_hash
                            updated_linked_source["source_mtime"] = file_info.modified_time
                            updated_linked_source["last_sync"] = now

                            # Mettre à jour les métadonnées
                            update_data = {
                                "linked_source": updated_linked_source,
                                "texte_extrait": content if content and not content.startswith("[Contenu") else None,
                                "taille": file_info.size,
                                "indexed": False
                            }

                            await service.merge(doc_id, update_data)

                            # Réindexer si contenu disponible
                            if content and not content.startswith("[Contenu"):
                                try:
                                    result = await indexing_service.index_document(
                                        document_id=doc_id,
                                        course_id=course_id,
                                        text_content=content
                                    )

                                    if result.get("success"):
                                        await service.merge(
                                            doc_id,
                                            {"indexed": True}
                                        )
                                except Exception as e:
                                    logger.error(f"Erreur lors de la réindexation de {doc_id}: {e}")

                            total_updated += 1
                            logger.info(f"Fichier mis à jour: {file_path}")

                        except Exception as e:
                            logger.error(f"Erreur lors de la mise à jour de {file_path}: {e}")

                    else:
                        # Fichier inchangé
                        total_unchanged += 1

        return {
            "added": total_added,
            "updated": total_updated,
            "removed": total_removed,
            "unchanged": total_unchanged,
            "message": f"Synchronisation terminée: {total_added} ajouté(s), {total_updated} mis à jour, {total_removed} supprimé(s)"
        }

    except Exception as e:
        logger.error(f"Erreur lors de la synchronisation des répertoires liés: {e}")
        logger.error(f"Traceback complet:\n{traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/courses/{course_id}/reindex-unindexed")
async def reindex_unindexed_documents_endpoint(
    course_id: str,
    user_id: str = Depends(require_auth)
):
    """
    Réindexe tous les documents non-indexés d'un cours.

    Returns:
        {
            "indexed": 5,
            "failed": 0,
            "total": 5
        }
    """
    try:
        service = get_surreal_service()
        if not service.db:
            await service.connect()

        # Normaliser l'ID du cours
        if not course_id.startswith("course:"):
            course_id = f"course:{course_id}"

        # Récupérer tous les documents non indexés
        query = """
            SELECT * FROM document
            WHERE course_id = $course_id
            AND indexed = false
            AND texte_extrait IS NOT NONE
        """
        result = await service.db.query(query, {"course_id": course_id})
        docs = result if result else []

        if not docs:
            return {
                "indexed": 0,
                "failed": 0,
                "total": 0,
                "message": "Aucun document non indexé trouvé"
            }

        indexing_service = DocumentIndexingService()
        indexed_count = 0
        failed_count = 0

        for doc in docs:
            doc_id = str(doc["id"])
            texte_extrait = doc.get("texte_extrait")

            if not texte_extrait or not texte_extrait.strip():
                continue

            try:
                result = await indexing_service.index_document(
                    document_id=doc_id,
                    case_id=course_id,
                    text_content=texte_extrait
                )

                if result.get("success"):
                    await service.merge(doc_id, {"indexed": True})
                    indexed_count += 1
                    logger.info(f"Indexed {doc.get('nom_fichier')}: {result.get('chunks_created')} chunks")
                else:
                    failed_count += 1
                    logger.error(f"Failed to index {doc.get('nom_fichier')}: {result.get('error')}")

            except Exception as e:
                failed_count += 1
                logger.error(f"Error indexing {doc.get('nom_fichier')}: {e}")

        return {
            "indexed": indexed_count,
            "failed": failed_count,
            "total": len(docs),
            "message": f"Indexation terminée: {indexed_count} indexé(s), {failed_count} échec(s)"
        }

    except Exception as e:
        logger.error(f"Erreur lors de la réindexation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.delete("/courses/{course_id}/link-directory/{link_id}")
async def cancel_link_directory(
    course_id: str,
    link_id: str,
    user_id: str = Depends(require_auth)
):
    """
    Annule une liaison de répertoire en cours et nettoie tous les documents associés.

    Supprime :
    - Tous les documents avec le link_id spécifié
    - Tous les embeddings associés à ces documents
    - Les fichiers markdown dérivés créés sur le disque (optionnel)

    Args:
        course_id: ID du cours
        link_id: ID de la liaison à annuler
        user_id: ID de l'utilisateur (auth)

    Returns:
        {
            "success": true,
            "documents_deleted": 10,
            "embeddings_deleted": 150,
            "message": "Liaison annulée avec succès"
        }
    """
    try:
        service = get_surreal_service()
        if not service.db:
            await service.connect()

        # Normaliser l'ID du cours
        if not course_id.startswith("course:"):
            course_id = f"course:{course_id}"

        logger.info(f"Annulation de la liaison {link_id} pour le cours {course_id}")

        # Récupérer tous les documents avec ce link_id
        query = """
            SELECT * FROM document
            WHERE course_id = $course_id
            AND source_type = 'linked'
            AND linked_source.link_id = $link_id
        """
        result = await service.db.query(query, {"course_id": course_id, "link_id": link_id})
        docs = result if result else []

        if not docs:
            return {
                "success": True,
                "documents_deleted": 0,
                "embeddings_deleted": 0,
                "message": "Aucun document trouvé pour ce link_id"
            }

        documents_deleted = 0
        embeddings_deleted = 0
        markdown_files_deleted = []

        # Supprimer chaque document et ses embeddings
        for doc in docs:
            doc_id = str(doc["id"])

            # Supprimer les embeddings associés
            embed_result = await service.db.query(
                "DELETE FROM embedding_chunk WHERE document_id = $doc_id RETURN BEFORE",
                {"doc_id": doc_id}
            )
            if embed_result and len(embed_result) > 0:
                embeddings_deleted += len(embed_result)

            # Si c'est un fichier markdown dérivé, supprimer le fichier du disque
            if doc.get("is_derived") and doc.get("derivation_type") in ["pdf_extraction", "word_extraction", "audio_transcription"]:
                file_path = doc.get("file_path")
                if file_path and Path(file_path).exists():
                    try:
                        Path(file_path).unlink()
                        markdown_files_deleted.append(file_path)
                        logger.info(f"Supprimé le fichier markdown dérivé: {file_path}")
                    except Exception as e:
                        logger.warning(f"Impossible de supprimer le fichier {file_path}: {e}")

            # Supprimer le document de la base de données
            await service.delete(doc_id)
            documents_deleted += 1

        logger.info(f"Liaison {link_id} annulée: {documents_deleted} documents et {embeddings_deleted} embeddings supprimés")

        return {
            "success": True,
            "documents_deleted": documents_deleted,
            "embeddings_deleted": embeddings_deleted,
            "markdown_files_deleted": len(markdown_files_deleted),
            "message": f"Liaison annulée: {documents_deleted} document(s) supprimé(s)"
        }

    except Exception as e:
        logger.error(f"Erreur lors de l'annulation de la liaison: {e}")
        logger.error(f"Traceback complet:\n{traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
