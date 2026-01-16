"""
Routes for audio summary management.

Endpoints:
- POST /api/courses/{course_id}/audio-summaries - Create an audio summary
- GET /api/courses/{course_id}/audio-summaries - List audio summaries
- GET /api/audio-summaries/{summary_id} - Get summary details
- POST /api/audio-summaries/{summary_id}/generate - Generate audio (SSE)
- GET /api/audio-summaries/{summary_id}/script - Download script file
- GET /api/audio-summaries/{summary_id}/audio - Stream audio file
- DELETE /api/audio-summaries/{summary_id} - Delete summary
- GET /api/audio-summaries/voices - List available voices
"""

import json
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import FileResponse, StreamingResponse

from services.surreal_service import get_surreal_service
from services.audio_summary_service import get_audio_summary_service
from models.audio_summary_models import (
    AudioSummaryCreate,
    AudioSummaryGenerateRequest,
    AudioSummaryResponse,
    AudioSummaryListResponse,
    AudioSourceDocument,
    VoiceInfo,
    AVAILABLE_VOICES,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Audio Summary"])


# ============================================================================
# Helper Functions
# ============================================================================

def generate_hex_id() -> str:
    """Generate a short hexadecimal ID compatible with SurrealDB."""
    return uuid.uuid4().hex[:8]


async def get_summary_by_id(service, summary_id: str) -> Optional[dict]:
    """Retrieve an audio summary by its ID."""
    # Ensure we have the full record ID format
    if not summary_id.startswith("audio_summary:"):
        record_id = f"audio_summary:{summary_id}"
    else:
        record_id = summary_id

    # Query directly using the record ID
    result = await service.query(f"SELECT * FROM {record_id}")

    if result and len(result) > 0:
        return result[0]
    return None


def format_summary_response(summary: dict) -> AudioSummaryResponse:
    """Format a summary for API response."""
    # Parse source_documents
    source_docs = []
    raw_sources = summary.get("source_documents", [])
    if raw_sources:
        for src in raw_sources:
            if isinstance(src, dict):
                source_docs.append(AudioSourceDocument(
                    doc_id=src.get("doc_id", ""),
                    name=src.get("name", ""),
                    relative_path=src.get("relative_path")
                ))

    # Format dates
    created_at = summary.get("created_at", "")
    if hasattr(created_at, "isoformat"):
        created_at = created_at.isoformat()
    elif not isinstance(created_at, str):
        created_at = str(created_at)

    updated_at = summary.get("updated_at")
    if updated_at:
        if hasattr(updated_at, "isoformat"):
            updated_at = updated_at.isoformat()
        elif not isinstance(updated_at, str):
            updated_at = str(updated_at)

    return AudioSummaryResponse(
        id=str(summary.get("id", "")),
        course_id=str(summary.get("course_id", "")),
        name=summary.get("name", ""),
        source_documents=source_docs,
        status=summary.get("status", "pending"),
        script_path=summary.get("script_path"),
        audio_path=summary.get("audio_path"),
        estimated_duration_seconds=summary.get("estimated_duration_seconds", 0.0),
        actual_duration_seconds=summary.get("actual_duration_seconds"),
        section_count=summary.get("section_count", 0),
        created_at=created_at,
        updated_at=updated_at,
        error_message=summary.get("error_message")
    )


# ============================================================================
# Voice Endpoints
# ============================================================================

@router.get(
    "/api/audio-summaries/voices",
    response_model=list[VoiceInfo],
    summary="List available voices"
)
async def list_voices():
    """List all available TTS voices for audio summaries."""
    return AVAILABLE_VOICES


# ============================================================================
# Summary Management Endpoints
# ============================================================================

@router.post(
    "/api/courses/{course_id}/audio-summaries",
    response_model=AudioSummaryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create audio summary"
)
async def create_audio_summary(course_id: str, request: AudioSummaryCreate):
    """
    Create a new audio summary record.

    The summary is created with status 'pending'. Use the generate endpoint
    to start the actual generation process.
    """
    service = get_surreal_service()

    # Normalize course_id
    if not course_id.startswith("course:"):
        course_id = f"course:{course_id}"

    # Verify course exists
    course_result = await service.query(f"SELECT * FROM {course_id}")
    if not course_result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cours non trouvé: {course_id}"
        )

    # Create summary record
    summary_id = generate_hex_id()

    # Build initial source_documents list
    source_docs = []
    for doc_id in request.source_document_ids:
        normalized_id = doc_id if doc_id.startswith("document:") else f"document:{doc_id}"
        doc_result = await service.query(f"SELECT * FROM {normalized_id}")
        if doc_result and len(doc_result) > 0:
            doc = doc_result[0]
            filename = doc.get("filename") or doc.get("nom_fichier") or doc_id
            if linked := doc.get("linked_source"):
                filename = linked.get("relative_path", filename)
            source_docs.append({
                "doc_id": normalized_id,
                "name": filename,
                "relative_path": doc.get("linked_source", {}).get("relative_path") if doc.get("linked_source") else None
            })

    summary_data = {
        "course_id": course_id,
        "name": request.name,
        "source_documents": source_docs,
        "status": "pending",
        "voice_config": {
            "titles": request.voice_titles
        },
        "estimated_duration_seconds": 0.0,
        "section_count": 0,
        "created_at": datetime.now(timezone.utc).isoformat()
    }

    await service.query(
        f"CREATE audio_summary:{summary_id} CONTENT $data",
        {"data": summary_data}
    )

    # Retrieve created record
    summary = await get_summary_by_id(service, summary_id)
    if not summary:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de la création du résumé audio"
        )

    logger.info(f"Audio summary created: {summary_id} for course {course_id}")
    return format_summary_response(summary)


