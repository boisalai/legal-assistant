"""
Routes API for OCR book scanning.

Endpoints:
- POST /api/admin/ocr/process - Upload ZIP and start OCR (SSE streaming)
- GET /api/admin/ocr/download/{filename} - Download result ZIP
- GET /api/admin/ocr/results - List available results
"""

import json
import logging
import shutil
import tempfile
import uuid
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse, StreamingResponse

from auth.helpers import require_admin
from config.settings import settings
from models.ocr_models import OCREngine, OCRJobStatus, OCRProgressEvent
from services.ocr_service import get_ocr_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin/ocr", tags=["OCR"])


def _parse_form_bool(value: str, default: bool = True) -> bool:
    """Parse form boolean value (handles 'true'/'false' strings)."""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() == "true"
    return default


@router.post("/process", summary="Process scanned book (SSE)")
async def process_ocr(
    file: UploadFile = File(..., description="ZIP file containing JPG page images"),
    title: Optional[str] = Form(default=None, description="Book title"),
    start_page: int = Form(default=1, ge=1, description="Starting page number"),
    extract_images: str = Form(default="true", description="Extract embedded images"),
    post_process_with_llm: str = Form(default="false", description="Clean with LLM"),
    model_id: Optional[str] = Form(default=None, description="LLM model ID"),
    ocr_engine: str = Form(
        default="docling",
        description="OCR engine: docling (recommended), paddleocr_vl, or mlx_dots_ocr",
    ),
    _user_id: str = Depends(require_admin),
):
    """
    Upload a ZIP file with scanned book pages and start OCR processing.

    Returns SSE stream with progress updates.

    OCR Engines:
    - docling: Docling VLM - local, MLX accelerated on Apple Silicon (default, recommended)
    - paddleocr_vl: PaddleOCR-VL - ~4 GB RAM, supports image extraction
    - mlx_dots_ocr: dots.ocr via MLX - model currently unavailable

    Event types:
    - extracting_zip: ZIP extraction in progress
    - loading_model: Loading OCR model
    - processing_pages: OCR processing pages
    - post_processing: LLM cleanup
    - generating_output: Creating output files
    - completed: Processing done (message contains filename for download)
    - error: Error occurred
    """
    # Validate file type
    if not file.filename or not file.filename.lower().endswith(".zip"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Le fichier doit etre au format ZIP",
        )

    # Save uploaded file to temp location
    temp_dir = Path(tempfile.mkdtemp(prefix="ocr_upload_"))
    temp_zip = temp_dir / f"{uuid.uuid4().hex}.zip"

    try:
        content = await file.read()
        temp_zip.write_bytes(content)
        logger.info(f"Uploaded ZIP saved: {temp_zip} ({len(content)} bytes)")
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de l'upload: {str(e)}",
        )

    # Parse OCR engine
    try:
        engine = OCREngine(ocr_engine)
    except ValueError:
        engine = OCREngine.DOCLING

    async def event_stream():
        """Generate SSE events for OCR progress."""
        ocr_service = get_ocr_service()

        try:
            async for event in ocr_service.process_zip(
                zip_path=temp_zip,
                title=title,
                start_page=start_page,
                extract_images=_parse_form_bool(extract_images, default=True),
                post_process_with_llm=_parse_form_bool(post_process_with_llm, default=False),
                model_id=model_id,
                engine=engine,
            ):
                yield f"data: {json.dumps(event.model_dump())}\n\n"

        except Exception as e:
            logger.error(f"OCR stream error: {e}", exc_info=True)
            error_event = OCRProgressEvent(
                status=OCRJobStatus.ERROR,
                message=str(e),
                percentage=0,
            )
            yield f"data: {json.dumps(error_event.model_dump())}\n\n"

        finally:
            # Cleanup temp upload
            try:
                shutil.rmtree(temp_dir)
            except Exception as e:
                logger.warning(f"Failed to cleanup temp: {e}")

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/download/{filename}", summary="Download OCR result")
async def download_ocr_result(
    filename: str,
    _user_id: str = Depends(require_admin),
):
    """
    Download the processed OCR result ZIP file.

    The filename is returned in the 'completed' SSE event message.
    """
    results_dir = Path(settings.upload_dir) / "ocr_results"
    file_path = results_dir / filename

    # Security: prevent path traversal
    try:
        file_path = file_path.resolve()
        if not str(file_path).startswith(str(results_dir.resolve())):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Acces refuse",
            )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Chemin invalide",
        )

    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Fichier non trouve",
        )

    return FileResponse(
        file_path,
        media_type="application/zip",
        filename=filename,
    )


@router.get("/results", summary="List OCR results")
async def list_ocr_results(
    _user_id: str = Depends(require_admin),
):
    """List available OCR result files for download."""
    results_dir = Path(settings.upload_dir) / "ocr_results"

    if not results_dir.exists():
        return {"results": []}

    results = []
    for f in results_dir.glob("ocr_*.zip"):
        stat = f.stat()
        results.append(
            {
                "filename": f.name,
                "size_bytes": stat.st_size,
                "created_at": stat.st_mtime,
            }
        )

    # Sort by creation time, newest first
    results.sort(key=lambda x: x["created_at"], reverse=True)

    return {"results": results}
