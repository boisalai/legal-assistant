"""
OCR Service for book scanning.

Uses PaddleOCR-VL for text extraction and OpenCV for image detection.
Adapted from ocr_livre_images_light.py reference script.
"""

import asyncio
import logging
import os
import re
import shutil
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path
from typing import AsyncGenerator, List, Optional, Tuple

import numpy as np
from PIL import Image

from config.settings import settings
from models.ocr_models import OCRJobStatus, OCRPageResult, OCRProgressEvent

logger = logging.getLogger(__name__)


class OCRConfig:
    """OCR configuration."""

    MODEL_ID = "PaddlePaddle/PaddleOCR-VL"
    IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".tiff", ".bmp"}
    PDF_EXTENSIONS = {".pdf"}
    MAX_NEW_TOKENS = 4096
    IMAGE_QUALITY = 95
    MIN_IMAGE_SIZE = 100
    IMAGE_VARIANCE_THRESHOLD = 500
    PDF_DPI = 200  # Resolution for PDF to image conversion


class OCRService:
    """Service for OCR processing of scanned books."""

    def __init__(self):
        self.model = None
        self.processor = None
        self.device = None
        self._model_loaded = False

    def _get_device(self) -> str:
        """Detect the best available device."""
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

    async def load_model(self) -> None:
        """Load the PaddleOCR-VL model."""
        if self._model_loaded:
            return

        import torch
        from transformers import AutoModelForCausalLM, AutoProcessor

        self.device = self._get_device()
        dtype = self._get_dtype(self.device)

        logger.info(f"Loading PaddleOCR-VL on {self.device}...")

        self.processor = AutoProcessor.from_pretrained(
            OCRConfig.MODEL_ID, trust_remote_code=True
        )

        self.model = (
            AutoModelForCausalLM.from_pretrained(
                OCRConfig.MODEL_ID,
                trust_remote_code=True,
                torch_dtype=dtype,
                low_cpu_mem_usage=True,
            )
            .to(self.device)
            .eval()
        )

        self._model_loaded = True
        logger.info("PaddleOCR-VL model loaded successfully")

    def _detect_image_regions(
        self, image_path: Path, min_size: int = 100
    ) -> List[Tuple[int, int, int, int]]:
        """
        Detect image regions in a page using OpenCV heuristics.

        Uses adaptive thresholding and contour detection to find
        regions that are likely images (not text).
        """
        try:
            import cv2
        except ImportError:
            logger.warning("OpenCV not available, using simple detection")
            return self._detect_image_regions_simple(image_path, min_size)

        img = cv2.imread(str(image_path))
        if img is None:
            return []

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        height, width = gray.shape

        regions = []

        # Adaptive threshold
        thresh = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 11, 2
        )

        # Dilate to connect regions
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
        dilated = cv2.dilate(thresh, kernel, iterations=3)

        # Find contours
        contours, _ = cv2.findContours(
            dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )

        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)

            # Filter by size
            if w < min_size or h < min_size:
                continue
            if w > width * 0.9 and h > height * 0.9:
                continue

            roi = gray[y : y + h, x : x + w]
            variance = np.var(roi)
            aspect_ratio = w / h

            if (
                variance > OCRConfig.IMAGE_VARIANCE_THRESHOLD
                and 0.2 < aspect_ratio < 5
            ):
                hist = cv2.calcHist([roi], [0], None, [256], [0, 256])
                hist = hist.flatten() / hist.sum()
                extreme_ratio = hist[:30].sum() + hist[225:].sum()

                if extreme_ratio < 0.5:
                    regions.append((x, y, x + w, y + h))

        return self._merge_overlapping_regions(regions)

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

    async def _ocr_page(self, image_path: Path) -> str:
        """Perform OCR on a single page."""
        import torch

        image = Image.open(image_path).convert("RGB")

        messages = [{"role": "user", "content": "OCR"}]
        text = self.processor.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )

        inputs = self.processor(
            text=[text], images=[image], return_tensors="pt"
        ).to(self.device)

        with torch.no_grad():
            generated = self.model.generate(
                **inputs,
                max_new_tokens=OCRConfig.MAX_NEW_TOKENS,
                do_sample=False,
                pad_token_id=self.processor.tokenizer.pad_token_id,
            )

        response = self.processor.batch_decode(
            generated[:, inputs["input_ids"].shape[1] :], skip_special_tokens=True
        )[0]

        return response.strip()

    async def process_page(
        self,
        image_path: Path,
        output_dir: Path,
        page_num: int,
        extract_images: bool = True,
    ) -> OCRPageResult:
        """Process a single page: OCR + optional image extraction."""
        result = OCRPageResult(page_num=page_num, text="", images=[])

        # OCR
        try:
            result.text = await self._ocr_page(image_path)
        except Exception as e:
            logger.error(f"OCR error on page {page_num}: {e}")
            result.error = str(e)
            result.text = f"*[OCR Error: {e}]*"

        # Image extraction
        if extract_images:
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
            root_path = Path(root)
            for f in files:
                if Path(f).suffix.lower() in OCRConfig.PDF_EXTENSIONS:
                    pdf_path = root_path / f
                    try:
                        doc = fitz.open(pdf_path)
                        pdf_stem = pdf_path.stem

                        for page_num in range(len(doc)):
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
                        logger.info(
                            f"Converted {pdf_path.name}: {len(doc)} pages"
                        )

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
        lines.append("Modele OCR : PaddleOCR-VL")
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
    ) -> AsyncGenerator[OCRProgressEvent, None]:
        """
        Process a ZIP file containing scanned pages.

        Yields OCRProgressEvent for SSE streaming.
        """
        work_dir = Path(tempfile.mkdtemp(prefix="ocr_"))
        extract_dir = work_dir / "pages"
        output_dir = work_dir / "output"

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
            yield OCRProgressEvent(
                status=OCRJobStatus.PROCESSING_PAGES,
                total_pages=total_pages,
                message="Chargement du modele OCR...",
                percentage=10,
            )

            await self.load_model()

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
                    img_path, output_dir, page_num, extract_images
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

            markdown_content = self._generate_markdown(pages_results, title, start_page)

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
