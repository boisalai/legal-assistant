"""
Routes d'administration pour Notary Assistant.

Endpoints (réservés aux admins):
- GET /api/admin/users - Liste des utilisateurs
- GET /api/admin/users/{id} - Détails d'un utilisateur
- POST /api/admin/users - Créer un utilisateur
- PUT /api/admin/users/{id} - Modifier un utilisateur
- DELETE /api/admin/users/{id} - Supprimer un utilisateur
"""

import secrets
import hashlib
import logging
from typing import Optional, List
from datetime import datetime

from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel, EmailStr

from services.surreal_service import get_surreal_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin", tags=["Administration"])

# OAuth2 scheme for token-based auth
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


# ============================================================================
# Pydantic Models
# ============================================================================

class UserBase(BaseModel):
    email: EmailStr
    name: str
    role: str = "notaire"
    actif: bool = True


class UserCreate(UserBase):
    password: str


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    name: Optional[str] = None
    role: Optional[str] = None
    actif: Optional[bool] = None
    password: Optional[str] = None


class UserResponse(BaseModel):
    id: str
    email: str
    name: str
    role: str
    actif: bool
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class UsersListResponse(BaseModel):
    users: List[UserResponse]
    total: int


# ============================================================================
# Helper Functions
# ============================================================================

def hash_password(password: str) -> str:
    """Hash a password using SHA256."""
    return hashlib.sha256(password.encode()).hexdigest()


# Import active_sessions from auth module
from routes.auth import active_sessions, get_user_by_id


async def get_current_admin_user(token: Optional[str] = Depends(oauth2_scheme)):
    """
    Vérifie que l'utilisateur est connecté ET est admin.
    """
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Non authentifié",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check if token is valid
    user_id = active_sessions.get(token)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalide ou expiré",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Get user and check role
    user = await get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Utilisateur non trouvé"
        )

    if user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès réservé aux administrateurs"
        )

    return user


def format_user(user: dict) -> UserResponse:
    """Format a user dict to UserResponse."""
    user_id = user.get("id", "")
    if isinstance(user_id, dict):
        user_id = f"{user_id.get('tb', 'user')}:{user_id.get('id', {}).get('String', '')}"
    elif hasattr(user_id, '__str__'):
        user_id = str(user_id)

    created_at = user.get("created_at")
    if created_at and hasattr(created_at, 'isoformat'):
        created_at = created_at.isoformat()
    elif created_at:
        created_at = str(created_at)

    updated_at = user.get("updated_at")
    if updated_at and hasattr(updated_at, 'isoformat'):
        updated_at = updated_at.isoformat()
    elif updated_at:
        updated_at = str(updated_at)

    return UserResponse(
        id=user_id,
        email=user.get("email", ""),
        name=user.get("nom", ""),
        role=user.get("role", "notaire"),
        actif=user.get("actif", True),
        created_at=created_at,
        updated_at=updated_at
    )


# ============================================================================
# Endpoints
# ============================================================================

def parse_query_result(result) -> list:
    """
    Parse SurrealDB query result which can be in different formats:
    - [user1, user2, ...] - direct list
    - [{"result": [user1, user2, ...]}] - wrapped in result key
    """
    if not result or len(result) == 0:
        return []

    first_item = result[0]
    # Check if wrapped in {"result": [...]}
    if isinstance(first_item, dict) and "result" in first_item:
        return first_item.get("result", [])
    # Direct list of items
    return result if isinstance(result, list) else []


@router.get("/users", response_model=UsersListResponse)
async def list_users(
    skip: int = 0,
    limit: int = 50,
    admin: dict = Depends(get_current_admin_user)
):
    """
    Liste tous les utilisateurs (admin seulement).
    """
    try:
        service = get_surreal_service()
        if not service.db:
            await service.connect()

        # Get total count
        count_result = await service.query("SELECT count() FROM user GROUP ALL")
        total = 0
        count_items = parse_query_result(count_result)
        if count_items:
            total = count_items[0].get("count", 0)

        # Get paginated users
        result = await service.query(
            "SELECT * FROM user ORDER BY created_at DESC LIMIT $limit START $skip",
            {"limit": limit, "skip": skip}
        )

        users = []
        for user in parse_query_result(result):
            users.append(format_user(user))

        return UsersListResponse(users=users, total=total)

    except Exception as e:
        logger.error(f"Error listing users: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de la récupération des utilisateurs"
        )


