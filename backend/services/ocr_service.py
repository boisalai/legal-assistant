"""
OCR Service for book scanning.

Supports OCR engines:
- Docling: Local VLM with MLX acceleration on Apple Silicon (default, recommended)
- PaddleOCR-VL: Local model (~5 sec/page), ~4 GB RAM, supports image extraction
- MLX dots.ocr: Apple Silicon optimized - model currently unavailable

Adapted from ocr_livre_images_light.py and ocr_livre_mlx.py reference scripts.
"""

import asyncio
import logging
import os
import platform
import re
import shutil
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path
from typing import AsyncGenerator, List, Optional, Tuple

import numpy as np
from PIL import Image

# Increase PIL decompression bomb limit for high-resolution scanned books
# Default is ~178M pixels, we allow up to 500M pixels (~22000x22000)
Image.MAX_IMAGE_PIXELS = 500_000_000

from config.settings import settings
from models.ocr_models import OCREngine, OCRJobStatus, OCRPageResult, OCRProgressEvent

logger = logging.getLogger(__name__)


class OCRConfig:
    """OCR configuration."""

    # Docling config (local VLM with MLX acceleration)
    DOCLING_VLM_MODEL = "granite_docling"  # GraniteDocling VLM for scanned documents

    # PaddleOCR-VL config
    PADDLE_MODEL_ID = "PaddlePaddle/PaddleOCR-VL"

    # MLX dots.ocr config (model currently unavailable)
    MLX_MODEL_ID = "mlx-community/dots.ocr-3B-4bit"
    MLX_PROMPT = "Convert this page to Markdown. Preserve all text, paragraphs, and formatting."

    # Common config
    IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".tiff", ".bmp"}
    PDF_EXTENSIONS = {".pdf"}
    MAX_NEW_TOKENS = 4096
    IMAGE_QUALITY = 95
    MIN_IMAGE_SIZE = 100
    IMAGE_VARIANCE_THRESHOLD = 500
    PDF_DPI = 200  # Resolution for PDF to image conversion

    # Image resizing for large scans (prevents memory issues and speeds up OCR)
    MAX_IMAGE_DIMENSION = 4000  # Max width or height in pixels
    RESIZE_QUALITY = Image.Resampling.LANCZOS  # High quality downsampling


