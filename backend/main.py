"""
Legal Assistant API - Point d'entree principal.

Application FastAPI pour l'assistant d'etudes juridiques.
"""

import logging
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config.settings import settings

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Gestion du cycle de vie de l'application.

    - Startup: Initialisation des connexions
    - Shutdown: Fermeture propre des ressources
    """
    # === STARTUP ===
    logger.info("=" * 60)
    logger.info("Legal Assistant API - Starting up...")
    logger.info("=" * 60)
    logger.info(f"Debug mode: {settings.debug}")
    logger.info(f"API URL: http://{settings.api_host}:{settings.api_port}")
    logger.info(f"SurrealDB: {settings.surreal_url}")
    logger.info(f"Default model: {settings.model_id}")

    yield

    # === SHUTDOWN ===
    logger.info("Legal Assistant API - Shutting down...")
    logger.info("Goodbye!")


# Creation de l'application FastAPI
app = FastAPI(
    title="Legal Assistant API",
    description="API pour l'assistant d'etudes juridiques - Resume de jugements",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configuration CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# ROUTES DE BASE
# ============================================================

@app.get("/")
async def root():
    """Endpoint racine - Information sur l'API."""
    return {
        "name": "Legal Assistant API",
        "version": "0.1.0",
        "description": "Assistant d'etudes juridiques - Resume de jugements",
        "endpoints": {
            "docs": "/docs",
            "health": "/health",
            "judgments": "/api/judgments (coming soon)",
            "summaries": "/api/summaries (coming soon)"
        }
    }


@app.get("/health")
async def health_check():
    """Verification de l'etat de l'API."""
    return {
        "status": "healthy",
        "services": {
            "api": "running",
            "database": "not_connected",  # A implementer
            "llm": "not_tested"  # A implementer
        }
    }


@app.get("/api/models")
async def list_models():
    """Liste les modeles LLM disponibles."""
    from config.models import get_all_models_for_api
    return get_all_models_for_api()


# ============================================================
# ROUTES API (A IMPLEMENTER)
# ============================================================

# TODO: Importer et inclure les routes
# from routes.judgments import router as judgments_router
# app.include_router(judgments_router, prefix="/api/judgments", tags=["judgments"])


# ============================================================
# POINT D'ENTREE
# ============================================================

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.api_reload,
        log_level="info"
    )
