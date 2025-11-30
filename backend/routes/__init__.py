"""Routes module for Legal Assistant."""

from .auth import router as auth_router
from .judgments import router as judgments_router
from .documents import router as documents_router
from .analysis import router as analysis_router
from .chat import router as chat_router

__all__ = ["auth_router", "judgments_router", "documents_router", "analysis_router", "chat_router"]
