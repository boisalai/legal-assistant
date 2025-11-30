"""
Routes pour la gestion des documents d'un dossier.

Endpoints:
- GET /api/judgments/{judgment_id}/documents - Liste des documents
- POST /api/judgments/{judgment_id}/documents - Upload d'un document
- GET /api/judgments/{judgment_id}/documents/{doc_id} - Details d'un document
- DELETE /api/judgments/{judgment_id}/documents/{doc_id} - Supprimer un document
- GET /api/judgments/{judgment_id}/documents/{doc_id}/download - Telecharger un document
"""

import logging
import uuid
import mimetypes
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, status, UploadFile, File, Depends
from fastapi.responses import FileResponse
from pydantic import BaseModel

from config.settings import settings
from services.surreal_service import get_surreal_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/judgments", tags=["Documents"])

# Reuse auth from judgments
from routes.judgments import require_auth, get_current_user_id

# Allowed file types
ALLOWED_EXTENSIONS = {
    '.pdf': 'application/pdf',
    '.doc': 'application/msword',
    '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    '.txt': 'text/plain',
    '.md': 'text/markdown',
    '.mp3': 'audio/mpeg',
    '.wav': 'audio/wav',
    '.m4a': 'audio/mp4',
    '.ogg': 'audio/ogg',
    '.webm': 'audio/webm',
}

MAX_FILE_SIZE = 500 * 1024 * 1024  # 500MB - Pour supporter les enregistrements audio de 3h+


# ============================================================================
# Pydantic Models
# ============================================================================

class DocumentResponse(BaseModel):
    id: str
    judgment_id: str
    nom_fichier: str
    type_fichier: str
    type_mime: str
    taille: int
    file_path: str
    created_at: str
    texte_extrait: Optional[str] = None
    file_exists: bool = True  # Whether the file exists on disk


class DocumentListResponse(BaseModel):
    documents: list[DocumentResponse]
    total: int
    missing_files: list[str] = []  # List of document IDs with missing files


class RegisterDocumentRequest(BaseModel):
    """Request to register a document by file path (no upload/copy)."""
    file_path: str  # Absolute path to the file on disk


# ============================================================================
# Helper Functions
# ============================================================================

def get_file_extension(filename: str) -> str:
    """Get file extension from filename."""
    return Path(filename).suffix.lower()


def is_allowed_file(filename: str) -> bool:
    """Check if file extension is allowed."""
    ext = get_file_extension(filename)
    return ext in ALLOWED_EXTENSIONS


def get_mime_type(filename: str) -> str:
    """Get MIME type from filename."""
    ext = get_file_extension(filename)
    return ALLOWED_EXTENSIONS.get(ext, 'application/octet-stream')


# ============================================================================
# Endpoints
# ============================================================================

@router.get("/{judgment_id}/documents", response_model=DocumentListResponse)
async def list_documents(
    judgment_id: str,
    verify_files: bool = True,
    auto_remove_missing: bool = True,
    user_id: Optional[str] = Depends(get_current_user_id)
):
    """
    Liste les documents d'un dossier.

    Args:
        judgment_id: ID du dossier
        verify_files: Si True, verifie que les fichiers existent sur le disque
        auto_remove_missing: Si True, supprime automatiquement les documents dont le fichier n'existe plus
    """
    try:
        service = get_surreal_service()
        if not service.db:
            await service.connect()

        # Normalize judgment ID
        if not judgment_id.startswith("judgment:"):
            judgment_id = f"judgment:{judgment_id}"

        # Query documents for this judgment
        result = await service.query(
            "SELECT * FROM document WHERE judgment_id = $judgment_id ORDER BY created_at DESC",
            {"judgment_id": judgment_id}
        )

        documents = []
        missing_files = []
        docs_to_remove = []

        if result and len(result) > 0:
            items = result[0].get("result", result) if isinstance(result[0], dict) else result
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

                    documents.append(DocumentResponse(
                        id=str(item.get("id", "")),
                        judgment_id=item.get("judgment_id", judgment_id),
                        nom_fichier=item.get("nom_fichier", ""),
                        type_fichier=item.get("type_fichier", ""),
                        type_mime=item.get("type_mime", ""),
                        taille=item.get("taille", 0),
                        file_path=file_path,
                        created_at=item.get("created_at", ""),
                        texte_extrait=item.get("texte_extrait"),
                        file_exists=file_exists,
                    ))

        # Auto-remove documents with missing files
        if docs_to_remove:
            for doc_id in docs_to_remove:
                try:
                    await service.delete(doc_id)
                    logger.info(f"Auto-removed document with missing file: {doc_id}")
                except Exception as e:
                    logger.warning(f"Could not auto-remove document {doc_id}: {e}")

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


