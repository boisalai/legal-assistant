"""
Routes pour l'import de documentation Docusaurus dans Legal Assistant.

Endpoints:
- GET /api/docusaurus/list - Liste les fichiers Markdown disponibles
- POST /api/courses/{course_id}/import-docusaurus - Importe des fichiers sélectionnés
- POST /api/courses/{course_id}/check-docusaurus-updates - Vérifie les mises à jour
- POST /api/documents/{doc_id}/reindex-docusaurus - Réindexe un document
"""

import logging
import hashlib
import os
import shutil
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel

from config.settings import settings
from services.surreal_service import get_surreal_service
from services.document_indexing_service import DocumentIndexingService
from models.document_models import DocumentResponse, DocusaurusSource
from auth.helpers import require_auth, get_current_user_id
from utils.text_utils import remove_yaml_frontmatter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["Docusaurus"])

# Chemin par défaut vers la documentation Docusaurus
DOCUSAURUS_BASE_PATH = "/Users/alain/Workspace/Docusaurus/docs"


# ============================================================================
# Pydantic Models
# ============================================================================

class DocusaurusFile(BaseModel):
    """Représentation d'un fichier Docusaurus."""
    absolute_path: str
    relative_path: str
    filename: str
    size: int
    modified_time: float
    folder: str  # Dossier parent (ex: "models", "cours/calcul-quebec")


class DocusaurusListResponse(BaseModel):
    """Réponse pour la liste des fichiers Docusaurus."""
    files: List[DocusaurusFile]
    total: int
    base_path: str


class ImportDocusaurusRequest(BaseModel):
    """Requête pour importer des fichiers Docusaurus."""
    file_paths: List[str]  # Liste de chemins absolus vers les fichiers à importer


class CheckUpdatesResponse(BaseModel):
    """Réponse pour la vérification des mises à jour."""
    documents_checked: int
    documents_needing_update: List[str]  # Liste d'IDs de documents


class ReindexResponse(BaseModel):
    """Réponse pour la réindexation d'un document."""
    success: bool
    document_id: str
    chunks_created: Optional[int] = None
    error: Optional[str] = None


# ============================================================================
# Helper Functions
# ============================================================================

def calculate_file_hash(file_path: Path) -> str:
    """Calcule le hash SHA-256 d'un fichier."""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def scan_docusaurus_files(base_path: str = DOCUSAURUS_BASE_PATH) -> List[DocusaurusFile]:
    """
    Scanne le répertoire Docusaurus pour trouver tous les fichiers Markdown.

    Args:
        base_path: Chemin de base vers la documentation Docusaurus

    Returns:
        Liste de DocusaurusFile
    """
    files = []
    base = Path(base_path)

    if not base.exists():
        logger.warning(f"Docusaurus base path does not exist: {base_path}")
        return files

    # Trouver tous les fichiers .md et .mdx
    for file_path in base.rglob("*.md"):
        # Ignorer node_modules et autres dossiers cachés
        if any(part.startswith('.') or part == 'node_modules' for part in file_path.parts):
            continue

        try:
            stat = file_path.stat()
            relative = file_path.relative_to(base)
            folder = str(relative.parent) if str(relative.parent) != '.' else 'root'

            files.append(DocusaurusFile(
                absolute_path=str(file_path),
                relative_path=str(relative),
                filename=file_path.name,
                size=stat.st_size,
                modified_time=stat.st_mtime,
                folder=folder
            ))
        except Exception as e:
            logger.warning(f"Error reading file {file_path}: {e}")

    # Même chose pour .mdx
    for file_path in base.rglob("*.mdx"):
        if any(part.startswith('.') or part == 'node_modules' for part in file_path.parts):
            continue

        try:
            stat = file_path.stat()
            relative = file_path.relative_to(base)
            folder = str(relative.parent) if str(relative.parent) != '.' else 'root'

            files.append(DocusaurusFile(
                absolute_path=str(file_path),
                relative_path=str(relative),
                filename=file_path.name,
                size=stat.st_size,
                modified_time=stat.st_mtime,
                folder=folder
            ))
        except Exception as e:
            logger.warning(f"Error reading file {file_path}: {e}")

    # Trier par chemin relatif
    files.sort(key=lambda f: f.relative_path)

    return files


# ============================================================================
# Endpoints
# ============================================================================

@router.get("/docusaurus/list", response_model=DocusaurusListResponse)
async def list_docusaurus_files(
    base_path: Optional[str] = None,
    user_id: Optional[str] = Depends(get_current_user_id)
):
    """
    Liste tous les fichiers Markdown disponibles dans la documentation Docusaurus.

    Args:
        base_path: Chemin personnalisé vers la doc (optionnel)
    """
    try:
        path = base_path or DOCUSAURUS_BASE_PATH
        files = scan_docusaurus_files(path)

        return DocusaurusListResponse(
            files=files,
            total=len(files),
            base_path=path
        )
    except Exception as e:
        logger.error(f"Error listing Docusaurus files: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/courses/{course_id}/import-docusaurus", response_model=List[DocumentResponse])
