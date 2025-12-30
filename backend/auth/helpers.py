"""
Helpers d'authentification centralisés pour éviter la duplication.

Utilisé par tous les routers nécessitant une authentification.
"""

from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from config.settings import settings

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


async def get_current_user_id(token: Optional[str] = Depends(oauth2_scheme)) -> Optional[str]:
    """
    Get current user ID from token.

    Args:
        token: JWT token from Authorization header

    Returns:
        User ID if token is valid, None otherwise
    """
    # Import here to avoid circular dependency
    from routes.auth import active_sessions

    if not token:
        return None
    return active_sessions.get(token)


async def require_auth(token: Optional[str] = Depends(oauth2_scheme)) -> str:
    """
    Require authentication (relaxed in debug mode).

    Args:
        token: JWT token from Authorization header

    Returns:
        User ID if authenticated

    Raises:
        HTTPException: If not authenticated in production mode
    """
    # Import here to avoid circular dependency
    from routes.auth import active_sessions

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


async def require_admin(token: Optional[str] = Depends(oauth2_scheme)) -> str:
    """
    Require admin role (strict authentication, no debug bypass).

    Args:
        token: JWT token from Authorization header

    Returns:
        User ID if authenticated and has admin role

    Raises:
        HTTPException: If not authenticated (401) or not admin (403)
    """
    # Import here to avoid circular dependency
    from routes.auth import get_user_by_id, active_sessions

    # First, ensure user is authenticated
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

    # Get user details to check role
    user = await get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Utilisateur non trouve",
        )

    # Check for admin role
    user_role = user.get("role", "")
    if user_role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acces administrateur requis",
        )

    return user_id
