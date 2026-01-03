"""
Routes API pour l'administration de la base de données.

Ce module fournit les endpoints pour:
- Gestion des utilisateurs (CRUD)
- Lister les tables avec leurs statistiques (Phase 1)
- Consulter les données des tables (Phase 1)
- Générer des mots de passe sécurisés
- Détecter les orphelins (Phase 2)
- Nettoyer les orphelins (Phase 3)
"""

import hashlib
import logging
import secrets
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, EmailStr

from auth.helpers import require_admin
from services.admin_service import get_admin_service
from services.password_generator_service import generate_passwords_batch
from services.surreal_service import get_surreal_service
from models.admin_models import TableInfo, TableDataResponse

logger = logging.getLogger(__name__)


def hash_password(password: str) -> str:
    """Hash a password using SHA256."""
    return hashlib.sha256(password.encode()).hexdigest()

router = APIRouter(prefix="/api/admin", tags=["Admin"])


# ============================================================================
# MODÈLES PYDANTIC POUR LA GESTION DES UTILISATEURS
# ============================================================================


class AdminUser(BaseModel):
    """Représentation d'un utilisateur pour l'admin."""
    id: str
    email: str
    name: str
    role: str
    actif: bool
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class UsersListResponse(BaseModel):
    """Réponse pour la liste des utilisateurs."""
    users: List[AdminUser]
    total: int


class CreateUserRequest(BaseModel):
    """Requête de création d'utilisateur."""
    email: EmailStr
    name: str
    password: str
    role: str = "notaire"
    actif: bool = True


class UpdateUserRequest(BaseModel):
    """Requête de mise à jour d'utilisateur."""
    email: Optional[EmailStr] = None
    name: Optional[str] = None
    password: Optional[str] = None
    role: Optional[str] = None
    actif: Optional[bool] = None


# ============================================================================
# ENDPOINTS: GESTION DES UTILISATEURS
# ============================================================================


def _user_to_admin_user(user: dict) -> AdminUser:
    """Convertit un utilisateur SurrealDB en AdminUser."""
    user_id = user.get("id")
    if isinstance(user_id, dict):
        user_id = f"{user_id.get('tb', 'user')}:{user_id.get('id', {}).get('String', '')}"
    elif hasattr(user_id, '__str__'):
        user_id = str(user_id)

    return AdminUser(
        id=user_id,
        email=user.get("email", ""),
        name=user.get("nom", ""),
        role=user.get("role", "notaire"),
        actif=user.get("actif", True),
        created_at=str(user.get("created_at", "")) if user.get("created_at") else None,
        updated_at=str(user.get("updated_at", "")) if user.get("updated_at") else None,
    )


@router.get("/users", response_model=UsersListResponse)
async def list_users(
    skip: int = Query(default=0, ge=0, description="Offset de pagination"),
    limit: int = Query(default=50, ge=1, le=100, description="Lignes par page"),
    _user_id: str = Depends(require_admin),
) -> UsersListResponse:
    """
    Liste tous les utilisateurs avec pagination.

    Requiert rôle admin.
    """
    try:
        service = get_surreal_service()
        if not service.db:
            await service.connect()

        # Compte total
        count_result = await service.db.query("SELECT count() AS count FROM user GROUP ALL")
        total = 0
        if count_result and len(count_result) > 0:
            total = count_result[0].get("count", 0)

        # Liste paginée
        result = await service.db.query(
            f"SELECT * FROM user ORDER BY created_at DESC LIMIT {limit} START {skip}"
        )

        users = [_user_to_admin_user(u) for u in result] if result else []

        return UsersListResponse(users=users, total=total)

    except Exception as e:
        logger.error(f"Erreur lors de la récupération des utilisateurs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la récupération des utilisateurs: {str(e)}",
        )


@router.get("/users/{user_id}", response_model=AdminUser)
async def get_user(
    user_id: str,
    _admin_id: str = Depends(require_admin),
) -> AdminUser:
    """
    Récupère un utilisateur par son ID.

    Requiert rôle admin.
    """
    try:
        service = get_surreal_service()
        if not service.db:
            await service.connect()

        # SurrealDB attend le format "table:id"
        if not user_id.startswith("user:"):
            user_id = f"user:{user_id}"

        result = await service.db.query(f"SELECT * FROM {user_id}")

        if not result or len(result) == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Utilisateur non trouvé",
            )

        return _user_to_admin_user(result[0])

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur lors de la récupération de l'utilisateur: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la récupération de l'utilisateur: {str(e)}",
        )


