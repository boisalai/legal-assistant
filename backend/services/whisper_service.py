"""
Service de transcription audio avec MLX Whisper.

Optimise pour Apple Silicon avec mlx-whisper.
Offre une meilleure qualite que openai-whisper standard.

Formats audio supportes: MP3, WAV, M4A, OGG, WEBM, FLAC, AAC
"""

import logging
import asyncio
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# Verifier si mlx-whisper est disponible
MLX_WHISPER_AVAILABLE = False
try:
    import mlx_whisper
    MLX_WHISPER_AVAILABLE = True
    logger.info("mlx-whisper disponible - utilisation des modeles MLX optimises")
except ImportError:
    logger.warning("mlx-whisper non installe. Installer avec: uv add mlx-whisper")

# Fallback sur openai-whisper si mlx-whisper n'est pas disponible
OPENAI_WHISPER_AVAILABLE = False
if not MLX_WHISPER_AVAILABLE:
    try:
        import whisper
        OPENAI_WHISPER_AVAILABLE = True
        logger.info("Fallback sur openai-whisper")
    except ImportError:
        logger.warning("Aucun service Whisper disponible")

# Au moins un service doit etre disponible
WHISPER_AVAILABLE = MLX_WHISPER_AVAILABLE or OPENAI_WHISPER_AVAILABLE


# Modeles MLX Whisper disponibles
MLX_MODELS = {
    "tiny": {
        "repo": "mlx-community/whisper-tiny-mlx",
        "speed": "Tres rapide",
        "quality": "Basique"
    },
    "base": {
        "repo": "mlx-community/whisper-base-mlx",
        "speed": "Rapide",
        "quality": "Bonne"
    },
    "small": {
        "repo": "mlx-community/whisper-small-mlx",
        "speed": "Moyen",
        "quality": "Tres bonne"
    },
    "medium": {
        "repo": "mlx-community/whisper-medium-mlx",
        "speed": "Lent",
        "quality": "Excellente"
    },
    "large-v3": {
        "repo": "mlx-community/whisper-large-v3-mlx",
        "speed": "Tres lent",
        "quality": "Optimale"
    },
    "large-v3-turbo": {
        "repo": "mlx-community/whisper-large-v3-turbo",
        "speed": "Rapide",
        "quality": "Optimale (recommande)"
    },
    "distil-large-v3": {
        "repo": "mlx-community/distil-whisper-large-v3",
        "speed": "Rapide",
        "quality": "Excellente"
    }
}


@dataclass
class TranscriptionResult:
    """Resultat de la transcription audio."""
    success: bool
    text: str = ""
    language: str = ""
    duration: float = 0.0
    segments: list = field(default_factory=list)
    error: Optional[str] = None
    method: str = "whisper"


