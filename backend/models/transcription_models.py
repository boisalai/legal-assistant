"""Modèles Pydantic pour la transcription et l'extraction de documents."""

from pydantic import BaseModel


class ExtractionResponse(BaseModel):
    """Réponse pour l'extraction de texte d'un document."""
    success: bool
    text: str = ""
    method: str = ""
    error: str = ""


class TranscriptionResponse(BaseModel):
    """Réponse de transcription audio."""
    success: bool
    text: str = ""
    language: str = ""
    duration: float = 0.0
    error: str = ""


class TranscribeWorkflowRequest(BaseModel):
    """Request pour le workflow de transcription complet."""
    language: str = "fr"
    create_markdown: bool = True
    raw_mode: bool = False  # Si True, pas de formatage LLM - juste la transcription Whisper brute


class YouTubeDownloadRequest(BaseModel):
    """Request pour télécharger l'audio d'une vidéo YouTube."""
    url: str
    auto_transcribe: bool = False  # Si True, lance la transcription automatiquement


class YouTubeInfoResponse(BaseModel):
    """Informations sur une vidéo YouTube."""
    title: str
    duration: int
    uploader: str
    thumbnail: str
    url: str


class YouTubeDownloadResponse(BaseModel):
    """Réponse du téléchargement YouTube."""
    success: bool
    document_id: str = ""
    filename: str = ""
    title: str = ""
    duration: int = 0
    error: str = ""