@router.post("/users", response_model=AdminUser, status_code=status.HTTP_201_CREATED)
async def create_user(
    request: CreateUserRequest,
    _admin_id: str = Depends(require_admin),
) -> AdminUser:
    """
    Crée un nouvel utilisateur.

    Requiert rôle admin.
    """
    try:
        service = get_surreal_service()
        if not service.db:
            await service.connect()

        email = request.email.lower()

        # Vérifier si l'email existe déjà
        existing = await service.db.query(
            "SELECT * FROM user WHERE email = $email",
            {"email": email}
        )
        if existing and len(existing) > 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cet email est déjà utilisé",
            )

        # Créer l'utilisateur
        user_id = secrets.token_hex(8)
        current_time = datetime.utcnow().isoformat()

        new_user = await service.create("user", {
            "email": email,
            "nom": request.name,
            "prenom": "",
            "password_hash": hash_password(request.password),
            "role": request.role,
            "actif": request.actif,
            "created_at": current_time,
            "updated_at": current_time,
        }, record_id=user_id)

        logger.info(f"Admin created user: {email}")

        return _user_to_admin_user(new_user)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur lors de la création de l'utilisateur: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la création de l'utilisateur: {str(e)}",
        )


@router.put("/users/{user_id}", response_model=AdminUser)
async def update_user(
    user_id: str,
    request: UpdateUserRequest,
    _admin_id: str = Depends(require_admin),
) -> AdminUser:
    """
    Met à jour un utilisateur.

    Requiert rôle admin.
    """
    try:
        service = get_surreal_service()
        if not service.db:
            await service.connect()

        # SurrealDB attend le format "table:id"
        if not user_id.startswith("user:"):
            user_id = f"user:{user_id}"

        # Vérifier que l'utilisateur existe
        existing = await service.db.query(f"SELECT * FROM {user_id}")
        if not existing or len(existing) == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Utilisateur non trouvé",
            )

        # Construire les champs à mettre à jour
        updates = {"updated_at": datetime.utcnow().isoformat()}

        if request.email is not None:
            email = request.email.lower()
            # Vérifier si l'email est déjà utilisé par un autre utilisateur
            email_check = await service.db.query(
                "SELECT * FROM user WHERE email = $email AND id != $user_id",
                {"email": email, "user_id": user_id}
            )
            if email_check and len(email_check) > 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cet email est déjà utilisé",
                )
            updates["email"] = email

        if request.name is not None:
            updates["nom"] = request.name

        if request.password is not None:
            updates["password_hash"] = hash_password(request.password)

        if request.role is not None:
            updates["role"] = request.role

        if request.actif is not None:
            updates["actif"] = request.actif

        # Construire la requête UPDATE
        set_clauses = ", ".join([f"{k} = ${k}" for k in updates.keys()])
        await service.db.query(
            f"UPDATE {user_id} SET {set_clauses}",
            updates
        )

        # Récupérer l'utilisateur mis à jour
        result = await service.db.query(f"SELECT * FROM {user_id}")

        logger.info(f"Admin updated user: {user_id}")

        return _user_to_admin_user(result[0])

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur lors de la mise à jour de l'utilisateur: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la mise à jour de l'utilisateur: {str(e)}",
        )


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: str,
    _admin_id: str = Depends(require_admin),
):
    """
    Supprime un utilisateur.

    Requiert rôle admin.
    """
    try:
        service = get_surreal_service()
        if not service.db:
            await service.connect()

        # SurrealDB attend le format "table:id"
        if not user_id.startswith("user:"):
            user_id = f"user:{user_id}"

        # Vérifier que l'utilisateur existe
        existing = await service.db.query(f"SELECT * FROM {user_id}")
        if not existing or len(existing) == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Utilisateur non trouvé",
            )

        # Supprimer l'utilisateur
        await service.db.query(f"DELETE {user_id}")

        logger.info(f"Admin deleted user: {user_id}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur lors de la suppression de l'utilisateur: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la suppression de l'utilisateur: {str(e)}",
        )


# ============================================================================
# ENDPOINTS PHASE 1: CONSULTATION DES TABLES
# ============================================================================


@router.get("/tables", response_model=List[TableInfo])
async def list_tables(
    user_id: str = Depends(require_admin),
) -> List[TableInfo]:
    """
    Liste toutes les tables SurrealDB avec leurs statistiques.

    Requiert rôle admin.

    Returns:
        Liste de TableInfo avec row_count pour chaque table

    Raises:
        401: Si non authentifié
        403: Si non admin
        500: Si erreur serveur
    """
    try:
        admin_service = get_admin_service()
        tables = await admin_service.get_all_tables()
        return tables

    except Exception as e:
        logger.error(f"Erreur lors de la récupération des tables: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la récupération des tables: {str(e)}",
        )


