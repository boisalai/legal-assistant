"""
Modeles de donnees pour les jugements juridiques.

Ce module definit les schemas Pydantic pour:
- Judgment: Un jugement/decision de justice
- JurisdictionType: Types de juridictions (Quebec, Canada, etc.)
- CourtLevel: Niveaux de tribunaux
"""

from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


# Types de juridictions
JurisdictionType = Literal[
    "quebec",      # Droit civil quebecois
    "canada",      # Droit federal canadien
    "common_law",  # Provinces de common law
    "other"        # Autres juridictions
]

# Niveaux de tribunaux
CourtLevel = Literal[
    "supreme_court",        # Cour supreme du Canada
    "court_of_appeal",      # Cours d'appel
    "superior_court",       # Cours superieures
    "provincial_court",     # Cours provinciales
    "administrative",       # Tribunaux administratifs
    "other"                 # Autres
]

# Domaines de droit
LegalDomain = Literal[
    "civil",            # Droit civil
    "criminal",         # Droit criminel
    "administrative",   # Droit administratif
    "constitutional",   # Droit constitutionnel
    "family",           # Droit de la famille
    "labour",           # Droit du travail
    "commercial",       # Droit commercial
    "property",         # Droit des biens
    "contract",         # Droit des contrats
    "tort",             # Responsabilite civile
    "other"             # Autre
]

# Statut du jugement
JudgmentStatus = Literal[
    "pending",      # En attente d'analyse
    "analyzing",    # En cours d'analyse
    "completed",    # Analyse terminee
    "error"         # Erreur lors de l'analyse
]


class JudgmentBase(BaseModel):
    """Schema de base pour un jugement."""

    # Identification
    title: str = Field(..., description="Nom de l'affaire (ex: Doe c. Smith)")
    citation: Optional[str] = Field(None, description="Reference officielle (ex: 2024 QCCS 1234)")
    neutral_citation: Optional[str] = Field(None, description="Reference neutre")

    # Tribunal
    court: str = Field(..., description="Nom du tribunal")
    court_level: CourtLevel = Field(default="superior_court", description="Niveau du tribunal")
    jurisdiction: JurisdictionType = Field(default="quebec", description="Juridiction")

    # Date et juge
    decision_date: Optional[date] = Field(None, description="Date de la decision")
    judge: Optional[str] = Field(None, description="Nom du juge")

    # Classification
    legal_domain: LegalDomain = Field(default="civil", description="Domaine de droit")
    keywords: list[str] = Field(default_factory=list, description="Mots-cles")

    # Source
    source_url: Optional[str] = Field(None, description="URL de la source (ex: CanLII)")


class JudgmentCreate(JudgmentBase):
    """Schema pour creer un nouveau jugement."""

    # Le texte original peut etre fourni directement ou via upload PDF
    original_text: Optional[str] = Field(None, description="Texte integral du jugement")
    file_path: Optional[str] = Field(None, description="Chemin du fichier PDF")


class JudgmentUpdate(BaseModel):
    """Schema pour mettre a jour un jugement."""

    title: Optional[str] = None
    citation: Optional[str] = None
    court: Optional[str] = None
    court_level: Optional[CourtLevel] = None
    jurisdiction: Optional[JurisdictionType] = None
    decision_date: Optional[date] = None
    judge: Optional[str] = None
    legal_domain: Optional[LegalDomain] = None
    keywords: Optional[list[str]] = None
    source_url: Optional[str] = None
    status: Optional[JudgmentStatus] = None


class Judgment(JudgmentBase):
    """Schema complet d'un jugement (avec ID et metadata)."""

    id: str = Field(..., description="ID unique du jugement")

    # Texte et fichiers
    original_text: Optional[str] = Field(None, description="Texte integral")
    file_path: Optional[str] = Field(None, description="Chemin du fichier PDF")
    file_hash: Optional[str] = Field(None, description="Hash SHA256 du fichier")

    # Statut
    status: JudgmentStatus = Field(default="pending", description="Statut de l'analyse")

    # Metadata
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    user_id: Optional[str] = Field(None, description="ID de l'utilisateur proprietaire")

    # Lien vers le resume
    summary_id: Optional[str] = Field(None, description="ID du resume genere")

    class Config:
        from_attributes = True


class JudgmentList(BaseModel):
    """Schema pour une liste de jugements (pagination)."""

    items: list[Judgment]
    total: int
    page: int = 1
    page_size: int = 20
    has_more: bool = False
