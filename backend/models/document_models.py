"""Modèles Pydantic pour les documents."""

from typing import Optional
from pydantic import BaseModel


class DocumentResponse(BaseModel):
    """Réponse pour un document unique."""
    id: str
    case_id: str
    nom_fichier: str
    type_fichier: str
    type_mime: str
    taille: int
    file_path: str
    created_at: str
    texte_extrait: Optional[str] = None
    file_exists: bool = True  # Whether the file exists on disk
    source_document_id: Optional[str] = None  # ID of parent document if this is derived
    is_derived: Optional[bool] = None  # True if this is a derived file
    derivation_type: Optional[str] = None  # transcription, pdf_extraction, tts


class DocumentListResponse(BaseModel):
    """Réponse pour une liste de documents."""
    documents: list[DocumentResponse]
    total: int
    missing_files: list[str] = []  # List of document IDs with missing files


class RegisterDocumentRequest(BaseModel):
    """Request to register a document by file path (no upload/copy)."""
    file_path: str  # Absolute path to the file on disk
