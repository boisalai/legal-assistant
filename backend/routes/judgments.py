"""
Routes pour la gestion des jugements juridiques.

Endpoints:
- GET /api/judgments - Liste des jugements
- POST /api/judgments - Upload d'un nouveau jugement
- GET /api/judgments/{id} - Details d'un jugement
- DELETE /api/judgments/{id} - Supprimer un jugement
- POST /api/judgments/{id}/summarize - Generer un resume
- GET /api/judgments/{id}/summary - Recuperer le resume
"""

import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, status, UploadFile, File, Form, Depends
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel

from config.settings import settings
from services.surreal_service import get_surreal_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/judgments", tags=["Judgments"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)

# In-memory session store (reuse from auth)
from routes.auth import active_sessions


# ============================================================================
# Pydantic Models
# ============================================================================

class JudgmentBase(BaseModel):
    title: Optional[str] = None
    citation: Optional[str] = None
    court: Optional[str] = None
    decision_date: Optional[str] = None
    legal_domain: Optional[str] = None


class JudgmentCreate(JudgmentBase):
    text: str


class JudgmentResponse(JudgmentBase):
    id: str
    text: Optional[str] = None
    file_path: Optional[str] = None
    status: str = "pending"
    created_at: str
    updated_at: Optional[str] = None
    user_id: Optional[str] = None


class JudgmentListResponse(BaseModel):
    judgments: list[JudgmentResponse]
    total: int


class SummarizeRequest(BaseModel):
    model_id: Optional[str] = None  # Format: "anthropic:claude-sonnet-4-5-20250929"


class SummaryResponse(BaseModel):
    id: str
    judgment_id: str
    case_brief: dict
    confidence_score: float
    key_takeaway: str
    model_used: str
    created_at: str


# ============================================================================
# Helper Functions
# ============================================================================

async def get_current_user_id(token: Optional[str] = Depends(oauth2_scheme)) -> Optional[str]:
    """Get current user ID from token."""
    if not token:
        return None
    return active_sessions.get(token)


async def require_auth(token: Optional[str] = Depends(oauth2_scheme)) -> str:
    """Require authentication."""
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Non authentifie",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user_id = active_sessions.get(token)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalide ou expire",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user_id


# ============================================================================
# Endpoints
# ============================================================================

