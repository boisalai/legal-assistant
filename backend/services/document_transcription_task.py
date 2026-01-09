"""
Document Transcription Task - Background task for automatic audio transcription.

Runs Whisper transcription on audio files and creates derived markdown documents.
"""

import logging

from services.surreal_service import get_surreal_service

logger = logging.getLogger(__name__)


async def update_transcription_status(
    document_id: str,
    status: str,
    error: str | None = None
) -> None:
    """Update transcription status in database."""
    surreal = get_surreal_service()
    if not surreal.db:
        await surreal.connect()

    # Normalize document ID
    if not document_id.startswith("document:"):
        document_id = f"document:{document_id}"

    update_data = {"transcription_status": status}
    if error:
        update_data["transcription_error"] = error

    await surreal.query(
        f"UPDATE {document_id} MERGE $data",
        {"data": update_data}
    )
    logger.info(f"Updated transcription status for {document_id}: {status}")


async def run_transcription_for_document(
    document_id: str,
    course_id: str,
    audio_path: str,
    language: str = "fr",
) -> None:
    """
    Background task to run transcription on an audio document.

    1. Update document status to "processing"
    2. Run Whisper transcription via TranscriptionWorkflow
    3. Create derived markdown document (handled by workflow)
    4. Update status to "completed" or "error"

    Args:
        document_id: ID of the audio document
        course_id: ID of the course
        audio_path: Absolute path to the audio file
        language: Language code for transcription (default: fr)
    """
    try:
        # Step 1: Update status to processing
        await update_transcription_status(document_id, "processing")

        # Step 2: Run transcription workflow
        logger.info(f"Starting transcription for document {document_id}")

        from workflows.transcribe_audio import TranscriptionWorkflow

        # Create workflow without SSE callbacks (background mode)
        workflow = TranscriptionWorkflow()

        # Normalize IDs
        if not course_id.startswith("course:"):
            course_id = f"course:{course_id}"
        if not document_id.startswith("document:"):
            document_id = f"document:{document_id}"

        # Run the workflow
        result = await workflow.run(
            audio_path=audio_path,
            course_id=course_id,
            language=language,
            create_markdown_doc=True,
            raw_mode=False,
            source_document_id=document_id
        )

        if not result.success:
            error_msg = result.error or "Transcription failed"
            await update_transcription_status(document_id, "error", error_msg)
            logger.error(f"Transcription failed for {document_id}: {error_msg}")
            return

        # Step 3: Update status to completed
        await update_transcription_status(document_id, "completed")
        logger.info(f"Transcription completed for {document_id}, created document {result.document_id}")

    except Exception as e:
        logger.error(f"Transcription task failed for {document_id}: {e}", exc_info=True)
        await update_transcription_status(document_id, "error", str(e))