@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: str,
    admin: dict = Depends(get_current_admin_user)
):
    """
    Récupère les détails d'un utilisateur (admin seulement).
    """
    try:
        service = get_surreal_service()
        if not service.db:
            await service.connect()

        # Ensure user_id has the correct format
        if not user_id.startswith("user:"):
            user_id = f"user:{user_id}"

        result = await service.select(user_id)

        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Utilisateur non trouvé"
            )

        user = result if isinstance(result, dict) else (result[0] if result else None)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Utilisateur non trouvé"
            )

        return format_user(user)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de la récupération de l'utilisateur"
        )


@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: UserCreate,
    admin: dict = Depends(get_current_admin_user)
):
    """
    Crée un nouvel utilisateur (admin seulement).
    """
    email = user_data.email.lower()
    name = user_data.name.strip()
    password = user_data.password
    role = user_data.role
    actif = user_data.actif

    # Validate
    if len(name) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Le nom doit contenir au moins 2 caractères"
        )

    if len(password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Le mot de passe doit contenir au moins 8 caractères"
        )

    if role not in ["notaire", "assistant", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Le rôle doit être 'notaire', 'assistant' ou 'admin'"
        )

    try:
        service = get_surreal_service()
        if not service.db:
            await service.connect()

        # Check if email already exists
        existing = await service.query(
            "SELECT * FROM user WHERE email = $email",
            {"email": email}
        )
        if parse_query_result(existing):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cet email est déjà associé à un compte"
            )

        # Create user
        user_id = secrets.token_hex(8)
        new_user = await service.create("user", {
            "email": email,
            "nom": name,
            "prenom": "",
            "password_hash": hash_password(password),
            "role": role,
            "actif": actif,
        }, record_id=user_id)

        logger.info(f"Admin created user: {email}")

        return format_user(new_user)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de la création de l'utilisateur"
        )


@router.put("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    user_data: UserUpdate,
    admin: dict = Depends(get_current_admin_user)
):
    """
    Met à jour un utilisateur (admin seulement).
    """
    try:
        service = get_surreal_service()
        if not service.db:
            await service.connect()

        # Ensure user_id has the correct format
        if not user_id.startswith("user:"):
            user_id = f"user:{user_id}"

        # Check if user exists
        existing = await service.select(user_id)
        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Utilisateur non trouvé"
            )

        # Build update data
        update_data = {"updated_at": datetime.utcnow()}

        if user_data.email is not None:
            email = user_data.email.lower()
            # Check if new email is already taken by another user
            check = await service.query(
                "SELECT * FROM user WHERE email = $email AND id != $id",
                {"email": email, "id": user_id}
            )
            if parse_query_result(check):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cet email est déjà utilisé par un autre compte"
                )
            update_data["email"] = email

        if user_data.name is not None:
            if len(user_data.name.strip()) < 2:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Le nom doit contenir au moins 2 caractères"
                )
            update_data["nom"] = user_data.name.strip()

        if user_data.role is not None:
            if user_data.role not in ["notaire", "assistant", "admin"]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Le rôle doit être 'notaire', 'assistant' ou 'admin'"
                )
            update_data["role"] = user_data.role

        if user_data.actif is not None:
            update_data["actif"] = user_data.actif

        if user_data.password is not None:
            if len(user_data.password) < 8:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Le mot de passe doit contenir au moins 8 caractères"
                )
            update_data["password_hash"] = hash_password(user_data.password)

        # Update user
        updated = await service.merge(user_id, update_data)

        logger.info(f"Admin updated user: {user_id}")

        return format_user(updated)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de la mise à jour de l'utilisateur"
        )


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: str,
    admin: dict = Depends(get_current_admin_user)
):
    """
    Supprime un utilisateur (admin seulement).
    """
    try:
        service = get_surreal_service()
        if not service.db:
            await service.connect()

        # Ensure user_id has the correct format
        if not user_id.startswith("user:"):
            user_id = f"user:{user_id}"

        # Check if user exists
        existing = await service.select(user_id)
        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Utilisateur non trouvé"
            )

        # Prevent admin from deleting themselves
        admin_id = admin.get("id", "")
        if isinstance(admin_id, dict):
            admin_id = f"{admin_id.get('tb', 'user')}:{admin_id.get('id', {}).get('String', '')}"
        elif hasattr(admin_id, '__str__'):
            admin_id = str(admin_id)

        if user_id == admin_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Vous ne pouvez pas supprimer votre propre compte"
            )

        # Delete user
        await service.delete(user_id)

        logger.info(f"Admin deleted user: {user_id}")

        return None

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de la suppression de l'utilisateur"
        )
