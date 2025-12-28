"""
Routes API pour l'administration de la base de données.

Ce module fournit les endpoints pour:
- Lister les tables avec leurs statistiques (Phase 1)
- Consulter les données des tables (Phase 1)
- Détecter les orphelins (Phase 2)
- Nettoyer les orphelins (Phase 3)
"""

import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status

from auth.helpers import require_admin
from services.admin_service import get_admin_service
from models.admin_models import TableInfo, TableDataResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin", tags=["Admin"])


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
