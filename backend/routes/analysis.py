"""
Routes pour l'analyse complete des dossiers.

Pipeline d'analyse:
1. Recuperer tous les documents du dossier
2. Extraire le texte (PDF, Word, etc.)
3. Transcrire l'audio (Whisper)
4. Vectoriser le contenu (embeddings)
5. Generer un resume avec le LLM

Endpoints:
- POST /api/analysis/{case_id}/start - Demarre l'analyse complete
- GET /api/analysis/{case_id}/status - Statut de l'analyse
- GET /api/analysis/{case_id}/checklist - Recupere la checklist generee
"""

import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, status, Depends, BackgroundTasks
from pydantic import BaseModel

from config.settings import settings
from services.surreal_service import get_surreal_service
from services.document_extraction_service import get_extraction_service
from services.embedding_service import get_embedding_service
from auth.helpers import get_current_user_id, require_auth

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/analysis", tags=["Analysis"])


# ============================================================================
# Pydantic Models
# ============================================================================

class AnalysisRequest(BaseModel):
    model_id: Optional[str] = None  # Format: "ollama:qwen2.5:7b" ou "anthropic:claude-..."


class AnalysisStatusResponse(BaseModel):
    case_id: str
    status: str  # pending, extracting, embedding, summarizing, complete, error
    progress: float  # 0-100
    message: str
    documents_processed: int
    documents_total: int


class ChecklistItem(BaseModel):
    titre: str
    description: Optional[str] = None
    complete: bool = False


class AnalysisResultResponse(BaseModel):
    case_id: str
    summary: str
    key_points: list[str]
    checklist: list[ChecklistItem]
    points_attention: list[str]
    confidence_score: float
    model_used: str
    created_at: str


# ============================================================================
# Helper Functions
# ============================================================================

async def get_case_documents(service, case_id: str) -> list[dict]:
    """Recupere tous les documents d'un dossier."""
    # Normalize ID
    if not case_id.startswith("case:"):
        case_id = f"case:{case_id}"

    result = await service.query(
        "SELECT * FROM document WHERE case_id = $case_id",
        {"case_id": case_id}
    )

    if not result or len(result) == 0:
        return []

    first_result = result[0]
    # Handle different result formats from SurrealDB
    if isinstance(first_result, dict) and "result" in first_result:
        items = first_result["result"]
    elif isinstance(first_result, list):
        items = first_result
    elif isinstance(first_result, dict):
        # Single dict result without "result" wrapper
        items = [first_result]
    else:
        return []

    return items if items else []


