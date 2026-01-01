"""Routes module for Legal Assistant."""

from .auth import router as auth_router
from .courses import router as courses_router
from .documents import router as documents_router
from .chat import router as chat_router
from .docusaurus import router as docusaurus_router
from .activity import router as activity_router
from .linked_directory import router as linked_directory_router
from .flashcards import router as flashcards_router
from .modules import router as modules_router

__all__ = [
    "auth_router",
    "courses_router",
    "documents_router",
    "chat_router",
    "docusaurus_router",
    "activity_router",
    "linked_directory_router",
    "flashcards_router",
    "modules_router",
]
