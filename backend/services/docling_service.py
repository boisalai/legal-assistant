"""
Service d'extraction de documents avec Docling.

Docling (IBM/RedHat) offre une extraction avancée de PDFs:
- OCR pour PDFs scannés
- Extraction de tableaux avec structure préservée
- Reconnaissance de formules et code
- Layout analysis

Modèles supportés:
- Standard Pipeline: Rapide, bon pour PDFs textuels
- VLM Pipeline (Granite-Docling): Précis, OCR avancé, tableaux complexes
"""

import logging
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# Flag pour vérifier si Docling est disponible
DOCLING_AVAILABLE = False
try:
    from docling.document_converter import DocumentConverter
    from docling.datamodel.base_models import InputFormat
    DOCLING_AVAILABLE = True
except ImportError:
    logger.warning("Docling non installé. Installer avec: uv sync --extra docling")


@dataclass
class DoclingExtractionResult:
    """Résultat de l'extraction Docling."""
    success: bool
    markdown: str = ""
    text: str = ""
    tables: list = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
    error: Optional[str] = None
    extraction_method: str = "docling"


class DoclingService:
    """
    Service d'extraction de documents PDF avec Docling.

    Modes d'extraction:
    - standard: Pipeline standard (rapide, ~0.5s/page)
    - vlm: Pipeline VLM avec Granite-Docling (précis, ~1s/page, OCR avancé)
    """

    def __init__(self, use_vlm: bool = False, vlm_model: str = "granite_docling"):
        """
        Initialise le service Docling.

        Args:
            use_vlm: Utiliser le pipeline VLM (plus lent mais plus précis)
            vlm_model: Modèle VLM à utiliser (granite_docling par défaut)
        """
        self.use_vlm = use_vlm
        self.vlm_model = vlm_model
        self._converter: Optional["DocumentConverter"] = None

        if not DOCLING_AVAILABLE:
            logger.warning("Docling non disponible - extraction limitée à pypdf")

    def _get_converter(self) -> Optional["DocumentConverter"]:
        """Obtient ou crée le convertisseur Docling (lazy loading)."""
        if not DOCLING_AVAILABLE:
            return None

        if self._converter is None:
            try:
                if self.use_vlm:
                    # Pipeline VLM avec Granite-Docling
                    from docling.pipeline.vlm_pipeline import VlmPipeline
                    self._converter = DocumentConverter(
                        pipeline=VlmPipeline(model=self.vlm_model)
                    )
                    logger.info(f"Docling VLM initialisé avec {self.vlm_model}")
                else:
                    # Pipeline standard SANS OCR (evite telecharger modeles)
                    # Pour PDFs numeriques, l'OCR n'est pas necessaire
                    from docling.datamodel.pipeline_options import PdfPipelineOptions
                    from docling.document_converter import PdfFormatOption

                    pipeline_options = PdfPipelineOptions(do_ocr=False)
                    self._converter = DocumentConverter(
                        format_options={
                            InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
                        }
                    )
                    logger.info("Docling standard initialisé (OCR désactivé)")
            except Exception as e:
                logger.error(f"Erreur initialisation Docling: {e}")
                return None

        return self._converter

    async def extract_pdf(self, pdf_path: str | Path) -> DoclingExtractionResult:
        """
        Extrait le contenu d'un fichier PDF.

        Args:
            pdf_path: Chemin vers le fichier PDF

        Returns:
            DoclingExtractionResult avec le contenu extrait
        """
        pdf_path = Path(pdf_path)

        if not pdf_path.exists():
            return DoclingExtractionResult(
                success=False,
                error=f"Fichier non trouvé: {pdf_path}"
            )

        converter = self._get_converter()
        if converter is None:
            return DoclingExtractionResult(
                success=False,
                error="Docling non disponible. Installer avec: uv sync --extra docling"
            )

        try:
            # Conversion du document
            result = converter.convert(str(pdf_path))
            doc = result.document

            # Export en différents formats
            markdown = doc.export_to_markdown()

            # Extraction des tableaux
            tables = []
            if hasattr(doc, 'tables'):
                for table in doc.tables:
                    tables.append({
                        "content": table.export_to_markdown() if hasattr(table, 'export_to_markdown') else str(table),
                        "rows": getattr(table, 'num_rows', 0),
                        "cols": getattr(table, 'num_cols', 0),
                    })

            # Métadonnées
            metadata = {
                "num_pages": getattr(doc, 'num_pages', 0),
                "num_tables": len(tables),
                "extraction_mode": "vlm" if self.use_vlm else "standard",
            }

            return DoclingExtractionResult(
                success=True,
                markdown=markdown,
                text=markdown,  # Fallback
                tables=tables,
                metadata=metadata,
                extraction_method=f"docling-{'vlm' if self.use_vlm else 'standard'}"
            )

        except Exception as e:
            logger.error(f"Erreur extraction Docling: {e}")
            return DoclingExtractionResult(
                success=False,
                error=str(e)
            )

    @staticmethod
    def is_available() -> bool:
        """Vérifie si Docling est disponible."""
        return DOCLING_AVAILABLE


# Singleton pour le service
_docling_service: Optional[DoclingService] = None


def get_docling_service(use_vlm: bool = False) -> DoclingService:
    """Obtient l'instance singleton du service Docling."""
    global _docling_service
    if _docling_service is None:
        _docling_service = DoclingService(use_vlm=use_vlm)
    return _docling_service


# Configuration des méthodes d'extraction disponibles
EXTRACTION_METHODS = {
    "pypdf": {
        "name": "PyPDF (Standard)",
        "description": "Extraction basique de texte - Rapide mais limité",
        "speed": "Très rapide",
        "quality": "Basique",
        "supports_ocr": False,
        "supports_tables": False,
        "recommended_for": "PDFs textuels simples",
        "available": True,  # Toujours disponible
    },
    "docling-standard": {
        "name": "Docling Standard",
        "description": "Extraction avancée avec analyse de layout",
        "speed": "Rapide (~0.5s/page)",
        "quality": "Bonne",
        "supports_ocr": True,
        "supports_tables": True,
        "recommended_for": "PDFs avec tableaux, mise en page complexe",
        "available": DOCLING_AVAILABLE,
    },
    "docling-vlm": {
        "name": "Docling VLM (Granite)",
        "description": "Extraction maximale avec vision-language model",
        "speed": "Lent (~1s/page)",
        "quality": "Excellente",
        "supports_ocr": True,
        "supports_tables": True,
        "recommended_for": "PDFs scannés, tableaux complexes, formules",
        "available": DOCLING_AVAILABLE,
    },
}


def get_available_extraction_methods() -> dict:
    """Retourne les méthodes d'extraction disponibles."""
    return {
        method: info
        for method, info in EXTRACTION_METHODS.items()
        if info["available"]
    }
