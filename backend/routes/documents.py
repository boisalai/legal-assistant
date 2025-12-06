"""
Routes pour la gestion des documents d'un dossier.

Endpoints:
- GET /api/cases/{case_id}/documents - Liste des documents
- POST /api/cases/{case_id}/documents - Upload d'un document
- GET /api/cases/{case_id}/documents/{doc_id} - Details d'un document
- DELETE /api/cases/{case_id}/documents/{doc_id} - Supprimer un document
- GET /api/cases/{case_id}/documents/{doc_id}/download - Telecharger un document
"""

import logging
import uuid
import mimetypes
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Optional, List

from fastapi import APIRouter, HTTPException, status, UploadFile, File, Depends
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel

from config.settings import settings
from services.surreal_service import get_surreal_service
from services.document_indexing_service import DocumentIndexingService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/cases", tags=["Documents"])

# Import auth helpers
from auth.helpers import require_auth, get_current_user_id

# Allowed file types
ALLOWED_EXTENSIONS = {
    '.pdf': 'application/pdf',
    '.doc': 'application/msword',
    '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    '.txt': 'text/plain',
    '.md': 'text/markdown',
    '.mdx': 'text/markdown',  # MDX (Markdown + JSX)
    '.mp3': 'audio/mpeg',
    '.wav': 'audio/wav',
    '.m4a': 'audio/mp4',
    '.ogg': 'audio/ogg',
    '.webm': 'audio/webm',
}

# Types de fichiers supportés pour les liens (fichiers/dossiers)
LINKABLE_EXTENSIONS = {'.md', '.mdx', '.pdf', '.txt', '.docx'}

MAX_FILE_SIZE = 500 * 1024 * 1024  # 500MB - Pour supporter les enregistrements audio de 3h+
MAX_LINKED_FILES = 50  # Limite de fichiers lors de la liaison d'un dossier


# ============================================================================
# Pydantic Models
# ============================================================================

class DocumentResponse(BaseModel):
    id: str
    case_id: str
    nom_fichier: str
    type_fichier: str
    type_mime: str
    taille: int
    file_path: str
    created_at: str
    texte_extrait: Optional[str] = None
    file_exists: bool = True  # Whether the file exists on disk
    source_document_id: Optional[str] = None  # ID of parent document if this is derived
    is_derived: Optional[bool] = None  # True if this is a derived file
    derivation_type: Optional[str] = None  # transcription, pdf_extraction, tts
    source_type: Optional[str] = None  # "upload" or "docusaurus"
    docusaurus_source: Optional[dict] = None  # Info Docusaurus si applicable
    indexed: Optional[bool] = None  # True si le document a été indexé pour RAG


class DocumentListResponse(BaseModel):
    documents: list[DocumentResponse]
    total: int
    missing_files: list[str] = []  # List of document IDs with missing files


class RegisterDocumentRequest(BaseModel):
    """Request to register a document by file path (no upload/copy)."""
    file_path: str  # Absolute path to the file on disk


class LinkPathRequest(BaseModel):
    """Request to link a file or folder."""
    path: str  # Absolute path to file or folder


class LinkPathResponse(BaseModel):
    """Response for link operation."""
    success: bool
    linked_count: int
    documents: List[DocumentResponse]
    warnings: Optional[List[str]] = None


# ============================================================================
# Helper Functions
# ============================================================================

def calculate_file_hash(file_path: Path) -> str:
    """Calculate SHA-256 hash of a file."""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def get_file_extension(filename: str) -> str:
    """Get file extension from filename."""
    return Path(filename).suffix.lower()


def is_allowed_file(filename: str) -> bool:
    """Check if file extension is allowed."""
    ext = get_file_extension(filename)
    return ext in ALLOWED_EXTENSIONS


def is_linkable_file(filename: str) -> bool:
    """Check if file can be linked (for folder linking)."""
    ext = get_file_extension(filename)
    return ext in LINKABLE_EXTENSIONS


def scan_folder_for_files(folder_path: Path, max_files: int = MAX_LINKED_FILES) -> List[Path]:
    """
    Scan a folder for linkable files (non-recursive).

    Returns list of file paths, limited to max_files.
    Filters by LINKABLE_EXTENSIONS.
    """
    files = []

    try:
        for item in folder_path.iterdir():
            if len(files) >= max_files:
                break

            # Skip hidden files and directories
            if item.name.startswith('.'):
                continue

            # Only process files (not subdirectories)
            if item.is_file() and is_linkable_file(item.name):
                files.append(item)
    except Exception as e:
        logger.error(f"Error scanning folder {folder_path}: {e}")

    return sorted(files, key=lambda p: p.name)


def get_mime_type(filename: str) -> str:
    """Get MIME type from filename."""
    ext = get_file_extension(filename)
    return ALLOWED_EXTENSIONS.get(ext, 'application/octet-stream')


# ============================================================================
# Endpoints
# ============================================================================

