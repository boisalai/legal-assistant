"""Modèles Pydantic pour les documents."""

from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class DocusaurusSource(BaseModel):
    """Informations sur la source Docusaurus d'un document."""
    absolute_path: str  # Chemin absolu vers le fichier source
    relative_path: str  # Chemin relatif dans la doc Docusaurus
    last_sync: str  # Timestamp de la dernière synchronisation
    source_hash: str  # SHA-256 du contenu lors de l'import
    source_mtime: float  # Timestamp de modification du fichier source
    needs_reindex: bool = False  # True si le fichier source a changé


class DocumentResponse(BaseModel):
    """Response for a single document.

    Uses English field names throughout the API for consistency.
    """
    id: str
    course_id: str
    filename: str
    file_type: str
    mime_type: str
    size: int
    file_path: str
    created_at: str
    extracted_text: Optional[str] = None
    file_exists: bool = True
    source_document_id: Optional[str] = None
    is_derived: Optional[bool] = None
    derivation_type: Optional[str] = None
    source_type: Optional[str] = None
    linked_source: Optional[Dict[str, Any]] = None
    docusaurus_source: Optional[DocusaurusSource] = None
    indexed: Optional[bool] = None
    module_id: Optional[str] = None  # ID du module auquel ce document est assigné


class DocumentListResponse(BaseModel):
    """Réponse pour une liste de documents."""
    documents: list[DocumentResponse]
    total: int
    missing_files: list[str] = []  # List of document IDs with missing files


class RegisterDocumentRequest(BaseModel):
    """Request to register a document by file path (no upload/copy)."""
    file_path: str  # Absolute path to the file on disk