@router.get("", response_model=JudgmentListResponse)
async def list_judgments(
    skip: int = 0,
    limit: int = 20,
    user_id: Optional[str] = Depends(get_current_user_id)
):
    """
    Liste les jugements de l'utilisateur.
    """
    try:
        service = get_surreal_service()
        if not service.db:
            await service.connect()

        # Query judgments for user (or all if no user)
        if user_id:
            result = await service.query(
                "SELECT * FROM judgment WHERE user_id = $user_id ORDER BY created_at DESC LIMIT $limit START $skip",
                {"user_id": user_id, "limit": limit, "skip": skip}
            )
        else:
            result = await service.query(
                "SELECT * FROM judgment ORDER BY created_at DESC LIMIT $limit START $skip",
                {"limit": limit, "skip": skip}
            )

        # Parse results
        judgments = []
        if result and len(result) > 0:
            items = result[0].get("result", result) if isinstance(result[0], dict) else result
            if isinstance(items, list):
                for item in items:
                    judgments.append(JudgmentResponse(
                        id=str(item.get("id", "")),
                        title=item.get("title"),
                        citation=item.get("citation"),
                        court=item.get("court"),
                        decision_date=item.get("decision_date"),
                        legal_domain=item.get("legal_domain"),
                        status=item.get("status", "pending"),
                        created_at=item.get("created_at", ""),
                        updated_at=item.get("updated_at"),
                        user_id=item.get("user_id"),
                        file_path=item.get("file_path"),
                    ))

        return JudgmentListResponse(judgments=judgments, total=len(judgments))

    except Exception as e:
        logger.error(f"Error listing judgments: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("", response_model=JudgmentResponse, status_code=status.HTTP_201_CREATED)
async def create_judgment(
    file: Optional[UploadFile] = File(None),
    text: Optional[str] = Form(None),
    title: Optional[str] = Form(None),
    citation: Optional[str] = Form(None),
    court: Optional[str] = Form(None),
    decision_date: Optional[str] = Form(None),
    legal_domain: Optional[str] = Form(None),
    user_id: str = Depends(require_auth)
):
    """
    Cree un nouveau jugement (upload PDF ou texte).
    """
    if not file and not text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Fournir un fichier PDF ou du texte"
        )

    judgment_id = str(uuid.uuid4())[:8]
    file_path = None
    judgment_text = text

    # Handle file upload
    if file:
        # Validate file type
        if not file.filename.lower().endswith('.pdf'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Seuls les fichiers PDF sont acceptes"
            )

        # Save file
        upload_dir = Path(settings.upload_dir)
        upload_dir.mkdir(parents=True, exist_ok=True)

        file_path = str(upload_dir / f"{judgment_id}_{file.filename}")
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)

        logger.info(f"File saved: {file_path}")

        # Extract text from PDF using Docling if available
        try:
            from services.docling_service import get_docling_service
            docling = get_docling_service()
            if docling.is_available():
                extraction = await docling.extract_pdf(file_path)
                if extraction.success:
                    judgment_text = extraction.markdown
                    logger.info(f"Text extracted from PDF: {len(judgment_text)} chars")
        except Exception as e:
            logger.warning(f"Could not extract text from PDF: {e}")

    # Create judgment in database
    try:
        service = get_surreal_service()
        if not service.db:
            await service.connect()

        now = datetime.utcnow().isoformat()
        judgment_data = {
            "title": title or (file.filename if file else "Sans titre"),
            "citation": citation,
            "court": court,
            "decision_date": decision_date,
            "legal_domain": legal_domain,
            "text": judgment_text,
            "file_path": file_path,
            "status": "pending",
            "user_id": user_id,
            "created_at": now,
            "updated_at": now,
        }

        result = await service.create("judgment", judgment_data, record_id=judgment_id)
        logger.info(f"Judgment created: {judgment_id}")

        return JudgmentResponse(
            id=f"judgment:{judgment_id}",
            **judgment_data
        )

    except Exception as e:
        logger.error(f"Error creating judgment: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/{judgment_id}", response_model=JudgmentResponse)
async def get_judgment(
    judgment_id: str,
    user_id: Optional[str] = Depends(get_current_user_id)
):
    """
    Recupere les details d'un jugement.
    """
    try:
        service = get_surreal_service()
        if not service.db:
            await service.connect()

        # Normalize ID
        if not judgment_id.startswith("judgment:"):
            judgment_id = f"judgment:{judgment_id}"

        result = await service.select(judgment_id)

        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Jugement non trouve"
            )

        item = result[0] if isinstance(result, list) else result

        return JudgmentResponse(
            id=str(item.get("id", judgment_id)),
            title=item.get("title"),
            citation=item.get("citation"),
            court=item.get("court"),
            decision_date=item.get("decision_date"),
            legal_domain=item.get("legal_domain"),
            text=item.get("text"),
            file_path=item.get("file_path"),
            status=item.get("status", "pending"),
            created_at=item.get("created_at", ""),
            updated_at=item.get("updated_at"),
            user_id=item.get("user_id"),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting judgment: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.delete("/{judgment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_judgment(
    judgment_id: str,
    user_id: str = Depends(require_auth)
):
    """
    Supprime un jugement.
    """
    try:
        service = get_surreal_service()
        if not service.db:
            await service.connect()

        if not judgment_id.startswith("judgment:"):
            judgment_id = f"judgment:{judgment_id}"

        # Check ownership
        result = await service.select(judgment_id)
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Jugement non trouve"
            )

        item = result[0] if isinstance(result, list) else result
        if item.get("user_id") != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Non autorise"
            )

        # Delete file if exists
        file_path = item.get("file_path")
        if file_path:
            try:
                Path(file_path).unlink(missing_ok=True)
            except Exception as e:
                logger.warning(f"Could not delete file: {e}")

        # Delete from database
        await service.delete(judgment_id)
        logger.info(f"Judgment deleted: {judgment_id}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting judgment: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/{judgment_id}/summarize", response_model=SummaryResponse)
