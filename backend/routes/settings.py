"""
Routes pour la configuration et les paramètres de l'application.

Endpoints:
- GET /api/settings/current - Paramètres actuels
- PUT /api/settings/current - Mettre à jour les paramètres
- GET /api/settings/extraction-methods - Méthodes d'extraction disponibles
- GET /api/settings/mlx/status - Statut du serveur MLX
- POST /api/settings/mlx/start - Démarrer le serveur MLX
- POST /api/settings/mlx/stop - Arrêter le serveur MLX
"""

import logging
from typing import Dict, Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from config.settings import settings
from config.models import get_all_models_for_api
from services.mlx_server_service import get_mlx_server_service, ensure_mlx_server

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/settings", tags=["Settings"])


# ============================================================================
# Pydantic Models
# ============================================================================

class SettingsUpdate(BaseModel):
    """Modèle pour la mise à jour des paramètres."""
    model_id: str | None = None
    extraction_method: str | None = None
    use_ocr: bool | None = None


class CurrentSettings(BaseModel):
    """Modèle pour les paramètres actuels."""
    analysis: Dict[str, Any]
    available_models: Dict[str, Any]
    available_extraction_methods: Dict[str, Any]


# ============================================================================
# Routes
# ============================================================================

@router.get("/current")
async def get_current_settings() -> Dict[str, Any]:
    """
    Récupère les paramètres actuels de l'application.

    Returns:
        Dict contenant:
        - analysis: Paramètres d'analyse (model_id, extraction_method, use_ocr)
        - available_models: Modèles LLM disponibles
        - available_extraction_methods: Méthodes d'extraction disponibles
    """
    try:
        # Récupérer les modèles disponibles
        available_models = get_all_models_for_api()

        # Récupérer les méthodes d'extraction disponibles
        extraction_methods = {
            "pypdf": {
                "name": "PyPDF (Standard)",
                "description": "Extraction basique, rapide",
                "available": True,
            },
            "docling-standard": {
                "name": "Docling Standard",
                "description": "Extraction avancée avec layout",
                "available": False,  # TODO: Implémenter
            },
            "docling-vlm": {
                "name": "Docling VLM",
                "description": "Extraction maximale avec vision",
                "available": False,  # TODO: Implémenter
            },
        }

        return {
            "analysis": {
                "model_id": settings.model_id,
                "extraction_method": "pypdf",  # Valeur par défaut
                "use_ocr": False,  # Valeur par défaut
            },
            "available_models": available_models,
            "available_extraction_methods": extraction_methods,
        }
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des paramètres: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/current")
async def update_settings(settings_update: SettingsUpdate) -> Dict[str, Any]:
    """
    Met à jour les paramètres de l'application.

    Args:
        settings_update: Nouveaux paramètres à appliquer

    Returns:
        Dict contenant le message de confirmation et les paramètres mis à jour
    """
    try:
        # Mettre à jour model_id si fourni
        if settings_update.model_id:
            settings.model_id = settings_update.model_id
            logger.info(f"Paramètre model_id mis à jour: {settings_update.model_id}")

        # TODO: Persister les paramètres dans un fichier ou base de données
        # Pour l'instant, les changements sont en mémoire seulement

        return {
            "message": "Paramètres mis à jour avec succès",
            "settings": {
                "model_id": settings.model_id,
                "extraction_method": settings_update.extraction_method or "pypdf",
                "use_ocr": settings_update.use_ocr or False,
            },
        }
    except Exception as e:
        logger.error(f"Erreur lors de la mise à jour des paramètres: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/extraction-methods")
async def get_extraction_methods() -> Dict[str, Any]:
    """
    Récupère les méthodes d'extraction de documents disponibles.

    Returns:
        Dict contenant:
        - methods: Dictionnaire des méthodes disponibles
        - docling_available: Si Docling est disponible
        - default: Méthode par défaut
    """
    return {
        "methods": {
            "pypdf": {
                "name": "PyPDF (Standard)",
                "description": "Extraction basique, rapide",
                "available": True,
            },
            "docling-standard": {
                "name": "Docling Standard",
                "description": "Extraction avancée avec layout",
                "available": False,
            },
            "docling-vlm": {
                "name": "Docling VLM",
                "description": "Extraction maximale avec vision",
                "available": False,
            },
        },
        "docling_available": False,
        "default": "pypdf",
    }


# ============================================================================
# MLX Server Management
# ============================================================================

class MLXStartRequest(BaseModel):
    """Modèle pour démarrer le serveur MLX."""
    model_id: str  # Format: "mlx:mlx-community/Qwen2.5-3B-Instruct-4bit"


@router.get("/mlx/status")
async def get_mlx_status() -> Dict[str, Any]:
    """
    Récupère le statut du serveur MLX.

    Returns:
        Dict contenant: running, model, port, host, url
    """
    service = get_mlx_server_service()
    return service.get_status()


@router.post("/mlx/start")
async def start_mlx_server(request: MLXStartRequest) -> Dict[str, Any]:
    """
    Démarre le serveur MLX avec le modèle spécifié.

    Args:
        request: Contient le model_id à démarrer

    Returns:
        Dict avec: success, message, status
    """
    try:
        logger.info(f"Demande de démarrage serveur MLX: {request.model_id}")

        # Démarrer le serveur (ou redémarrer si déjà en cours avec un autre modèle)
        success = await ensure_mlx_server(request.model_id)

        if success:
            service = get_mlx_server_service()
            return {
                "success": True,
                "message": f"Serveur MLX démarré avec {request.model_id}",
                "status": service.get_status(),
            }
        else:
            return {
                "success": False,
                "message": "Échec du démarrage du serveur MLX. Vérifiez les logs.",
                "status": get_mlx_server_service().get_status(),
            }
    except Exception as e:
        logger.error(f"Erreur lors du démarrage du serveur MLX: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/mlx/stop")
async def stop_mlx_server() -> Dict[str, Any]:
    """
    Arrête le serveur MLX en cours.

    Returns:
        Dict avec: success, message
    """
    try:
        service = get_mlx_server_service()
        await service.stop()
        return {
            "success": True,
            "message": "Serveur MLX arrêté",
        }
    except Exception as e:
        logger.error(f"Erreur lors de l'arrêt du serveur MLX: {e}")
        raise HTTPException(status_code=500, detail=str(e))
