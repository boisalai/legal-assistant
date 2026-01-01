"""
Routes pour la gestion des modules d'étude.

Endpoints:
- POST /api/courses/{course_id}/modules - Créer un module
- GET /api/courses/{course_id}/modules - Lister les modules d'un cours
- GET /api/courses/{course_id}/modules/progress - Lister avec progression
- GET /api/courses/{course_id}/progress - Résumé de progression du cours
- POST /api/courses/{course_id}/modules/auto-detect - Détecter les modules
- POST /api/courses/{course_id}/modules/bulk - Créer plusieurs modules
- GET /api/modules/{module_id} - Détails d'un module
- PATCH /api/modules/{module_id} - Mettre à jour un module
- DELETE /api/modules/{module_id} - Supprimer un module
- GET /api/modules/{module_id}/documents - Documents du module
- POST /api/modules/{module_id}/documents - Assigner des documents
- DELETE /api/modules/{module_id}/documents - Désassigner des documents
- GET /api/courses/{course_id}/documents/unassigned - Documents sans module
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, status, Query
from pydantic import BaseModel

from services.module_service import get_module_service
from models.module_models import (
    ModuleCreate,
    ModuleUpdate,
    ModuleResponse,
    ModuleWithProgress,
    ModuleListResponse,
    ModuleListWithProgressResponse,
    AssignDocumentsRequest,
    AssignDocumentsResponse,
    ModuleBulkCreateRequest,
    ModuleBulkCreateResponse,
    AutoDetectResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Modules"])


# ============================================================================
# Course-scoped Module Endpoints
# ============================================================================

@router.post(
    "/api/courses/{course_id}/modules",
    response_model=ModuleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Créer un module"
)
async def create_module(course_id: str, request: ModuleCreate):
    """
    Crée un nouveau module pour un cours.

    Un module permet de grouper des documents par thème/chapitre
    et de suivre la progression d'apprentissage.
    """
    service = get_module_service()

    try:
        module = await service.create_module(course_id, request)
        return module
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Erreur création module: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la création du module: {str(e)}"
        )


@router.get(
    "/api/courses/{course_id}/modules",
    response_model=ModuleListResponse,
    summary="Lister les modules d'un cours"
)
async def list_modules(course_id: str):
    """Liste tous les modules d'un cours, ordonnés par order_index."""
    service = get_module_service()

    modules, total = await service.list_modules(course_id)

    return ModuleListResponse(modules=modules, total=total)


@router.get(
    "/api/courses/{course_id}/modules/progress",
    response_model=ModuleListWithProgressResponse,
    summary="Lister les modules avec progression"
)
async def list_modules_with_progress(
    course_id: str,
    user_id: str = Query(default="user:default", description="ID utilisateur")
):
    """
    Liste tous les modules d'un cours avec leurs métriques de progression.

    Inclut:
    - Progression de lecture (% documents lus)
    - Progression flashcards (% cartes maîtrisées)
    - Scores de quiz
    - Niveau de maîtrise global
    """
    service = get_module_service()

    summary = await service.get_course_progress_summary(course_id, user_id)

    modules = [ModuleWithProgress(**m) for m in summary["modules"]]

    return ModuleListWithProgressResponse(
        modules=modules,
        total=len(modules),
        course_overall_progress=summary["overall_progress"],
        recommended_module_id=summary.get("recommended_module_id"),
        recommendation_message=summary.get("recommendation_message")
    )


@router.get(
    "/api/courses/{course_id}/progress",
    summary="Résumé de progression du cours"
)
async def get_course_progress(
    course_id: str,
    user_id: str = Query(default="user:default", description="ID utilisateur")
):
    """
    Récupère un résumé complet de la progression pour le cours.

    Retourne:
    - Progression globale pondérée par exam_weight
    - Module recommandé pour étude
    - Message de recommandation personnalisé
    """
    service = get_module_service()

    return await service.get_course_progress_summary(course_id, user_id)


@router.post(
    "/api/courses/{course_id}/modules/auto-detect",
    response_model=AutoDetectResponse,
    summary="Détecter automatiquement les modules"
)
async def auto_detect_modules(course_id: str):
    """
    Analyse les noms de fichiers pour détecter automatiquement les modules.

    Patterns reconnus:
    - "Module X - ..." ou "module-X-..."
    - "Chapitre X - ..." ou "chapitre-X-..."
    - "Semaine X - ..." ou "semaine-X-..."
    - Préfixes numériques: "01_...", "1-...", "1_..."

    Retourne des suggestions de modules avec les documents correspondants.
    """
    service = get_module_service()

    detected, unassigned = await service.auto_detect_modules(course_id)

    # Compter le total des documents
    total = sum(d.document_count for d in detected) + len(unassigned)

    return AutoDetectResponse(
        detected_modules=detected,
        unassigned_documents=unassigned,
        total_documents=total
    )


class CreateFromDetectionRequest(BaseModel):
    """Requête pour créer des modules depuis la détection."""
    assign_documents: bool = True


