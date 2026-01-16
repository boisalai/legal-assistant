"""Modèles Pydantic pour les résumés audio."""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


# ============================================================================
# Source Document Reference
# ============================================================================

class AudioSourceDocument(BaseModel):
    """Référence à un document source pour un résumé audio."""
    doc_id: str
    name: str
    relative_path: Optional[str] = None


# ============================================================================
# Script Section Models
# ============================================================================

class ScriptSection(BaseModel):
    """Une section dans le script généré."""
    id: str
    level: str  # "intro", "h1", "h2", "h3", "body", "outro"
    title: Optional[str] = None
    content: str
    voice: str
    pause_before_ms: int = 0
    estimated_duration_seconds: float = 0.0


class ScriptData(BaseModel):
    """Données structurées du script audio."""
    title: str
    source_documents: List[str] = []
    generated_at: str
    estimated_duration_seconds: float = 0.0
    sections: List[ScriptSection] = []


# ============================================================================
# Request Models
# ============================================================================

class AudioSummaryCreate(BaseModel):
    """Requête pour créer un résumé audio."""
    name: str = Field(..., min_length=1, max_length=200)
    source_document_ids: List[str] = Field(..., min_length=1)
    voice_titles: str = Field(default="fr-CA-SylvieNeural", description="Voix pour les titres H1/H2")
    generate_script_only: bool = Field(default=False, description="Générer uniquement le script sans audio")


class AudioSummaryGenerateRequest(BaseModel):
    """Requête pour générer l'audio d'un résumé existant."""
    model_id: Optional[str] = Field(default=None, description="Modèle LLM à utiliser")
    regenerate_script: bool = Field(default=False, description="Regénérer le script même s'il existe")


# ============================================================================
# Response Models
# ============================================================================

class AudioSummaryResponse(BaseModel):
    """Réponse pour un résumé audio."""
    id: str
    course_id: str
    name: str
    source_documents: List[AudioSourceDocument] = []
    status: str  # "pending", "script_ready", "generating", "completed", "error"
    script_path: Optional[str] = None
    audio_path: Optional[str] = None
    estimated_duration_seconds: float = 0.0
    actual_duration_seconds: Optional[float] = None
    section_count: int = 0
    created_at: str
    updated_at: Optional[str] = None
    error_message: Optional[str] = None


class AudioSummaryListResponse(BaseModel):
    """Réponse pour une liste de résumés audio."""
    summaries: List[AudioSummaryResponse]
    total: int


# ============================================================================
# Progress Models
# ============================================================================

class AudioGenerationProgress(BaseModel):
    """Progression de la génération d'un résumé audio."""
    status: str  # "loading", "restructuring", "generating_script", "generating_audio", "concatenating", "completed", "error"
    message: str
    current_section: Optional[int] = None
    total_sections: Optional[int] = None
    percentage: float = 0.0
    estimated_remaining_seconds: Optional[float] = None


# ============================================================================
# Voice Configuration
# ============================================================================

class VoiceInfo(BaseModel):
    """Information sur une voix disponible."""
    id: str
    name: str
    gender: str  # "female", "male"
    region: str  # "Canada", "France", "Belgique", "Suisse"
    language: str = "fr"


# Voix françaises disponibles (toutes régions - pour sélection dans l'interface)
AVAILABLE_VOICES: List[VoiceInfo] = [
    # Canada
    VoiceInfo(id="fr-CA-SylvieNeural", name="Sylvie", gender="female", region="Canada"),
    VoiceInfo(id="fr-CA-AntoineNeural", name="Antoine", gender="male", region="Canada"),
    VoiceInfo(id="fr-CA-JeanNeural", name="Jean", gender="male", region="Canada"),
    VoiceInfo(id="fr-CA-ThierryNeural", name="Thierry", gender="male", region="Canada"),
    # France
    VoiceInfo(id="fr-FR-DeniseNeural", name="Denise", gender="female", region="France"),
    VoiceInfo(id="fr-FR-HenriNeural", name="Henri", gender="male", region="France"),
    VoiceInfo(id="fr-FR-EloiseNeural", name="Éloïse", gender="female", region="France"),
    # Belgique
    VoiceInfo(id="fr-BE-CharlineNeural", name="Charline", gender="female", region="Belgique"),
    VoiceInfo(id="fr-BE-GerardNeural", name="Gérard", gender="male", region="Belgique"),
    # Suisse
    VoiceInfo(id="fr-CH-ArianeNeural", name="Ariane", gender="female", region="Suisse"),
    VoiceInfo(id="fr-CH-FabriceNeural", name="Fabrice", gender="male", region="Suisse"),
]

# Voix fr-CA et fr-FR uniquement (pour sélection aléatoire des sections de contenu)
BODY_VOICES: List[str] = [
    # Canada
    "fr-CA-SylvieNeural",
    "fr-CA-AntoineNeural",
    "fr-CA-JeanNeural",
    "fr-CA-ThierryNeural",
    # France
    "fr-FR-DeniseNeural",
    "fr-FR-HenriNeural",
    "fr-FR-EloiseNeural",
]


# Configuration des pauses par défaut (en millisecondes)
DEFAULT_PAUSE_CONFIG = {
    "h1": 1500,        # 1.5s avant H1
    "h2": 1000,        # 1s avant H2
    "h3": 750,         # 0.75s avant H3
    "paragraph": 500,  # 0.5s entre paragraphes
    "intro": 0,        # Pas de pause avant intro
    "outro": 1000,     # 1s avant conclusion
}
