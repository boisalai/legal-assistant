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
    """Réponse pour un document unique.

    Note: Uses serialization_alias to maintain backwards compatibility with French field names
    in the API response while using English names internally.
    """
    id: str
    course_id: str
    filename: str = Field(serialization_alias="nom_fichier")
    file_type: str = Field(serialization_alias="type_fichier")
    mime_type: str = Field(serialization_alias="type_mime")
    size: int = Field(serialization_alias="taille")
    file_path: str
    created_at: str
    extracted_text: Optional[str] = Field(default=None, serialization_alias="texte_extrait")
    file_exists: bool = True
    source_document_id: Optional[str] = None
    is_derived: Optional[bool] = None
    derivation_type: Optional[str] = None
    source_type: Optional[str] = None
    linked_source: Optional[Dict[str, Any]] = None
    docusaurus_source: Optional[DocusaurusSource] = None
    indexed: Optional[bool] = None

    class Config:
        populate_by_name = True  # Allow populating by both alias and field name


class DocumentListResponse(BaseModel):
    """Réponse pour une liste de documents."""
    documents: list[DocumentResponse]
    total: int
    missing_files: list[str] = []  # List of document IDs with missing files


class RegisterDocumentRequest(BaseModel):
    """Request to register a document by file path (no upload/copy)."""
    file_path: str  # Absolute path to the file on disk