@router.get("/{case_id}/documents", response_model=DocumentListResponse)
async def list_documents(
    case_id: str,
    verify_files: bool = True,
    auto_remove_missing: bool = True,
    auto_discover: bool = False,  # Désactivé par défaut pour éviter les duplicatas
    include_derived: bool = True,  # Inclure les fichiers dérivés par défaut (filtrage dans le frontend)
    user_id: Optional[str] = Depends(get_current_user_id)
):
    """
    Liste les documents d'un dossier.

    Args:
        case_id: ID du dossier
        verify_files: Si True, verifie que les fichiers existent sur le disque
        auto_remove_missing: Si True, supprime automatiquement les documents dont le fichier n'existe plus
        auto_discover: Si True, découvre et enregistre automatiquement les fichiers orphelins dans /data/uploads/[id]/
        include_derived: Si True, inclut les fichiers dérivés (transcriptions, extractions, TTS). Par défaut False.
    """
    try:
        service = get_surreal_service()
        if not service.db:
            await service.connect()

        # Normalize case ID
        if not case_id.startswith("case:"):
            case_id = f"case:{case_id}"

        # Query documents for this case
        # TEMPORARY: Support both "case:" and "judgment:" formats during migration
        legacy_case_id = case_id.replace("case:", "judgment:")

        if include_derived:
            # Include all documents
            result = await service.query(
                "SELECT * FROM document WHERE case_id IN [$case_id, $legacy_case_id] ORDER BY created_at DESC",
                {"case_id": case_id, "legacy_case_id": legacy_case_id}
            )
        else:
            # Exclude derived documents (only show source documents)
            # Use "!= true" instead of "= false OR IS NULL" for SurrealDB compatibility
            result = await service.query(
                "SELECT * FROM document WHERE case_id IN [$case_id, $legacy_case_id] AND is_derived != true ORDER BY created_at DESC",
                {"case_id": case_id, "legacy_case_id": legacy_case_id}
            )

        # Unwrap SurrealDB query result
        # SurrealDB query() can return results in different formats:
        # 1. Direct list of documents: [doc1, doc2, doc3]
        # 2. Wrapped format: [{result: [doc1, doc2, doc3]}]
        items = []
        if result and len(result) > 0:
            first_result = result[0]
            # Check if it's the wrapped format with "result" key
            if isinstance(first_result, dict) and "result" in first_result:
                items = first_result["result"]
            # Otherwise, assume it's already a direct list of documents
            elif isinstance(result, list):
                items = result

        logger.info(f"GET /documents unwrapped result: {len(items)} documents")
        logger.info(f"Query case_id: {case_id}, legacy_case_id: {legacy_case_id}")
        logger.info(f"Raw query result: {result}")
        if items and len(items) > 0:
            logger.info(f"First 3 documents from unwrapped result:")
            for doc in items[:3]:
                logger.info(f"  - {doc.get('nom_fichier')} (case_id: {doc.get('case_id')}, source_type: {doc.get('source_type')})")

        documents = []
        missing_files = []
        docs_to_remove = []
        registered_files = set()  # Track files already in database (by absolute path)
        registered_filenames = set()  # Track filenames already in database (fallback check)

        if items and len(items) > 0:
            if isinstance(items, list):
                for item in items:
                    file_path = item.get("file_path", "")
                    file_exists = True

                    # Check if file exists on disk
                    if verify_files and file_path:
                        file_exists = Path(file_path).exists()
                        if not file_exists:
                            doc_id = str(item.get("id", ""))
                            missing_files.append(doc_id)
                            if auto_remove_missing:
                                docs_to_remove.append(doc_id)
                                continue  # Skip adding to response

                    # Track this file as registered (both by absolute path and filename)
                    if file_path:
                        # Try to resolve to absolute path, handle both relative and absolute paths
                        try:
                            abs_path = Path(file_path).resolve()
                            registered_files.add(abs_path)
                        except Exception:
                            # If path resolution fails, just add as-is
                            registered_files.add(Path(file_path))

                        # Also track by filename as a fallback
                        registered_filenames.add(item.get("nom_fichier", ""))

                    documents.append(DocumentResponse(
                        id=str(item.get("id", "")),
                        case_id=item.get("case_id", case_id),
                        nom_fichier=item.get("nom_fichier", ""),
                        type_fichier=item.get("type_fichier", ""),
                        type_mime=item.get("type_mime", ""),
                        taille=item.get("taille", 0),
                        file_path=file_path,
                        created_at=item.get("created_at", ""),
                        texte_extrait=item.get("texte_extrait"),
                        file_exists=file_exists,
                        source_document_id=item.get("source_document_id"),
                        is_derived=item.get("is_derived"),
                        derivation_type=item.get("derivation_type"),
                        source_type=item.get("source_type"),
                        docusaurus_source=item.get("docusaurus_source"),
                        indexed=item.get("indexed"),
                    ))

        # Auto-remove documents with missing files
        if docs_to_remove:
            for doc_id in docs_to_remove:
                try:
                    await service.delete(doc_id)
                    logger.info(f"Auto-removed document with missing file: {doc_id}")
                except Exception as e:
                    logger.warning(f"Could not auto-remove document {doc_id}: {e}")

        # Auto-discover orphaned files in uploads directory
        if auto_discover:
            upload_dir = Path(settings.upload_dir) / case_id.replace("case:", "")
            if upload_dir.exists() and upload_dir.is_dir():
                for file_path in upload_dir.iterdir():
                    if file_path.is_file():
                        # Check if this file is already registered (by path OR by filename)
                        is_registered = (
                            file_path.resolve() in registered_files or
                            file_path.name in registered_filenames
                        )
                        if not is_registered:
                            # Skip markdown files - they are always derived files (transcriptions/extractions)
                            # and should be created by the transcription/extraction workflows
                            ext = get_file_extension(file_path.name).lower()
                            if ext in ['.md', '.markdown']:
                                logger.debug(f"Skipping auto-discovery of markdown file (derived file): {file_path.name}")
                                continue

                            # Check if file type is allowed
                            if is_allowed_file(file_path.name):
                                try:
                                    # Auto-register this orphaned file
                                    doc_id = str(uuid.uuid4())[:8]
                                    ext = get_file_extension(file_path.name)
                                    file_size = file_path.stat().st_size
                                    now = datetime.utcnow().isoformat()

                                    # Use relative path (consistent with upload endpoint)
                                    relative_path = f"data/uploads/{case_id.replace('case:', '')}/{file_path.name}"

                                    document_data = {
                                        "case_id": case_id,
                                        "nom_fichier": file_path.name,
                                        "type_fichier": ext.lstrip('.'),
                                        "type_mime": get_mime_type(file_path.name),
                                        "taille": file_size,
                                        "file_path": relative_path,
                                        "user_id": user_id or "system",
                                        "created_at": now,
                                        "auto_discovered": True,  # Flag to indicate this was auto-discovered
                                        "is_derived": False,  # Source documents are not derived
                                    }

                                    await service.create("document", document_data, record_id=doc_id)
                                    logger.info(f"Auto-discovered and registered file: {file_path.name}")

                                    # Add to response
                                    documents.append(DocumentResponse(
                                        id=f"document:{doc_id}",
                                        case_id=case_id,
                                        nom_fichier=file_path.name,
                                        type_fichier=ext.lstrip('.'),
                                        type_mime=get_mime_type(file_path.name),
                                        taille=file_size,
                                        file_path=relative_path,
                                        created_at=now,
                                        file_exists=True,
                                        source_document_id=None,
                                        is_derived=False,
                                        derivation_type=None,
                                    ))
                                except Exception as e:
                                    logger.warning(f"Could not auto-register file {file_path.name}: {e}")

        # Sort documents by created_at descending
        documents.sort(key=lambda d: d.created_at, reverse=True)

        return DocumentListResponse(
            documents=documents,
            total=len(documents),
            missing_files=missing_files
        )

    except Exception as e:
        logger.error(f"Error listing documents: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/{case_id}/documents", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    case_id: str,
    file: UploadFile = File(...),
    user_id: str = Depends(require_auth)
):
    """
    Upload un document pour un dossier.
    Accepte: PDF, Word, TXT, Markdown, Audio (MP3, WAV, M4A)
    """
    # Validate file type
    if not file.filename or not is_allowed_file(file.filename):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Type de fichier non supporte. Extensions acceptees: {', '.join(ALLOWED_EXTENSIONS.keys())}"
        )

    # Read file content
    content = await file.read()

    # Check file size
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Fichier trop volumineux. Taille max: {MAX_FILE_SIZE // (1024*1024)} MB"
        )

    try:
        service = get_surreal_service()
        if not service.db:
            await service.connect()

        # Normalize case ID
        if not case_id.startswith("case:"):
            case_id = f"case:{case_id}"

        # Generate document ID and save file
        doc_id = str(uuid.uuid4())[:8]
        ext = get_file_extension(file.filename)

        # Create upload directory
        upload_dir = Path(settings.upload_dir) / case_id.replace("case:", "")
        upload_dir.mkdir(parents=True, exist_ok=True)

        # Save file
        file_path = str(upload_dir / f"{doc_id}{ext}")
        with open(file_path, "wb") as f:
            f.write(content)

        logger.info(f"Document saved: {file_path}")

        # Create document record in database
        now = datetime.utcnow().isoformat()
        document_data = {
            "case_id": case_id,
            "nom_fichier": file.filename,
            "type_fichier": ext.lstrip('.'),
            "type_mime": get_mime_type(file.filename),
            "taille": len(content),
            "file_path": file_path,
            "user_id": user_id,
            "created_at": now,
            "source_type": "upload",
        }

        await service.create("document", document_data, record_id=doc_id)
        logger.info(f"Document record created: {doc_id}")

        return DocumentResponse(
            id=f"document:{doc_id}",
            case_id=case_id,
            nom_fichier=file.filename,
            type_fichier=ext.lstrip('.'),
            type_mime=get_mime_type(file.filename),
            taille=len(content),
            file_path=file_path,
            created_at=now,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading document: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/{case_id}/documents/register", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def register_document(
    case_id: str,
    request: RegisterDocumentRequest,
    user_id: str = Depends(require_auth)
):
    """
    Enregistre un document par son chemin de fichier (sans copie).

    Le fichier reste a son emplacement d'origine sur le disque.
    L'application stocke uniquement une reference vers ce fichier.
    Le texte est automatiquement extrait pour permettre l'analyse par l'IA.
    """
    file_path = Path(request.file_path)

    # Verify file exists
    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Le fichier n'existe pas: {request.file_path}"
        )

    if not file_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Le chemin n'est pas un fichier: {request.file_path}"
        )

    # Check file type
    filename = file_path.name
    if not is_allowed_file(filename):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Type de fichier non supporte. Extensions acceptees: {', '.join(ALLOWED_EXTENSIONS.keys())}"
        )

    try:
        service = get_surreal_service()
        if not service.db:
            await service.connect()

        # Normalize case ID
        if not case_id.startswith("case:"):
            case_id = f"case:{case_id}"

        # Get file info
        file_size = file_path.stat().st_size
        ext = get_file_extension(filename)

        # Check file size
        if file_size > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Fichier trop volumineux. Taille max: {MAX_FILE_SIZE // (1024*1024)} MB"
            )

        # Generate document ID
        doc_id = str(uuid.uuid4())[:8]

        # NOTE: No automatic text extraction on file registration
        # User must explicitly trigger extraction/transcription via the UI or assistant

        # Create document record in database (no file copy!)
        now = datetime.utcnow().isoformat()
        document_data = {
            "case_id": case_id,
            "nom_fichier": filename,
            "type_fichier": ext.lstrip('.'),
            "type_mime": get_mime_type(filename),
            "taille": file_size,
            "file_path": str(file_path.absolute()),  # Store absolute path
            "user_id": user_id,
            "created_at": now,
        }

        await service.create("document", document_data, record_id=doc_id)
        logger.info(f"Document registered (no copy): {doc_id} -> {file_path}")

        return DocumentResponse(
            id=f"document:{doc_id}",
            case_id=case_id,
            nom_fichier=filename,
            type_fichier=ext.lstrip('.'),
            type_mime=get_mime_type(filename),
            taille=file_size,
            file_path=str(file_path.absolute()),
            created_at=now,
            file_exists=True,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error registering document: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/{case_id}/documents/link", response_model=LinkPathResponse, status_code=status.HTTP_201_CREATED)
async def link_file_or_folder(
    case_id: str,
    request: LinkPathRequest,
    user_id: str = Depends(require_auth)
):
    """
    Lie un fichier ou un dossier sans copie.

    - Si le chemin est un fichier : lie ce fichier uniquement
    - Si le chemin est un dossier : lie tous les fichiers supportés du dossier (non-récursif)

    Les fichiers sont référencés à leur emplacement d'origine.
    Un hash SHA-256 et mtime sont stockés pour détecter les modifications.

    Types supportés : .md, .mdx, .pdf, .txt, .docx
    Limite : 50 fichiers maximum par dossier
    """
    path = Path(request.path)
    warnings = []
    linked_documents = []

    # Verify path exists
    if not path.exists():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Le chemin n'existe pas : {request.path}"
        )

    try:
        service = get_surreal_service()
        if not service.db:
            await service.connect()

        # Normalize case ID (must match GET endpoint normalization)
        if not case_id.startswith("case:"):
            case_id = f"case:{case_id}"

        # Determine if path is file or folder
        files_to_link = []

        if path.is_file():
            # Single file
            if not is_linkable_file(path.name):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Type de fichier non supporté. Extensions acceptées : {', '.join(LINKABLE_EXTENSIONS)}"
                )
            files_to_link = [path]

        elif path.is_dir():
            # Folder - scan for files
            files_to_link = scan_folder_for_files(path, MAX_LINKED_FILES)

            if len(files_to_link) == 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Aucun fichier supporté trouvé dans ce dossier. Extensions acceptées : {', '.join(LINKABLE_EXTENSIONS)}"
                )

            if len(files_to_link) == MAX_LINKED_FILES:
                warnings.append(f"Limite de {MAX_LINKED_FILES} fichiers atteinte. Certains fichiers ont été ignorés.")

        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Le chemin n'est ni un fichier ni un dossier"
            )

        # Link each file
        now = datetime.utcnow().isoformat()

        for file_path in files_to_link:
            try:
                # Get file info
                file_stat = file_path.stat()
                file_size = file_stat.st_size
                ext = get_file_extension(file_path.name)

                # Check file size
                if file_size > MAX_FILE_SIZE:
                    warnings.append(f"Fichier ignoré (trop volumineux) : {file_path.name}")
                    continue

                # Calculate hash and get mtime
                file_hash = calculate_file_hash(file_path)
                file_mtime = file_stat.st_mtime

                # Generate document ID
                doc_id = str(uuid.uuid4())[:8]

                # Create linked source metadata
                linked_source = {
                    "absolute_path": str(file_path.absolute()),
                    "last_sync": now,
                    "source_hash": file_hash,
                    "source_mtime": file_mtime,
                    "needs_reindex": False
                }

                # Read file content for text files
                texte_extrait = None
                if ext in {'.md', '.mdx', '.txt'}:
                    try:
                        texte_extrait = file_path.read_text(encoding='utf-8')
                    except Exception as e:
                        logger.warning(f"Could not read text from {file_path}: {e}")

                # Create document record
                document_data = {
                    "case_id": case_id,
                    "nom_fichier": file_path.name,
                    "type_fichier": ext.lstrip('.'),
                    "type_mime": get_mime_type(file_path.name),
                    "taille": file_size,
                    "file_path": str(file_path.absolute()),
                    "user_id": user_id,
                    "created_at": now,
                    "source_type": "linked",
                    "linked_source": linked_source,
                    "texte_extrait": texte_extrait,
                    "indexed": False  # Will be set to True after indexing
                }

                created_doc = await service.create("document", document_data, record_id=doc_id)
                logger.info(f"Linked file: {file_path.name} -> document:{doc_id}")
                logger.info(f"Created document in DB: {created_doc}")
                logger.info(f"Document case_id: {document_data['case_id']}")

                # Index text content if available
                if texte_extrait:
                    try:
                        indexing_service = DocumentIndexingService()
                        result = await indexing_service.index_document(
                            document_id=f"document:{doc_id}",
                            case_id=case_id,
                            text_content=texte_extrait
                        )

                        if result.get("success"):
                            await service.merge(f"document:{doc_id}", {"indexed": True})
                            logger.info(f"Indexed document:{doc_id} with {result.get('chunks_created', 0)} chunks")
                    except Exception as e:
                        logger.error(f"Error indexing document:{doc_id}: {e}")

                # Add to response
                linked_documents.append(DocumentResponse(
                    id=f"document:{doc_id}",
                    case_id=case_id,
                    nom_fichier=file_path.name,
                    type_fichier=ext.lstrip('.'),
                    type_mime=get_mime_type(file_path.name),
                    taille=file_size,
                    file_path=str(file_path.absolute()),
                    created_at=now,
                    source_type="linked",
                    texte_extrait=texte_extrait[:500] + "..." if texte_extrait and len(texte_extrait) > 500 else texte_extrait,
                    indexed=texte_extrait is not None,
                    file_exists=True
                ))

            except Exception as e:
                logger.error(f"Error linking file {file_path}: {e}")
                warnings.append(f"Erreur lors de la liaison de {file_path.name} : {str(e)}")

        if len(linked_documents) == 0:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Aucun fichier n'a pu être lié. Vérifiez les warnings."
            )

        return LinkPathResponse(
            success=True,
            linked_count=len(linked_documents),
            documents=linked_documents,
            warnings=warnings if warnings else None
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error linking path: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/{case_id}/documents/{doc_id}/derived")
async def get_derived_documents(
    case_id: str,
    doc_id: str,
    user_id: Optional[str] = Depends(get_current_user_id)
):
    """
    Récupère tous les fichiers dérivés d'un document source.

    Retourne les transcriptions, extractions PDF, fichiers TTS, etc.
    créés à partir du document spécifié.
    """
    try:
        service = get_surreal_service()
        if not service.db:
            await service.connect()

        # Normalize IDs
        if not case_id.startswith("case:"):
            case_id = f"case:{case_id}"
        if not doc_id.startswith("document:"):
            doc_id = f"document:{doc_id}"

        # Query derived documents
        result = await service.query(
            "SELECT * FROM document WHERE source_document_id = $doc_id ORDER BY created_at DESC",
            {"doc_id": doc_id}
        )

        derived = []
        if result and len(result) > 0:
            # SurrealDB query() returns a list of results directly
            items = result
            if isinstance(items, list):
                for item in items:
                    file_path = item.get("file_path", "")
                    file_exists = Path(file_path).exists() if file_path else False

                    derived.append(DocumentResponse(
                        id=str(item.get("id", "")),
                        case_id=item.get("case_id", case_id),
                        nom_fichier=item.get("nom_fichier", ""),
                        type_fichier=item.get("type_fichier", ""),
                        type_mime=item.get("type_mime", ""),
                        taille=item.get("taille", 0),
                        file_path=file_path,
                        created_at=item.get("created_at", ""),
                        texte_extrait=item.get("texte_extrait"),
                        file_exists=file_exists,
                        source_document_id=item.get("source_document_id"),
                        is_derived=item.get("is_derived"),
                        derivation_type=item.get("derivation_type"),
                    ))

        return {"derived": derived, "total": len(derived)}

    except Exception as e:
        logger.error(f"Error getting derived documents: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/{case_id}/documents/{doc_id}", response_model=DocumentResponse)
async def get_document(
    case_id: str,
    doc_id: str,
    user_id: Optional[str] = Depends(get_current_user_id)
):
    """
    Recupere les details d'un document.
    """
    try:
        service = get_surreal_service()
        if not service.db:
            await service.connect()

        # Normalize IDs
        if not case_id.startswith("case:"):
            case_id = f"case:{case_id}"
        if not doc_id.startswith("document:"):
            doc_id = f"document:{doc_id}"

        # Query document
        clean_id = doc_id.replace("document:", "")
        result = await service.query(
            "SELECT * FROM document WHERE id = type::thing('document', $doc_id)",
            {"doc_id": clean_id}
        )

        if not result or len(result) == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document non trouve"
            )

        # SurrealDB query() returns a list of results directly
        items = result
        if not items or len(items) == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document non trouve"
            )

        item = items[0]

        return DocumentResponse(
            id=str(item.get("id", doc_id)),
            case_id=item.get("case_id", case_id),
            nom_fichier=item.get("nom_fichier", ""),
            type_fichier=item.get("type_fichier", ""),
            type_mime=item.get("type_mime", ""),
            taille=item.get("taille", 0),
            file_path=item.get("file_path", ""),
            created_at=item.get("created_at", ""),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting document: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.delete("/{case_id}/documents/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    case_id: str,
    doc_id: str,
    filename: Optional[str] = None,
    file_path: Optional[str] = None,
    user_id: str = Depends(require_auth)
):
    """
    Supprime un document.

    Args:
        filename: Optional - nom du fichier à supprimer (utilisé si le document n'est pas en base)
        file_path: Optional - chemin complet du fichier à supprimer (utilisé si le document n'est pas en base)
    """
    try:
        service = get_surreal_service()
        if not service.db:
            await service.connect()

        # Normalize IDs
        if not case_id.startswith("case:"):
            case_id = f"case:{case_id}"
        if not doc_id.startswith("document:"):
            doc_id = f"document:{doc_id}"

        # Get document to find file path
        clean_id = doc_id.replace("document:", "")
        logger.info(f"Attempting to delete document with ID: {doc_id} (clean: {clean_id})")

        result = await service.query(
            "SELECT * FROM document WHERE id = type::thing('document', $doc_id)",
            {"doc_id": clean_id}
        )

        logger.info(f"Query result type: {type(result)}, length: {len(result) if result else 0}")
        logger.info(f"Query result content: {result}")

        # Parse SurrealDB response - it can have different structures
        items = []
        if result and len(result) > 0:
            first_item = result[0]
            if isinstance(first_item, dict):
                # Check if it's wrapped in a "result" key
                if "result" in first_item:
                    items = first_item["result"] if isinstance(first_item["result"], list) else [first_item["result"]]
                # Check if it has an "id" field directly (it's the document)
                elif "id" in first_item:
                    items = result
            elif isinstance(first_item, list):
                items = first_item

        logger.info(f"Parsed items: {items}")

        # If document exists in database, handle cleanup
        if items and len(items) > 0:
            item = items[0]
            logger.info(f"Found document to delete: {item.get('nom_fichier', 'unknown')}")

            # If this is a transcription document, clear texte_extrait from the source audio
            if item.get("is_transcription") and item.get("source_audio"):
                source_audio_filename = item.get("source_audio")
                case_id_for_query = item.get("case_id", case_id)
                if not case_id_for_query.startswith("case:"):
                    case_id_for_query = f"case:{case_id_for_query}"

                # Find the source audio document
                audio_result = await service.query(
                    "SELECT * FROM document WHERE case_id = $case_id AND nom_fichier = $filename",
                    {"case_id": case_id_for_query, "filename": source_audio_filename}
                )

                if audio_result and len(audio_result) > 0:
                    # SurrealDB query() returns a list of results directly
                    audio_items = audio_result
                    if isinstance(audio_items, list) and len(audio_items) > 0:
                        audio_doc = audio_items[0]
                        audio_doc_id = str(audio_doc.get("id", ""))
                        if audio_doc_id:
                            # Clear texte_extrait from the audio document
                            await service.merge(audio_doc_id, {"texte_extrait": None})
                            logger.info(f"Cleared texte_extrait from source audio document: {audio_doc_id}")

            # Delete file from disk if it's in data/uploads/ (uploaded files)
            # But keep linked files (external file_path)
            file_path = item.get("file_path")
            if file_path:
                file_path_obj = Path(file_path)
                # Check if file is in uploads directory
                if "data/uploads/" in str(file_path_obj) or str(settings.upload_dir) in str(file_path_obj):
                    if file_path_obj.exists():
                        try:
                            file_path_obj.unlink()
                            logger.info(f"Deleted uploaded file from disk: {file_path}")
                        except Exception as e:
                            logger.warning(f"Could not delete file from disk: {e}")
                    else:
                        logger.warning(f"File does not exist on disk: {file_path}")
                else:
                    logger.info(f"Linked file kept on disk (external path): {file_path}")

            # Delete from database
            await service.delete(doc_id)
            logger.info(f"Document record deleted: {doc_id}")
        else:
            # Document not in database, but try to delete file if it exists in uploads
            logger.warning(f"Document not found in database (may have been auto-removed): {doc_id}")

            # Try to delete orphaned file using provided file_path or filename
            if file_path:
                # Use provided file_path directly
                file_path_obj = Path(file_path)
                if file_path_obj.exists():
                    # Check if file is in uploads directory
                    if "data/uploads/" in str(file_path_obj) or str(settings.upload_dir) in str(file_path_obj):
                        try:
                            file_path_obj.unlink()
                            logger.info(f"Deleted orphaned file from disk using file_path: {file_path}")
                        except Exception as e:
                            logger.warning(f"Could not delete orphaned file: {e}")
                    else:
                        logger.info(f"Orphaned file is external (not deleting): {file_path}")
                else:
                    logger.warning(f"Orphaned file does not exist: {file_path}")
            elif filename:
                # Use filename to find file in uploads directory
                upload_dir = Path(settings.upload_dir) / case_id.replace("case:", "")
                if upload_dir.exists():
                    file_path_obj = upload_dir / filename
                    if file_path_obj.exists():
                        try:
                            file_path_obj.unlink()
                            logger.info(f"Deleted orphaned file from disk using filename: {filename}")
                        except Exception as e:
                            logger.warning(f"Could not delete orphaned file: {e}")
                    else:
                        logger.warning(f"Orphaned file does not exist: {file_path_obj}")
            else:
                # Fallback: try to find file with matching ID in name (old behavior)
                upload_dir = Path(settings.upload_dir) / case_id.replace("case:", "")
                if upload_dir.exists():
                    # Look for file with matching ID in name
                    clean_id_short = clean_id[:8] if len(clean_id) > 8 else clean_id
                    found_any = False
                    for orphan_file in upload_dir.glob(f"{clean_id_short}*"):
                        try:
                            orphan_file.unlink()
                            logger.info(f"Deleted orphaned file from disk: {orphan_file}")
                            found_any = True
                        except Exception as e:
                            logger.warning(f"Could not delete orphaned file: {e}")
                    if not found_any:
                        logger.warning(f"No orphaned files found with ID pattern: {clean_id_short}*")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting document: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/{case_id}/documents/{doc_id}/download")
async def download_document(
    case_id: str,
    doc_id: str,
    inline: bool = False,
    user_id: Optional[str] = Depends(get_current_user_id)
):
    """
    Telecharge un document ou l'affiche inline.

    Args:
        inline: Si True, affiche le fichier dans le navigateur (pour iframe/preview)
                Si False, force le telechargement
    """
    try:
        service = get_surreal_service()
        if not service.db:
            await service.connect()

        # Normalize ID
        if not doc_id.startswith("document:"):
            doc_id = f"document:{doc_id}"

        # Get document
        clean_id = doc_id.replace("document:", "")
        result = await service.query(
            "SELECT * FROM document WHERE id = type::thing('document', $doc_id)",
            {"doc_id": clean_id}
        )

        if not result or len(result) == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document non trouve"
            )

        # SurrealDB query() returns a list of results directly
        items = result
        if not items or len(items) == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document non trouve"
            )

        item = items[0]
        file_path = item.get("file_path")

        if not file_path or not Path(file_path).exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Fichier non trouve sur le disque"
            )

        media_type = item.get("type_mime", "application/octet-stream")

        if inline:
            # For inline display (iframe/preview), don't set filename
            # This results in Content-Disposition: inline
            return FileResponse(
                path=file_path,
                media_type=media_type,
            )
        else:
            # For download, set filename which triggers attachment disposition
            return FileResponse(
                path=file_path,
                filename=item.get("nom_fichier", "document"),
                media_type=media_type,
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading document: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


# Audio file extensions that can be transcribed
AUDIO_EXTENSIONS = {'.mp3', '.wav', '.m4a', '.ogg', '.webm', '.flac', '.aac'}


class ExtractionResponse(BaseModel):
    success: bool
    text: str = ""
    method: str = ""
    error: str = ""


@router.post("/{case_id}/documents/{doc_id}/extract", response_model=ExtractionResponse)
async def extract_document_text(
    case_id: str,
    doc_id: str,
    user_id: str = Depends(require_auth)
):
    """
    Extrait le texte d'un document (PDF, Word, texte, markdown).

    Pour les fichiers audio, utilisez l'endpoint /transcribe.
    """
    try:
        service = get_surreal_service()
        if not service.db:
            await service.connect()

        # Normalize IDs
        if not case_id.startswith("case:"):
            case_id = f"case:{case_id}"
        if not doc_id.startswith("document:"):
            doc_id = f"document:{doc_id}"

        # Get document
        clean_id = doc_id.replace("document:", "")
        result = await service.query(
            "SELECT * FROM document WHERE id = type::thing('document', $doc_id)",
            {"doc_id": clean_id}
        )

        if not result or len(result) == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document non trouve"
            )

        # SurrealDB query() returns a list of results directly
        items = result
        if not items or len(items) == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document non trouve"
            )

        item = items[0]
        file_path = item.get("file_path")

        if not file_path:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Chemin du fichier non trouve"
            )

        if not Path(file_path).exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Fichier non trouve sur le disque"
            )

        # Check if it's an audio file (should use transcribe endpoint instead)
        ext = Path(file_path).suffix.lower()
        if ext in AUDIO_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Utilisez l'endpoint /transcribe pour les fichiers audio"
            )

        # Extract text
        from services.document_extraction_service import get_extraction_service

        extraction_service = get_extraction_service()
        extraction_result = await extraction_service.extract(file_path)

        if not extraction_result.success:
            logger.error(f"Extraction failed for {file_path}: {extraction_result.error}")
            return ExtractionResponse(
                success=False,
                error=extraction_result.error or "Erreur d'extraction inconnue"
            )

        # Update document with extracted text
        now = datetime.utcnow().isoformat()
        await service.merge(doc_id, {
            "texte_extrait": extraction_result.text,
            "extraction_method": extraction_result.extraction_method,
            "updated_at": now,
        })

        logger.info(f"Text extracted for document {doc_id}: {len(extraction_result.text)} chars via {extraction_result.extraction_method}")

        return ExtractionResponse(
            success=True,
            text=extraction_result.text[:500] + "..." if len(extraction_result.text) > 500 else extraction_result.text,
            method=extraction_result.extraction_method
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error extracting document: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.delete("/{case_id}/documents/{doc_id}/text")
async def clear_document_text(
    case_id: str,
    doc_id: str,
    user_id: str = Depends(require_auth)
):
    """
    Efface le texte extrait d'un document.

    Supprime le champ texte_extrait du document dans la base de données.
    """
    try:
        service = get_surreal_service()
        if not service.db:
            await service.connect()

        # Normalize IDs
        if not case_id.startswith("case:"):
            case_id = f"case:{case_id}"
        if not doc_id.startswith("document:"):
            doc_id = f"document:{doc_id}"

        # Get document to verify it exists
        clean_id = doc_id.replace("document:", "")
        result = await service.query(
            "SELECT * FROM document WHERE id = type::thing('document', $doc_id)",
            {"doc_id": clean_id}
        )

        if not result or len(result) == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document non trouvé"
            )

        # Clear texte_extrait
        now = datetime.utcnow().isoformat()
        await service.merge(doc_id, {
            "texte_extrait": None,
            "extraction_method": None,
            "updated_at": now,
        })

        logger.info(f"Cleared texte_extrait for document {doc_id}")

        return {"success": True, "message": "Texte extrait supprimé"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error clearing document text: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


class TranscriptionResponse(BaseModel):
    success: bool
    text: str = ""
    language: str = ""
    duration: float = 0.0
    error: str = ""


@router.post("/{case_id}/documents/{doc_id}/transcribe", response_model=TranscriptionResponse)
async def transcribe_document(
    case_id: str,
    doc_id: str,
    language: str = "fr",
    user_id: str = Depends(require_auth)
):
    """
    Transcrit un document audio en texte.

    Utilise OpenAI Whisper pour la transcription.
    Le texte transcrit est enregistré dans le document.
    """
    try:
        service = get_surreal_service()
        if not service.db:
            await service.connect()

        # Normalize IDs
        if not case_id.startswith("case:"):
            case_id = f"case:{case_id}"
        if not doc_id.startswith("document:"):
            doc_id = f"document:{doc_id}"

        # Get document
        clean_id = doc_id.replace("document:", "")
        result = await service.query(
            "SELECT * FROM document WHERE id = type::thing('document', $doc_id)",
            {"doc_id": clean_id}
        )

        if not result or len(result) == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document non trouve"
            )

        # SurrealDB query() returns a list of results directly
        items = result
        if not items or len(items) == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document non trouve"
            )

        item = items[0]
        file_path = item.get("file_path")

        if not file_path:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Chemin du fichier non trouve"
            )

        # Check if it's an audio file
        ext = Path(file_path).suffix.lower()
        if ext not in AUDIO_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Ce n'est pas un fichier audio. Extensions supportees: {', '.join(AUDIO_EXTENSIONS)}"
            )

        if not Path(file_path).exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Fichier audio non trouve sur le disque"
            )

        # Import and use whisper service
        from services.whisper_service import get_whisper_service, WHISPER_AVAILABLE

        if not WHISPER_AVAILABLE:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Service de transcription non disponible. Installer openai-whisper: uv sync --extra whisper"
            )

        whisper_service = get_whisper_service()
        logger.info(f"Starting transcription for {file_path} (language={language})")

        # Transcribe
        transcription = await whisper_service.transcribe(file_path, language=language)

        if not transcription.success:
            logger.error(f"Transcription failed: {transcription.error}")
            return TranscriptionResponse(
                success=False,
                error=transcription.error or "Erreur de transcription inconnue"
            )

        # Update document with transcription
        from datetime import datetime
        now = datetime.utcnow().isoformat()

        await service.merge(doc_id, {
            "texte_extrait": transcription.text,
            "is_transcription": True,
            "extraction_method": transcription.method,
            "updated_at": now,
            "metadata": {
                "language": transcription.language,
                "duration_seconds": transcription.duration,
                "transcribed_at": now
            }
        })

        logger.info(f"Transcription saved for document {doc_id}: {len(transcription.text)} chars")

        return TranscriptionResponse(
            success=True,
            text=transcription.text,
            language=transcription.language,
            duration=transcription.duration
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error transcribing document: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


# ============================================================================
# Transcription avec Workflow et SSE
# ============================================================================

import json
import asyncio
from fastapi.responses import StreamingResponse


class TranscribeWorkflowRequest(BaseModel):
    language: str = "fr"
    create_markdown: bool = True
    raw_mode: bool = False  # Si True, pas de formatage LLM - juste la transcription Whisper brute


class YouTubeDownloadRequest(BaseModel):
    """Request pour télécharger l'audio d'une vidéo YouTube."""
    url: str
    auto_transcribe: bool = False  # Si True, lance la transcription automatiquement


@router.post("/{case_id}/documents/{doc_id}/transcribe-workflow")
async def transcribe_document_workflow(
    case_id: str,
    doc_id: str,
    request: TranscribeWorkflowRequest = TranscribeWorkflowRequest(),
    user_id: str = Depends(require_auth)
):
    """
    Transcrit un document audio avec un workflow Agno.

    Retourne un stream SSE avec les événements de progression:
    - progress: {step, message, percentage}
    - step_start: {step}
    - step_complete: {step, success}
    - complete: {result}
    - error: {message}
    """
    try:
        service = get_surreal_service()
        if not service.db:
            await service.connect()

        # Normalize IDs
        if not case_id.startswith("case:"):
            case_id = f"case:{case_id}"
        if not doc_id.startswith("document:"):
            doc_id = f"document:{doc_id}"

        # Get document
        clean_id = doc_id.replace("document:", "")
        result = await service.query(
            "SELECT * FROM document WHERE id = type::thing('document', $doc_id)",
            {"doc_id": clean_id}
        )

        if not result or len(result) == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document non trouve"
            )

        # SurrealDB query() returns a list of results directly
        items = result
        if not items or len(items) == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document non trouve"
            )

        item = items[0]
        file_path = item.get("file_path")

        if not file_path:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Chemin du fichier non trouve"
            )

        # Check if it's an audio file
        ext = Path(file_path).suffix.lower()
        if ext not in AUDIO_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Ce n'est pas un fichier audio. Extensions supportees: {', '.join(AUDIO_EXTENSIONS)}"
            )

        if not Path(file_path).exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Fichier audio non trouve sur le disque"
            )

        # Create SSE generator
        async def event_generator():
            progress_queue = asyncio.Queue()

            def on_progress(step: str, message: str, percentage: int):
                asyncio.create_task(progress_queue.put({
                    "type": "progress",
                    "data": {"step": step, "message": message, "percentage": percentage}
                }))

            def on_step_start(step: str):
                asyncio.create_task(progress_queue.put({
                    "type": "step_start",
                    "data": {"step": step}
                }))

            def on_step_complete(step: str, success: bool):
                asyncio.create_task(progress_queue.put({
                    "type": "step_complete",
                    "data": {"step": step, "success": success}
                }))

            # Import workflow
            from workflows.transcribe_audio import TranscriptionWorkflow

            workflow = TranscriptionWorkflow(
                on_progress=on_progress,
                on_step_start=on_step_start,
                on_step_complete=on_step_complete
            )

            # Run workflow in background task
            async def run_workflow():
                try:
                    result = await workflow.run(
                        audio_path=file_path,
                        case_id=case_id,
                        language=request.language,
                        create_markdown_doc=request.create_markdown,
                        raw_mode=request.raw_mode,
                        source_document_id=doc_id  # Link transcription to source audio
                    )
                    await progress_queue.put({
                        "type": "complete",
                        "data": {
                            "success": result.success,
                            "document_id": result.document_id,
                            "document_path": result.document_path,
                            "transcript_text": result.transcript_text[:500] if result.transcript_text else "",
                            "error": result.error
                        }
                    })
                except Exception as e:
                    logger.error(f"Workflow error: {e}", exc_info=True)
                    await progress_queue.put({
                        "type": "error",
                        "data": {"message": str(e)}
                    })
                finally:
                    await progress_queue.put(None)  # Signal end

            # Start workflow
            task = asyncio.create_task(run_workflow())

            try:
                while True:
                    event = await progress_queue.get()
                    if event is None:
                        break

                    yield f"event: {event['type']}\n"
                    yield f"data: {json.dumps(event['data'], ensure_ascii=False)}\n\n"

            except asyncio.CancelledError:
                task.cancel()
                raise

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting transcription workflow: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


