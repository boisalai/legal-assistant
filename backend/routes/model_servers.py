"""
API routes pour gérer les serveurs de modèles locaux (MLX et vLLM).

Permet de vérifier le statut, démarrer et arrêter les serveurs.
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from services.model_server_manager import get_model_server_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/model-servers", tags=["Model Servers"])


class ServerStatus(BaseModel):
    """Statut d'un serveur de modèle."""
    running: bool
    model: Optional[str] = None
    port: Optional[int] = None
    host: Optional[str] = None
    url: Optional[str] = None


class AllServersStatus(BaseModel):
    """Statut de tous les serveurs."""
    mlx: ServerStatus
    vllm: ServerStatus


@router.get("/status", response_model=AllServersStatus)
async def get_servers_status():
    """
    Retourne le statut de tous les serveurs de modèles.

    Returns:
        Statut de MLX et vLLM
    """
    try:
        manager = get_model_server_manager()
        status = manager.get_status()

        return AllServersStatus(
            mlx=ServerStatus(**status["mlx"]),
            vllm=ServerStatus(**status["vllm"])
        )
    except Exception as e:
        logger.error(f"Error getting server status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stop-all")
async def stop_all_servers():
    """
    Arrête tous les serveurs de modèles.

    Utile pour libérer les ressources.
    """
    try:
        manager = get_model_server_manager()
        await manager.stop_all_servers()

        return {"success": True, "message": "All model servers stopped"}
    except Exception as e:
        logger.error(f"Error stopping servers: {e}")
        raise HTTPException(status_code=500, detail=str(e))
