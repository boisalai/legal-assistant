"""
Document OCR Task - Background task for automatic PDF OCR.

Runs OCR on uploaded PDFs and creates derived markdown documents.
"""

import logging
from pathlib import Path

from services.surreal_service import get_surreal_service
from services.ocr_service import get_ocr_service
from services.document_service import get_document_service
from services.document_indexing_service import DocumentIndexingService
from models.ocr_models import OCREngine

logger = logging.getLogger(__name__)


async def update_ocr_status(
    document_id: str,
    status: str,
    error: str | None = None
) -> None:
    """Update OCR status in database."""
    surreal = get_surreal_service()
    if not surreal.db:
        await surreal.connect()

    # Normalize document ID
    if not document_id.startswith("document:"):
        document_id = f"document:{document_id}"

    update_data = {"ocr_status": status}
    if error:
        update_data["ocr_error"] = error

    await surreal.query(
        f"UPDATE {document_id} MERGE $data",
        {"data": update_data}
    )
    logger.info(f"Updated OCR status for {document_id}: {status}")


async def run_ocr_for_document(
    document_id: str,
    course_id: str,
    pdf_path: str,
) -> None:
    """
    Background task to run OCR on a PDF document.

    1. Update document status to "processing"
    2. Run OCR using Docling VLM
    3. Save markdown file to disk
    4. Create derived markdown document record
    5. Index markdown for RAG
    6. Update status to "completed" or "error"

    Args:
        document_id: ID of the PDF document
        course_id: ID of the course
        pdf_path: Absolute path to the PDF file
    """
    derived_doc_id = None

    try:
        # Step 1: Update status to processing
        await update_ocr_status(document_id, "processing")

        # Step 2: Run OCR
        logger.info(f"Starting OCR for document {document_id}")
        ocr_service = get_ocr_service()
        pdf_path_obj = Path(pdf_path)

        markdown_content, error = await ocr_service.process_pdf_to_markdown(
            pdf_path_obj,
            engine=OCREngine.DOCLING
        )

        if error:
            await update_ocr_status(document_id, "error", error)
            logger.error(f"OCR failed for {document_id}: {error}")
            return

        if not markdown_content:
            await update_ocr_status(document_id, "error", "Aucun contenu extrait")
            logger.error(f"OCR returned empty content for {document_id}")
            return

        # Step 3: Save markdown file to disk
        # Create markdown file in same directory as PDF
        md_filename = pdf_path_obj.stem + "_ocr.md"
        md_path = pdf_path_obj.parent / md_filename
        md_path.write_text(markdown_content, encoding="utf-8")
        logger.info(f"Saved markdown to {md_path}")

        # Step 4: Create derived document record
        doc_service = get_document_service()

        # Normalize course_id
        if not course_id.startswith("course:"):
            course_id = f"course:{course_id}"

        # Normalize document_id for source_document_id
        source_doc_id = document_id
        if not source_doc_id.startswith("document:"):
            source_doc_id = f"document:{source_doc_id}"

        derived_doc = await doc_service.create_document(
            course_id=course_id,
            filename=md_filename,
            file_path=str(md_path),
            file_size=len(markdown_content.encode("utf-8")),
            file_type="md",
            mime_type="text/markdown",
            extracted_text=markdown_content[:10000],  # First 10k chars for preview
            source_type="upload",
            source_document_id=source_doc_id,
            is_derived=True,
            derivation_type="ocr_extraction"
        )
        derived_doc_id = derived_doc.id
        logger.info(f"Created derived document {derived_doc_id}")

        # Step 5: Index for RAG
        try:
            indexing_service = DocumentIndexingService()
            await indexing_service.index_document(
                document_id=derived_doc_id,
                content=markdown_content,
                course_id=course_id
            )
            logger.info(f"Indexed derived document {derived_doc_id}")
        except Exception as e:
            logger.warning(f"Failed to index document {derived_doc_id}: {e}")
            # Continue even if indexing fails - document is still usable

        # Step 6: Update status to completed
        await update_ocr_status(document_id, "completed")
        logger.info(f"OCR completed successfully for {document_id}")

    except Exception as e:
        logger.error(f"OCR task failed for {document_id}: {e}", exc_info=True)
        await update_ocr_status(document_id, "error", str(e))
