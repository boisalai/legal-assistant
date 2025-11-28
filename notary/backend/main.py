"""
Point d'entrée principal de l'API Notary Assistant.

Cette application utilise AgentOS pour gérer les agents Agno et exposer
une API FastAPI avec des endpoints pré-construits + nos routes personnalisées.
"""

import asyncio
import logging
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from agno.os import AgentOS
from agno.db.sqlite import SqliteDb

from config import settings
from workflows.agents import create_all_agents
from services.surreal_service import init_surreal_service, get_surreal_service

# Configuration du logging structuré
logging.basicConfig(
    level=logging.INFO if settings.debug else logging.WARNING,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s - [%(filename)s:%(lineno)d]",
    handlers=[
        logging.StreamHandler(),
    ]
)
logger = logging.getLogger(__name__)

# Configurer le niveau de log pour les bibliothèques externes
logging.getLogger("uvicorn").setLevel(logging.INFO)
logging.getLogger("fastapi").setLevel(logging.INFO)
logging.getLogger("agno").setLevel(logging.INFO if settings.debug else logging.WARNING)


# ============================================================================
# Configuration et création des agents
# ============================================================================

print("🚀 Démarrage de l'application Notary Assistant...")
print(f"   - Mode: {'DEBUG' if settings.debug else 'PRODUCTION'}")
print(f"   - LLM Provider: {settings.llm_provider}")
print(f"   - Upload dir: {settings.upload_dir}")

# Créer le répertoire data si nécessaire
data_dir = Path("data")
data_dir.mkdir(exist_ok=True)

# Créer tous les agents avec la base de données SQLite partagée
logger.info("Création des agents Agno...")
agents_dict = create_all_agents(
    model=None,  # Utilise MLX par défaut
    db_file=str(data_dir / "agno.db")
)

# Convertir le dict en liste pour AgentOS
agents = list(agents_dict.values())

logger.info(f"✓ {len(agents)} agents créés")


# ============================================================================
# Initialisation de la connexion SurrealDB GLOBALE (lazy)
# ============================================================================

# IMPORTANT: Initialiser le service mais ne PAS connecter immédiatement
# La connexion sera établie à la première requête (lazy initialization)
# Cela évite les problèmes avec asyncio.run() et l'event loop d'Uvicorn

logger.info("🔌 Initializing global SurrealDB service (lazy)...")

surreal_service = init_surreal_service(
    url=settings.surreal_url,
    namespace=settings.surreal_namespace,
    database=settings.surreal_database,
    username=settings.surreal_username,
    password=settings.surreal_password,
)

logger.info("✅ SurrealDB service initialized (will connect on first request)")


# ============================================================================
# Création de l'application avec AgentOS
# ============================================================================

# AgentOS crée automatiquement une application FastAPI avec des endpoints
# pour servir, monitorer et gérer les agents
agent_os = AgentOS(agents=agents)

# Obtenir l'application FastAPI générée par AgentOS
app = agent_os.get_app()

# Personnaliser les métadonnées de l'application
app.title = "Notary Assistant API"
app.description = (
    "API pour l'assistant IA de vérification notariale.\n\n"
    "Cette API combine:\n"
    "- Endpoints Agno pré-construits pour les agents (/v1/agents/*)\n"
    "- Routes personnalisées pour la gestion de dossiers (/api/dossiers/*)\n"
    "- Documentation interactive (Swagger UI)\n"
)
app.version = "0.2.0"  # Version 0.2.0 avec AgentOS
app.debug = settings.debug

logger.info("✓ Application FastAPI créée via AgentOS")


# ============================================================================
# Shutdown handler: Fermeture propre de la connexion SurrealDB
# ============================================================================

import atexit

def cleanup_db_connection():
    """Ferme la connexion SurrealDB à l'arrêt de l'application."""
    try:
        logger.info("🔌 Closing global SurrealDB connection...")
        service = get_surreal_service()
        asyncio.run(service.disconnect())
        logger.info("✅ Global SurrealDB connection closed")
    except Exception as e:
        logger.warning(f"Error during DB cleanup: {e}")

# Enregistrer le cleanup à l'arrêt
atexit.register(cleanup_db_connection)


# ============================================================================
# Configuration CORS
# ============================================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # Frontend Next.js (port par défaut)
        "http://localhost:3001",  # Frontend Next.js (port alternatif)
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logger.info("✓ Middleware CORS configuré")

# Ajouter le middleware de gestion d'erreurs
from middleware.error_handler import ErrorHandlerMiddleware, setup_exception_handlers

app.add_middleware(ErrorHandlerMiddleware)
setup_exception_handlers(app)

logger.info("✓ Middleware de gestion d'erreurs configuré")


# ============================================================================
# Routes personnalisées
# ============================================================================

# Ajouter nos routes personnalisées pour la gestion de dossiers
from routes import dossiers_router, settings_router, chat_router, auth_router, admin_router, migration_router

app.include_router(
    dossiers_router,
    prefix="/api/dossiers",
    tags=["Dossiers Notariaux"]
)

app.include_router(
    settings_router,
    tags=["Settings & Configuration"]
)

app.include_router(
    chat_router,
    tags=["Chat & Assistant IA"]
)

app.include_router(
    auth_router,
    tags=["Authentication"]
)

app.include_router(
    admin_router,
    tags=["Administration"]
)

app.include_router(
    migration_router,
    tags=["Migration"]
)

logger.info("✓ Routes personnalisées ajoutées")


# ============================================================================
# Routes de base additionnelles
# ============================================================================

@app.get("/", tags=["Info"])
async def root():
    """
    Endpoint racine pour vérifier que l'API fonctionne.
    """
    return {
        "message": "Bienvenue sur l'API Notary Assistant (powered by AgentOS)",
        "version": "0.2.0",
        "status": "operational",
        "agents": {
            "count": len(agents),
            "agents": [agent.name for agent in agents]
        },
        "docs": {
            "swagger": "/docs",
            "redoc": "/redoc",
        },
        "endpoints": {
            "agents": "/v1/agents",  # Endpoints Agno
            "dossiers": "/api/dossiers",  # Routes personnalisées
        }
    }


@app.get("/health", tags=["Info"])
async def health_check():
    """
    Health check pour monitoring.
    """
    return {
        "status": "healthy",
        "llm_provider": settings.llm_provider,
        "debug": settings.debug,
        "agents": {
            "count": len(agents),
            "names": [agent.name for agent in agents]
        }
    }


# ============================================================================
# Gestion des erreurs
# ============================================================================

# NOTE: La gestion des erreurs est maintenant gérée par ErrorHandlerMiddleware
# et setup_exception_handlers() configurés ci-dessus


# ============================================================================
# Logging de démarrage
# ============================================================================

print("\n" + "="*70)
print("✨ Notary Assistant API prête")
print("="*70)
print(f"📚 Documentation: http://{settings.api_host}:{settings.api_port}/docs")
print(f"🤖 Agents Agno: {len(agents)} agents disponibles")
print(f"📁 Routes dossiers: /api/dossiers")
print("="*70 + "\n")


if __name__ == "__main__":
    """
    Permet de lancer l'API directement avec: python main.py
    """
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.api_reload,
    )
