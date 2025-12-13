"""
Modèles de données pour les sessions académiques.

Ce module définit les schémas Pydantic pour:
- Session: Une session académique (ex: "Automne 2024", "Hiver 2025")
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class SessionBase(BaseModel):
    """Schéma de base pour une session académique."""

    # Identification
    title: str = Field(..., description="Titre de la session (ex: 'Automne 2024')")
    semester: str = Field(..., description="Semestre (ex: 'Automne', 'Hiver', 'Été')")
    year: int = Field(..., ge=2020, le=2100, description="Année académique")

    # Dates
    start_date: datetime = Field(..., description="Date de début de la session")
    end_date: datetime = Field(..., description="Date de fin de la session")


class SessionCreate(SessionBase):
    """Schéma pour créer une nouvelle session académique."""
    pass


class SessionUpdate(BaseModel):
    """Schéma pour mettre à jour une session académique."""

    title: Optional[str] = None
    semester: Optional[str] = None
    year: Optional[int] = Field(None, ge=2020, le=2100)
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


class Session(SessionBase):
    """Schéma complet d'une session académique (avec ID et metadata)."""

    id: str = Field(..., description="ID unique de la session")

    # Metadata
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    class Config:
        from_attributes = True


class SessionList(BaseModel):
    """Schéma pour une liste de sessions (pagination)."""

    items: list[Session]
    total: int
    page: int = 1
    page_size: int = 20
    has_more: bool = False