# ============================================================================
# PDF Extraction to Markdown
# ============================================================================

@router.post("/{case_id}/documents/{doc_id}/extract-to-markdown")
async def extract_pdf_to_markdown(
    case_id: str,
    doc_id: str,
    user_id: str = Depends(require_auth)
):
    """
    Extrait le texte d'un PDF et le formate en markdown avec sections détectées par LLM.

    Retourne un stream SSE avec les événements de progression:
    - progress: {step, message, percentage}
    - step_start: {step}
    - step_complete: {step, success}
    - complete: {result}
    - error: {message}
    """
    try:
        service = get_surreal_service()
        if not service.db:
            await service.connect()

        # Normalize IDs
        if not case_id.startswith("case:"):
            case_id = f"case:{case_id}"
        if not doc_id.startswith("document:"):
            doc_id = f"document:{doc_id}"

        # Get document
        clean_id = doc_id.replace("document:", "")
        result = await service.query(
            "SELECT * FROM document WHERE id = type::thing('document', $doc_id)",
            {"doc_id": clean_id}
        )

        if not result or len(result) == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document non trouve"
            )

        # SurrealDB query() returns a list of results directly
        items = result
        if not items or len(items) == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document non trouve"
            )

        item = items[0]
        file_path = item.get("file_path")

        if not file_path:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Chemin du fichier non trouve"
            )

        # Check if it's a PDF file
        ext = Path(file_path).suffix.lower()
        if ext != '.pdf':
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Ce n'est pas un fichier PDF. Extension: {ext}"
            )

        if not Path(file_path).exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Fichier PDF non trouve sur le disque"
            )

        # Create SSE generator
        async def event_generator():
            import asyncio
            import json
            progress_queue = asyncio.Queue()

            async def run_extraction():
                try:
                    # Check if a markdown already exists for this PDF
                    original_filename = item.get("nom_fichier", "document.pdf")
                    markdown_filename = Path(original_filename).stem + ".md"

                    # Get judgment directory
                    judgment_dir = Path(settings.upload_dir) / case_id.replace("case:", "")
                    markdown_path = judgment_dir / markdown_filename

                    # Check if markdown file exists on disk
                    if markdown_path.exists():
                        await progress_queue.put({
                            "type": "error",
                            "data": {"message": f"Un fichier markdown '{markdown_filename}' existe déjà sur le disque pour ce PDF. Supprimez-le d'abord si vous voulez réextraire."}
                        })
                        return

                    # Check existing documents in database
                    docs_result = await service.query(
                        "SELECT * FROM document WHERE case_id = $case_id AND nom_fichier = $filename",
                        {"case_id": case_id, "filename": markdown_filename}
                    )

                    if docs_result and len(docs_result) > 0:
                        # Parse result
                        existing_docs = []
                        first_item = docs_result[0]
                        if isinstance(first_item, dict):
                            if "result" in first_item:
                                existing_docs = first_item["result"] if isinstance(first_item["result"], list) else []
                            elif "id" in first_item:
                                existing_docs = docs_result
                        elif isinstance(first_item, list):
                            existing_docs = first_item

                        if existing_docs and len(existing_docs) > 0:
                            await progress_queue.put({
                                "type": "error",
                                "data": {"message": f"Un fichier markdown '{markdown_filename}' existe déjà en base de données pour ce PDF. Supprimez-le d'abord si vous voulez réextraire."}
                            })
                            return

                    # Step 1: Extract text with MarkItDown
                    await progress_queue.put({
                        "type": "progress",
                        "data": {"step": "extract", "message": "Extraction du texte avec MarkItDown...", "percentage": 20}
                    })

                    from services.document_extraction_service import get_extraction_service
                    extraction_service = get_extraction_service()

                    extraction_result = await extraction_service.extract(
                        file_path=file_path,
                        content_type="application/pdf"
                    )

                    if not extraction_result.success:
                        await progress_queue.put({
                            "type": "error",
                            "data": {"message": extraction_result.error or "Échec de l'extraction"}
                        })
                        return

                    await progress_queue.put({
                        "type": "progress",
                        "data": {"step": "extract", "message": "Texte extrait avec succès", "percentage": 60}
                    })

                    # Step 2: Save as markdown file
                    await progress_queue.put({
                        "type": "progress",
                        "data": {"step": "save", "message": "Création du fichier markdown...", "percentage": 70}
                    })

                    # Ensure judgment directory exists (judgment_dir and markdown_path already defined at the beginning)
                    judgment_dir.mkdir(parents=True, exist_ok=True)

                    # Write markdown file
                    with open(markdown_path, "w", encoding="utf-8") as f:
                        f.write(extraction_result.text)

                    # Step 3: Create document record in SurrealDB
                    await progress_queue.put({
                        "type": "progress",
                        "data": {"step": "save", "message": "Enregistrement dans la base de données...", "percentage": 85}
                    })

                    new_doc_id = str(uuid.uuid4())
                    doc_record = {
                        # ❌ NE PAS inclure "id" dans doc_record car CREATE va l'ajouter automatiquement
                        "case_id": case_id,
                        "nom_fichier": markdown_filename,
                        "type_fichier": "md",
                        "type_mime": "text/markdown",
                        "taille": len(extraction_result.text.encode('utf-8')),
                        "file_path": str(markdown_path),
                        "texte_extrait": extraction_result.text,  # Store for indexing
                        "is_transcription": False,
                        "source_document_id": doc_id,  # Link to source PDF
                        "is_derived": True,
                        "derivation_type": "pdf_extraction",
                        "created_at": datetime.utcnow().isoformat(),
                        "updated_at": datetime.utcnow().isoformat(),
                    }

                    # Utiliser service.create() avec record_id pour garantir le bon format
                    await service.create("document", doc_record, record_id=new_doc_id)

                    # Index le document pour la recherche sémantique
                    try:
                        from services.document_indexing_service import get_document_indexing_service

                        await progress_queue.put({
                            "type": "progress",
                            "data": {"step": "save", "message": "Indexation pour recherche sémantique...", "percentage": 90}
                        })

                        indexing_service = get_document_indexing_service()
                        index_result = await indexing_service.index_document(
                            document_id=f"document:{new_doc_id}",
                            case_id=case_id,
                            text_content=extraction_result.text,
                            force_reindex=False
                        )

                        if index_result.get("success"):
                            logger.info(f"Document indexed: {index_result.get('chunks_created', 0)} chunks")
                        else:
                            logger.warning(f"Indexing failed: {index_result.get('error', 'Unknown error')}")
                    except Exception as e:
                        # Ne pas bloquer si l'indexation échoue
                        logger.warning(f"Could not index document: {e}")

                    await progress_queue.put({
                        "type": "complete",
                        "data": {
                            "success": True,
                            "document_id": f"document:{new_doc_id}",
                            "document_path": str(markdown_path),
                            "page_count": extraction_result.metadata.get("num_pages", 0)
                        }
                    })

                except Exception as e:
                    logger.error(f"Extraction error: {e}", exc_info=True)
                    await progress_queue.put({
                        "type": "error",
                        "data": {"message": str(e)}
                    })
                finally:
                    await progress_queue.put(None)  # Signal end

            # Start extraction
            task = asyncio.create_task(run_extraction())

            try:
                while True:
                    event = await progress_queue.get()
                    if event is None:
                        break

                    yield f"event: {event['type']}\n"
                    yield f"data: {json.dumps(event['data'], ensure_ascii=False)}\n\n"

            except asyncio.CancelledError:
                task.cancel()
                raise

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting PDF extraction workflow: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


