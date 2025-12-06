"""
Routes pour l'extraction de texte depuis les documents.

Endpoints:
- POST /api/cases/{case_id}/documents/{doc_id}/extract - Extraction simple de texte
- DELETE /api/cases/{case_id}/documents/{doc_id}/text - Effacer le texte extrait
- POST /api/cases/{case_id}/documents/{doc_id}/extract-to-markdown - Extraction PDF avancée avec Docling
"""

import logging
import uuid
import json
import asyncio
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from config.settings import settings
from services.surreal_service import get_surreal_service
from auth.helpers import require_auth
from utils.file_utils import AUDIO_EXTENSIONS

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/cases", tags=["Extraction"])


# ============================================================================
# Pydantic Models
# ============================================================================

class ExtractionResponse(BaseModel):
    """Réponse d'extraction de texte."""
    success: bool
    text: str = ""
    method: str = ""
    error: str = ""


# ============================================================================
# Endpoints - Extraction simple
# ============================================================================

@router.post("/{case_id}/documents/{doc_id}/extract", response_model=ExtractionResponse)
async def extract_document_text(
    case_id: str,
    doc_id: str,
    user_id: str = Depends(require_auth)
):
    """
    Extrait le texte d'un document (PDF, Word, texte, markdown).

    Pour les fichiers audio, utilisez l'endpoint /transcribe.
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

        if not Path(file_path).exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Fichier non trouve sur le disque"
            )

        # Check if it's an audio file (should use transcribe endpoint instead)
        ext = Path(file_path).suffix.lower()
        if ext in AUDIO_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Utilisez l'endpoint /transcribe pour les fichiers audio"
            )

        # Extract text
        from services.document_extraction_service import get_extraction_service

        extraction_service = get_extraction_service()
        extraction_result = await extraction_service.extract(file_path)

        if not extraction_result.success:
            logger.error(f"Extraction failed for {file_path}: {extraction_result.error}")
            return ExtractionResponse(
                success=False,
                error=extraction_result.error or "Erreur d'extraction inconnue"
            )

        # Update document with extracted text
        now = datetime.utcnow().isoformat()
        await service.merge(doc_id, {
            "texte_extrait": extraction_result.text,
            "extraction_method": extraction_result.extraction_method,
            "updated_at": now,
        })

        logger.info(f"Text extracted for document {doc_id}: {len(extraction_result.text)} chars via {extraction_result.extraction_method}")

        return ExtractionResponse(
            success=True,
            text=extraction_result.text[:500] + "..." if len(extraction_result.text) > 500 else extraction_result.text,
            method=extraction_result.extraction_method
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error extracting document: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.delete("/{case_id}/documents/{doc_id}/text")
async def clear_document_text(
    case_id: str,
    doc_id: str,
    user_id: str = Depends(require_auth)
):
    """
    Efface le texte extrait d'un document.

    Supprime le champ texte_extrait du document dans la base de données.
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

        # Get document to verify it exists
        clean_id = doc_id.replace("document:", "")
        result = await service.query(
            "SELECT * FROM document WHERE id = type::thing('document', $doc_id)",
            {"doc_id": clean_id}
        )

        if not result or len(result) == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document non trouvé"
            )

        # Clear texte_extrait
        now = datetime.utcnow().isoformat()
        await service.merge(doc_id, {
            "texte_extrait": None,
            "extraction_method": None,
            "updated_at": now,
        })

        logger.info(f"Cleared texte_extrait for document {doc_id}")

        return {"success": True, "message": "Texte extrait supprimé"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error clearing document text: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


# ============================================================================
# Endpoints - Extraction PDF avancée avec Docling
# ============================================================================

@router.post("/{case_id}/documents/{doc_id}/extract-to-markdown")
async def extract_pdf_to_markdown(
    case_id: str,
    doc_id: str,
    user_id: str = Depends(require_auth)
):
    """
    Extrait le texte d'un PDF et le formate en markdown avec sections détectées par LLM.

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

        # Check if it's a PDF file
        ext = Path(file_path).suffix.lower()
        if ext != '.pdf':
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Ce n'est pas un fichier PDF. Extension: {ext}"
            )

        if not Path(file_path).exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Fichier PDF non trouve sur le disque"
            )

        # Create SSE generator
        async def event_generator():
            progress_queue = asyncio.Queue()

            async def run_extraction():
                try:
                    # Check if a markdown already exists for this PDF
                    original_filename = item.get("nom_fichier", "document.pdf")
                    markdown_filename = Path(original_filename).stem + ".md"

                    # Get judgment directory
                    judgment_dir = Path(settings.upload_dir) / case_id.replace("case:", "")
                    markdown_path = judgment_dir / markdown_filename

                    # Check if markdown file exists on disk
                    if markdown_path.exists():
                        await progress_queue.put({
                            "type": "error",
                            "data": {"message": f"Un fichier markdown '{markdown_filename}' existe déjà sur le disque pour ce PDF. Supprimez-le d'abord si vous voulez réextraire."}
                        })
                        return

                    # Check existing documents in database
                    docs_result = await service.query(
                        "SELECT * FROM document WHERE case_id = $case_id AND nom_fichier = $filename",
                        {"case_id": case_id, "filename": markdown_filename}
                    )

                    if docs_result and len(docs_result) > 0:
                        # Parse result
                        existing_docs = []
                        first_item = docs_result[0]
                        if isinstance(first_item, dict):
                            if "result" in first_item:
                                existing_docs = first_item["result"] if isinstance(first_item["result"], list) else []
                            elif "id" in first_item:
                                existing_docs = docs_result
                        elif isinstance(first_item, list):
                            existing_docs = first_item

                        if existing_docs and len(existing_docs) > 0:
                            await progress_queue.put({
                                "type": "error",
                                "data": {"message": f"Un fichier markdown '{markdown_filename}' existe déjà en base de données pour ce PDF. Supprimez-le d'abord si vous voulez réextraire."}
                            })
                            return

                    # Step 1: Extract text with MarkItDown
                    await progress_queue.put({
                        "type": "progress",
                        "data": {"step": "extract", "message": "Extraction du texte avec MarkItDown...", "percentage": 20}
                    })

                    from services.document_extraction_service import get_extraction_service
                    extraction_service = get_extraction_service()

                    extraction_result = await extraction_service.extract(
                        file_path=file_path,
                        content_type="application/pdf"
                    )

                    if not extraction_result.success:
                        await progress_queue.put({
                            "type": "error",
                            "data": {"message": extraction_result.error or "Échec de l'extraction"}
                        })
                        return

                    await progress_queue.put({
                        "type": "progress",
                        "data": {"step": "extract", "message": "Texte extrait avec succès", "percentage": 60}
                    })

                    # Step 2: Save as markdown file
                    await progress_queue.put({
                        "type": "progress",
                        "data": {"step": "save", "message": "Création du fichier markdown...", "percentage": 70}
                    })

                    # Ensure judgment directory exists
                    judgment_dir.mkdir(parents=True, exist_ok=True)

                    # Write markdown file
                    with open(markdown_path, "w", encoding="utf-8") as f:
                        f.write(extraction_result.text)

                    # Step 3: Create document record in SurrealDB
                    await progress_queue.put({
                        "type": "progress",
                        "data": {"step": "save", "message": "Enregistrement dans la base de données...", "percentage": 85}
                    })

                    new_doc_id = str(uuid.uuid4())
                    doc_record = {
                        "case_id": case_id,
                        "nom_fichier": markdown_filename,
                        "type_fichier": "md",
                        "type_mime": "text/markdown",
                        "taille": len(extraction_result.text.encode('utf-8')),
                        "file_path": str(markdown_path),
                        "texte_extrait": extraction_result.text,  # Store for indexing
                        "is_transcription": False,
                        "source_document_id": doc_id,  # Link to source PDF
                        "is_derived": True,
                        "derivation_type": "pdf_extraction",
                        "created_at": datetime.utcnow().isoformat(),
                        "updated_at": datetime.utcnow().isoformat(),
                    }

                    await service.create("document", doc_record, record_id=new_doc_id)

                    # Index le document pour la recherche sémantique
                    try:
                        from services.document_indexing_service import get_document_indexing_service

                        await progress_queue.put({
                            "type": "progress",
                            "data": {"step": "save", "message": "Indexation pour recherche sémantique...", "percentage": 90}
                        })

                        indexing_service = get_document_indexing_service()
                        index_result = await indexing_service.index_document(
                            document_id=f"document:{new_doc_id}",
                            case_id=case_id,
                            text_content=extraction_result.text,
                            force_reindex=False
                        )

                        if index_result.get("success"):
                            logger.info(f"Document indexed: {index_result.get('chunks_created', 0)} chunks")
                        else:
                            logger.warning(f"Indexing failed: {index_result.get('error', 'Unknown error')}")
                    except Exception as e:
                        # Ne pas bloquer si l'indexation échoue
                        logger.warning(f"Could not index document: {e}")

                    await progress_queue.put({
                        "type": "complete",
                        "data": {
                            "success": True,
                            "document_id": f"document:{new_doc_id}",
                            "document_path": str(markdown_path),
                            "page_count": extraction_result.metadata.get("num_pages", 0)
                        }
                    })

                except Exception as e:
                    logger.error(f"Extraction error: {e}", exc_info=True)
                    await progress_queue.put({
                        "type": "error",
                        "data": {"message": str(e)}
                    })
                finally:
                    await progress_queue.put(None)  # Signal end

            # Start extraction
            task = asyncio.create_task(run_extraction())

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
        logger.error(f"Error starting PDF extraction workflow: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
