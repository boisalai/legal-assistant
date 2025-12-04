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


class CaseCreate(CaseBase):
    """Schema pour creer un nouveau dossier."""
    pass


class CaseUpdate(BaseModel):
    """Schema pour mettre a jour un dossier."""

    title: Optional[str] = None
    description: Optional[str] = None
    keywords: Optional[list[str]] = None


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
