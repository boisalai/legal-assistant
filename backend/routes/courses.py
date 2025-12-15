"""
Routes pour la gestion des cours academiques.

Endpoints:
- GET /api/courses - Liste des cours
- POST /api/courses - Creer un nouveau cours
- GET /api/courses/{id} - Details d'un cours
- PUT /api/courses/{id} - Mettre a jour un cours
- DELETE /api/courses/{id} - Supprimer un cours
- POST /api/courses/{id}/summarize - Generer un resume
- GET /api/courses/{id}/summary - Recuperer le resume
"""

import logging
import shutil
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, status, Form, Depends
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel

from config.settings import settings
from services.surreal_service import get_surreal_service
from models.course import Course, CourseCreate, CourseUpdate
from services.course_service import get_course_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/courses", tags=["Courses"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)

# In-memory session store (reuse from auth)
from routes.auth import active_sessions


# ============================================================================
# Pydantic Models
# ============================================================================

class CourseResponse(BaseModel):
    """Response model for a case/course."""
    id: str
    title: str
    description: Optional[str] = None
    keywords: list[str] = []
    created_at: str
    updated_at: Optional[str] = None

    # Academic fields
    session_id: Optional[str] = None
    course_code: Optional[str] = None
    course_name: Optional[str] = None
    professor: Optional[str] = None
    credits: Optional[int] = None
    color: Optional[str] = None


class CourseListResponse(BaseModel):
    """Response model for a list of courses/courses."""
    courses: list[CourseResponse]
    total: int


class SummarizeRequest(BaseModel):
    """Request model for course summarization."""
    model_id: Optional[str] = None  # Format: "anthropic:claude-sonnet-4-5-20250929"


class SummaryResponse(BaseModel):
    """Response model for course summary."""
    id: str
    course_id: str
    case_brief: dict
    confidence_score: float
    key_takeaway: str
    model_used: str
    created_at: str


# ============================================================================
# Helper Functions
# ============================================================================

async def get_course_by_id(service, course_id: str) -> Optional[dict]:
    """
    Fetch a case by ID using SurrealQL query.
    Returns the case dict or None if not found.
    """
    # Normalize ID
    record_id = course_id.replace("case:", "")

    query_result = await service.query(
        "SELECT * FROM course WHERE id = type::thing('case', $record_id)",
        {"record_id": record_id}
    )

    if not query_result or len(query_result) == 0:
        return None

    first_result = query_result[0]
    if isinstance(first_result, dict) and "result" in first_result:
        items = first_result["result"]
    elif isinstance(first_result, list):
        items = first_result
    elif isinstance(first_result, dict):
        items = [first_result]
    else:
        return None

    return items[0] if items else None


async def get_current_user_id(token: Optional[str] = Depends(oauth2_scheme)) -> Optional[str]:
    """Get current user ID from token."""
    if not token:
        return None
    return active_sessions.get(token)


async def require_auth(token: Optional[str] = Depends(oauth2_scheme)) -> str:
    """Require authentication (relaxed in debug mode)."""
    # In debug mode, allow unauthenticated access with a default user
    if settings.debug:
        if not token:
            return "user:dev_user"
        user_id = active_sessions.get(token)
        return user_id or "user:dev_user"

    # Production mode: strict authentication
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