async def import_docusaurus_files(
    course_id: str,
    request: ImportDocusaurusRequest,
    user_id: str = Depends(require_auth)
):
    """
    Importe des fichiers Docusaurus sélectionnés dans un dossier.

    Pour chaque fichier :
    1. Lit le contenu
    2. Calcule le hash SHA-256
    3. Copie le fichier dans data/uploads/{course_id}/
    4. Crée un document dans SurrealDB avec les métadonnées Docusaurus
    5. Indexe le contenu pour la recherche sémantique

    Args:
        course_id: ID du dossier
        request: Liste des chemins de fichiers à importer
    """
    try:
        service = get_surreal_service()
        if not service.db:
            await service.connect()

        # Normaliser l'ID du dossier
        if not course_id.startswith("course:"):
            course_id = f"course:{course_id}"

        # Créer le répertoire d'upload
        upload_dir = Path(settings.upload_dir) / course_id.replace("course:", "")
        upload_dir.mkdir(parents=True, exist_ok=True)

        imported_documents = []
        now = datetime.utcnow().isoformat()

        for file_path_str in request.file_paths:
            try:
                source_file = Path(file_path_str)

                # Vérifier que le fichier existe
                if not source_file.exists():
                    logger.warning(f"File not found: {file_path_str}")
                    continue

                # Lire le contenu et calculer le hash
                raw_content = source_file.read_text(encoding='utf-8')
                # Retirer le frontmatter YAML (métadonnées Docusaurus)
                content = remove_yaml_frontmatter(raw_content)
                file_hash = calculate_file_hash(source_file)
                file_stat = source_file.stat()

                # Générer un ID unique pour le document
                doc_id = str(uuid.uuid4())[:8]

                # Copier le fichier dans le dossier d'upload
                dest_file = upload_dir / f"{doc_id}{source_file.suffix}"
                shutil.copy2(source_file, dest_file)

                # Calculer le chemin relatif depuis la base Docusaurus
                try:
                    relative_path = str(source_file.relative_to(DOCUSAURUS_BASE_PATH))
                except ValueError:
                    # Si le fichier n'est pas dans DOCUSAURUS_BASE_PATH, utiliser le nom
                    relative_path = source_file.name

                # Créer les métadonnées Docusaurus
                docusaurus_source = {
                    "absolute_path": str(source_file),
                    "relative_path": relative_path,
                    "last_sync": now,
                    "source_hash": file_hash,
                    "source_mtime": file_stat.st_mtime,
                    "needs_reindex": False
                }

                # Créer le document dans SurrealDB
                document_data = {
                    "course_id": course_id,
                    "nom_fichier": source_file.name,
                    "type_fichier": source_file.suffix.lstrip('.'),
                    "type_mime": "text/markdown",
                    "taille": file_stat.st_size,
                    "file_path": str(dest_file),
                    "user_id": user_id,
                    "created_at": now,
                    "source_type": "docusaurus",
                    "docusaurus_source": docusaurus_source,
                    "texte_extrait": content,  # Stocker le contenu directement
                    "indexed": False  # Sera mis à True après indexation
                }

                await service.create("document", document_data, record_id=doc_id)
                logger.info(f"Imported Docusaurus file: {source_file.name} -> document:{doc_id}")

                # Indexer le document pour la recherche sémantique
                try:
                    indexing_service = DocumentIndexingService()
                    result = await indexing_service.index_document(
                        document_id=f"document:{doc_id}",
                        course_id=course_id,
                        text_content=content
                    )

                    if result.get("success"):
                        # Marquer comme indexé
                        await service.merge(
                            f"document:{doc_id}",
                            {"indexed": True}
                        )
                        logger.info(f"Indexed document:{doc_id} with {result.get('chunks_created', 0)} chunks")
                except Exception as e:
                    logger.error(f"Error indexing document:{doc_id}: {e}")

                # Ajouter à la liste des résultats
                imported_documents.append(DocumentResponse(
                    id=f"document:{doc_id}",
                    course_id=course_id,
                    nom_fichier=source_file.name,
                    type_fichier=source_file.suffix.lstrip('.'),
                    type_mime="text/markdown",
                    taille=file_stat.st_size,
                    file_path=str(dest_file),
                    created_at=now,
                    source_type="docusaurus",
                    docusaurus_source=DocusaurusSource(**docusaurus_source),
                    texte_extrait=content[:500] + "..." if len(content) > 500 else content,
                    indexed=True,
                    file_exists=True
                ))

            except Exception as e:
                logger.error(f"Error importing file {file_path_str}: {e}")
                continue

        return imported_documents

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error importing Docusaurus files: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/courses/{course_id}/check-docusaurus-updates", response_model=CheckUpdatesResponse)
async def check_docusaurus_updates(
    course_id: str,
    user_id: Optional[str] = Depends(get_current_user_id)
):
    """
    Vérifie si les fichiers Docusaurus sources ont été modifiés.

    Compare le mtime actuel avec celui stocké lors de l'import.
    Si différent, marque le document comme nécessitant une réindexation.

    Args:
        course_id: ID du dossier
    """
    try:
        service = get_surreal_service()
        if not service.db:
            await service.connect()

        # Normaliser l'ID du dossier
        if not course_id.startswith("course:"):
            course_id = f"course:{course_id}"

        # Récupérer tous les documents Docusaurus du dossier
        result = await service.query(
            """
            SELECT * FROM document
            WHERE course_id = $course_id
            AND source_type = 'docusaurus'
            """,
            {"course_id": course_id}
        )

        documents_checked = 0
        documents_needing_update = []

        if result and len(result) > 0:
            for doc in result:
                documents_checked += 1
                doc_id = str(doc.get("id", ""))
                docusaurus_source = doc.get("docusaurus_source", {})

                if not docusaurus_source:
                    continue

                source_path = Path(docusaurus_source.get("absolute_path", ""))
                stored_mtime = docusaurus_source.get("source_mtime", 0)

                # Vérifier si le fichier source existe encore
                if not source_path.exists():
                    logger.warning(f"Source file no longer exists: {source_path}")
                    continue

                # Comparer le mtime
                current_mtime = source_path.stat().st_mtime

                if current_mtime != stored_mtime:
                    # Le fichier a été modifié
                    logger.info(f"Document {doc_id} needs update (mtime changed)")

                    # Mettre à jour needs_reindex
                    docusaurus_source["needs_reindex"] = True
                    await service.merge(doc_id, {
                        "docusaurus_source": docusaurus_source
                    })

                    documents_needing_update.append(doc_id)

        return CheckUpdatesResponse(
            documents_checked=documents_checked,
            documents_needing_update=documents_needing_update
        )

    except Exception as e:
        logger.error(f"Error checking Docusaurus updates: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/documents/{doc_id}/reindex-docusaurus", response_model=ReindexResponse)