async def run_analysis_pipeline(
    case_id: str,
    model_id: str,
    user_id: str
):
    """
    Pipeline d'analyse complet execute en arriere-plan.
    """
    service = get_surreal_service()
    if not service.db:
        await service.connect()

    extraction_service = get_extraction_service()
    embedding_service = get_embedding_service()

    try:
        # Normaliser l'ID
        if not case_id.startswith("case:"):
            case_id = f"case:{case_id}"

        # Mettre a jour le statut: en cours
        await service.merge(case_id, {
            "status": "analyzing",
            "updated_at": datetime.utcnow().isoformat()
        })

        # 1. Recuperer les documents
        documents = await get_case_documents(service, case_id)

        if not documents:
            await service.merge(case_id, {
                "status": "error",
                "error_message": "Aucun document trouve dans le dossier",
                "updated_at": datetime.utcnow().isoformat()
            })
            return

        logger.info(f"Analyse de {len(documents)} documents pour {case_id}")

        # 2. Extraire le texte de chaque document
        all_text_parts = []
        chunks_to_embed = []

        for doc in documents:
            file_path = doc.get("file_path")
            if not file_path or not Path(file_path).exists():
                logger.warning(f"Fichier non trouve: {file_path}")
                continue

            # Extraire le texte
            extraction = await extraction_service.extract(file_path)

            if extraction.success and extraction.text:
                text = extraction.text.strip()
                all_text_parts.append(f"## Document: {doc.get('nom_fichier', 'Sans nom')}\n\n{text}")

                # Stocker le texte extrait dans le document
                doc_id = str(doc.get("id", ""))
                if doc_id:
                    await service.merge(doc_id, {
                        "texte_extrait": text[:10000],  # Limiter la taille
                        "extraction_method": extraction.extraction_method,
                        "is_transcription": extraction.is_transcription,
                        "updated_at": datetime.utcnow().isoformat()
                    })

                # Chunker pour les embeddings
                chunk_result = embedding_service.chunk_text(text, chunk_size=500, overlap=50)
                for i, chunk in enumerate(chunk_result.chunks):
                    chunks_to_embed.append({
                        "document_id": doc_id,
                        "chunk_index": i,
                        "text": chunk
                    })

                logger.info(f"Extrait {len(text)} caracteres de {doc.get('nom_fichier')}")
            else:
                logger.warning(f"Extraction echouee pour {file_path}: {extraction.error}")

        if not all_text_parts:
            await service.merge(case_id, {
                "status": "error",
                "error_message": "Aucun texte n'a pu etre extrait des documents",
                "updated_at": datetime.utcnow().isoformat()
            })
            return

        # 3. Generer et stocker les embeddings
        logger.info(f"Generation de {len(chunks_to_embed)} embeddings...")
        for chunk_data in chunks_to_embed[:50]:  # Limiter pour eviter timeout
            embedding_result = await embedding_service.generate_embedding(chunk_data["text"])

            if embedding_result.success:
                # Stocker le chunk avec son embedding dans SurrealDB
                chunk_id = str(uuid.uuid4())[:8]
                await service.create("document_chunk", {
                    "document_id": chunk_data["document_id"],
                    "case_id": case_id,
                    "chunk_index": chunk_data["chunk_index"],
                    "text": chunk_data["text"],
                    "embedding": embedding_result.embedding,
                    "dimensions": embedding_result.dimensions,
                    "created_at": datetime.utcnow().isoformat()
                }, record_id=chunk_id)

        # 4. Combiner tout le texte pour l'analyse
        combined_text = "\n\n---\n\n".join(all_text_parts)

        # Limiter la taille pour le LLM
        if len(combined_text) > 30000:
            combined_text = combined_text[:30000] + "\n\n[... texte tronque ...]"

        # 5. Generer le resume avec le LLM
        try:
            from services.model_factory import create_model
            from agno.models.message import Message

            logger.info(f"Generation du resume avec {model_id}")
            model = create_model(model_id)

            # Prompt pour l'analyse juridique
            prompt = f"""Vous etes un assistant juridique expert. Analysez les documents suivants d'un dossier juridique et fournissez:

1. Un resume clair et structure du dossier (2-3 paragraphes)
2. Les points cles a retenir (liste de 3-5 points)
3. Une checklist des actions a entreprendre
4. Les points d'attention ou risques identifies

Documents du dossier:

{combined_text}

Repondez en francais avec un format structure."""

            # Appel au modele avec la bonne API Agno
            messages = [Message(role="user", content=prompt)]
            response = model.response(messages)
            summary_text = response.content if hasattr(response, 'content') else str(response)

            # Parser la reponse (simplification - idealement utiliser structured output)
            key_points = []
            checklist_items = []
            points_attention = []

            # Extraction basique des sections
            lines = summary_text.split('\n')
            current_section = None

            for line in lines:
                line = line.strip()
                if not line:
                    continue

                if "point" in line.lower() and "cle" in line.lower():
                    current_section = "key_points"
                elif "checklist" in line.lower() or "action" in line.lower():
                    current_section = "checklist"
                elif "attention" in line.lower() or "risque" in line.lower():
                    current_section = "attention"
                elif line.startswith("-") or line.startswith("•") or line.startswith("*"):
                    item = line.lstrip("-•* ").strip()
                    if current_section == "key_points":
                        key_points.append(item)
                    elif current_section == "checklist":
                        checklist_items.append({"titre": item, "complete": False})
                    elif current_section == "attention":
                        points_attention.append(item)

            # Sauvegarder le resultat de l'analyse
            analysis_id = str(uuid.uuid4())[:8]
            now = datetime.utcnow().isoformat()

            analysis_data = {
                "case_id": case_id,
                "summary": summary_text,
                "key_points": key_points or ["Voir le resume pour les details"],
                "checklist": checklist_items or [{"titre": "Analyser le dossier en detail", "complete": False}],
                "points_attention": points_attention or [],
                "confidence_score": 0.75,  # A ameliorer avec un scoring reel
                "model_used": model_id,
                "user_id": user_id,
                "created_at": now
            }

            await service.create("analysis_result", analysis_data, record_id=analysis_id)

            # Mettre a jour le dossier avec le resume
            await service.merge(case_id, {
                "status": "complete",
                "text": combined_text[:10000],  # Stocker le texte extrait
                "summary": summary_text[:5000],
                "score_confiance": 75,
                "updated_at": now
            })

            logger.info(f"Analyse complete pour {case_id}")

        except Exception as llm_error:
            logger.error(f"Erreur LLM: {llm_error}")
            # Meme en cas d'erreur LLM, on sauvegarde le texte extrait
            await service.merge(case_id, {
                "status": "complete",
                "text": combined_text[:10000],
                "summary": "Resume automatique non disponible. Texte extrait disponible.",
                "updated_at": datetime.utcnow().isoformat()
            })

    except Exception as e:
        logger.error(f"Erreur pipeline analyse: {e}")
        try:
            await service.merge(case_id, {
                "status": "error",
                "error_message": str(e),
                "updated_at": datetime.utcnow().isoformat()
            })
        except Exception:
            pass


