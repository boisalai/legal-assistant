"""Modèles Pydantic pour les modules d'étude.

Un module représente une unité d'étude au sein d'un cours (ex: Module 3 - Sources du droit).
Les modules permettent de grouper les documents.
"""

from typing import Optional, List
from pydantic import BaseModel, Field


# ============================================================================
# Module Base Models
# ============================================================================

class ModuleBase(BaseModel):
    """Schéma de base pour un module."""
    name: str = Field(..., min_length=1, max_length=200, description="Nom du module")
    order_index: int = Field(default=0, ge=0, description="Index pour l'ordre d'affichage")
    exam_weight: Optional[float] = Field(None, ge=0, le=1, description="Poids dans l'examen (0-1)")


class ModuleCreate(ModuleBase):
    """Requête pour créer un nouveau module."""
    pass


class ModuleUpdate(BaseModel):
    """Requête pour mettre à jour un module."""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    order_index: Optional[int] = Field(None, ge=0)
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


class ModuleListResponse(BaseModel):
    """Réponse pour une liste de modules."""
    modules: List[ModuleResponse]
    total: int


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
    exam_weight: Optional[float] = Field(None, ge=0, le=1)


class ModuleBulkCreateRequest(BaseModel):
    """Requête pour créer plusieurs modules à la fois."""
    modules: List[ModuleBulkCreateItem] = Field(..., min_length=1, max_length=20)


class ModuleBulkCreateResponse(BaseModel):
    """Réponse après création en masse."""
    created_count: int
    modules: List[ModuleResponse]
