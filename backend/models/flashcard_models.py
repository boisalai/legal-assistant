"""Modèles Pydantic pour les fiches de révision (flashcards)."""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


# ============================================================================
# Source Document Reference
# ============================================================================

class SourceDocument(BaseModel):
    """Référence à un document source pour un deck."""
    doc_id: str
    name: str
    relative_path: Optional[str] = None


# ============================================================================
# Flashcard Deck Models
# ============================================================================

class FlashcardDeckCreate(BaseModel):
    """Requête pour créer un nouveau deck de révision."""
    name: str = Field(..., min_length=1, max_length=200)
    source_document_ids: List[str] = Field(..., min_items=1)
    card_count: int = Field(default=50, ge=5, le=200)
    generate_audio: bool = Field(default=False, description="Générer un audio récapitulatif")


class FlashcardDeckResponse(BaseModel):
    """Réponse pour un deck de révision."""
    id: str
    course_id: str
    name: str
    source_documents: List[SourceDocument] = []
    total_cards: int = 0
    created_at: str
    has_summary_audio: bool = False


class FlashcardDeckListResponse(BaseModel):
    """Réponse pour une liste de decks."""
    decks: List[FlashcardDeckResponse]
    total: int


# ============================================================================
# Flashcard Models
# ============================================================================

class FlashcardCreate(BaseModel):
    """Requête pour créer une fiche (utilisé en interne)."""
    deck_id: str
    document_id: str
    front: str
    back: str
    source_excerpt: Optional[str] = None
    source_location: Optional[str] = None


class FlashcardResponse(BaseModel):
    """Réponse pour une fiche de révision."""
    id: str
    deck_id: str
    document_id: str
    front: str
    back: str
    source_excerpt: Optional[str] = None
    source_location: Optional[str] = None
    created_at: str


class FlashcardListResponse(BaseModel):
    """Réponse pour une liste de fiches."""
    cards: List[FlashcardResponse]
    total: int


# ============================================================================
# Study Session Models
# ============================================================================

class StudySessionResponse(BaseModel):
    """Réponse pour une session de révision."""
    deck_id: str
    deck_name: str
    cards: List[FlashcardResponse]
    total_cards: int


# ============================================================================
# TTS Models
# ============================================================================

class TTSRequest(BaseModel):
    """Requête pour générer l'audio d'une fiche."""
    side: str = Field(..., pattern="^(front|back)$")
    voice: str = Field(default="fr-CA-SylvieNeural")


class TTSResponse(BaseModel):
    """Réponse avec l'URL de l'audio généré."""
    audio_url: str
    voice: str
    duration: Optional[float] = None


# ============================================================================
# Generation Models
# ============================================================================

class GenerationProgress(BaseModel):
    """Progression de la génération de fiches."""
    status: str  # "generating", "completed", "error"
    current: int = 0
    total: int = 0
    message: Optional[str] = None


class GeneratedCard(BaseModel):
    """Fiche générée par le LLM (avant sauvegarde)."""
    front: str
    back: str
    source_excerpt: Optional[str] = None
    source_location: Optional[str] = None
