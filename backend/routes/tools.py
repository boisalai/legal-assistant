"""
Routes pour les outils indépendants des cours.

Endpoints:
- POST /api/tools/convert-to-markdown - Conversion de documents en markdown
"""

import logging
import tempfile
from pathlib import Path

from fastapi import APIRouter, HTTPException, status, Depends, UploadFile, File
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from auth.helpers import require_auth

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/tools", tags=["Tools"])


class MarkdownConversionResponse(BaseModel):
    """Réponse de conversion en markdown."""
    success: bool
    markdown: str = ""
    filename: str = ""
    error: str = ""


SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".pptx"}


@router.post("/convert-to-markdown", response_model=MarkdownConversionResponse)
async def convert_to_markdown(
    file: UploadFile = File(...),
    user_id: str = Depends(require_auth)
):
    """
    Convertit un document (PDF, DOCX, PPTX) en markdown.

    Utilise la bibliothèque markitdown pour la conversion.
    Retourne le contenu markdown que le frontend peut télécharger.
    """
    try:
        # Validate file extension
        if not file.filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Nom de fichier manquant"
            )

        ext = Path(file.filename).suffix.lower()
        if ext not in SUPPORTED_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Format non supporté: {ext}. Formats acceptés: PDF, DOCX, PPTX"
            )

        # Save uploaded file to temp location
        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp_file:
            content = await file.read()
            tmp_file.write(content)
            tmp_path = tmp_file.name

        try:
            # Convert using markitdown
            from markitdown import MarkItDown

            md = MarkItDown()
            result = md.convert(tmp_path)

            if not result or not result.text_content:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="La conversion n'a produit aucun contenu"
                )

            # Generate output filename
            original_stem = Path(file.filename).stem
            output_filename = f"{original_stem}.md"

            logger.info(f"Converted {file.filename} to markdown: {len(result.text_content)} chars")

            return MarkdownConversionResponse(
                success=True,
                markdown=result.text_content,
                filename=output_filename
            )

        finally:
            # Clean up temp file
            try:
                Path(tmp_path).unlink()
            except Exception as e:
                logger.warning(f"Could not delete temp file {tmp_path}: {e}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error converting document: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
