"""
Service de synthèse vocale (Text-to-Speech) avec edge-tts.

Utilise Microsoft Edge TTS pour convertir du texte en audio.
Support du français et de l'anglais avec des voix naturelles.
"""

import logging
import asyncio
import re
from pathlib import Path
from typing import Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Check if edge-tts is available
try:
    import edge_tts
    EDGE_TTS_AVAILABLE = True
except ImportError:
    EDGE_TTS_AVAILABLE = False
    logger.warning("edge-tts n'est pas installé. Exécuter: uv add edge-tts")


@dataclass
class TTSResult:
    """Résultat de la synthèse vocale."""
    success: bool
    audio_path: str = ""
    duration: float = 0.0
    error: str = ""
    voice: str = ""
    language: str = ""


class TTSService:
    """
    Service de synthèse vocale avec edge-tts.

    Voix disponibles:
    - Français: fr-FR-DeniseNeural (femme), fr-FR-HenriNeural (homme)
    - Anglais: en-US-AriaNeural (femme), en-US-GuyNeural (homme)
    """

    # Liste complète des voix disponibles
    AVAILABLE_VOICES = [
        {"name": "fr-FR-HenriNeural", "locale": "fr-FR", "country": "France", "language": "French", "gender": "Male"},
        {"name": "fr-FR-RemyMultilingualNeural", "locale": "fr-FR", "country": "France", "language": "French", "gender": "Male"},
        {"name": "fr-FR-VivienneMultilingualNeural", "locale": "fr-FR", "country": "France", "language": "French", "gender": "Female"},
        {"name": "fr-BE-CharlineNeural", "locale": "fr-BE", "country": "Belgium", "language": "French", "gender": "Female"},
        {"name": "fr-BE-GerardNeural", "locale": "fr-BE", "country": "Belgium", "language": "French", "gender": "Male"},
        {"name": "fr-CA-AntoineNeural", "locale": "fr-CA", "country": "Canada", "language": "French", "gender": "Male"},
        {"name": "fr-CA-JeanNeural", "locale": "fr-CA", "country": "Canada", "language": "French", "gender": "Male"},
        {"name": "fr-CA-SylvieNeural", "locale": "fr-CA", "country": "Canada", "language": "French", "gender": "Female"},
        {"name": "fr-CA-ThierryNeural", "locale": "fr-CA", "country": "Canada", "language": "French", "gender": "Male"},
        {"name": "fr-CH-ArianeNeural", "locale": "fr-CH", "country": "Switzerland", "language": "French", "gender": "Female"},
        {"name": "fr-CH-FabriceNeural", "locale": "fr-CH", "country": "Switzerland", "language": "French", "gender": "Male"},
        {"name": "fr-FR-DeniseNeural", "locale": "fr-FR", "country": "France", "language": "French", "gender": "Female"},
        {"name": "fr-FR-EloiseNeural", "locale": "fr-FR", "country": "France", "language": "French", "gender": "Female"},
        {"name": "en-CA-ClaraNeural", "locale": "en-CA", "country": "Canada", "language": "English", "gender": "Female"},
        {"name": "en-CA-LiamNeural", "locale": "en-CA", "country": "Canada", "language": "English", "gender": "Male"},
    ]

    # Voix par défaut pour chaque langue
    DEFAULT_VOICES = {
        "fr": "fr-FR-DeniseNeural",  # Voix féminine française
        "en": "en-CA-ClaraNeural",    # Voix féminine anglaise (Canada)
    }

    def __init__(self):
        if not EDGE_TTS_AVAILABLE:
            logger.error("edge-tts n'est pas disponible")
        else:
            logger.info("Service TTS initialisé avec edge-tts")

    def clean_markdown(self, text: str) -> str:
        """
        Nettoie le markdown pour le convertir en texte brut lisible par TTS.

        Supprime les symboles de formatage markdown tout en préservant le contenu textuel.
        """
        # Sauvegarder le texte original pour logging
        original_length = len(text)

        # 1. Remplacer les titres (# Titre) par juste le texte
        text = re.sub(r'^#{1,6}\s+(.+)$', r'\1', text, flags=re.MULTILINE)

        # 2. Supprimer le gras/italique (**texte** ou *texte*)
        text = re.sub(r'\*\*\*(.+?)\*\*\*', r'\1', text)  # Bold + italic
        text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)      # Bold
        text = re.sub(r'\*(.+?)\*', r'\1', text)          # Italic
        text = re.sub(r'__(.+?)__', r'\1', text)          # Bold alt
        text = re.sub(r'_(.+?)_', r'\1', text)            # Italic alt

        # 3. Supprimer les liens mais garder le texte [texte](url)
        text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)

        # 4. Supprimer les images ![alt](url)
        text = re.sub(r'!\[([^\]]*)\]\([^\)]+\)', r'\1', text)

        # 5. Supprimer le code inline `code`
        text = re.sub(r'`([^`]+)`', r'\1', text)

        # 6. Supprimer les blocs de code ```
        text = re.sub(r'```[\s\S]*?```', '', text)
        text = re.sub(r'~~~[\s\S]*?~~~', '', text)

        # 7. Supprimer les citations (> texte)
        text = re.sub(r'^>\s+', '', text, flags=re.MULTILINE)

        # 8. Supprimer les listes à puces (-, *, +)
        text = re.sub(r'^[\*\-\+]\s+', '', text, flags=re.MULTILINE)

        # 9. Supprimer les listes numérotées (1. texte)
        text = re.sub(r'^\d+\.\s+', '', text, flags=re.MULTILINE)

        # 10. Supprimer les lignes horizontales (---, ***, ___)
        text = re.sub(r'^[\-\*_]{3,}$', '', text, flags=re.MULTILINE)

        # 11. Supprimer les tableaux markdown (lignes avec |)
        text = re.sub(r'^\|.*\|$', '', text, flags=re.MULTILINE)

        # 12. Supprimer les balises HTML si présentes
        text = re.sub(r'<[^>]+>', '', text)

        # 13. Remplacer les multiples espaces par un seul
        text = re.sub(r'  +', ' ', text)

        # 14. Remplacer les multiples sauts de ligne par deux max (paragraphes)
        text = re.sub(r'\n{3,}', '\n\n', text)

        # 15. Nettoyer les espaces en début/fin de lignes
        text = '\n'.join(line.strip() for line in text.split('\n'))

        # 16. Supprimer les lignes vides en début et fin
        text = text.strip()

        cleaned_length = len(text)
        logger.info(f"Markdown nettoyé: {original_length} → {cleaned_length} caractères")

        return text

    def get_voice_for_language(self, language: str, gender: str = "female") -> str:
        """
        Récupère la voix appropriée pour une langue.

        Args:
            language: Code de langue (fr, en)
            gender: Genre de la voix (female, male)

        Returns:
            Identifiant de la voix edge-tts
        """
        lang_code = language.lower()[:2]  # Prendre les 2 premiers caractères

        voices = {
            "fr": {
                "female": "fr-FR-DeniseNeural",
                "male": "fr-FR-HenriNeural",
            },
            "en": {
                "female": "en-US-AriaNeural",
                "male": "en-US-GuyNeural",
            },
        }

        # Fallback sur français si langue non supportée
        if lang_code not in voices:
            logger.warning(f"Langue {language} non supportée, utilisation du français")
            lang_code = "fr"

        # Fallback sur female si genre non supporté
        if gender not in voices[lang_code]:
            gender = "female"

        return voices[lang_code][gender]

    async def text_to_speech(
        self,
        text: str,
        output_path: str,
        language: str = "fr",
        voice: Optional[str] = None,
        rate: str = "+0%",
        volume: str = "+0%",
        clean_markdown: bool = True
    ) -> TTSResult:
        """
        Convertit du texte en audio avec edge-tts.

        Args:
            text: Texte à convertir en audio
            output_path: Chemin du fichier audio de sortie (.mp3)
            language: Langue du texte (fr, en)
            voice: Voix spécifique à utiliser (optionnel, auto-détecté si None)
            rate: Vitesse de lecture (ex: "+20%" pour 20% plus rapide, "-10%" pour 10% plus lent)
            volume: Volume (ex: "+10%" pour 10% plus fort, "-10%" pour 10% plus faible)
            clean_markdown: Si True, nettoie le markdown avant conversion (par défaut: True)

        Returns:
            TTSResult avec le résultat de la synthèse
        """
        if not EDGE_TTS_AVAILABLE:
            return TTSResult(
                success=False,
                error="edge-tts n'est pas installé. Exécuter: uv add edge-tts"
            )

        if not text or not text.strip():
            return TTSResult(
                success=False,
                error="Texte vide fourni"
            )

        try:
            # Nettoyer le markdown si demandé
            if clean_markdown:
                text = self.clean_markdown(text)

            # Vérifier qu'il reste du texte après nettoyage
            if not text or not text.strip():
                return TTSResult(
                    success=False,
                    error="Texte vide après nettoyage markdown"
                )

            # Sélectionner la voix
            selected_voice = voice or self.get_voice_for_language(language)

            logger.info(f"Génération TTS avec voix {selected_voice} (rate: {rate}, volume: {volume})")
            logger.info(f"Texte à convertir: {len(text)} caractères")

            # Créer le répertoire de sortie si nécessaire
            output_path_obj = Path(output_path)
            output_path_obj.parent.mkdir(parents=True, exist_ok=True)

            # Créer la communication avec edge-tts
            communicate = edge_tts.Communicate(
                text=text,
                voice=selected_voice,
                rate=rate,
                volume=volume
            )

            # Sauvegarder l'audio
            await communicate.save(str(output_path_obj))

            # Vérifier que le fichier a été créé
            if not output_path_obj.exists():
                return TTSResult(
                    success=False,
                    error="Le fichier audio n'a pas été créé"
                )

            file_size = output_path_obj.stat().st_size
            logger.info(f"Audio généré avec succès: {output_path} ({file_size} bytes)")

            # Estimer la durée (approximation: ~150 mots/minute, ~5 caractères/mot)
            words = len(text) / 5
            estimated_duration = (words / 150) * 60  # en secondes

            return TTSResult(
                success=True,
                audio_path=str(output_path_obj),
                duration=estimated_duration,
                voice=selected_voice,
                language=language
            )

        except Exception as e:
            logger.error(f"Erreur lors de la synthèse vocale: {e}", exc_info=True)
            return TTSResult(
                success=False,
                error=str(e)
            )

    def get_available_voices(self) -> list[dict]:
        """
        Retourne la liste des voix TTS disponibles.

        Returns:
            Liste de dictionnaires avec les informations des voix
        """
        return self.AVAILABLE_VOICES

    async def list_all_voices_from_edge(self) -> list[dict]:
        """
        Liste toutes les voix disponibles directement depuis edge-tts (pour référence).

        Returns:
            Liste de dictionnaires avec les informations des voix
        """
        if not EDGE_TTS_AVAILABLE:
            return []

        try:
            voices = await edge_tts.list_voices()
            return [
                {
                    "name": v["Name"],
                    "short_name": v["ShortName"],
                    "gender": v["Gender"],
                    "locale": v["Locale"],
                }
                for v in voices
            ]
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des voix: {e}")
            return []


# Singleton instance
_tts_service: Optional[TTSService] = None


def get_tts_service() -> TTSService:
    """Récupère l'instance singleton du service TTS."""
    global _tts_service
    if _tts_service is None:
        _tts_service = TTSService()
    return _tts_service
