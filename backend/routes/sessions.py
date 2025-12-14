"""
Routes pour la gestion des sessions académiques.

Endpoints:
- GET /api/sessions - Liste des sessions
- POST /api/sessions - Créer une nouvelle session
- GET /api/sessions/{session_id} - Détails d'une session
- PUT /api/sessions/{session_id} - Mettre à jour une session
- DELETE /api/sessions/{session_id} - Supprimer une session
- GET /api/sessions/{session_id}/courses - Cours d'une session
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.security import OAuth2PasswordBearer

from models.session import Session, SessionCreate, SessionUpdate, SessionList
from services.session_service import get_session_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/sessions", tags=["Sessions"])

# Import auth helpers
from auth.helpers import require_auth, get_current_user_id


# ============================================================================
# Endpoints
# ============================================================================

@router.get("", response_model=SessionList)
async def list_sessions(
    page: int = 1,
    page_size: int = 20,
    year: Optional[int] = None,
    user_id: Optional[str] = Depends(get_current_user_id)
):
    """
    Liste toutes les sessions académiques avec pagination.

    Args:
        page: Numéro de page (1-indexed)
        page_size: Nombre de sessions par page
        year: Filtrer par année (optionnel)
        user_id: ID de l'utilisateur (authentification optionnelle)

    Returns:
        SessionList avec sessions et informations de pagination
    """
    try:
        service = get_session_service()
        return await service.list_sessions(page=page, page_size=page_size, year=year)

    except Exception as e:
        logger.error(f"Failed to list sessions: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la récupération des sessions: {str(e)}"
        )


@router.post("", response_model=Session, status_code=status.HTTP_201_CREATED)
async def create_session(
    session_data: SessionCreate,
    user_id: str = Depends(require_auth)
):
    """
    Crée une nouvelle session académique.

    Args:
        session_data: Données de la session
        user_id: ID de l'utilisateur (authentification requise)

    Returns:
        Session créée

    Raises:
        HTTPException 400: Si la session existe déjà (même semestre/année)
        HTTPException 500: Si erreur lors de la création
    """
    try:
        service = get_session_service()

        # Check if session already exists (same semester + year)
        existing_sessions = await service.list_sessions(year=session_data.year)
        for session in existing_sessions.items:
            if session.semester == session_data.semester and session.year == session_data.year:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Session '{session_data.semester} {session_data.year}' existe déjà"
                )

        result = await service.create_session(session_data)

        if not result:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Erreur lors de la création de la session"
            )

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create session: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la création de la session: {str(e)}"
        )


@router.get("/{session_id}", response_model=Session)
async def get_session(
    session_id: str,
    user_id: Optional[str] = Depends(get_current_user_id)
):
    """
    Récupère les détails d'une session.

    Args:
        session_id: ID de la session (avec ou sans préfixe "session:")
        user_id: ID de l'utilisateur (authentification optionnelle)

    Returns:
        Session

    Raises:
        HTTPException 404: Si la session n'existe pas
        HTTPException 500: Si erreur lors de la récupération
    """
    try:
        service = get_session_service()
        result = await service.get_session(session_id)

        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session '{session_id}' non trouvée"
            )

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get session {session_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la récupération de la session: {str(e)}"
        )


@router.put("/{session_id}", response_model=Session)
async def update_session(
    session_id: str,
    session_data: SessionUpdate,
    user_id: str = Depends(require_auth)
):
    """
    Met à jour une session académique.

    Args:
        session_id: ID de la session (avec ou sans préfixe "session:")
        session_data: Données de mise à jour
        user_id: ID de l'utilisateur (authentification requise)

    Returns:
        Session mise à jour

    Raises:
        HTTPException 404: Si la session n'existe pas
        HTTPException 500: Si erreur lors de la mise à jour
    """
    try:
        service = get_session_service()

        # Check if session exists
        existing = await service.get_session(session_id)
        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session '{session_id}' non trouvée"
            )

        result = await service.update_session(session_id, session_data)

        if not result:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Erreur lors de la mise à jour de la session"
            )

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update session {session_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la mise à jour de la session: {str(e)}"
        )


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(
    session_id: str,
    user_id: str = Depends(require_auth)
):
    """
    Supprime une session académique.

    IMPORTANT: Impossible de supprimer une session si elle contient des cours.
    Supprimer d'abord tous les cours de la session.

    Args:
        session_id: ID de la session (avec ou sans préfixe "session:")
        user_id: ID de l'utilisateur (authentification requise)

    Raises:
        HTTPException 404: Si la session n'existe pas
        HTTPException 400: Si la session contient des cours
        HTTPException 500: Si erreur lors de la suppression
    """
    try:
        service = get_session_service()

        # Check if session exists
        existing = await service.get_session(session_id)
        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session '{session_id}' non trouvée"
            )

        # Attempt to delete (service will check for courses)
        try:
            success = await service.delete_session(session_id)
            if not success:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Erreur lors de la suppression de la session"
                )
        except ValueError as e:
            # Session has courses
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete session {session_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la suppression de la session: {str(e)}"
        )


@router.get("/{session_id}/courses")
async def get_session_courses(
    session_id: str,
    user_id: Optional[str] = Depends(get_current_user_id)
):
    """
    Récupère tous les cours d'une session.

    Args:
        session_id: ID de la session (avec ou sans préfixe "session:")
        user_id: ID de l'utilisateur (authentification optionnelle)

    Returns:
        Liste des cours

    Raises:
        HTTPException 404: Si la session n'existe pas
        HTTPException 500: Si erreur lors de la récupération
    """
    try:
        service = get_session_service()

        # Check if session exists
        existing = await service.get_session(session_id)
        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session '{session_id}' non trouvée"
            )

        courses = await service.get_session_courses(session_id)
        return {"courses": courses, "total": len(courses)}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get courses for session {session_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la récupération des cours: {str(e)}"
        )
