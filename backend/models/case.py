"""
Modeles de donnees pour les dossiers academiques.

Ce module definit les schemas Pydantic pour:
- Case: Un dossier de cours (ex: DRT-1001)
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class CaseBase(BaseModel):
    """Schema de base pour un dossier."""

    # Identification
    title: str = Field(..., description="Nom du dossier (ex: DRT-1001 - Introduction au droit)")
    description: Optional[str] = Field(None, description="Description du dossier")

    # Metadata
    keywords: list[str] = Field(default_factory=list, description="Mots-cles")

    # Academic fields (optional - dual mode support)
    session_id: Optional[str] = Field(None, description="ID de la session académique")
    course_code: Optional[str] = Field(None, description="Code du cours (ex: 'DRT-1151G')")
    course_name: Optional[str] = Field(None, description="Nom du cours")
    professor: Optional[str] = Field(None, description="Nom du professeur")
    credits: int = Field(3, ge=1, le=12, description="Nombre de crédits (1-12)")
    color: Optional[str] = Field(None, description="Couleur pour l'UI (hex code)")


class CaseCreate(CaseBase):
    """Schema pour creer un nouveau dossier."""
    pass


class CaseUpdate(BaseModel):
    """Schema pour mettre a jour un dossier."""

    title: Optional[str] = None
    description: Optional[str] = None
    keywords: Optional[list[str]] = None

    # Academic fields (optional)
    session_id: Optional[str] = None
    course_code: Optional[str] = None
    course_name: Optional[str] = None
    professor: Optional[str] = None
    credits: Optional[int] = Field(None, ge=1, le=12)
    color: Optional[str] = None


class Case(CaseBase):
    """Schema complet d'un dossier (avec ID et metadata)."""

    id: str = Field(..., description="ID unique du dossier")

    # Metadata
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    class Config:
        from_attributes = True


class CaseList(BaseModel):
    """Schema pour une liste de dossiers (pagination)."""

    items: list[Case]
    total: int
    page: int = 1
    page_size: int = 20
    has_more: bool = False