@router.get("", response_model=CourseListResponse)
async def list_courses(
    skip: int = 0,
    limit: int = 20,
    user_id: Optional[str] = Depends(get_current_user_id)
):
    """
    Liste les cours de l'utilisateur.
    """
    try:
        service = get_surreal_service()
        if not service.db:
            await service.connect()

        # Query courses for user (or all if no user)
        if user_id:
            result = await service.query(
                "SELECT * FROM course ORDER BY created_at DESC LIMIT $limit START $skip",
                {"limit": limit, "skip": skip}
            )
        else:
            result = await service.query(
                "SELECT * FROM course ORDER BY created_at DESC LIMIT $limit START $skip",
                {"limit": limit, "skip": skip}
            )

        # Parse results
        courses = []
        if result and len(result) > 0:
            # SurrealDB query() returns a list of results directly
            items = result
            if isinstance(items, list):
                for item in items:
                    courses.append(CourseResponse(
                        id=str(item.get("id", "")),
                        title=item.get("title", ""),
                        description=item.get("description"),
                        keywords=item.get("keywords", []),
                        created_at=item.get("created_at", ""),
                        updated_at=item.get("updated_at"),
                        # Academic fields
                        session_id=str(item.get("session_id")) if item.get("session_id") else None,
                        course_code=item.get("course_code"),
                        course_name=item.get("course_name"),
                        professor=item.get("professor"),
                        credits=item.get("credits"),
                        color=item.get("color"),
                    ))

        return CourseListResponse(cases=cases, total=len(cases))

    except Exception as e:
        logger.error(f"Error listing courses: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("", response_model=CourseResponse, status_code=status.HTTP_201_CREATED)
async def create_course(
    case_create: CourseCreate,
    user_id: str = Depends(require_auth)
):
    """
    Cree un nouveau dossier / cours.

    Supports both legal mode (basic fields) and academic mode (with session, course code, etc.)
    """
    course_id = str(uuid.uuid4())[:8]

    # Create case in database
    try:
        service = get_surreal_service()
        if not service.db:
            await service.connect()

        now = datetime.utcnow().isoformat()

        # Convert Pydantic model to dict
        case_data = case_create.model_dump(exclude_unset=True)
        case_data["created_at"] = now
        case_data["updated_at"] = now

        # Ensure title exists
        if "title" not in case_data or not case_data["title"]:
            case_data["title"] = "Sans titre"

        # Normalize session_id if present
        if "session_id" in case_data and case_data["session_id"]:
            if not case_data["session_id"].startswith("session:"):
                case_data["session_id"] = f"session:{case_data['session_id']}"

        # Check for duplicate course_code in same session (if academic mode)
        if case_data.get("course_code") and case_data.get("session_id"):
            course_service = get_course_service()
            exists = await course_service.check_course_code_exists(
                course_code=case_data["course_code"],
                session_id=case_data["session_id"]
            )
            if exists:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Course code '{case_data['course_code']}' already exists in this session"
                )

        result = await service.create("case", case_data, record_id=course_id)
        logger.info(f"Case/Course created: {course_id}")

        # Get the created case to return full data
        created_case = await get_course_by_id(service, f"case:{course_id}")
        if not created_case:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Case created but could not be retrieved"
            )

        return CourseResponse(
            id=str(created_case.get("id", f"case:{course_id}")),
            title=created_case.get("title", ""),
            description=created_case.get("description"),
            keywords=created_case.get("keywords", []),
            created_at=created_case.get("created_at", now),
            updated_at=created_case.get("updated_at"),
            # Academic fields
            session_id=str(created_case.get("session_id")) if created_case.get("session_id") else None,
            course_code=created_case.get("course_code"),
            course_name=created_case.get("course_name"),
            professor=created_case.get("professor"),
            credits=created_case.get("credits"),
            color=created_case.get("color"),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating case: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/{course_id}", response_model=CourseResponse)
async def get_case(
    course_id: str,
    user_id: Optional[str] = Depends(get_current_user_id)
):
    """
    Recupere les details d'un dossier.
    """
    try:
        service = get_surreal_service()
        if not service.db:
            await service.connect()

        # Normalize ID
        if not course_id.startswith("case:"):
            course_id = f"case:{course_id}"

        item = await get_course_by_id(service, course_id)

        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Dossier non trouve"
            )

        return CourseResponse(
            id=str(item.get("id", course_id)),
            title=item.get("title", ""),
            description=item.get("description"),
            keywords=item.get("keywords", []),
            created_at=item.get("created_at", ""),
            updated_at=item.get("updated_at"),
            # Academic fields
            session_id=str(item.get("session_id")) if item.get("session_id") else None,
            course_code=item.get("course_code"),
            course_name=item.get("course_name"),
            professor=item.get("professor"),
            credits=item.get("credits"),
            color=item.get("color"),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting case: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.put("/{course_id}", response_model=CourseResponse)
@router.patch("/{course_id}", response_model=CourseResponse)
async def update_course(
    course_id: str,
    update_data: CourseUpdate,
    user_id: str = Depends(require_auth)
):
    """
    Met a jour un dossier.
    """
    try:
        service = get_surreal_service()
        if not service.db:
            await service.connect()

        if not course_id.startswith("case:"):
            course_id = f"case:{course_id}"

        # Check existence
        item = await get_course_by_id(service, course_id)
        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Dossier non trouve"
            )

        # Build update dict (only explicitly set values)
        now = datetime.utcnow().isoformat()
        updates = update_data.model_dump(exclude_unset=True)
        updates["updated_at"] = now

        # Normalize session_id if present
        if "session_id" in updates and updates["session_id"]:
            if not updates["session_id"].startswith("session:"):
                updates["session_id"] = f"session:{updates['session_id']}"

        # Check for duplicate course_code if updating it
        if "course_code" in updates and updates["course_code"]:
            # Get current session_id (from updates or existing item)
            session_id = updates.get("session_id") or item.get("session_id")
            if session_id:
                course_service = get_course_service()
                exists = await course_service.check_course_code_exists(
                    course_code=updates["course_code"],
                    session_id=session_id,
                    exclude_id=course_id
                )
                if exists:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Course code '{updates['course_code']}' already exists in this session"
                    )

        # Update in database
        await service.merge(course_id, updates)

        # Fetch updated record
        updated_item = await get_course_by_id(service, course_id)

        logger.info(f"Case/Course updated: {course_id}")

        return CourseResponse(
            id=str(updated_item.get("id", course_id)),
            title=updated_item.get("title", ""),
            description=updated_item.get("description"),
            keywords=updated_item.get("keywords", []),
            created_at=updated_item.get("created_at", ""),
            updated_at=updated_item.get("updated_at"),
            # Academic fields
            session_id=str(updated_item.get("session_id")) if updated_item.get("session_id") else None,
            course_code=updated_item.get("course_code"),
            course_name=updated_item.get("course_name"),
            professor=updated_item.get("professor"),
            credits=updated_item.get("credits"),
            color=updated_item.get("color"),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating case: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.delete("/{course_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_course(
    course_id: str,
    user_id: str = Depends(require_auth)
):
    """
    Supprime un dossier et tous ses fichiers uploades.
    Suppression en cascade : conversations, chunks d'embeddings, documents.
    """

    try:
        service = get_surreal_service()
        if not service.db:
            await service.connect()

        if not course_id.startswith("case:"):
            course_id = f"case:{course_id}"

        # Check existence
        item = await get_course_by_id(service, course_id)
        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Dossier non trouve"
            )

        # Get the record ID without the "case:" prefix
        record_id = course_id.replace("case:", "")

        # Delete the entire uploads directory for this case
        uploads_dir = settings.upload_dir / record_id
        if uploads_dir.exists() and uploads_dir.is_dir():
            try:
                shutil.rmtree(uploads_dir)
                logger.info(f"Deleted uploads directory: {uploads_dir}")
            except Exception as e:
                logger.warning(f"Could not delete uploads directory {uploads_dir}: {e}")

        # Delete related data from database (cascade)
        # 1. Delete conversation history
        try:
            await service.query(
                "DELETE FROM conversation WHERE course_id = $course_id",
                {"course_id": course_id}
            )
            logger.info(f"Deleted conversation history for {course_id}")
        except Exception as e:
            logger.warning(f"Could not delete conversation history: {e}")

        # 2. Delete document chunks (embeddings)
        try:
            # Get all documents for this case first
            docs_result = await service.query(
                "SELECT id FROM document WHERE course_id = $course_id",
                {"course_id": course_id}
            )

            if docs_result and len(docs_result) > 0:
                # Parse document IDs
                doc_ids = []
                first_item = docs_result[0]
                if isinstance(first_item, dict) and "result" in first_item:
                    doc_ids = [doc.get("id") for doc in first_item["result"] if doc.get("id")]
                elif isinstance(first_item, list):
                    doc_ids = [doc.get("id") for doc in first_item if doc.get("id")]
                elif isinstance(first_item, dict):
                    doc_ids = [doc.get("id") for doc in docs_result if doc.get("id")]

                # Delete chunks for each document
                for doc_id in doc_ids:
                    await service.query(
                        "DELETE FROM document_chunk WHERE document_id = $document_id",
                        {"document_id": doc_id}
                    )

                logger.info(f"Deleted document chunks for {len(doc_ids)} documents")
        except Exception as e:
            logger.warning(f"Could not delete document chunks: {e}")

        # 3. Delete documents
        try:
            await service.query(
                "DELETE FROM document WHERE course_id = $course_id",
                {"course_id": course_id}
            )
            logger.info(f"Deleted documents for {course_id}")
        except Exception as e:
            logger.warning(f"Could not delete documents: {e}")

        # 4. Delete the case itself
        await service.delete(course_id)
        logger.info(f"Case deleted: {course_id}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting case: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/{course_id}/summarize", response_model=SummaryResponse)