@router.get(
    "/api/courses/{course_id}/audio-summaries",
    response_model=AudioSummaryListResponse,
    summary="List audio summaries"
)
async def list_audio_summaries(course_id: str):
    """List all audio summaries for a course."""
    service = get_surreal_service()

    # Normalize course_id
    if not course_id.startswith("course:"):
        course_id = f"course:{course_id}"

    result = await service.query(
        """
        SELECT * FROM audio_summary
        WHERE course_id = $course_id
        ORDER BY created_at DESC
        """,
        {"course_id": course_id}
    )

    summaries = []
    if result and len(result) > 0:
        for summary in result:
            summaries.append(format_summary_response(summary))

    return AudioSummaryListResponse(summaries=summaries, total=len(summaries))


@router.get(
    "/api/audio-summaries/{summary_id}",
    response_model=AudioSummaryResponse,
    summary="Get summary details"
)
async def get_audio_summary(summary_id: str):
    """Retrieve audio summary details."""
    service = get_surreal_service()

    summary = await get_summary_by_id(service, summary_id)
    if not summary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Résumé audio non trouvé: {summary_id}"
        )

    return format_summary_response(summary)


@router.delete(
    "/api/audio-summaries/{summary_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete audio summary"
)
async def delete_audio_summary(summary_id: str):
    """Delete an audio summary and its associated files."""
    service = get_surreal_service()

    summary = await get_summary_by_id(service, summary_id)
    if not summary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Résumé audio non trouvé: {summary_id}"
        )

    record_id = summary_id.replace("audio_summary:", "")

    # Delete script file
    script_path = summary.get("script_path")
    if script_path and os.path.exists(script_path):
        try:
            os.remove(script_path)
            # Also try to remove JSON version (handle both .md and .txt extensions)
            json_path = script_path.replace("_script.md", "_script.json").replace("_script.txt", "_script.json")
            if os.path.exists(json_path):
                os.remove(json_path)
            logger.info(f"Script files deleted: {script_path}")
        except Exception as e:
            logger.warning(f"Error deleting script file: {e}")

    # Delete audio file
    audio_path = summary.get("audio_path")
    if audio_path and os.path.exists(audio_path):
        try:
            os.remove(audio_path)
            logger.info(f"Audio file deleted: {audio_path}")
        except Exception as e:
            logger.warning(f"Error deleting audio file: {e}")

    # Delete database record
    await service.query(
        "DELETE audio_summary WHERE id = type::thing('audio_summary', $summary_id)",
        {"summary_id": record_id}
    )

    logger.info(f"Audio summary deleted: {summary_id}")
    return None


