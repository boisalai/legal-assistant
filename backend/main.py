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
from services.surreal_service import init_surreal_service, get_surreal_service

# Configuration du logging
logging.basicConfig(
    level=logging.INFO if settings.debug else logging.WARNING,
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

    # Initialize SurrealDB service
    logger.info("Initializing SurrealDB service...")
    surreal_service = init_surreal_service(
        url=settings.surreal_url,
        namespace=settings.surreal_namespace,
        database=settings.surreal_database,
        username=settings.surreal_username,
        password=settings.surreal_password,
    )

    try:
        await surreal_service.connect()
        logger.info("SurrealDB connected successfully")
    except Exception as e:
        logger.warning(f"Could not connect to SurrealDB: {e}")
        logger.warning("API will start but database features may not work")

    yield

    # === SHUTDOWN ===
    logger.info("Legal Assistant API - Shutting down...")

    # Shutdown all model servers (MLX, vLLM) if running
    try:
        from services.model_server_manager import shutdown_all_model_servers
        await shutdown_all_model_servers()
        logger.info("All model servers stopped")
    except Exception as e:
        logger.warning(f"Error stopping model servers: {e}")

    # Shutdown SurrealDB
    try:
        service = get_surreal_service()
        await service.disconnect()
        logger.info("SurrealDB disconnected")
    except Exception as e:
        logger.warning(f"Error during shutdown: {e}")

    logger.info("Goodbye!")


# Creation de l'application FastAPI
app = FastAPI(
    title="Legal Assistant API",
    description="""
    API pour l'assistant d'etudes juridiques.

    ## Fonctionnalites

    - **Dossiers**: Gestion de dossiers academiques (cours de droit)
    - **Documents**: Upload et gestion de documents
    - **Authentification**: Systeme de connexion securise

    ## Endpoints principaux

    - `/api/auth/*` - Authentification (login, register, logout)
    - `/api/cases/*` - Gestion des dossiers
    """,
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configuration CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Error handling middleware
try:
    from middleware.error_handler import ErrorHandlerMiddleware, setup_exception_handlers
    app.add_middleware(ErrorHandlerMiddleware)
    setup_exception_handlers(app)
    logger.info("Error handler middleware configured")
except ImportError as e:
    logger.warning(f"Could not load error handler middleware: {e}")


# ============================================================
# ROUTES
# ============================================================

from routes import auth_router, cases_router, documents_router, analysis_router, chat_router, docusaurus_router, activity_router
from routes.settings import router as settings_router
from routes.transcription import router as transcription_router
from routes.extraction import router as extraction_router
from routes.model_servers import router as model_servers_router

app.include_router(auth_router, tags=["Authentication"])
app.include_router(cases_router, tags=["Cases"])
app.include_router(documents_router, tags=["Documents"])
app.include_router(transcription_router, tags=["Transcription"])
app.include_router(extraction_router, tags=["Extraction"])
app.include_router(analysis_router, tags=["Analysis"])
app.include_router(chat_router, tags=["Chat"])
app.include_router(settings_router, tags=["Settings"])
app.include_router(model_servers_router, tags=["Model Servers"])
app.include_router(docusaurus_router, tags=["Docusaurus"])
app.include_router(activity_router, tags=["Activity"])

logger.info("Routes configured: /api/auth, /api/cases, /api/cases/{id}/documents, /api/transcription, /api/extraction, /api/analysis, /api/chat, /api/settings, /api/model-servers, /api/docusaurus")


# ============================================================
# ROUTES DE BASE
# ============================================================

@app.get("/", tags=["Info"])
async def root():
    """Endpoint racine - Information sur l'API."""
    return {
        "name": "Legal Assistant API",
        "version": "0.1.0",
        "description": "Assistant d'etudes juridiques - Gestion de dossiers",
        "endpoints": {
            "docs": "/docs",
            "health": "/health",
            "auth": "/api/auth",
            "cases": "/api/cases"
        }
    }


@app.get("/health", tags=["Info"])
async def health_check():
    """Verification de l'etat de l'API."""
    db_status = "unknown"
    try:
        service = get_surreal_service()
        if service.db:
            db_status = "connected"
        else:
            db_status = "not_connected"
    except Exception:
        db_status = "not_initialized"

    return {
        "status": "healthy",
        "database": db_status,
        "model": settings.model_id,
        "debug": settings.debug,
    }


@app.get("/api/models", tags=["Info"])
async def list_models():
    """Liste les modeles LLM disponibles."""
    from config.models import get_all_models_for_api
    return get_all_models_for_api()


# ============================================================
# POINT D'ENTREE
# ============================================================

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("  Legal Assistant API")
    print("=" * 60)
    print(f"  Mode: {'DEBUG' if settings.debug else 'PRODUCTION'}")
    print(f"  Model: {settings.model_id}")
    print(f"  Docs: http://{settings.api_host}:{settings.api_port}/docs")
    print("=" * 60 + "\n")

    uvicorn.run(
        "main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.api_reload,
        log_level="info"
    )