# ============================================================================
# Endpoints
# ============================================================================

@router.post("/{case_id}/start")
async def start_analysis(
    case_id: str,
    request: Optional[AnalysisRequest] = None,
    background_tasks: BackgroundTasks = None,
    user_id: str = Depends(require_auth)
):
    """
    Demarre l'analyse complete d'un dossier.
    """
    try:
        service = get_surreal_service()
        if not service.db:
            await service.connect()

        # Normaliser l'ID
        if not case_id.startswith("case:"):
            case_id = f"case:{case_id}"

        # Verifier que le dossier existe - importer le helper depuis judgments
        from routes.judgments import get_judgment_by_id
        judgment = await get_judgment_by_id(service, case_id)

        if not judgment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Dossier non trouve"
            )

        # Verifier qu'il y a des documents
        documents = await get_case_documents(service, case_id)
        if not documents:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Le dossier ne contient aucun document. Ajoutez des documents avant de lancer l'analyse."
            )

        # Determiner le modele a utiliser
        model_id = request.model_id if request and request.model_id else settings.model_id

        # Lancer l'analyse en arriere-plan
        background_tasks.add_task(
            run_analysis_pipeline,
            case_id,
            model_id,
            user_id
        )

        return {
            "message": "Analyse demarree",
            "case_id": case_id,
            "documents_count": len(documents),
            "model": model_id
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur demarrage analyse: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/{case_id}/status", response_model=AnalysisStatusResponse)
async def get_analysis_status(
    case_id: str,
    user_id: Optional[str] = Depends(get_current_user_id)
):
    """
    Recupere le statut de l'analyse d'un dossier.
    """
    try:
        service = get_surreal_service()
        if not service.db:
            await service.connect()

        if not case_id.startswith("case:"):
            case_id = f"case:{case_id}"

        # Use helper from judgments route
        from routes.judgments import get_judgment_by_id
        item = await get_judgment_by_id(service, case_id)

        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Dossier non trouve"
            )

        case_status = item.get("status", "pending")

        # Mapper les statuts
        status_messages = {
            "pending": "En attente d'analyse",
            "analyzing": "Analyse en cours...",
            "complete": "Analyse terminee",
            "summarized": "Analyse terminee",
            "error": item.get("error_message", "Erreur lors de l'analyse")
        }

        progress_map = {
            "pending": 0,
            "analyzing": 50,
            "complete": 100,
            "summarized": 100,
            "error": 0
        }

        documents = await get_case_documents(service, case_id)

        return AnalysisStatusResponse(
            case_id=case_id,
            status=case_status,
            progress=progress_map.get(case_status, 0),
            message=status_messages.get(case_status, case_status),
            documents_processed=len(documents) if case_status in ["complete", "summarized"] else 0,
            documents_total=len(documents)
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur statut analyse: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/{case_id}/checklist")
async def get_analysis_checklist(
    case_id: str,
    user_id: Optional[str] = Depends(get_current_user_id)
):
    """
    Recupere la checklist generee par l'analyse.
    """
    try:
        service = get_surreal_service()
        if not service.db:
            await service.connect()

        if not case_id.startswith("case:"):
            case_id = f"case:{case_id}"

        # Chercher le resultat d'analyse le plus recent
        result = await service.query(
            "SELECT * FROM analysis_result WHERE case_id = $case_id ORDER BY created_at DESC LIMIT 1",
            {"case_id": case_id}
        )

        if not result or len(result) == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Aucune analyse trouvee pour ce dossier"
            )

        first_result = result[0]
        if isinstance(first_result, dict) and "result" in first_result:
            items = first_result["result"]
        elif isinstance(first_result, list):
            items = first_result
        elif isinstance(first_result, dict):
            # Single dict result without "result" wrapper
            items = [first_result]
        else:
            items = []

        if not items:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Aucune analyse trouvee pour ce dossier"
            )

        item = items[0]

        return {
            "items": item.get("checklist", []),
            "points_attention": item.get("points_attention", []),
            "key_points": item.get("key_points", []),
            "summary": item.get("summary", ""),
            "confidence_score": item.get("confidence_score", 0),
            "model_used": item.get("model_used", ""),
            "created_at": item.get("created_at", "")
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur recuperation checklist: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