# ============================================================================
# YouTube Download
# ============================================================================

class YouTubeInfoResponse(BaseModel):
    """Informations sur une vidéo YouTube."""
    title: str
    duration: int
    uploader: str
    thumbnail: str
    url: str


class YouTubeDownloadResponse(BaseModel):
    """Réponse du téléchargement YouTube."""
    success: bool
    document_id: str = ""
    filename: str = ""
    title: str = ""
    duration: int = 0
    error: str = ""


@router.post("/{case_id}/documents/youtube/info", response_model=YouTubeInfoResponse)
async def get_youtube_info(
    case_id: str,
    request: YouTubeDownloadRequest,
    user_id: str = Depends(require_auth)
):
    """
    Récupère les informations d'une vidéo YouTube sans la télécharger.
    """
    try:
        from services.youtube_service import get_youtube_service, YTDLP_AVAILABLE

        if not YTDLP_AVAILABLE:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="yt-dlp n'est pas installé. Exécuter: uv add yt-dlp"
            )

        youtube_service = get_youtube_service()

        if not youtube_service.is_valid_youtube_url(request.url):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="URL YouTube invalide"
            )

        info = await youtube_service.get_video_info(request.url)

        return YouTubeInfoResponse(
            title=info.title,
            duration=info.duration,
            uploader=info.uploader,
            thumbnail=info.thumbnail,
            url=info.url,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting YouTube info: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/{case_id}/documents/youtube", response_model=YouTubeDownloadResponse)
async def download_youtube_audio(
    case_id: str,
    request: YouTubeDownloadRequest,
    user_id: str = Depends(require_auth)
):
    """
    Télécharge l'audio d'une vidéo YouTube et l'ajoute comme document.

    Le fichier est téléchargé en MP3 et enregistré dans le dossier du jugement.
    """
    try:
        from services.youtube_service import get_youtube_service, YTDLP_AVAILABLE

        if not YTDLP_AVAILABLE:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="yt-dlp n'est pas installé. Exécuter: uv add yt-dlp"
            )

        youtube_service = get_youtube_service()

        if not youtube_service.is_valid_youtube_url(request.url):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="URL YouTube invalide"
            )

        service = get_surreal_service()
        if not service.db:
            await service.connect()

        # Normalize case ID
        if not case_id.startswith("case:"):
            case_id = f"case:{case_id}"

        # Create upload directory for this judgment
        upload_dir = Path(settings.upload_dir) / case_id.replace("case:", "")
        upload_dir.mkdir(parents=True, exist_ok=True)

        # Download audio
        logger.info(f"Downloading YouTube audio: {request.url}")
        result = await youtube_service.download_audio(request.url, str(upload_dir))

        if not result.success:
            return YouTubeDownloadResponse(
                success=False,
                error=result.error or "Erreur de téléchargement inconnue"
            )

        # Create document record in database
        doc_id = str(uuid.uuid4())[:8]
        now = datetime.utcnow().isoformat()

        file_path = Path(result.file_path)
        document_data = {
            "case_id": case_id,
            "nom_fichier": result.filename,
            "type_fichier": "mp3",
            "type_mime": "audio/mpeg",
            "taille": file_path.stat().st_size if file_path.exists() else 0,
            "file_path": str(file_path.absolute()),
            "user_id": user_id,
            "created_at": now,
            "source_type": "youtube",
            "source": "youtube",
            "source_url": request.url,
            "metadata": {
                "youtube_title": result.title,
                "duration_seconds": result.duration,
            }
        }

        await service.create("document", document_data, record_id=doc_id)
        logger.info(f"YouTube audio saved as document: {doc_id}")

        return YouTubeDownloadResponse(
            success=True,
            document_id=f"document:{doc_id}",
            filename=result.filename,
            title=result.title,
            duration=result.duration,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading YouTube audio: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


# ============================================================================
# TEXT-TO-SPEECH ENDPOINTS
# ============================================================================

class TTSVoice(BaseModel):
    """Voix TTS disponible."""
    name: str
    locale: str
    country: str
    language: str
    gender: str


@router.get("/tts/voices", response_model=list[TTSVoice])
async def list_tts_voices(
    user_id: Optional[str] = Depends(get_current_user_id)
):
    """
    Liste toutes les voix TTS disponibles.

    Retourne la liste des voix supportées pour la synthèse vocale.
    """
    try:
        from services.tts_service import get_tts_service, EDGE_TTS_AVAILABLE

        if not EDGE_TTS_AVAILABLE:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Service TTS non disponible. Installer edge-tts: uv add edge-tts"
            )

        tts_service = get_tts_service()
        voices = tts_service.get_available_voices()

        return [TTSVoice(**voice) for voice in voices]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing TTS voices: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


