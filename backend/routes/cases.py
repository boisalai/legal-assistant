"""
Routes pour la gestion des dossiers academiques.

Endpoints:
- GET /api/cases - Liste des dossiers
- POST /api/cases - Creer un nouveau dossier
- GET /api/cases/{id} - Details d'un dossier
- PUT /api/cases/{id} - Mettre a jour un dossier
- DELETE /api/cases/{id} - Supprimer un dossier
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

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/cases", tags=["Cases"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)

# In-memory session store (reuse from auth)
from routes.auth import active_sessions


# ============================================================================
# Pydantic Models
# ============================================================================

class CaseBase(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None


class CaseCreate(CaseBase):
    pass


class CaseResponse(CaseBase):
    id: str
    keywords: list[str] = []
    created_at: str
    updated_at: Optional[str] = None


class CaseListResponse(BaseModel):
    cases: list[CaseResponse]
    total: int


class CaseUpdate(BaseModel):
    """Model for updating a case."""
    title: Optional[str] = None
    description: Optional[str] = None
    keywords: Optional[list[str]] = None


# ============================================================================
# Helper Functions
# ============================================================================

async def get_case_by_id(service, case_id: str) -> Optional[dict]:
    """
    Fetch a case by ID using SurrealQL query.
    Returns the case dict or None if not found.
    """
    # Normalize ID
    record_id = case_id.replace("case:", "")

    query_result = await service.query(
        "SELECT * FROM case WHERE id = type::thing('case', $record_id)",
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

@router.get("", response_model=CaseListResponse)
async def list_cases(
    skip: int = 0,
    limit: int = 20,
    user_id: Optional[str] = Depends(get_current_user_id)
):
    """
    Liste les dossiers de l'utilisateur.
    """
    try:
        service = get_surreal_service()
        if not service.db:
            await service.connect()

        # Query cases for user (or all if no user)
        if user_id:
            result = await service.query(
                "SELECT * FROM case ORDER BY created_at DESC LIMIT $limit START $skip",
                {"limit": limit, "skip": skip}
            )
        else:
            result = await service.query(
                "SELECT * FROM case ORDER BY created_at DESC LIMIT $limit START $skip",
                {"limit": limit, "skip": skip}
            )

        # Parse results
        cases = []
        if result and len(result) > 0:
            # SurrealDB query() returns a list of results directly
            items = result
            if isinstance(items, list):
                for item in items:
                    cases.append(CaseResponse(
                        id=str(item.get("id", "")),
                        title=item.get("title"),
                        description=item.get("description"),
                        keywords=item.get("keywords", []),
                        created_at=item.get("created_at", ""),
                        updated_at=item.get("updated_at"),
                    ))

        return CaseListResponse(cases=cases, total=len(cases))

    except Exception as e:
        logger.error(f"Error listing cases: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("", response_model=CaseResponse, status_code=status.HTTP_201_CREATED)
async def create_case(
    title: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    user_id: str = Depends(require_auth)
):
    """
    Cree un nouveau dossier.
    """

    case_id = str(uuid.uuid4())[:8]

    # Create case in database
    try:
        service = get_surreal_service()
        if not service.db:
            await service.connect()

        now = datetime.utcnow().isoformat()
        case_data = {
            "title": title or "Sans titre",
            "description": description,
            "keywords": [],
            "created_at": now,
            "updated_at": now,
        }

        result = await service.create("case", case_data, record_id=case_id)
        logger.info(f"Case created: {case_id}")

        return CaseResponse(
            id=f"case:{case_id}",
            **case_data
        )

    except Exception as e:
        logger.error(f"Error creating case: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/{case_id}", response_model=CaseResponse)
async def get_case(
    case_id: str,
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
        if not case_id.startswith("case:"):
            case_id = f"case:{case_id}"

        item = await get_case_by_id(service, case_id)

        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Dossier non trouve"
            )

        return CaseResponse(
            id=str(item.get("id", case_id)),
            title=item.get("title"),
            description=item.get("description"),
            keywords=item.get("keywords", []),
            created_at=item.get("created_at", ""),
            updated_at=item.get("updated_at"),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting case: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.put("/{case_id}", response_model=CaseResponse)
@router.patch("/{case_id}", response_model=CaseResponse)
async def update_case(
    case_id: str,
    update_data: CaseUpdate,
    user_id: str = Depends(require_auth)
):
    """
    Met a jour un dossier.
    """
    try:
        service = get_surreal_service()
        if not service.db:
            await service.connect()

        if not case_id.startswith("case:"):
            case_id = f"case:{case_id}"

        # Check existence
        item = await get_case_by_id(service, case_id)
        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Dossier non trouve"
            )

        # Build update dict (only non-None values)
        now = datetime.utcnow().isoformat()
        updates = {"updated_at": now}

        if update_data.title is not None:
            updates["title"] = update_data.title
        if update_data.description is not None:
            updates["description"] = update_data.description
        if update_data.keywords is not None:
            updates["keywords"] = update_data.keywords

        # Update in database
        await service.merge(case_id, updates)

        # Fetch updated record
        updated_item = await get_case_by_id(service, case_id)

        logger.info(f"Case updated: {case_id}")

        return CaseResponse(
            id=str(updated_item.get("id", case_id)),
            title=updated_item.get("title"),
            description=updated_item.get("description"),
            keywords=updated_item.get("keywords", []),
            created_at=updated_item.get("created_at", ""),
            updated_at=updated_item.get("updated_at"),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating case: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.delete("/{case_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_case(
    case_id: str,
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

        if not case_id.startswith("case:"):
            case_id = f"case:{case_id}"

        # Check existence
        item = await get_case_by_id(service, case_id)
        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Dossier non trouve"
            )

        # Get the record ID without the "case:" prefix
        record_id = case_id.replace("case:", "")

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
                "DELETE FROM conversation WHERE case_id = $case_id",
                {"case_id": case_id}
            )
            logger.info(f"Deleted conversation history for {case_id}")
        except Exception as e:
            logger.warning(f"Could not delete conversation history: {e}")

        # 2. Delete document chunks (embeddings)
        try:
            # Get all documents for this case first
            docs_result = await service.query(
                "SELECT id FROM document WHERE case_id = $case_id",
                {"case_id": case_id}
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
                "DELETE FROM document WHERE case_id = $case_id",
                {"case_id": case_id}
            )
            logger.info(f"Deleted documents for {case_id}")
        except Exception as e:
            logger.warning(f"Could not delete documents: {e}")

        # 4. Delete the case itself
        await service.delete(case_id)
        logger.info(f"Case deleted: {case_id}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting case: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