class WhisperService:
    """
    Service de transcription audio avec MLX Whisper (Apple Silicon optimise).

    Utilise mlx-whisper par defaut pour de meilleures performances sur Mac.
    Fallback sur openai-whisper si mlx-whisper n'est pas disponible.
    """

    SUPPORTED_FORMATS = {'.mp3', '.wav', '.m4a', '.ogg', '.webm', '.flac', '.aac'}

    def __init__(self, model_name: str = "large-v3-turbo"):
        """
        Initialise le service Whisper.

        Args:
            model_name: Modele a utiliser (pour MLX: tiny, base, small, medium,
                       large-v3, large-v3-turbo, distil-large-v3)
        """
        self.model_name = model_name
        self._openai_model = None  # Pour fallback openai-whisper

        if not WHISPER_AVAILABLE:
            logger.warning("Aucun service Whisper disponible - transcription desactivee")

    def _get_mlx_model_repo(self) -> str:
        """Obtient le repo HuggingFace pour le modele MLX."""
        if self.model_name in MLX_MODELS:
            return MLX_MODELS[self.model_name]["repo"]
        # Fallback sur large-v3-turbo si modele inconnu
        logger.warning(f"Modele {self.model_name} inconnu, utilisation de large-v3-turbo")
        return MLX_MODELS["large-v3-turbo"]["repo"]

    def _load_openai_model(self):
        """Charge le modele openai-whisper (fallback)."""
        if not OPENAI_WHISPER_AVAILABLE:
            return None

        if self._openai_model is None:
            try:
                import whisper
                # Mapper le nom du modele MLX vers openai-whisper
                openai_model_name = self.model_name
                if self.model_name in ["large-v3", "large-v3-turbo", "distil-large-v3"]:
                    openai_model_name = "large"

                logger.info(f"Chargement du modele openai-whisper: {openai_model_name}")
                self._openai_model = whisper.load_model(openai_model_name)
                logger.info(f"Modele openai-whisper {openai_model_name} charge")
            except Exception as e:
                logger.error(f"Erreur chargement modele openai-whisper: {e}")
                return None

        return self._openai_model

    async def transcribe(
        self,
        audio_path: str | Path,
        language: Optional[str] = None
    ) -> TranscriptionResult:
        """
        Transcrit un fichier audio en texte.

        Args:
            audio_path: Chemin vers le fichier audio
            language: Langue de l'audio (optionnel, auto-detect sinon)

        Returns:
            TranscriptionResult avec le texte transcrit
        """
        audio_path = Path(audio_path)

        if not audio_path.exists():
            return TranscriptionResult(
                success=False,
                error=f"Fichier non trouve: {audio_path}"
            )

        if audio_path.suffix.lower() not in self.SUPPORTED_FORMATS:
            return TranscriptionResult(
                success=False,
                error=f"Format non supporte: {audio_path.suffix}. Formats acceptes: {', '.join(self.SUPPORTED_FORMATS)}"
            )

        if not WHISPER_AVAILABLE:
            return TranscriptionResult(
                success=False,
                error="Whisper non disponible. Installer avec: uv add mlx-whisper"
            )

        # Utiliser MLX Whisper si disponible
        if MLX_WHISPER_AVAILABLE:
            return await self._transcribe_mlx(audio_path, language)
        else:
            return await self._transcribe_openai(audio_path, language)

    async def _transcribe_mlx(
        self,
        audio_path: Path,
        language: Optional[str] = None
    ) -> TranscriptionResult:
        """Transcription avec mlx-whisper."""
        try:
            import mlx_whisper

            model_repo = self._get_mlx_model_repo()
            logger.info(f"Transcription MLX avec {model_repo}")

            # Transcription dans un thread separe
            loop = asyncio.get_event_loop()

            def do_transcribe():
                return mlx_whisper.transcribe(
                    str(audio_path),
                    path_or_hf_repo=model_repo,
                    language=language,
                    word_timestamps=True
                )

            result = await loop.run_in_executor(None, do_transcribe)

            # Extraire les segments
            segments = []
            for seg in result.get("segments", []):
                segments.append({
                    "start": seg.get("start", 0),
                    "end": seg.get("end", 0),
                    "text": seg.get("text", "").strip()
                })

            # Calculer la duree totale
            duration = segments[-1]["end"] if segments else 0.0

            return TranscriptionResult(
                success=True,
                text=result.get("text", "").strip(),
                language=result.get("language", language or ""),
                duration=duration,
                segments=segments,
                method=f"mlx-whisper-{self.model_name}"
            )

        except Exception as e:
            logger.error(f"Erreur transcription MLX: {e}", exc_info=True)
            return TranscriptionResult(
                success=False,
                error=str(e)
            )

    async def _transcribe_openai(
        self,
        audio_path: Path,
        language: Optional[str] = None
    ) -> TranscriptionResult:
        """Transcription avec openai-whisper (fallback)."""
        model = self._load_openai_model()
        if model is None:
            return TranscriptionResult(
                success=False,
                error="Impossible de charger le modele openai-whisper"
            )

        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: model.transcribe(
                    str(audio_path),
                    language=language,
                    verbose=False
                )
            )

            segments = []
            for seg in result.get("segments", []):
                segments.append({
                    "start": seg["start"],
                    "end": seg["end"],
                    "text": seg["text"].strip()
                })

            duration = segments[-1]["end"] if segments else 0.0

            return TranscriptionResult(
                success=True,
                text=result["text"].strip(),
                language=result.get("language", ""),
                duration=duration,
                segments=segments,
                method=f"openai-whisper-{self.model_name}"
            )

        except Exception as e:
            logger.error(f"Erreur transcription openai-whisper: {e}")
            return TranscriptionResult(
                success=False,
                error=str(e)
            )

    @staticmethod
    def is_available() -> bool:
        """Verifie si Whisper est disponible."""
        return WHISPER_AVAILABLE

    @staticmethod
    def get_available_models() -> list[dict]:
        """Retourne la liste des modeles disponibles."""
        models = []
        for name, info in MLX_MODELS.items():
            models.append({
                "name": name,
                "repo": info["repo"],
                "quality": info["quality"],
                "speed": info["speed"],
                "recommended": name == "large-v3-turbo"
            })
        return models

    @staticmethod
    def get_backend() -> str:
        """Retourne le backend utilise (mlx ou openai)."""
        if MLX_WHISPER_AVAILABLE:
            return "mlx-whisper"
        elif OPENAI_WHISPER_AVAILABLE:
            return "openai-whisper"
        return "none"


# Singleton pour le service
_whisper_service: Optional[WhisperService] = None


def get_whisper_service(model_name: str = "large-v3-turbo") -> WhisperService:
    """Obtient l'instance singleton du service Whisper."""
    global _whisper_service
    if _whisper_service is None:
        _whisper_service = WhisperService(model_name=model_name)
    return _whisper_service