@router.post(
    "/api/courses/{course_id}/modules/from-detection",
    response_model=ModuleBulkCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Créer les modules détectés"
)
async def create_modules_from_detection(
    course_id: str,
    request: Optional[CreateFromDetectionRequest] = None
):
    """
    Exécute la détection automatique et crée les modules détectés.

    Par défaut, assigne automatiquement les documents aux modules créés.
    """
    service = get_module_service()

    assign_docs = request.assign_documents if request else True

    # Détecter les modules
    detected, _ = await service.auto_detect_modules(course_id)

    if not detected:
        return ModuleBulkCreateResponse(created_count=0, modules=[])

    # Créer les modules
    created = await service.create_modules_from_detection(
        course_id,
        detected,
        assign_documents=assign_docs
    )

    return ModuleBulkCreateResponse(
        created_count=len(created),
        modules=created
    )


@router.post(
    "/api/courses/{course_id}/modules/bulk",
    response_model=ModuleBulkCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Créer plusieurs modules"
)
async def bulk_create_modules(course_id: str, request: ModuleBulkCreateRequest):
    """
    Crée plusieurs modules en une seule requête.

    Utile pour configurer rapidement la structure d'un cours.
    """
    service = get_module_service()

    created = []
    for item in request.modules:
        module_data = ModuleCreate(
            name=item.name,
            order_index=item.order_index,
            description=item.description,
            exam_weight=item.exam_weight
        )
        try:
            module = await service.create_module(course_id, module_data)
            created.append(module)
        except Exception as e:
            logger.error(f"Erreur création module {item.name}: {e}")

    return ModuleBulkCreateResponse(
        created_count=len(created),
        modules=created
    )


@router.get(
    "/api/courses/{course_id}/documents/unassigned",
    summary="Documents sans module"
)
async def get_unassigned_documents(course_id: str):
    """
    Récupère les documents du cours qui ne sont assignés à aucun module.

    Utile pour identifier les documents à organiser.
    """
    service = get_module_service()

    documents = await service.get_unassigned_documents(course_id)

    return {
        "documents": documents,
        "total": len(documents)
    }


# ============================================================================
# Module-specific Endpoints
# ============================================================================

@router.get(
    "/api/modules/{module_id}",
    response_model=ModuleResponse,
    summary="Détails d'un module"
)
async def get_module(module_id: str):
    """Récupère les détails d'un module."""
    service = get_module_service()

    module = await service.get_module(module_id)
    if not module:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Module non trouvé: {module_id}"
        )

    return module


@router.get(
    "/api/modules/{module_id}/progress",
    response_model=ModuleWithProgress,
    summary="Module avec progression"
)
async def get_module_with_progress(
    module_id: str,
    user_id: str = Query(default="user:default", description="ID utilisateur")
):
    """Récupère un module avec ses métriques de progression."""
    service = get_module_service()

    module = await service.get_module_with_progress(module_id, user_id)
    if not module:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Module non trouvé: {module_id}"
        )

    return module


@router.patch(
    "/api/modules/{module_id}",
    response_model=ModuleResponse,
    summary="Mettre à jour un module"
)
async def update_module(module_id: str, request: ModuleUpdate):
    """Met à jour les propriétés d'un module."""
    service = get_module_service()

    module = await service.update_module(module_id, request)
    if not module:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Module non trouvé: {module_id}"
        )

    return module


@router.delete(
    "/api/modules/{module_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Supprimer un module"
)
async def delete_module(module_id: str):
    """
    Supprime un module.

    Les documents assignés ne sont pas supprimés, ils sont simplement désassignés.
    """
    service = get_module_service()

    deleted = await service.delete_module(module_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Module non trouvé: {module_id}"
        )

    return None


# ============================================================================
# Document Assignment Endpoints
# ============================================================================

@router.get(
    "/api/modules/{module_id}/documents",
    summary="Documents du module"
)
async def get_module_documents(module_id: str):
    """Récupère tous les documents assignés à un module."""
    service = get_module_service()

    # Vérifier que le module existe
    module = await service.get_module(module_id)
    if not module:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Module non trouvé: {module_id}"
        )

    documents = await service.get_module_documents(module_id)

    return {
        "module_id": module_id,
        "documents": documents,
        "total": len(documents)
    }


@router.post(
    "/api/modules/{module_id}/documents",
    response_model=AssignDocumentsResponse,
    summary="Assigner des documents"
)
async def assign_documents(module_id: str, request: AssignDocumentsRequest):
    """
    Assigne des documents à un module.

    Les documents seront déplacés de leur module actuel (s'il y en a un)
    vers ce module.
    """
    service = get_module_service()

    try:
        count = await service.assign_documents(module_id, request.document_ids)
        return AssignDocumentsResponse(
            module_id=module_id,
            assigned_count=count,
            document_ids=request.document_ids
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.delete(
    "/api/modules/{module_id}/documents",
    summary="Désassigner des documents"
)
async def unassign_documents(module_id: str, request: AssignDocumentsRequest):
    """
    Retire des documents d'un module.

    Les documents ne seront plus associés à aucun module.
    """
    service = get_module_service()

    count = await service.unassign_documents(module_id, request.document_ids)

    return {
        "module_id": module_id,
        "unassigned_count": count,
        "document_ids": request.document_ids
    }