# ============================================================================
# Generation Endpoint
# ============================================================================

@router.post(
    "/api/audio-summaries/{summary_id}/generate",
    summary="Generate audio summary"
)
async def generate_audio_summary(
    summary_id: str,
    request: Optional[AudioSummaryGenerateRequest] = None
):
    """
    Generate audio for an existing summary.

    Returns an SSE stream with progress updates.
    """
    service = get_surreal_service()

    # Retrieve the summary
    summary = await get_summary_by_id(service, summary_id)
    if not summary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Résumé audio non trouvé: {summary_id}"
        )

    # Get configuration
    source_docs = summary.get("source_documents", [])
    voice_config = summary.get("voice_config", {})
    course_id = summary.get("course_id", "")
    name = summary.get("name", "")

    # Extract doc_ids
    source_doc_ids = []
    for doc in source_docs:
        if isinstance(doc, dict):
            source_doc_ids.append(doc.get("doc_id", ""))
        elif isinstance(doc, str):
            source_doc_ids.append(doc)

    if not source_doc_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Aucun document source trouvé pour ce résumé"
        )

    # Model ID and options
    model_id = request.model_id if request else None
    regenerate_script = request.regenerate_script if request else False

    # Check if script already exists and we don't need to regenerate
    generate_script_only = False
    if summary.get("status") == "script_ready" and not regenerate_script:
        # Script exists, just generate audio
        generate_script_only = False
    elif summary.get("status") == "completed" and not regenerate_script:
        # Already completed, nothing to do
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Le résumé audio a déjà été généré. Utilisez regenerate_script=true pour regénérer."
        )

    async def event_stream():
        """Generate SSE events for progress updates."""
        audio_summary_service = get_audio_summary_service()

        try:
            async for update in audio_summary_service.generate_audio_summary(
                summary_id=summary_id,
                course_id=course_id,
                source_document_ids=source_doc_ids,
                name=name,
                voice_titles=voice_config.get("titles", "fr-CA-SylvieNeural"),
                model_id=model_id,
                generate_script_only=generate_script_only
            ):
                yield f"data: {json.dumps(update)}\n\n"

        except Exception as e:
            logger.error(f"Error in generation stream: {e}")
            yield f"data: {json.dumps({'status': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


# ============================================================================
# File Endpoints
# ============================================================================

@router.get(
    "/api/audio-summaries/{summary_id}/script",
    summary="Download script file"
)
async def download_script(summary_id: str):
    """Download the generated script as a markdown file."""
    service = get_surreal_service()

    summary = await get_summary_by_id(service, summary_id)
    if not summary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Résumé audio non trouvé: {summary_id}"
        )

    script_path = summary.get("script_path")
    if not script_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Script non encore généré"
        )

    if not os.path.exists(script_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Fichier script non trouvé sur le serveur"
        )

    name = summary.get("name", "script")
    safe_name = name.replace(" ", "_")[:30]

    return FileResponse(
        script_path,
        media_type="text/markdown; charset=utf-8",
        filename=f"{safe_name}_script.md"
    )


@router.get(
    "/api/audio-summaries/{summary_id}/audio",
    summary="Stream audio file"
)
async def stream_audio(summary_id: str):
    """Stream or download the generated MP3 file."""
    service = get_surreal_service()

    summary = await get_summary_by_id(service, summary_id)
    if not summary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Résumé audio non trouvé: {summary_id}"
        )

    audio_path = summary.get("audio_path")
    if not audio_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Audio non encore généré"
        )

    if not os.path.exists(audio_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Fichier audio non trouvé sur le serveur"
        )

    name = summary.get("name", "audio")
    safe_name = name.replace(" ", "_")[:30]

    return FileResponse(
        audio_path,
        media_type="audio/mpeg",
        filename=f"{safe_name}.mp3"
    )