async def summarize_judgment(
    judgment_id: str,
    request: Optional[SummarizeRequest] = None,
    user_id: str = Depends(require_auth)
):
    """
    Genere un resume (case brief) pour un jugement.
    """
    try:
        service = get_surreal_service()
        if not service.db:
            await service.connect()

        if not judgment_id.startswith("judgment:"):
            judgment_id = f"judgment:{judgment_id}"

        # Get judgment
        result = await service.select(judgment_id)
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Jugement non trouve"
            )

        item = result[0] if isinstance(result, list) else result
        judgment_text = item.get("text")

        if not judgment_text:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Le jugement n'a pas de texte a analyser"
            )

        # Get model configuration
        model_id = request.model_id if request and request.model_id else settings.model_id

        # Create model and run workflow
        from services.model_factory import create_model
        from workflows.summarize_judgment import SimpleJudgmentSummarizer

        logger.info(f"Creating model: {model_id}")
        model = create_model(model_id)

        logger.info(f"Starting summarization for judgment: {judgment_id}")
        summarizer = SimpleJudgmentSummarizer(model=model)
        summary_result = summarizer.summarize(judgment_text)

        if not summary_result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Erreur lors de la generation du resume: {summary_result.get('error')}"
            )

        # Save summary to database
        summary_id = str(uuid.uuid4())[:8]
        now = datetime.utcnow().isoformat()

        summary_data = {
            "judgment_id": judgment_id,
            "case_brief": summary_result.get("case_brief", {}),
            "confidence_score": summary_result.get("confidence_score", 0),
            "key_takeaway": summary_result.get("key_takeaway", ""),
            "intermediate_results": summary_result.get("intermediate_results", {}),
            "model_used": model_id,
            "user_id": user_id,
            "created_at": now,
        }

        await service.create("summary", summary_data, record_id=summary_id)

        # Update judgment status
        await service.merge(judgment_id, {"status": "summarized", "updated_at": now})

        logger.info(f"Summary created: {summary_id}")

        return SummaryResponse(
            id=f"summary:{summary_id}",
            judgment_id=judgment_id,
            case_brief=summary_data["case_brief"],
            confidence_score=summary_data["confidence_score"],
            key_takeaway=summary_data["key_takeaway"],
            model_used=model_id,
            created_at=now,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error summarizing judgment: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/{judgment_id}/summary", response_model=SummaryResponse)
async def get_judgment_summary(
    judgment_id: str,
    user_id: Optional[str] = Depends(get_current_user_id)
):
    """
    Recupere le resume d'un jugement.
    """
    try:
        service = get_surreal_service()
        if not service.db:
            await service.connect()

        if not judgment_id.startswith("judgment:"):
            judgment_id = f"judgment:{judgment_id}"

        # Get latest summary for this judgment
        result = await service.query(
            "SELECT * FROM summary WHERE judgment_id = $judgment_id ORDER BY created_at DESC LIMIT 1",
            {"judgment_id": judgment_id}
        )

        if not result or len(result) == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Aucun resume trouve pour ce jugement"
            )

        items = result[0].get("result", result) if isinstance(result[0], dict) else result
        if not items or len(items) == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Aucun resume trouve pour ce jugement"
            )

        item = items[0]

        return SummaryResponse(
            id=str(item.get("id", "")),
            judgment_id=item.get("judgment_id", judgment_id),
            case_brief=item.get("case_brief", {}),
            confidence_score=item.get("confidence_score", 0),
            key_takeaway=item.get("key_takeaway", ""),
            model_used=item.get("model_used", "unknown"),
            created_at=item.get("created_at", ""),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting summary: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
