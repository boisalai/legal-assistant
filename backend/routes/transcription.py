"""
Routes pour la transcription audio et le téléchargement YouTube.

Endpoints:
- POST /api/cases/{case_id}/documents/{doc_id}/transcribe - Transcription simple Whisper
- POST /api/cases/{case_id}/documents/{doc_id}/transcribe-workflow - Transcription avec workflow Agno
- POST /api/cases/{case_id}/documents/youtube/info - Informations vidéo YouTube
- POST /api/cases/{case_id}/documents/youtube - Télécharger audio YouTube
"""

import logging
import uuid
import json
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from config.settings import settings
from services.surreal_service import get_surreal_service
from auth.helpers import require_auth
from utils.file_utils import AUDIO_EXTENSIONS

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/cases", tags=["Transcription"])


# ============================================================================
# Pydantic Models
# ============================================================================

class TranscriptionResponse(BaseModel):
    """Réponse de transcription simple."""
    success: bool
    text: str = ""
    language: str = ""
    duration: float = 0.0
    error: str = ""


class TranscribeWorkflowRequest(BaseModel):
    """Requête pour transcription avec workflow."""
    language: str = "fr"
    create_markdown: bool = True
    raw_mode: bool = False  # Si True, pas de formatage LLM


class YouTubeDownloadRequest(BaseModel):
    """Requête pour télécharger l'audio d'une vidéo YouTube."""
    url: str
    auto_transcribe: bool = False


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


# ============================================================================
# Endpoints - Transcription
# ============================================================================

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
# Endpoints - YouTube
# ============================================================================

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

        # Normalize judgment ID
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
