"""
Routes pour la liaison de répertoires locaux dans Legal Assistant.

Endpoints:
- POST /api/linked-directory/scan - Scanne un répertoire et retourne les statistiques
- POST /api/cases/{case_id}/link-directory - Lie et indexe les fichiers d'un répertoire
- POST /api/linked-directory/{link_id}/refresh - Rafraîchit les fichiers d'un répertoire lié
"""

import logging
import hashlib
import os
import uuid
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

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["Linked Directory"])


# ============================================================================
# Pydantic Models
# ============================================================================

class FileInfo(BaseModel):
    """Information sur un fichier trouvé."""
    absolute_path: str
    relative_path: str
    filename: str
    size: int
    modified_time: float
    extension: str
    parent_folder: str  # Chemin relatif du dossier parent


class DirectoryScanResult(BaseModel):
    """Résultat du scan d'un répertoire."""
    base_path: str
    total_files: int
    total_size: int
    files_by_type: Dict[str, int]  # ex: {"pdf": 5, "md": 12, ...}
    files: List[FileInfo]
    folder_structure: Dict[str, int]  # ex: {"contrats/": 5, "jurisprudence/2024/": 8}


class ScanDirectoryRequest(BaseModel):
    """Requête pour scanner un répertoire."""
    directory_path: str


class LinkDirectoryRequest(BaseModel):
    """Requête pour lier un répertoire."""
    directory_path: str
    file_paths: Optional[List[str]] = None  # Si None, importe tous les fichiers trouvés


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

SUPPORTED_EXTENSIONS = {".md", ".mdx", ".pdf", ".txt", ".docx", ".doc"}


def calculate_file_hash(file_path: Path) -> str:
    """Calcule le hash SHA-256 d'un fichier."""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def scan_directory(directory_path: str) -> DirectoryScanResult:
    """
    Scanne un répertoire et retourne les statistiques.

    Args:
        directory_path: Chemin du répertoire à scanner

    Returns:
        DirectoryScanResult avec les statistiques
    """
    base_path = Path(directory_path)

    if not base_path.exists():
        raise ValueError(f"Le répertoire n'existe pas: {directory_path}")

    if not base_path.is_dir():
        raise ValueError(f"Le chemin n'est pas un répertoire: {directory_path}")

    files = []
    total_size = 0
    files_by_type = defaultdict(int)
    folder_structure = defaultdict(int)

    # Parcourir récursivement le répertoire
    for file_path in base_path.rglob("*"):
        # Ignorer les dossiers cachés et node_modules
        if any(part.startswith('.') or part == 'node_modules' for part in file_path.parts):
            continue

        # Ignorer les dossiers
        if file_path.is_dir():
            continue

        # Vérifier l'extension
        extension = file_path.suffix.lower()
        if extension not in SUPPORTED_EXTENSIONS:
            continue

        try:
            stat = file_path.stat()
            relative = file_path.relative_to(base_path)
            parent_folder = str(relative.parent) if str(relative.parent) != '.' else 'root'

            file_info = FileInfo(
                absolute_path=str(file_path),
                relative_path=str(relative),
                filename=file_path.name,
                size=stat.st_size,
                modified_time=stat.st_mtime,
                extension=extension.lstrip('.'),
                parent_folder=parent_folder
            )

            files.append(file_info)
            total_size += stat.st_size
            files_by_type[extension.lstrip('.')] += 1
            folder_structure[parent_folder] += 1

        except Exception as e:
            logger.warning(f"Erreur lors de la lecture du fichier {file_path}: {e}")

    # Trier les fichiers par chemin relatif
    files.sort(key=lambda f: f.relative_path)

    return DirectoryScanResult(
        base_path=str(base_path),
        total_files=len(files),
        total_size=total_size,
        files_by_type=dict(files_by_type),
        files=files,
        folder_structure=dict(folder_structure)
    )


def extract_text_from_file(file_path: Path) -> str:
    """
    Extrait le texte d'un fichier selon son type.

    Args:
        file_path: Chemin du fichier

    Returns:
        Contenu textuel du fichier
    """
    extension = file_path.suffix.lower()

    if extension in [".md", ".mdx", ".txt"]:
        # Fichiers texte : lecture directe
        return file_path.read_text(encoding='utf-8', errors='ignore')

    elif extension == ".pdf":
        # PDF : Pour l'instant, on retourne un placeholder
        # L'extraction PDF sera faite via docling dans un second temps
        return f"[Contenu PDF - {file_path.name}]"

    elif extension in [".docx", ".doc"]:
        # Word : Pour l'instant, on retourne un placeholder
        # L'extraction Word sera faite via python-docx dans un second temps
        return f"[Contenu Word - {file_path.name}]"

    else:
        return ""


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


@router.post("/cases/{case_id}/link-directory")
async def link_directory_endpoint(
    case_id: str,
    request: LinkDirectoryRequest,
    user_id: str = Depends(require_auth)
):
    """
    Lie un répertoire à un dossier et indexe tous les fichiers.

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

        # Normaliser l'ID du dossier
        if not case_id.startswith("case:"):
            case_id = f"case:{case_id}"

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

            # Créer une entrée pour le répertoire lié
            link_id = str(uuid.uuid4())[:8]
            link_metadata = {
                "base_path": scan_result.base_path,
                "linked_at": now,
                "total_files": total,
                "total_size": sum(f.size for f in files_to_index),
                "last_refresh": now
            }

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
                            "case_id": case_id,
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
                                    case_id=case_id,
                                    text_content=content
                                )

                                if result.get("success"):
                                    await service.merge(
                                        f"document:{doc_id}",
                                        {"indexed": True}
                                    )
                            except Exception as e:
                                logger.error(f"Erreur lors de l'indexation du document:{doc_id}: {e}")

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