class OCRService:
    """Service for OCR processing of scanned books."""

    def __init__(self):
        # Docling state
        self._docling_converter = None
        self._docling_loaded = False

        # PaddleOCR-VL state
        self._paddle_model = None
        self._paddle_processor = None
        self._paddle_device = None
        self._paddle_loaded = False

        # MLX dots.ocr state
        self._mlx_model = None
        self._mlx_processor = None
        self._mlx_loaded = False

        # Current engine
        self._current_engine: Optional[OCREngine] = None

    def _is_apple_silicon(self) -> bool:
        """Check if running on Apple Silicon."""
        return platform.system() == "Darwin" and platform.machine() == "arm64"

    def _resize_image_if_needed(self, image_path: Path) -> Path:
        """
        Resize image if it exceeds MAX_IMAGE_DIMENSION.

        Returns the path to the resized image (or original if no resize needed).
        Creates a temporary file for resized images.
        """
        img = Image.open(image_path)
        width, height = img.size
        max_dim = OCRConfig.MAX_IMAGE_DIMENSION

        # Check if resize is needed
        if width <= max_dim and height <= max_dim:
            img.close()
            return image_path

        # Calculate new dimensions maintaining aspect ratio
        if width > height:
            new_width = max_dim
            new_height = int(height * (max_dim / width))
        else:
            new_height = max_dim
            new_width = int(width * (max_dim / height))

        logger.info(
            f"Resizing image from {width}x{height} to {new_width}x{new_height} "
            f"({width * height / 1_000_000:.1f}M -> {new_width * new_height / 1_000_000:.1f}M pixels)"
        )

        # Resize with high quality
        img_resized = img.resize((new_width, new_height), OCRConfig.RESIZE_QUALITY)
        img.close()

        # Save to temp file
        temp_path = image_path.parent / f"_resized_{image_path.name}"
        img_resized.save(temp_path, quality=OCRConfig.IMAGE_QUALITY)
        img_resized.close()

        return temp_path

    def _get_device(self) -> str:
        """Detect the best available device for PyTorch."""
        import torch

        if torch.cuda.is_available():
            return "cuda"
        elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            return "mps"
        return "cpu"

    def _get_dtype(self, device: str):
        """Get optimal dtype for device."""
        import torch

        if device == "mps":
            return torch.float16
        elif device == "cuda":
            return torch.bfloat16
        return torch.float32

    async def load_model(self, engine: OCREngine = OCREngine.DOCLING) -> None:
        """Load the OCR model for the specified engine."""
        if engine == OCREngine.DOCLING:
            await self._load_docling()
        elif engine == OCREngine.MLX_DOTS_OCR:
            await self._load_mlx_model()
        else:
            await self._load_paddle_model()
        self._current_engine = engine

    async def _load_docling(self) -> None:
        """Load the Docling converter with VLM pipeline."""
        if self._docling_loaded:
            return

        logger.info("Loading Docling with VLM pipeline...")

        def _init_docling():
            from docling.datamodel.pipeline_options import VlmPipelineOptions
            from docling.document_converter import DocumentConverter, PdfFormatOption
            from docling.pipeline.vlm_pipeline import VlmPipeline

            # Configure VLM pipeline for scanned documents
            vlm_options = VlmPipelineOptions(
                vlm_model=OCRConfig.DOCLING_VLM_MODEL,
            )

            converter = DocumentConverter(
                format_options={
                    "pdf": PdfFormatOption(
                        pipeline_cls=VlmPipeline,
                        pipeline_options=vlm_options,
                    ),
                }
            )
            return converter

        self._docling_converter = await asyncio.to_thread(_init_docling)
        self._docling_loaded = True
        logger.info("Docling VLM pipeline loaded successfully")

    async def _load_paddle_model(self) -> None:
        """Load the PaddleOCR-VL model."""
        if self._paddle_loaded:
            return

        import torch
        from transformers import AutoModelForCausalLM, AutoProcessor

        self._paddle_device = self._get_device()
        dtype = self._get_dtype(self._paddle_device)

        logger.info(f"Loading PaddleOCR-VL on {self._paddle_device}...")

        self._paddle_processor = AutoProcessor.from_pretrained(
            OCRConfig.PADDLE_MODEL_ID, trust_remote_code=True
        )

        self._paddle_model = (
            AutoModelForCausalLM.from_pretrained(
                OCRConfig.PADDLE_MODEL_ID,
                trust_remote_code=True,
                torch_dtype=dtype,
                low_cpu_mem_usage=True,
            )
            .to(self._paddle_device)
            .eval()
        )

        self._paddle_loaded = True
        logger.info("PaddleOCR-VL model loaded successfully")

    async def _load_mlx_model(self) -> None:
        """Load the MLX dots.ocr model."""
        if self._mlx_loaded:
            return

        if not self._is_apple_silicon():
            raise RuntimeError(
                "MLX dots.ocr requires Apple Silicon (M1/M2/M3). "
                "Use PaddleOCR-VL engine instead."
            )

        from mlx_vlm import load

        logger.info(f"Loading MLX dots.ocr ({OCRConfig.MLX_MODEL_ID})...")

        # Load model in thread to avoid blocking
        self._mlx_model, self._mlx_processor = await asyncio.to_thread(
            load, OCRConfig.MLX_MODEL_ID
        )

        self._mlx_loaded = True
        logger.info("MLX dots.ocr model loaded successfully")

    def _detect_image_regions(
        self, image_path: Path, min_size: int = 100
    ) -> List[Tuple[int, int, int, int]]:
        """
        Detect image regions in a page.

        Uses PIL-based heuristic detection (lighter than OpenCV).
        """
        # Use simple PIL-based detection (more reliable, less memory)
        return self._detect_image_regions_simple(image_path, min_size)

    def _detect_image_regions_simple(
        self, image_path: Path, min_size: int = 100
    ) -> List[Tuple[int, int, int, int]]:
        """
        Simple image region detection without OpenCV.

        Divides the image into a grid and analyzes variance.
        """
        img = Image.open(image_path).convert("L")
        img_array = np.array(img)

        height, width = img_array.shape
        regions = []

        cell_size = 200

        for y in range(0, height - cell_size, cell_size // 2):
            for x in range(0, width - cell_size, cell_size // 2):
                cell = img_array[y : y + cell_size, x : x + cell_size]
                variance = np.var(cell)

                # Images have intermediate variance
                if 1000 < variance < 5000:
                    regions.append((x, y, x + cell_size, y + cell_size))

        regions = self._merge_overlapping_regions(regions)

        # Filter by size
        regions = [
            (x1, y1, x2, y2)
            for x1, y1, x2, y2 in regions
            if (x2 - x1) >= min_size and (y2 - y1) >= min_size
        ]

        return regions

    def _merge_overlapping_regions(
        self, regions: List[Tuple]
    ) -> List[Tuple[int, int, int, int]]:
        """Merge overlapping regions."""
        if not regions:
            return []

        regions = sorted(regions, key=lambda r: (r[0], r[1]))
        merged = [regions[0]]

        for current in regions[1:]:
            last = merged[-1]
            x1 = max(last[0], current[0])
            y1 = max(last[1], current[1])
            x2 = min(last[2], current[2])
            y2 = min(last[3], current[3])

            if x1 < x2 and y1 < y2:
                merged[-1] = (
                    min(last[0], current[0]),
                    min(last[1], current[1]),
                    max(last[2], current[2]),
                    max(last[3], current[3]),
                )
            else:
                merged.append(current)

        return merged

    def _extract_images_from_page(
        self,
        image_path: Path,
        regions: List[Tuple],
        output_dir: Path,
        page_num: int,
    ) -> List[str]:
        """Extract detected image regions from a page."""
        if not regions:
            return []

        source_image = Image.open(image_path).convert("RGB")
        images_dir = output_dir / "images"
        images_dir.mkdir(exist_ok=True)

        extracted = []

        for i, (x1, y1, x2, y2) in enumerate(regions):
            cropped = source_image.crop((x1, y1, x2, y2))
            filename = f"page_{page_num:03d}_img_{i + 1:03d}.jpg"
            filepath = images_dir / filename
            cropped.save(filepath, quality=OCRConfig.IMAGE_QUALITY)
            extracted.append(f"images/{filename}")

        return extracted

    async def _ocr_page(
        self, image_path: Path, engine: OCREngine = OCREngine.DOCLING
    ) -> str:
        """Perform OCR on a single page using the specified engine."""
        if engine == OCREngine.DOCLING:
            return await self._ocr_page_docling(image_path)
        elif engine == OCREngine.MLX_DOTS_OCR:
            return await self._ocr_page_mlx(image_path)
        return await self._ocr_page_paddle(image_path)

    async def _ocr_page_paddle(self, image_path: Path) -> str:
        """Perform OCR using PaddleOCR-VL."""
        import torch

        image = Image.open(image_path).convert("RGB")

        messages = [{"role": "user", "content": "OCR"}]
        text = self._paddle_processor.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )

        inputs = self._paddle_processor(
            text=[text], images=[image], return_tensors="pt"
        ).to(self._paddle_device)

        with torch.no_grad():
            generated = self._paddle_model.generate(
                **inputs,
                max_new_tokens=OCRConfig.MAX_NEW_TOKENS,
                do_sample=False,
                pad_token_id=self._paddle_processor.tokenizer.pad_token_id,
            )

        response = self._paddle_processor.batch_decode(
            generated[:, inputs["input_ids"].shape[1] :], skip_special_tokens=True
        )[0]

        return response.strip()

    async def _ocr_page_mlx(self, image_path: Path) -> str:
        """Perform OCR using MLX dots.ocr."""
        from mlx_vlm import generate
        from mlx_vlm.utils import load_image

        # Load image using mlx_vlm utility
        image = await asyncio.to_thread(load_image, str(image_path))

        # Generate text using MLX
        output = await asyncio.to_thread(
            generate,
            self._mlx_model,
            self._mlx_processor,
            image,
            OCRConfig.MLX_PROMPT,
            max_tokens=OCRConfig.MAX_NEW_TOKENS,
            temperature=0.0,  # Deterministic for OCR
            verbose=False,
        )

        return output.strip()

    async def _ocr_page_docling(self, image_path: Path) -> str:
        """Perform OCR using Docling VLM pipeline."""
        from docling_core.types.doc import ImageRefMode

        # Resize image if too large (prevents memory issues)
        resized_path = self._resize_image_if_needed(image_path)
        use_resized = resized_path != image_path

        def _convert_image():
            # Convert single image using Docling
            result = self._docling_converter.convert(str(resized_path))
            # Export to markdown
            return result.document.export_to_markdown(image_mode=ImageRefMode.EMBEDDED)

        try:
            markdown = await asyncio.to_thread(_convert_image)
            return markdown.strip()
        finally:
            # Cleanup resized temp file
            if use_resized and resized_path.exists():
                try:
                    resized_path.unlink()
                except Exception:
                    pass

    async def process_page(
        self,
        image_path: Path,
        output_dir: Path,
        page_num: int,
        extract_images: bool = True,
        engine: OCREngine = OCREngine.DOCLING,
    ) -> OCRPageResult:
        """Process a single page: OCR + optional image extraction."""
        result = OCRPageResult(page_num=page_num, text="", images=[])

        # OCR
        try:
            result.text = await self._ocr_page(image_path, engine)
        except Exception as e:
            logger.error(f"OCR error on page {page_num}: {e}")
            result.error = str(e)
            result.text = f"*[OCR Error: {e}]*"

        # Image extraction (only for PaddleOCR-VL engine - Docling handles images internally)
        if extract_images and engine == OCREngine.PADDLEOCR_VL:
            try:
                regions = self._detect_image_regions(image_path)
                if regions:
                    result.images = self._extract_images_from_page(
                        image_path, regions, output_dir, page_num
                    )
            except Exception as e:
                logger.warning(f"Image extraction error on page {page_num}: {e}")

        return result

    async def post_process_with_llm(
        self,
        markdown_content: str,
        model_id: Optional[str] = None,
    ) -> str:
        """Post-process OCR output with LLM to clean errors and detect chapters."""
        from agno.agent import Agent

        from services.model_factory import create_model

        model = create_model(model_id or settings.model_id)

        agent = Agent(
            model=model,
            description="Tu es un expert en correction de texte OCR.",
            instructions=[
                "Corrige les erreurs d'OCR courantes (caracteres mal reconnus, mots colles)",
                "Detecte et formate les titres de chapitres avec # markdown",
                "Preserve la structure du document",
                "Ne modifie pas le sens du texte",
            ],
        )

        # Limit content to avoid context overflow
        content_to_process = markdown_content[:50000]

        prompt = f"""Corrige ce texte OCR et formate les chapitres en markdown:

{content_to_process}

Retourne UNIQUEMENT le texte corrige, sans commentaires."""

        response = await asyncio.to_thread(agent.run, prompt)
        return response.content if response else markdown_content

    def _convert_pdfs_to_images(self, input_dir: Path) -> int:
        """
        Convert all PDF files in directory to images.

        Each page of each PDF is saved as a separate JPG file.
        Returns the number of images created.
        """
        try:
            import fitz  # PyMuPDF
        except ImportError:
            logger.warning("PyMuPDF not installed, skipping PDF conversion")
            return 0

        images_created = 0

        for root, _dirs, files in os.walk(input_dir):
            # Skip __MACOSX directories
            if "__MACOSX" in root:
                continue

            root_path = Path(root)
            for f in files:
                # Skip macOS metadata files
                if f.startswith("._"):
                    continue

                if Path(f).suffix.lower() in OCRConfig.PDF_EXTENSIONS:
                    pdf_path = root_path / f
                    try:
                        doc = fitz.open(pdf_path)
                        pdf_stem = pdf_path.stem
                        num_pages = len(doc)

                        for page_num in range(num_pages):
                            page = doc[page_num]
                            # Render page to image at specified DPI
                            mat = fitz.Matrix(
                                OCRConfig.PDF_DPI / 72, OCRConfig.PDF_DPI / 72
                            )
                            pix = page.get_pixmap(matrix=mat)

                            # Save as JPG
                            img_filename = f"{pdf_stem}_page_{page_num + 1:03d}.jpg"
                            img_path = root_path / img_filename
                            pix.save(str(img_path))
                            images_created += 1

                        doc.close()
                        logger.info(f"Converted {pdf_path.name}: {num_pages} pages")

                        # Remove original PDF after conversion
                        pdf_path.unlink()

                    except Exception as e:
                        logger.error(f"Error converting PDF {pdf_path}: {e}")

        return images_created

    def _collect_images_from_dir(self, input_dir: Path) -> List[Path]:
        """
        Collect and sort image files from directory (including nested).

        Also converts any PDF files to images first.
        """
        # First, convert any PDFs to images
        pdf_images = self._convert_pdfs_to_images(input_dir)
        if pdf_images > 0:
            logger.info(f"Converted PDFs to {pdf_images} images")

        # Then collect all images
        images = []
        for root, _dirs, files in os.walk(input_dir):
            for f in files:
                if Path(f).suffix.lower() in OCRConfig.IMAGE_EXTENSIONS:
                    images.append(Path(root) / f)

        def natural_sort_key(path: Path):
            parts = re.split(r"(\d+)", path.stem)
            return [int(p) if p.isdigit() else p.lower() for p in parts]

        images.sort(key=natural_sort_key)
        return images

    def _generate_markdown(
        self,
        pages_results: List[OCRPageResult],
        title: Optional[str] = None,
        start_page: int = 1,
        engine: OCREngine = OCREngine.DOCLING,
    ) -> str:
        """Generate the final Markdown document."""
        lines = []

        if title:
            lines.append(f"# {title}")
            lines.append("")

        lines.append("---")
        lines.append(
            f"Date d'extraction : {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        )
        lines.append(f"Nombre de pages : {len(pages_results)}")

        total_images = sum(len(r.images) for r in pages_results)
        lines.append(f"Images extraites : {total_images}")

        # Show engine name
        engine_names = {
            OCREngine.DOCLING: "Docling VLM",
            OCREngine.PADDLEOCR_VL: "PaddleOCR-VL",
            OCREngine.MLX_DOTS_OCR: "dots.ocr (MLX)",
        }
        engine_name = engine_names.get(engine, str(engine))
        lines.append(f"Modele OCR : {engine_name}")
        lines.append("---")
        lines.append("")

        for i, page_result in enumerate(pages_results):
            page_num = start_page + i

            lines.append(f"<!-- Page {page_num} -->")
            lines.append("")

            if page_result.text:
                lines.append(page_result.text)
            else:
                lines.append(f"*[Page {page_num} : aucun texte detecte]*")

            for img_path in page_result.images:
                lines.append("")
                lines.append(f"![Figure]({img_path})")

            lines.append("")
            lines.append("---")
            lines.append("")

        return "\n".join(lines)

    async def process_zip(
        self,
        zip_path: Path,
        title: Optional[str] = None,
        start_page: int = 1,
        extract_images: bool = True,
        post_process_with_llm: bool = True,
        model_id: Optional[str] = None,
        engine: OCREngine = OCREngine.DOCLING,
    ) -> AsyncGenerator[OCRProgressEvent, None]:
        """
        Process a ZIP file containing scanned pages.

        Args:
            zip_path: Path to the ZIP file
            title: Optional book title
            start_page: Starting page number
            extract_images: Extract embedded images (only for PaddleOCR-VL)
            post_process_with_llm: Clean OCR errors with LLM
            model_id: LLM model ID for post-processing
            engine: OCR engine to use (docling, paddleocr_vl, or mlx_dots_ocr)

        Yields OCRProgressEvent for SSE streaming.
        """
        work_dir = Path(tempfile.mkdtemp(prefix="ocr_"))
        extract_dir = work_dir / "pages"
        output_dir = work_dir / "output"

        # For Docling and MLX engines, disable image extraction (handled internally or not supported)
        if engine in (OCREngine.DOCLING, OCREngine.MLX_DOTS_OCR):
            extract_images = False

        try:
            # Step 1: Extract ZIP
            yield OCRProgressEvent(
                status=OCRJobStatus.EXTRACTING_ZIP,
                message="Extraction du fichier ZIP...",
                percentage=5,
            )

            with zipfile.ZipFile(zip_path, "r") as zf:
                zf.extractall(extract_dir)

            # Collect images (also converts any PDFs to images)
            yield OCRProgressEvent(
                status=OCRJobStatus.EXTRACTING_ZIP,
                message="Conversion des PDF en images...",
                percentage=8,
            )
            images = self._collect_images_from_dir(extract_dir)

            if not images:
                yield OCRProgressEvent(
                    status=OCRJobStatus.ERROR,
                    message="Aucune image trouvee dans le ZIP",
                    percentage=0,
                )
                return

            total_pages = len(images)
            output_dir.mkdir(parents=True, exist_ok=True)

            # Step 2: Load model
            engine_names = {
                OCREngine.DOCLING: "Docling VLM",
                OCREngine.PADDLEOCR_VL: "PaddleOCR-VL",
                OCREngine.MLX_DOTS_OCR: "dots.ocr (MLX)",
            }
            engine_name = engine_names.get(engine, str(engine))
            yield OCRProgressEvent(
                status=OCRJobStatus.LOADING_MODEL,
                total_pages=total_pages,
                message=f"Chargement du modele {engine_name}...",
                percentage=10,
            )

            await self.load_model(engine)

            # Step 3: Process pages
            pages_results: List[OCRPageResult] = []
            total_images_extracted = 0

            for i, img_path in enumerate(images):
                page_num = start_page + i

                yield OCRProgressEvent(
                    status=OCRJobStatus.PROCESSING_PAGES,
                    current_page=i + 1,
                    total_pages=total_pages,
                    images_extracted=total_images_extracted,
                    message=f"OCR page {page_num}...",
                    percentage=10 + int((i / total_pages) * 70),
                )

                result = await self.process_page(
                    img_path, output_dir, page_num, extract_images, engine
                )
                pages_results.append(result)
                total_images_extracted += len(result.images)

            # Step 4: Generate Markdown
            yield OCRProgressEvent(
                status=OCRJobStatus.GENERATING_OUTPUT,
                current_page=total_pages,
                total_pages=total_pages,
                images_extracted=total_images_extracted,
                message="Generation du document Markdown...",
                percentage=80,
            )

            markdown_content = self._generate_markdown(
                pages_results, title, start_page, engine
            )

            # Step 5: LLM post-processing (optional)
            if post_process_with_llm:
                yield OCRProgressEvent(
                    status=OCRJobStatus.POST_PROCESSING,
                    current_page=total_pages,
                    total_pages=total_pages,
                    images_extracted=total_images_extracted,
                    message="Post-traitement LLM...",
                    percentage=85,
                )

                try:
                    markdown_content = await self.post_process_with_llm(
                        markdown_content, model_id
                    )
                except Exception as e:
                    logger.warning(f"LLM post-processing failed: {e}")

            # Step 6: Save markdown and create output ZIP
            markdown_path = output_dir / "livre.md"
            markdown_path.write_text(markdown_content, encoding="utf-8")

            # Create result ZIP
            result_zip_path = work_dir / "result.zip"
            with zipfile.ZipFile(
                result_zip_path, "w", zipfile.ZIP_DEFLATED
            ) as zf:
                for file_path in output_dir.rglob("*"):
                    if file_path.is_file():
                        arcname = file_path.relative_to(output_dir)
                        zf.write(file_path, arcname)

            # Move result to permanent location
            results_dir = Path(settings.upload_dir) / "ocr_results"
            results_dir.mkdir(parents=True, exist_ok=True)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            final_filename = f"ocr_{timestamp}.zip"
            final_path = results_dir / final_filename
            shutil.move(str(result_zip_path), str(final_path))

            yield OCRProgressEvent(
                status=OCRJobStatus.COMPLETED,
                current_page=total_pages,
                total_pages=total_pages,
                images_extracted=total_images_extracted,
                message=final_filename,
                percentage=100,
            )

        except Exception as e:
            logger.error(f"OCR processing error: {e}", exc_info=True)
            yield OCRProgressEvent(
                status=OCRJobStatus.ERROR,
                message=str(e),
                percentage=0,
            )

        finally:
            # Cleanup work directory
            try:
                shutil.rmtree(work_dir)
            except Exception as e:
                logger.warning(f"Failed to cleanup work dir: {e}")


# Singleton
_ocr_service: Optional[OCRService] = None


def get_ocr_service() -> OCRService:
    """Get the OCR service singleton."""
    global _ocr_service
    if _ocr_service is None:
        _ocr_service = OCRService()
    return _ocr_service
