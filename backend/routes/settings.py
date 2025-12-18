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
from services.document_indexing_service import get_document_indexing_service
from services.surreal_service import get_surreal_service

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
    embedding_provider: str | None = None
    embedding_model: str | None = None


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
            "embedding": {
                "provider": settings.embedding_provider,
                "model": settings.embedding_model,
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

        # Mettre à jour embedding_provider et embedding_model si fournis
        if settings_update.embedding_provider:
            settings.embedding_provider = settings_update.embedding_provider
            logger.info(f"Paramètre embedding_provider mis à jour: {settings_update.embedding_provider}")

        if settings_update.embedding_model:
            settings.embedding_model = settings_update.embedding_model
            logger.info(f"Paramètre embedding_model mis à jour: {settings_update.embedding_model}")

        # TODO: Persister les paramètres dans un fichier ou base de données
        # Pour l'instant, les changements sont en mémoire seulement

        return {
            "message": "Paramètres mis à jour avec succès",
            "settings": {
                "model_id": settings.model_id,
                "extraction_method": settings_update.extraction_method or "pypdf",
                "use_ocr": settings_update.use_ocr or False,
                "embedding_provider": settings.embedding_provider,
                "embedding_model": settings.embedding_model,
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


@router.get("/embedding-models")
async def get_embedding_models() -> Dict[str, Any]:
    """
    Récupère les modèles d'embedding disponibles.

    Returns:
        Dict contenant:
        - providers: Dictionnaire des providers disponibles
        - default_provider: Provider par défaut
        - default_model: Modèle par défaut
    """
    return {
        "providers": {
            "local": {
                "name": "Local (Gratuit)",
                "description": "Modèle local gratuit avec support GPU (Apple Silicon/CUDA)",
                "icon": "cpu",
                "requires_api_key": False,
                "cost": "Gratuit",
                "models": [
                    {
                        "id": "BAAI/bge-m3",
                        "name": "BGE-M3 (Recommandé)",
                        "dimensions": 1024,
                        "description": "Multilingue (100+ langues), SOTA pour juridique FR/EN",
                        "recommended": True,
                        "multilingual": True,
                        "languages": "FR, EN, 100+ langues",
                        "quality": "Excellent",
                        "speed": "Rapide (~5 chunks/s avec GPU)",
                        "ram": "~2 GB",
                    }
                ],
                "default": "BAAI/bge-m3",
            },
            "openai": {
                "name": "OpenAI (Payant)",
                "description": "Embeddings OpenAI via API (nécessite clé API)",
                "icon": "cloud",
                "requires_api_key": True,
                "cost": "Payant (à la requête)",
                "models": [
                    {
                        "id": "text-embedding-3-small",
                        "name": "Text Embedding 3 Small",
                        "dimensions": 1536,
                        "description": "Multilingue, bon rapport qualité/prix",
                        "recommended": True,
                        "multilingual": True,
                        "languages": "FR, EN, multilingue",
                        "quality": "Très bon",
                        "cost": "~$0.00002 / 1K tokens",
                        "best_for": "Usage général avec petit budget",
                    },
                    {
                        "id": "text-embedding-3-large",
                        "name": "Text Embedding 3 Large",
                        "dimensions": 3072,
                        "description": "Multilingue, meilleure qualité OpenAI",
                        "recommended": False,
                        "multilingual": True,
                        "languages": "FR, EN, multilingue",
                        "quality": "Excellent",
                        "cost": "~$0.00013 / 1K tokens",
                        "best_for": "Maximum de précision, budget plus élevé",
                    },
                ],
                "default": "text-embedding-3-small",
            },
        },
        "default_provider": "local",
        "default_model": "BAAI/bge-m3",
        "current": {
            "provider": settings.embedding_provider,
            "model": settings.embedding_model,
        },
    }


# ============================================================================
# Embedding Model Management
# ============================================================================

@router.get("/check-embedding-mismatch")
async def check_embedding_mismatch() -> Dict[str, Any]:
    """
    Vérifie si des embeddings existent avec un modèle différent du modèle actuel.

    Returns:
        Dict contenant:
        - has_mismatch: bool - True si réindexation nécessaire
        - current_model: str - Modèle actuellement configuré
        - existing_models: list[str] - Modèles trouvés dans la DB
        - total_chunks: int - Chunks avec le modèle actuel
        - mismatched_chunks: int - Chunks avec un modèle différent
        - documents_to_reindex: int - Nombre de documents à réindexer
    """
    try:
        indexing_service = get_document_indexing_service()
        result = await indexing_service.check_embedding_model_mismatch()
        return result
    except Exception as e:
        logger.error(f"Erreur lors de la vérification du modèle d'embedding: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reindex-all")
async def reindex_all_documents() -> Dict[str, Any]:
    """
    Réindexe tous les documents avec le modèle d'embedding actuel.

    ATTENTION: Cette opération:
    1. Supprime TOUS les anciens embeddings (tous modèles confondus)
    2. Réindexe tous les documents avec le modèle actuel
    3. Peut prendre plusieurs minutes selon le nombre de documents

    Returns:
        Dict avec:
        - success: bool
        - message: str
        - documents_processed: int
        - chunks_created: int
        - errors: list[str]
    """
    try:
        logger.info("Début de la réindexation de tous les documents")

        surreal_service = get_surreal_service()
        if not surreal_service.db:
            await surreal_service.connect()

        # Récupérer tous les documents avec du texte extrait
        query = """
        SELECT id, course_id, texte_extrait
        FROM document
        WHERE texte_extrait IS NOT NONE AND texte_extrait != ''
        """
        result = await surreal_service.query(query)

        documents = []
        if result and len(result) > 0:
            docs_data = result[0]
            if isinstance(docs_data, dict) and "result" in docs_data:
                documents = docs_data["result"] if isinstance(docs_data["result"], list) else []
            elif isinstance(docs_data, list):
                documents = docs_data

        if not documents:
            return {
                "success": True,
                "message": "Aucun document à réindexer",
                "documents_processed": 0,
                "chunks_created": 0,
                "errors": []
            }

        logger.info(f"Trouvé {len(documents)} documents à réindexer")

        # Supprimer TOUS les anciens embeddings
        logger.info("Suppression de tous les anciens embeddings...")
        await surreal_service.query("DELETE document_embedding")

        # Réindexer tous les documents
        indexing_service = get_document_indexing_service()
        documents_processed = 0
        total_chunks_created = 0
        errors = []

        for doc in documents:
            try:
                doc_id = doc.get("id")
                course_id = doc.get("course_id")
                texte_extrait = doc.get("texte_extrait")

                if not doc_id or not course_id or not texte_extrait:
                    logger.warning(f"Document incomplet ignoré: {doc_id}")
                    continue

                logger.info(f"Réindexation de {doc_id}...")
                index_result = await indexing_service.index_document(
                    document_id=doc_id,
                    case_id=course_id,
                    text_content=texte_extrait,
                    force_reindex=True
                )

                if index_result.get("success"):
                    documents_processed += 1
                    total_chunks_created += index_result.get("chunks_created", 0)
                    logger.info(f"✓ {doc_id}: {index_result.get('chunks_created', 0)} chunks créés")
                else:
                    error_msg = f"Échec {doc_id}: {index_result.get('error', 'Unknown error')}"
                    errors.append(error_msg)
                    logger.error(error_msg)

            except Exception as e:
                error_msg = f"Erreur {doc.get('id', 'unknown')}: {str(e)}"
                errors.append(error_msg)
                logger.error(error_msg)

        logger.info(f"Réindexation terminée: {documents_processed}/{len(documents)} documents, {total_chunks_created} chunks")

        return {
            "success": True,
            "message": f"Réindexation terminée avec succès",
            "documents_processed": documents_processed,
            "total_documents": len(documents),
            "chunks_created": total_chunks_created,
            "errors": errors[:10]  # Limiter à 10 premières erreurs
        }

    except Exception as e:
        logger.error(f"Erreur lors de la réindexation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


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