@router.get("/tables/{table_name}", response_model=TableDataResponse)
async def get_table_data(
    table_name: str,
    skip: int = Query(default=0, ge=0, description="Offset de pagination"),
    limit: int = Query(default=50, ge=1, le=100, description="Lignes par page"),
    sort: Optional[str] = Query(default=None, description="Champ de tri"),
    order: str = Query(default="asc", regex="^(asc|desc)$", description="Ordre de tri"),
    user_id: str = Depends(require_admin),
) -> TableDataResponse:
    """
    Récupère les données paginées d'une table.

    Requiert rôle admin.

    Args:
        table_name: Nom de la table SurrealDB
        skip: Nombre de lignes à sauter (pagination)
        limit: Nombre de lignes à retourner (1-100)
        sort: Champ de tri (optionnel)
        order: Ordre de tri ('asc' ou 'desc')

    Returns:
        TableDataResponse avec les lignes paginées

    Raises:
        400: Si nom de table invalide
        401: Si non authentifié
        403: Si non admin
        500: Si erreur serveur
    """
    try:
        admin_service = get_admin_service()
        data = await admin_service.get_table_data(
            table_name=table_name,
            skip=skip,
            limit=limit,
            sort_field=sort,
            sort_order=order,
        )
        return data

    except ValueError as e:
        # Table invalide
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des données: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la récupération des données: {str(e)}",
        )


@router.delete("/tables/{table_name}/{record_id}")
async def delete_record(
    table_name: str,
    record_id: str,
    user_id: str = Depends(require_admin),
) -> dict:
    """
    Supprime un enregistrement d'une table.

    Requiert rôle admin.

    Args:
        table_name: Nom de la table SurrealDB
        record_id: ID de l'enregistrement (format: "table:id" ou juste "id")

    Returns:
        Dict avec message de succès

    Raises:
        400: Si nom de table invalide
        401: Si non authentifié
        403: Si non admin
        500: Si erreur serveur
    """
    try:
        admin_service = get_admin_service()
        await admin_service.delete_record(table_name=table_name, record_id=record_id)
        return {"message": f"Enregistrement {record_id} supprimé avec succès"}

    except ValueError as e:
        # Table invalide
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Erreur lors de la suppression de l'enregistrement: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la suppression: {str(e)}",
        )


# ============================================================================
# ENDPOINTS: GÉNÉRATION DE MOTS DE PASSE
# ============================================================================


class PasswordResponse(BaseModel):
    """Réponse pour un mot de passe généré."""
    password: str
    length: int
    strength: str
    score: int
    remarks: List[str]


class PasswordGenerateRequest(BaseModel):
    """Requête pour générer des mots de passe."""
    count: int = 20
    length: int = 16
    include_uppercase: bool = True
    include_lowercase: bool = True
    include_digits: bool = True
    include_symbols: bool = True
    exclude_ambiguous: bool = False


@router.post("/passwords/generate", response_model=List[PasswordResponse])
async def generate_passwords(
    request: PasswordGenerateRequest,
    user_id: str = Depends(require_admin),
) -> List[PasswordResponse]:
    """
    Génère un lot de mots de passe sécurisés.

    Requiert rôle admin.

    Args:
        request: Paramètres de génération

    Returns:
        Liste de mots de passe avec évaluation de force

    Raises:
        401: Si non authentifié
        403: Si non admin
        400: Si paramètres invalides
    """
    try:
        # Limiter le nombre de mots de passe (1-100)
        count = max(1, min(100, request.count))
        # Limiter la longueur (4-128)
        length = max(4, min(128, request.length))

        results = generate_passwords_batch(
            count=count,
            length=length,
            include_uppercase=request.include_uppercase,
            include_lowercase=request.include_lowercase,
            include_digits=request.include_digits,
            include_symbols=request.include_symbols,
            exclude_ambiguous=request.exclude_ambiguous,
        )

        return [
            PasswordResponse(
                password=r.password,
                length=r.length,
                strength=r.strength,
                score=r.score,
                remarks=r.remarks,
            )
            for r in results
        ]

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Erreur lors de la génération des mots de passe: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la génération: {str(e)}",
        )


# ============================================================================
# ENDPOINTS PHASE 2: DÉTECTION D'ORPHELINS (À IMPLÉMENTER)
# ============================================================================

# @router.post("/orphans/analyze", response_model=OrphanAnalysisResult)
# async def analyze_orphans(user_id: str = Depends(require_admin)):
#     """Analyser les orphelins dans la base de données (Phase 2)."""
#     pass


# @router.get("/orphans/types", response_model=List[OrphanTypeInfo])
# async def list_orphan_types(user_id: str = Depends(require_admin)):
#     """Liste les types d'orphelins détectables (Phase 2)."""
#     pass


# ============================================================================
# ENDPOINTS PHASE 3: NETTOYAGE D'ORPHELINS (À IMPLÉMENTER)
# ============================================================================

# @router.post("/orphans/cleanup", response_model=OrphanCleanupResult)
# async def cleanup_orphans(
#     dry_run: bool = Query(default=False),
#     user_id: str = Depends(require_admin)
# ):
#     """Nettoyer les orphelins (Phase 3)."""
#     pass
