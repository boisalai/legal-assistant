"""
Routes for application configuration and settings.

Endpoints:
- GET /api/settings/current - Current settings
- PUT /api/settings/current - Update settings
- GET /api/settings/extraction-methods - Available extraction methods
- GET /api/settings/mlx/status - MLX server status
- POST /api/settings/mlx/start - Start MLX server
- POST /api/settings/mlx/stop - Stop MLX server
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
    """Model for updating settings."""
    model_id: str | None = None
    extraction_method: str | None = None
    use_ocr: bool | None = None
    embedding_provider: str | None = None
    embedding_model: str | None = None


class CurrentSettings(BaseModel):
    """Model for current settings."""
    analysis: Dict[str, Any]
    available_models: Dict[str, Any]
    available_extraction_methods: Dict[str, Any]


# ============================================================================
# Routes
# ============================================================================

@router.get("/current")
async def get_current_settings() -> Dict[str, Any]:
    """
    Retrieve current application settings.

    Returns:
        Dict containing:
        - analysis: Analysis parameters (model_id, extraction_method, use_ocr)
        - available_models: Available LLM models
        - available_extraction_methods: Available extraction methods
    """
    try:
        # Get available models
        available_models = get_all_models_for_api()

        # Get available extraction methods
        extraction_methods = {
            "pypdf": {
                "name": "PyPDF (Standard)",
                "description": "Basic extraction, fast",
                "available": True,
            },
            "docling-standard": {
                "name": "Docling Standard",
                "description": "Advanced extraction with layout",
                "available": False,  # TODO: Implement
            },
            "docling-vlm": {
                "name": "Docling VLM",
                "description": "Maximum extraction with vision",
                "available": False,  # TODO: Implement
            },
        }

        return {
            "analysis": {
                "model_id": settings.model_id,
                "extraction_method": "pypdf",  # Default value
                "use_ocr": False,  # Default value
            },
            "embedding": {
                "provider": settings.embedding_provider,
                "model": settings.embedding_model,
            },
            "available_models": available_models,
            "available_extraction_methods": extraction_methods,
        }
    except Exception as e:
        logger.error(f"Error retrieving settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/current")
async def update_settings(settings_update: SettingsUpdate) -> Dict[str, Any]:
    """
    Update application settings.

    Args:
        settings_update: New settings to apply

    Returns:
        Dict containing confirmation message and updated settings
    """
    try:
        # Update model_id if provided
        if settings_update.model_id:
            settings.model_id = settings_update.model_id
            logger.info(f"Setting model_id updated: {settings_update.model_id}")

        # Update embedding_provider and embedding_model if provided
        if settings_update.embedding_provider:
            settings.embedding_provider = settings_update.embedding_provider
            logger.info(f"Setting embedding_provider updated: {settings_update.embedding_provider}")

        if settings_update.embedding_model:
            settings.embedding_model = settings_update.embedding_model
            logger.info(f"Setting embedding_model updated: {settings_update.embedding_model}")

        # TODO: Persist settings to file or database
        # For now, changes are in memory only

        return {
            "message": "Settings updated successfully",
            "settings": {
                "model_id": settings.model_id,
                "extraction_method": settings_update.extraction_method or "pypdf",
                "use_ocr": settings_update.use_ocr or False,
                "embedding_provider": settings.embedding_provider,
                "embedding_model": settings.embedding_model,
            },
        }
    except Exception as e:
        logger.error(f"Error updating settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/extraction-methods")
async def get_extraction_methods() -> Dict[str, Any]:
    """
    Retrieve available document extraction methods.

    Returns:
        Dict containing:
        - methods: Dictionary of available methods
        - docling_available: Whether Docling is available
        - default: Default method
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
    Retrieve available embedding models.

    Returns:
        Dict containing:
        - providers: Dictionary of available providers
        - default_provider: Default provider
        - default_model: Default model
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
    Check if embeddings exist with a different model than the current one.

    Returns:
        Dict containing:
        - has_mismatch: bool - True if reindexing is needed
        - current_model: str - Currently configured model
        - existing_models: list[str] - Models found in the DB
        - total_chunks: int - Chunks with the current model
        - mismatched_chunks: int - Chunks with a different model
        - documents_to_reindex: int - Number of documents to reindex
    """
    try:
        indexing_service = get_document_indexing_service()
        result = await indexing_service.check_embedding_model_mismatch()
        return result
    except Exception as e:
        logger.error(f"Error checking embedding model: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reindex-all")
async def reindex_all_documents() -> Dict[str, Any]:
    """
    Reindex all documents with the current embedding model.

    WARNING: This operation:
    1. Deletes ALL old embeddings (all models)
    2. Reindexes all documents with the current model
    3. May take several minutes depending on the number of documents

    Returns:
        Dict with:
        - success: bool
        - message: str
        - documents_processed: int
        - chunks_created: int
        - errors: list[str]
    """
    try:
        logger.info("Starting reindexation of all documents")

        surreal_service = get_surreal_service()
        if not surreal_service.db:
            await surreal_service.connect()

        # Retrieve all documents with extracted text
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

        logger.info(f"Found {len(documents)} documents to reindex")

        # Delete ALL old embeddings
        logger.info("Deleting all old embeddings...")
        await surreal_service.query("DELETE document_embedding")

        # Reindex all documents
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
                    logger.warning(f"Incomplete document skipped: {doc_id}")
                    continue

                logger.info(f"Reindexing {doc_id}...")
                index_result = await indexing_service.index_document(
                    document_id=doc_id,
                    case_id=course_id,
                    text_content=texte_extrait,
                    force_reindex=True
                )

                if index_result.get("success"):
                    documents_processed += 1
                    total_chunks_created += index_result.get("chunks_created", 0)
                    logger.info(f"✓ {doc_id}: {index_result.get('chunks_created', 0)} chunks created")
                else:
                    error_msg = f"Failed {doc_id}: {index_result.get('error', 'Unknown error')}"
                    errors.append(error_msg)
                    logger.error(error_msg)

            except Exception as e:
                error_msg = f"Error {doc.get('id', 'unknown')}: {str(e)}"
                errors.append(error_msg)
                logger.error(error_msg)

        logger.info(f"Reindexation completed: {documents_processed}/{len(documents)} documents, {total_chunks_created} chunks")

        return {
            "success": True,
            "message": f"Réindexation terminée avec succès",
            "documents_processed": documents_processed,
            "total_documents": len(documents),
            "chunks_created": total_chunks_created,
            "errors": errors[:10]  # Limit to first 10 errors
        }

    except Exception as e:
        logger.error(f"Error during reindexation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# MLX Server Management
# ============================================================================

class MLXStartRequest(BaseModel):
    """Model for starting the MLX server."""
    model_id: str  # Format: "mlx:mlx-community/Qwen2.5-3B-Instruct-4bit"


@router.get("/mlx/status")
async def get_mlx_status() -> Dict[str, Any]:
    """
    Retrieve the MLX server status.

    Returns:
        Dict containing: running, model, port, host, url
    """
    service = get_mlx_server_service()
    return service.get_status()


@router.post("/mlx/start")
async def start_mlx_server(request: MLXStartRequest) -> Dict[str, Any]:
    """
    Start the MLX server with the specified model.

    Args:
        request: Contains the model_id to start

    Returns:
        Dict with: success, message, status
    """
    try:
        logger.info(f"MLX server start request: {request.model_id}")

        # Start the server (or restart if already running with a different model)
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
        logger.error(f"Error starting MLX server: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/mlx/stop")
async def stop_mlx_server() -> Dict[str, Any]:
    """
    Stop the running MLX server.

    Returns:
        Dict with: success, message
    """
    try:
        service = get_mlx_server_service()
        await service.stop()
        return {
            "success": True,
            "message": "Serveur MLX arrêté",
        }
    except Exception as e:
        logger.error(f"Error stopping MLX server: {e}")
        raise HTTPException(status_code=500, detail=str(e))
