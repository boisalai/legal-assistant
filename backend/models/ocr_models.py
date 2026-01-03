"""
Pydantic models for OCR book scanning.

Models for OCR job status, progress events, and page results.
"""

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class OCREngine(str, Enum):
    """OCR engine choice."""

    DOCLING = "docling"  # Docling with VLM - local, MLX accelerated on Apple Silicon (default)
    PADDLEOCR_VL = "paddleocr_vl"  # PaddleOCR-VL (Transformers) - ~4 GB RAM
    MLX_DOTS_OCR = "mlx_dots_ocr"  # dots.ocr via MLX - model unavailable


class OCRJobStatus(str, Enum):
    """Status of an OCR job."""

    PENDING = "pending"
    EXTRACTING_ZIP = "extracting_zip"
    LOADING_MODEL = "loading_model"
    PROCESSING_PAGES = "processing_pages"
    POST_PROCESSING = "post_processing"
    GENERATING_OUTPUT = "generating_output"
    COMPLETED = "completed"
    ERROR = "error"


class OCRProgressEvent(BaseModel):
    """SSE progress event during OCR processing."""

    status: OCRJobStatus
    current_page: int = 0
    total_pages: int = 0
    images_extracted: int = 0
    message: str
    percentage: int = 0


class OCRPageResult(BaseModel):
    """Result of OCR processing for a single page."""

    page_num: int
    text: str
    images: List[str] = Field(default_factory=list)  # Relative paths to extracted images
    error: Optional[str] = None
