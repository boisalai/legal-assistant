"""
Modeles de donnees pour les cours academiques.

Ce module definit les schemas Pydantic pour:
- Course: Un cours academique (ex: DRT-1001)
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class CourseBase(BaseModel):
    """Schema de base pour un cours."""

    # Identification
    title: str = Field(..., description="Nom du cours (ex: DRT-1001 - Introduction au droit)")
    description: Optional[str] = Field(None, description="Description du cours")

    # Metadata
    keywords: list[str] = Field(default_factory=list, description="Mots-cles")

    # Academic fields
    session_id: Optional[str] = Field(None, description="ID de la session académique")
    course_code: Optional[str] = Field(None, description="Code du cours (ex: 'DRT-1151G')")
    course_name: Optional[str] = Field(None, description="Nom du cours")
    professor: Optional[str] = Field(None, description="Nom du professeur")
    credits: int = Field(3, ge=1, le=12, description="Nombre de crédits (1-12)")
    color: Optional[str] = Field(None, description="Couleur pour l'UI (hex code)")

    # UI preferences
    pinned: bool = Field(False, description="Cours épinglé en haut de la liste")


class CourseCreate(CourseBase):
    """Schema pour creer un nouveau cours."""
    pass


class CourseUpdate(BaseModel):
    """Schema pour mettre a jour un cours."""

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

    # UI preferences (optional)
    pinned: Optional[bool] = None


class Course(CourseBase):
    """Schema complet d'un cours (avec ID et metadata)."""

    id: str = Field(..., description="ID unique du cours")

    # Metadata
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    class Config:
        from_attributes = True


class CourseList(BaseModel):
    """Schema pour une liste de cours (pagination)."""

    items: list[Course]
    total: int
    page: int = 1
    page_size: int = 20
    has_more: bool = False


# Backward compatibility aliases
Case = Course
CaseBase = CourseBase
CaseCreate = CourseCreate
CaseUpdate = CourseUpdate
CaseList = CourseList
