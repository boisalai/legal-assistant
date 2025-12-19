"""Modèles Pydantic pour les documents."""

from typing import Optional, Dict, Any
from pydantic import BaseModel


class DocusaurusSource(BaseModel):
    """Informations sur la source Docusaurus d'un document."""
    absolute_path: str  # Chemin absolu vers le fichier source
    relative_path: str  # Chemin relatif dans la doc Docusaurus
    last_sync: str  # Timestamp de la dernière synchronisation
    source_hash: str  # SHA-256 du contenu lors de l'import
    source_mtime: float  # Timestamp de modification du fichier source
    needs_reindex: bool = False  # True si le fichier source a changé


class DocumentResponse(BaseModel):
    """Réponse pour un document unique."""
    id: str
    course_id: str
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
    source_type: Optional[str] = None  # "upload", "linked", or "docusaurus"
    linked_source: Optional[Dict[str, Any]] = None  # Info linked directory si applicable
    docusaurus_source: Optional[DocusaurusSource] = None  # Info Docusaurus si applicable
    indexed: Optional[bool] = None  # True si le document a été indexé pour RAG


class DocumentListResponse(BaseModel):
    """Réponse pour une liste de documents."""
    documents: list[DocumentResponse]
    total: int
    missing_files: list[str] = []  # List of document IDs with missing files


class RegisterDocumentRequest(BaseModel):
    """Request to register a document by file path (no upload/copy)."""
    file_path: str  # Absolute path to the file on disk
