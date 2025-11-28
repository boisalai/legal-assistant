"""
Modèles Pydantic pour Notary Assistant.

Ce module définit tous les modèles de données utilisés par l'API:
- Dossier: Dossier notarial principal
- Document: Documents attachés (PDF, Word, audio, etc.)
- Checklist: Liste de vérification générée
- User: Utilisateur (notaire, assistant)
"""

from datetime import datetime
from typing import Optional, Literal
from pydantic import BaseModel, Field


# ============================================================================
# Types énumérés
# ============================================================================

CaseStatus = Literal["nouveau", "en_analyse", "termine", "en_erreur", "archive"]
TransactionType = Literal["vente", "achat", "hypotheque", "testament", "succession", "autre"]
Priority = Literal["critique", "haute", "moyenne", "basse", "normale"]
ChecklistItemStatus = Literal["complete", "incomplete", "en_attente", "a_verifier", "non_applicable"]
ExtractionStatus = Literal["pending", "processing", "completed", "error"]


# ============================================================================
# Modèles Dossier
# ============================================================================

class DossierBase(BaseModel):
    """Base pour les dossiers."""
    nom_dossier: str = Field(..., min_length=1, max_length=200)
    type_transaction: TransactionType = "vente"
    summary: Optional[str] = Field(None, max_length=200)


class DossierCreate(DossierBase):
    """Données pour créer un dossier."""
    user_id: str


class DossierUpdate(BaseModel):
    """Données pour mettre à jour un dossier."""
    nom_dossier: Optional[str] = None
    type_transaction: Optional[TransactionType] = None
    statut: Optional[CaseStatus] = None
    score_confiance: Optional[float] = None
    summary: Optional[str] = Field(None, max_length=200)


class Dossier(DossierBase):
    """Dossier notarial complet."""
    id: str
    statut: CaseStatus = "nouveau"
    user_id: str
    score_confiance: Optional[float] = None
    pinned: bool = False
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# Modèles Document
# ============================================================================

class DocumentBase(BaseModel):
    """Base pour les documents."""
    nom_fichier: str


class DocumentCreate(DocumentBase):
    """Données pour créer un document."""
    dossier_id: str
    type_mime: str = "application/pdf"
    type_fichier: str = "pdf"
    taille_bytes: int = 0


class Document(BaseModel):
    """Document attaché à un dossier."""
    id: str
    dossier_id: str
    nom_fichier: str
    chemin_fichier: Optional[str] = None  # Alias: chemin_stockage
    type_mime: Optional[str] = "application/pdf"
    type_fichier: Optional[str] = "pdf"  # pdf, doc, docx, txt, md, audio, image
    taille_bytes: Optional[int] = Field(default=0, alias="taille")
    hash_sha256: Optional[str] = None

    # Métadonnées du document
    document_type: Optional[str] = None  # certificat, contrat, pièce d'identité, etc.
    language: Optional[str] = "fr"
    use_ocr: Optional[bool] = False
    is_recording: Optional[bool] = False
    identify_speakers: Optional[bool] = False

    # Extraction et transcription
    texte_extrait: Optional[str] = None
    transcription: Optional[str] = None
    extraction_status: ExtractionStatus = "pending"

    # Timestamps
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    uploaded_at: Optional[datetime] = None  # Alias pour created_at

    class Config:
        from_attributes = True
        populate_by_name = True

    def model_post_init(self, __context):
        """Post-init hook pour gérer les alias."""
        # uploaded_at = created_at si non défini
        if self.uploaded_at is None and self.created_at:
            object.__setattr__(self, 'uploaded_at', self.created_at)
        # chemin_fichier = chemin_stockage
        if hasattr(self, 'chemin_stockage') and self.chemin_fichier is None:
            object.__setattr__(self, 'chemin_fichier', getattr(self, 'chemin_stockage', None))
        # taille = taille_bytes
        if self.taille_bytes == 0 and hasattr(self, 'taille') and self.taille:
            object.__setattr__(self, 'taille_bytes', getattr(self, 'taille', 0))


# ============================================================================
# Modèles Checklist
# ============================================================================

class ChecklistItem(BaseModel):
    """Item de checklist."""
    titre: str
    description: Optional[str] = None
    statut: ChecklistItemStatus = "incomplete"
    priorite: Priority = "normale"
    categorie: Optional[str] = None


class NextStep(BaseModel):
    """Prochaine étape recommandée."""
    etape: str
    delai: str
    responsable: str = "notaire"


class Checklist(BaseModel):
    """Checklist générée par l'analyse."""
    id: Optional[str] = None
    dossier_id: str
    items: list[ChecklistItem] = Field(default_factory=list)
    points_attention: list[str] = Field(default_factory=list)
    documents_manquants: list[str] = Field(default_factory=list)
    score_confiance: float = 0.0
    commentaires: Optional[str] = None
    generated_by: Optional[str] = None
    prochaines_etapes: list[NextStep] = Field(default_factory=list)
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ============================================================================
# Modèles User
# ============================================================================

class UserBase(BaseModel):
    """Base pour les utilisateurs."""
    email: str
    nom: str
    prenom: str


class UserCreate(UserBase):
    """Données pour créer un utilisateur."""
    password: str
    role: Literal["notaire", "assistant", "admin"] = "notaire"


class User(UserBase):
    """Utilisateur du système."""
    id: str
    role: Literal["notaire", "assistant", "admin"] = "notaire"
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# Modèles d'extraction de données
# ============================================================================

class ExtractedAmount(BaseModel):
    """Montant extrait d'un document."""
    montant: float
    format_original: str
    contexte: str = ""


class ExtractedDate(BaseModel):
    """Date extraite d'un document."""
    date: str
    format_original: str
    contexte: str = ""


class ExtractedName(BaseModel):
    """Nom extrait d'un document."""
    nom: str
    role: str = ""
    contexte: str = ""


class ExtractedAddress(BaseModel):
    """Adresse extraite d'un document."""
    adresse_complete: str
    numero_civique: Optional[str] = None
    rue: Optional[str] = None
    ville: Optional[str] = None
    code_postal: Optional[str] = None


class ExtractedDocument(BaseModel):
    """Données extraites d'un document."""
    nom_fichier: str
    texte: str = ""
    montants: list[ExtractedAmount] = Field(default_factory=list)
    dates: list[ExtractedDate] = Field(default_factory=list)
    noms: list[ExtractedName] = Field(default_factory=list)
    adresses: list[ExtractedAddress] = Field(default_factory=list)


class ExtractedData(BaseModel):
    """Ensemble des données extraites."""
    documents: list[ExtractedDocument] = Field(default_factory=list)


# ============================================================================
# Exports
# ============================================================================

__all__ = [
    # Types
    "CaseStatus",
    "TransactionType",
    "Priority",
    "ChecklistItemStatus",
    "ExtractionStatus",
    # Dossier
    "DossierBase",
    "DossierCreate",
    "DossierUpdate",
    "Dossier",
    # Document
    "DocumentBase",
    "DocumentCreate",
    "Document",
    # Checklist
    "ChecklistItem",
    "NextStep",
    "Checklist",
    # User
    "UserBase",
    "UserCreate",
    "User",
    # Extraction
    "ExtractedAmount",
    "ExtractedDate",
    "ExtractedName",
    "ExtractedAddress",
    "ExtractedDocument",
    "ExtractedData",
]