async def reindex_docusaurus_document(
    doc_id: str,
    user_id: str = Depends(require_auth)
):
    """
    Réindexe un document Docusaurus depuis son fichier source.

    1. Lit le fichier source actuel
    2. Recalcule le hash
    3. Met à jour le contenu dans la base de données
    4. Réindexe les embeddings
    5. Met à jour les métadonnées (last_sync, source_hash, source_mtime)

    Args:
        doc_id: ID du document
    """
    try:
        service = get_surreal_service()
        if not service.db:
            await service.connect()

        # Normaliser l'ID du document
        if not doc_id.startswith("document:"):
            doc_id = f"document:{doc_id}"

        # Récupérer le document
        result = await service.select(doc_id)

        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document not found: {doc_id}"
            )

        # Vérifier que c'est un document Docusaurus
        if result.get("source_type") != "docusaurus":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This is not a Docusaurus document"
            )

        docusaurus_source = result.get("docusaurus_source", {})
        source_path = Path(docusaurus_source.get("absolute_path", ""))

        # Vérifier que le fichier source existe
        if not source_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Source file not found: {source_path}"
            )

        # Lire le nouveau contenu
        raw_content = source_path.read_text(encoding='utf-8')
        # Retirer le frontmatter YAML (métadonnées Docusaurus)
        content = remove_frontmatter(raw_content)
        new_hash = calculate_file_hash(source_path)
        new_mtime = source_path.stat().st_mtime
        now = datetime.utcnow().isoformat()

        # Mettre à jour les métadonnées
        docusaurus_source["last_sync"] = now
        docusaurus_source["source_hash"] = new_hash
        docusaurus_source["source_mtime"] = new_mtime
        docusaurus_source["needs_reindex"] = False

        # Mettre à jour le document
        await service.merge(doc_id, {
            "texte_extrait": content,
            "docusaurus_source": docusaurus_source,
            "indexed": False  # Sera mis à True après réindexation
        })

        # Réindexer le document
        indexing_service = DocumentIndexingService()
        result = await indexing_service.index_document(
            document_id=doc_id,
            course_id=result.get("course_id"),
            text_content=content,
            force_reindex=True  # Forcer la réindexation
        )

        if result.get("success"):
            # Marquer comme indexé
            await service.merge(doc_id, {"indexed": True})
            logger.info(f"Reindexed {doc_id} with {result.get('chunks_created', 0)} chunks")

            return ReindexResponse(
                success=True,
                document_id=doc_id,
                chunks_created=result.get("chunks_created")
            )
        else:
            return ReindexResponse(
                success=False,
                document_id=doc_id,
                error=result.get("error", "Unknown error")
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error reindexing document {doc_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
