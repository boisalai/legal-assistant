"""
Routes API pour les paramètres et configuration.

Endpoints:
- GET /api/settings/models - Liste des modèles LLM disponibles
- GET /api/settings/extraction-methods - Méthodes d'extraction PDF
- GET /api/settings/current - Configuration actuelle
- PUT /api/settings/current - Modifier la configuration
"""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

from config.models import get_all_models_for_api, DEFAULT_OLLAMA_MODEL
from services.docling_service import get_available_extraction_methods, DOCLING_AVAILABLE

router = APIRouter(prefix="/api/settings", tags=["settings"])


# ========================================
# Modèles Pydantic pour les settings
# ========================================

class AnalysisSettings(BaseModel):
    """Configuration pour l'analyse de dossiers."""
    model_id: str = f"ollama:{DEFAULT_OLLAMA_MODEL}"
    extraction_method: str = "pypdf"
    use_ocr: bool = False


class SettingsResponse(BaseModel):
    """Réponse pour la configuration actuelle."""
    analysis: AnalysisSettings
    available_models: dict
    available_extraction_methods: dict


# Configuration globale en mémoire (pour MVP)
# TODO: Persister dans SurrealDB par utilisateur
_current_settings = AnalysisSettings()


# ========================================
# Endpoints
# ========================================

@router.get("/models")
async def get_models():
    """
    Liste tous les modèles LLM disponibles.

    Retourne les modèles groupés par provider:
    - ollama: Modèles locaux open-source
    - anthropic: Claude API (production)
    - mlx: Modèles Apple Silicon
    - huggingface: Modèles Transformers

    Chaque modèle inclut:
    - id: Identifiant unique (ex: "ollama:qwen2.5:7b")
    - name: Nom affiché
    - recommended: Si recommandé pour M1 Pro 16Go
    - quality/speed/ram: Caractéristiques
    """
    return {
        "providers": get_all_models_for_api(),
        "defaults": {
            "model_id": f"ollama:{DEFAULT_OLLAMA_MODEL}",
            "extraction_method": "pypdf",
        },
    }


@router.get("/extraction-methods")
async def get_extraction_methods():
    """
    Liste les méthodes d'extraction PDF disponibles.

    Méthodes:
    - pypdf: Extraction basique (toujours disponible)
    - docling-standard: Extraction avancée avec layout
    - docling-vlm: Extraction maximale avec vision model
    """
    return {
        "methods": get_available_extraction_methods(),
        "docling_available": DOCLING_AVAILABLE,
        "default": "pypdf",
    }


@router.get("/current")
async def get_current_settings():
    """Retourne la configuration actuelle."""
    return SettingsResponse(
        analysis=_current_settings,
        available_models=get_all_models_for_api(),
        available_extraction_methods=get_available_extraction_methods(),
    )


@router.put("/current")
async def update_settings(settings: AnalysisSettings):
    """
    Met à jour la configuration.

    Paramètres:
    - model_id: ID du modèle (ex: "ollama:qwen2.5:7b", "anthropic:claude-sonnet-4-5-20250929")
    - extraction_method: Méthode d'extraction PDF
    - use_ocr: Activer l'OCR pour PDFs scannés
    """
    global _current_settings
    _current_settings = settings
    return {"message": "Settings updated", "settings": settings}


@router.get("/health")
async def settings_health():
    """Vérifie l'état des services de configuration."""
    return {
        "status": "ok",
        "docling_available": DOCLING_AVAILABLE,
        "models_loaded": True,
    }