class TTSRequest(BaseModel):
    """Request pour générer l'audio TTS d'un document."""
    language: str = "fr"  # fr ou en
    voice: Optional[str] = None  # Voix spécifique (optionnel)
    gender: str = "female"  # female ou male
    rate: str = "+0%"  # Vitesse de lecture (-50% à +100%)
    volume: str = "+0%"  # Volume (-100% à +100%)


class TTSResponse(BaseModel):
    """Réponse de la génération TTS."""
    success: bool
    audio_url: str = ""
    duration: float = 0.0
    voice: str = ""
    error: str = ""


@router.post("/{case_id}/documents/{doc_id}/tts", response_model=TTSResponse)
async def generate_tts(
    case_id: str,
    doc_id: str,
    request: TTSRequest = TTSRequest(),
    user_id: str = Depends(require_auth)
):
    """
    Génère un fichier audio TTS à partir du texte extrait d'un document.

    Le fichier audio est généré en MP3 et sauvegardé dans le répertoire du jugement.
    Retourne l'URL pour télécharger/streamer l'audio.
    """
    try:
        from services.tts_service import get_tts_service, EDGE_TTS_AVAILABLE

        if not EDGE_TTS_AVAILABLE:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Service TTS non disponible. Installer edge-tts: uv add edge-tts"
            )

        service = get_surreal_service()
        if not service.db:
            await service.connect()

        # Normalize IDs
        if not case_id.startswith("case:"):
            case_id = f"case:{case_id}"
        if not doc_id.startswith("document:"):
            doc_id = f"document:{doc_id}"

        # Get document
        clean_id = doc_id.replace("document:", "")
        result = await service.query(
            "SELECT * FROM document WHERE id = type::thing('document', $doc_id)",
            {"doc_id": clean_id}
        )

        if not result or len(result) == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document non trouvé"
            )

        # SurrealDB query() returns a list of results directly
        items = result
        if not items or len(items) == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document non trouvé"
            )

        item = items[0]

        # Get extracted text
        text_content = item.get("texte_extrait")
        if not text_content:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ce document n'a pas de texte extrait. Utilisez d'abord l'extraction ou la transcription."
            )

        # Generate TTS
        tts_service = get_tts_service()

        # Create output path
        judgment_dir = Path(settings.upload_dir) / case_id.replace("case:", "")
        judgment_dir.mkdir(parents=True, exist_ok=True)

        # Generate filename based on document name
        original_filename = item.get("nom_fichier", "document")
        audio_filename = f"{Path(original_filename).stem}_tts.mp3"
        audio_path = judgment_dir / audio_filename

        logger.info(f"Generating TTS for document {doc_id}: {len(text_content)} chars")

        # Generate audio
        tts_result = await tts_service.text_to_speech(
            text=text_content,
            output_path=str(audio_path),
            language=request.language,
            voice=request.voice if request.voice else tts_service.get_voice_for_language(
                request.language,
                request.gender
            ),
            rate=request.rate,
            volume=request.volume
        )

        if not tts_result.success:
            logger.error(f"TTS generation failed: {tts_result.error}")
            return TTSResponse(
                success=False,
                error=tts_result.error or "Erreur de génération TTS inconnue"
            )

        # Create document record for the TTS audio
        tts_doc_id = str(uuid.uuid4())[:8]
        now = datetime.utcnow().isoformat()

        tts_doc_data = {
            "case_id": case_id,
            "nom_fichier": audio_filename,
            "type_fichier": "mp3",
            "type_mime": "audio/mpeg",
            "taille": Path(tts_result.audio_path).stat().st_size,
            "file_path": tts_result.audio_path,
            "user_id": user_id,
            "created_at": now,
            "is_tts": True,
            "source_document": doc_id,  # Garder pour compatibilité
            "source_document_id": doc_id,  # Nouveau champ
            "is_derived": True,
            "derivation_type": "tts",
            "metadata": {
                "voice": tts_result.voice,
                "language": tts_result.language,
                "duration_seconds": tts_result.duration,
                "generated_at": now
            }
        }

        await service.create("document", tts_doc_data, record_id=tts_doc_id)
        logger.info(f"TTS audio saved as document: {tts_doc_id}")

        # Return URL for downloading/streaming
        clean_case_id = case_id.replace("case:", "")
        audio_url = f"/api/cases/{clean_case_id}/documents/document:{tts_doc_id}/download?inline=true"

        return TTSResponse(
            success=True,
            audio_url=audio_url,
            duration=tts_result.duration,
            voice=tts_result.voice
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating TTS: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


# ============================================================================
# DIAGNOSTIC ENDPOINT
# ============================================================================

class DiagnosticResult(BaseModel):
    """Résultat du diagnostic de cohérence fichiers/base de données."""
    total_documents: int
    missing_files: list[dict]
    orphan_records: list[dict]
    ok_count: int


@router.get("/{case_id}/documents/diagnostic", response_model=DiagnosticResult)
async def diagnose_documents(
    case_id: str,
    user_id: str = Depends(get_current_user_id)
):
    """
    Diagnostic de cohérence entre base de données et système de fichiers.

    Identifie:
    - Les enregistrements en base sans fichier physique (orphelins)
    - Les fichiers physiques sans enregistrement en base (manquants)
    """
    service = get_surreal_service()
    if not service.db:
        await service.connect()

    # Normaliser case_id
    if not case_id.startswith("case:"):
        case_id = f"case:{case_id}"

    # Récupérer tous les documents de la base de données
    docs_result = await service.query(
        "SELECT * FROM document WHERE case_id = $case_id",
        {"case_id": case_id}
    )

    documents = []
    if docs_result and len(docs_result) > 0:
        first_item = docs_result[0]
        if isinstance(first_item, dict):
            if "result" in first_item:
                documents = first_item["result"] if isinstance(first_item["result"], list) else []
            elif "id" in first_item:
                documents = docs_result
        elif isinstance(first_item, list):
            documents = first_item

    missing_files = []
    ok_count = 0

    # Vérifier chaque document
    for doc in documents:
        doc_id = doc.get("id", "unknown")
        doc_name = doc.get("nom_fichier", "unknown")
        file_path = doc.get("file_path", "")

        if not file_path:
            missing_files.append({
                "id": doc_id,
                "filename": doc_name,
                "reason": "Aucun chemin de fichier enregistré"
            })
            continue

        if not Path(file_path).exists():
            missing_files.append({
                "id": doc_id,
                "filename": doc_name,
                "path": file_path,
                "reason": "Fichier physique manquant"
            })
        else:
            ok_count += 1

    return DiagnosticResult(
        total_documents=len(documents),
        missing_files=missing_files,
        orphan_records=missing_files,  # Alias pour clarté
        ok_count=ok_count
    )
