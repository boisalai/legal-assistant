"""
Routes API de l'application Notary Assistant.
"""

from .dossiers import router as dossiers_router
from .settings import router as settings_router
from .chat import router as chat_router
from .auth import router as auth_router
from .admin import router as admin_router
from .migration import router as migration_router

__all__ = ["dossiers_router", "settings_router", "chat_router", "auth_router", "admin_router", "migration_router"]
