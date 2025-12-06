"""Utilitaires partagés."""

from .id_utils import normalize_case_id, normalize_document_id, extract_record_id
from .file_utils import (
    get_file_extension,
    is_allowed_file,
    get_mime_type,
    is_audio_file,
    ALLOWED_EXTENSIONS,
    AUDIO_EXTENSIONS,
    MAX_FILE_SIZE,
)

__all__ = [
    # ID utilities
    "normalize_case_id",
    "normalize_document_id",
    "extract_record_id",
    # File utilities
    "get_file_extension",
    "is_allowed_file",
    "get_mime_type",
    "is_audio_file",
    "ALLOWED_EXTENSIONS",
    "AUDIO_EXTENSIONS",
    "MAX_FILE_SIZE",
]
