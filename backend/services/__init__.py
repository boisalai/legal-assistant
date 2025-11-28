"""Services module for Legal Assistant."""

from .model_factory import create_model
from .surreal_service import (
    SurrealDBService,
    get_surreal_service,
    init_surreal_service,
    get_db_connection,
)
from .docling_service import (
    DoclingService,
    DoclingExtractionResult,
    get_docling_service,
    get_available_extraction_methods,
)

__all__ = [
    "create_model",
    "SurrealDBService",
    "get_surreal_service",
    "init_surreal_service",
    "get_db_connection",
    "DoclingService",
    "DoclingExtractionResult",
    "get_docling_service",
    "get_available_extraction_methods",
]