async def summarize_course(
    course_id: str,
    request: Optional[SummarizeRequest] = None,
    user_id: str = Depends(require_auth)
):
    """
    Genere un resume (case brief) pour un cours.
    """
    try:
        service = get_surreal_service()
        if not service.db:
            await service.connect()

        if not course_id.startswith("course:"):
            course_id = f"course:{course_id}"

        # Get course
        item = await get_course_by_id(service, course_id)
        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cours non trouve"
            )

        course_text = item.get("text")

        if not course_text:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Le cours n'a pas de texte a analyser. Ajoutez des documents puis lancez l'analyse."
            )

        # Get model configuration
        model_id = request.model_id if request and request.model_id else settings.model_id

        # Create model and run workflow
        from services.model_factory import create_model
        from workflows.summarize_judgment import SimpleJudgmentSummarizer

        logger.info(f"Creating model: {model_id}")
        model = create_model(model_id)

        logger.info(f"Starting summarization for course: {course_id}")
        summarizer = SimpleJudgmentSummarizer(model=model)
        summary_result = summarizer.summarize(course_text)

        if not summary_result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Erreur lors de la generation du resume: {summary_result.get('error')}"
            )

        # Save summary to database
        summary_id = str(uuid.uuid4())[:8]
        now = datetime.utcnow().isoformat()

        summary_data = {
            "course_id": course_id,
            "case_brief": summary_result.get("case_brief", {}),
            "confidence_score": summary_result.get("confidence_score", 0),
            "key_takeaway": summary_result.get("key_takeaway", ""),
            "intermediate_results": summary_result.get("intermediate_results", {}),
            "model_used": model_id,
            "user_id": user_id,
            "created_at": now,
        }

        await service.create("summary", summary_data, record_id=summary_id)

        # Update course status
        await service.merge(course_id, {"status": "summarized", "updated_at": now})

        logger.info(f"Summary created: {summary_id}")

        return SummaryResponse(
            id=f"summary:{summary_id}",
            course_id=course_id,
            case_brief=summary_data["case_brief"],
            confidence_score=summary_data["confidence_score"],
            key_takeaway=summary_data["key_takeaway"],
            model_used=model_id,
            created_at=now,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error summarizing course: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/{course_id}/summary", response_model=SummaryResponse)
async def get_course_summary(
    course_id: str,
    user_id: Optional[str] = Depends(get_current_user_id)
):
    """
    Recupere le resume d'un cours.
    """
    try:
        service = get_surreal_service()
        if not service.db:
            await service.connect()

        if not course_id.startswith("course:"):
            course_id = f"course:{course_id}"

        # Get latest summary for this course
        result = await service.query(
            "SELECT * FROM summary WHERE course_id = $course_id ORDER BY created_at DESC LIMIT 1",
            {"course_id": course_id}
        )

        if not result or len(result) == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Aucun resume trouve pour ce cours"
            )

        # SurrealDB query() returns a list of results directly
        items = result
        if not items or len(items) == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Aucun resume trouve pour ce cours"
            )

        item = items[0]

        return SummaryResponse(
            id=str(item.get("id", "")),
            course_id=item.get("course_id", course_id),
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
