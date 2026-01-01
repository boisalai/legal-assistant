"""Modèles Pydantic pour les modules d'étude.

Un module représente une unité d'étude au sein d'un cours (ex: Module 3 - Sources du droit).
Les modules permettent de grouper les documents et de suivre la progression.
"""

from datetime import datetime
from typing import Optional, List
from enum import Enum
from pydantic import BaseModel, Field


class MasteryLevel(str, Enum):
    """Niveau de maîtrise d'un module."""
    NOT_STARTED = "not_started"
    LEARNING = "learning"
    PROFICIENT = "proficient"
    MASTERED = "mastered"


# ============================================================================
# Module Base Models
# ============================================================================

class ModuleBase(BaseModel):
    """Schéma de base pour un module."""
    name: str = Field(..., min_length=1, max_length=200, description="Nom du module")
    order_index: int = Field(default=0, ge=0, description="Index pour l'ordre d'affichage")
    description: Optional[str] = Field(None, max_length=1000, description="Description du module")
    exam_weight: Optional[float] = Field(None, ge=0, le=1, description="Poids dans l'examen (0-1)")


class ModuleCreate(ModuleBase):
    """Requête pour créer un nouveau module."""
    pass


class ModuleUpdate(BaseModel):
    """Requête pour mettre à jour un module."""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    order_index: Optional[int] = Field(None, ge=0)
    description: Optional[str] = Field(None, max_length=1000)
    exam_weight: Optional[float] = Field(None, ge=0, le=1)


# ============================================================================
# Module Response Models
# ============================================================================

class ModuleResponse(ModuleBase):
    """Réponse pour un module."""
    id: str
    course_id: str
    created_at: str
    updated_at: Optional[str] = None
    document_count: int = 0


class ModuleWithProgress(ModuleResponse):
    """Module avec informations de progression."""
    # Reading progress
    documents_total: int = 0
    documents_completed: int = 0
    reading_percent: float = 0.0

    # Flashcard progress
    flashcards_total: int = 0
    flashcards_mastered: int = 0
    flashcard_percent: float = 0.0

    # Quiz progress
    quiz_attempts: int = 0
    quiz_average_score: float = 0.0
    quiz_best_score: float = 0.0

    # Combined metrics
    overall_progress: float = 0.0
    mastery_level: MasteryLevel = MasteryLevel.NOT_STARTED

    # Time tracking
    total_study_time_seconds: int = 0
    last_activity_at: Optional[str] = None


class ModuleListResponse(BaseModel):
    """Réponse pour une liste de modules."""
    modules: List[ModuleResponse]
    total: int


class ModuleListWithProgressResponse(BaseModel):
    """Réponse pour une liste de modules avec progression."""
    modules: List[ModuleWithProgress]
    total: int
    course_overall_progress: float = 0.0
    recommended_module_id: Optional[str] = None
    recommendation_message: Optional[str] = None


# ============================================================================
# Document Assignment Models
# ============================================================================

class AssignDocumentsRequest(BaseModel):
    """Requête pour assigner des documents à un module."""
    document_ids: List[str] = Field(..., min_length=1, description="Liste des IDs de documents")


class AssignDocumentsResponse(BaseModel):
    """Réponse après assignation de documents."""
    module_id: str
    assigned_count: int
    document_ids: List[str]


# ============================================================================
# Bulk Operations Models
# ============================================================================

class ModuleBulkCreateItem(BaseModel):
    """Item pour création en masse de modules."""
    name: str = Field(..., min_length=1, max_length=200)
    order_index: int = Field(default=0, ge=0)
    description: Optional[str] = None
    exam_weight: Optional[float] = Field(None, ge=0, le=1)


class ModuleBulkCreateRequest(BaseModel):
    """Requête pour créer plusieurs modules à la fois."""
    modules: List[ModuleBulkCreateItem] = Field(..., min_length=1, max_length=20)


class ModuleBulkCreateResponse(BaseModel):
    """Réponse après création en masse."""
    created_count: int
    modules: List[ModuleResponse]


# ============================================================================
# Auto-detect Models
# ============================================================================

class DetectedModule(BaseModel):
    """Module détecté automatiquement depuis les noms de fichiers."""
    suggested_name: str
    document_ids: List[str]
    document_count: int


class AutoDetectResponse(BaseModel):
    """Réponse de la détection automatique de modules."""
    detected_modules: List[DetectedModule]
    unassigned_documents: List[str]
    total_documents: int