@router.post("/{judgment_id}/documents", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    judgment_id: str,
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

        # Normalize judgment ID
        if not judgment_id.startswith("judgment:"):
            judgment_id = f"judgment:{judgment_id}"

        # Generate document ID and save file
        doc_id = str(uuid.uuid4())[:8]
        ext = get_file_extension(file.filename)

        # Create upload directory
        upload_dir = Path(settings.upload_dir) / judgment_id.replace("judgment:", "")
        upload_dir.mkdir(parents=True, exist_ok=True)

        # Save file
        file_path = str(upload_dir / f"{doc_id}{ext}")
        with open(file_path, "wb") as f:
            f.write(content)

        logger.info(f"Document saved: {file_path}")

        # Create document record in database
        now = datetime.utcnow().isoformat()
        document_data = {
            "judgment_id": judgment_id,
            "nom_fichier": file.filename,
            "type_fichier": ext.lstrip('.'),
            "type_mime": get_mime_type(file.filename),
            "taille": len(content),
            "file_path": file_path,
            "user_id": user_id,
            "created_at": now,
        }

        await service.create("document", document_data, record_id=doc_id)
        logger.info(f"Document record created: {doc_id}")

        return DocumentResponse(
            id=f"document:{doc_id}",
            judgment_id=judgment_id,
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


@router.post("/{judgment_id}/documents/register", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def register_document(
    judgment_id: str,
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

        # Normalize judgment ID
        if not judgment_id.startswith("judgment:"):
            judgment_id = f"judgment:{judgment_id}"

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
            "judgment_id": judgment_id,
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
            judgment_id=judgment_id,
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


@router.get("/{judgment_id}/documents/{doc_id}", response_model=DocumentResponse)
async def get_document(
    judgment_id: str,
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
        if not judgment_id.startswith("judgment:"):
            judgment_id = f"judgment:{judgment_id}"
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

        items = result[0].get("result", result) if isinstance(result[0], dict) else result
        if not items or len(items) == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document non trouve"
            )

        item = items[0]

        return DocumentResponse(
            id=str(item.get("id", doc_id)),
            judgment_id=item.get("judgment_id", judgment_id),
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


@router.delete("/{judgment_id}/documents/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    judgment_id: str,
    doc_id: str,
    user_id: str = Depends(require_auth)
):
    """
    Supprime un document.
    """
    try:
        service = get_surreal_service()
        if not service.db:
            await service.connect()

        # Normalize IDs
        if not doc_id.startswith("document:"):
            doc_id = f"document:{doc_id}"

        # Get document to find file path
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

        items = result[0].get("result", result) if isinstance(result[0], dict) else result
        if not items or len(items) == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document non trouve"
            )

        item = items[0]

        # If this is a transcription document, clear texte_extrait from the source audio
        if item.get("is_transcription") and item.get("source_audio"):
            source_audio_filename = item.get("source_audio")
            judgment_id_for_query = item.get("judgment_id", judgment_id)
            if not judgment_id_for_query.startswith("judgment:"):
                judgment_id_for_query = f"judgment:{judgment_id_for_query}"

            # Find the source audio document
            audio_result = await service.query(
                "SELECT * FROM document WHERE judgment_id = $judgment_id AND nom_fichier = $filename",
                {"judgment_id": judgment_id_for_query, "filename": source_audio_filename}
            )

            if audio_result and len(audio_result) > 0:
                audio_items = audio_result[0].get("result", audio_result) if isinstance(audio_result[0], dict) else audio_result
                if isinstance(audio_items, list) and len(audio_items) > 0:
                    audio_doc = audio_items[0]
                    audio_doc_id = str(audio_doc.get("id", ""))
                    if audio_doc_id:
                        # Clear texte_extrait from the audio document
                        await service.merge(audio_doc_id, {"texte_extrait": None})
                        logger.info(f"Cleared texte_extrait from source audio document: {audio_doc_id}")

        # NOTE: We no longer delete files from disk!
        # Documents are now references to files at their original location.
        # Only the database record is deleted.
        file_path = item.get("file_path")
        logger.info(f"Document reference removed (file NOT deleted): {doc_id} -> {file_path}")

        # Delete from database only
        await service.delete(doc_id)
        logger.info(f"Document record deleted: {doc_id}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting document: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/{judgment_id}/documents/{doc_id}/download")
async def download_document(
    judgment_id: str,
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

        items = result[0].get("result", result) if isinstance(result[0], dict) else result
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


@router.post("/{judgment_id}/documents/{doc_id}/extract", response_model=ExtractionResponse)
async def extract_document_text(
    judgment_id: str,
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
        if not judgment_id.startswith("judgment:"):
            judgment_id = f"judgment:{judgment_id}"
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

        items = result[0].get("result", result) if isinstance(result[0], dict) else result
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


@router.delete("/{judgment_id}/documents/{doc_id}/text")
async def clear_document_text(
    judgment_id: str,
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
        if not judgment_id.startswith("judgment:"):
            judgment_id = f"judgment:{judgment_id}"
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


@router.post("/{judgment_id}/documents/{doc_id}/transcribe", response_model=TranscriptionResponse)
async def transcribe_document(
    judgment_id: str,
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
        if not judgment_id.startswith("judgment:"):
            judgment_id = f"judgment:{judgment_id}"
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

        items = result[0].get("result", result) if isinstance(result[0], dict) else result
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


@router.post("/{judgment_id}/documents/{doc_id}/transcribe-workflow")
async def transcribe_document_workflow(
    judgment_id: str,
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
        if not judgment_id.startswith("judgment:"):
            judgment_id = f"judgment:{judgment_id}"
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

        items = result[0].get("result", result) if isinstance(result[0], dict) else result
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
                        judgment_id=judgment_id,
                        language=request.language,
                        create_markdown_doc=request.create_markdown,
                        raw_mode=request.raw_mode
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


@router.post("/{judgment_id}/documents/youtube/info", response_model=YouTubeInfoResponse)
async def get_youtube_info(
    judgment_id: str,
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


@router.post("/{judgment_id}/documents/youtube", response_model=YouTubeDownloadResponse)
async def download_youtube_audio(
    judgment_id: str,
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

        # Normalize judgment ID
        if not judgment_id.startswith("judgment:"):
            judgment_id = f"judgment:{judgment_id}"

        # Create upload directory for this judgment
        upload_dir = Path(settings.upload_dir) / judgment_id.replace("judgment:", "")
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
            "judgment_id": judgment_id,
            "nom_fichier": result.filename,
            "type_fichier": "mp3",
            "type_mime": "audio/mpeg",
            "taille": file_path.stat().st_size if file_path.exists() else 0,
            "file_path": str(file_path.absolute()),
            "user_id": user_id,
            "created_at": now,
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
