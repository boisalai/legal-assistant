"""Modèles Pydantic pour la synthèse vocale (TTS)."""

from typing import Optional
from pydantic import BaseModel


class TTSVoice(BaseModel):
    """Voix TTS disponible."""
    name: str
    locale: str
    country: str
    language: str
    gender: str


class TTSRequest(BaseModel):
    """Request pour générer l'audio TTS d'un document."""
    language: str = "fr"  # fr ou en
    voice: Optional[str] = None  # Voix spécifique (optionnel)
    gender: str = "female"  # female ou male
    rate: str = "+0%"  # Vitesse de lecture (-50% à +100%)
    volume: str = "+0%"  # Volume (-100% à +100%)


class TTSResponse(BaseModel):
    """Réponse de la génération TTS."""
    success: bool
    audio_url: str = ""
    duration: float = 0.0
    voice: str = ""
    error: str = ""
