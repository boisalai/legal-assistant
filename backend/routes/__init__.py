"""Routes module for Legal Assistant."""

from .auth import router as auth_router
from .judgments import router as judgments_router

__all__ = ["auth_router", "judgments_router"]
