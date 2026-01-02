"""
Text-to-Speech service with edge-tts.

Uses Microsoft Edge TTS to convert text to audio.
Supports French and English with natural voices.
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
    logger.warning("edge-tts is not installed. Run: uv add edge-tts")


@dataclass
class TTSResult:
    """Text-to-speech result."""
    success: bool
    audio_path: str = ""
    duration: float = 0.0
    error: str = ""
    voice: str = ""
    language: str = ""


class TTSService:
    """
    Text-to-speech service with edge-tts.

    Available voices:
    - French: fr-FR-DeniseNeural (female), fr-FR-HenriNeural (male)
    - English: en-US-AriaNeural (female), en-US-GuyNeural (male)
    """

    # Complete list of available voices
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

    # Default voice for each language
    DEFAULT_VOICES = {
        "fr": "fr-FR-DeniseNeural",  # French female voice
        "en": "en-CA-ClaraNeural",    # English female voice (Canada)
    }

    def __init__(self):
        if not EDGE_TTS_AVAILABLE:
            logger.error("edge-tts is not available")
        else:
            logger.info("TTS service initialized with edge-tts")

    def clean_markdown(self, text: str) -> str:
        """
        Clean markdown to convert it to plain text readable by TTS.

        Removes markdown formatting symbols while preserving textual content.
        """
        # Save original text for logging
        original_length = len(text)

        # 0. Remove Docusaurus YAML frontmatter (---\n...\n---)
        # Frontmatter must be at the beginning of the file
        text = re.sub(r'^---\n.*?\n---\n', '', text, flags=re.DOTALL)

        # 1. Replace headings (# Title) with just the text
        text = re.sub(r'^#{1,6}\s+(.+)$', r'\1', text, flags=re.MULTILINE)

        # 2. Remove bold/italic (**text** or *text*)
        text = re.sub(r'\*\*\*(.+?)\*\*\*', r'\1', text)  # Bold + italic
        text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)      # Bold
        text = re.sub(r'\*(.+?)\*', r'\1', text)          # Italic
        text = re.sub(r'__(.+?)__', r'\1', text)          # Bold alt
        text = re.sub(r'_(.+?)_', r'\1', text)            # Italic alt

        # 3. Remove links but keep the text [text](url)
        text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)

        # 4. Remove images ![alt](url)
        text = re.sub(r'!\[([^\]]*)\]\([^\)]+\)', r'\1', text)

        # 5. Remove inline code `code`
        text = re.sub(r'`([^`]+)`', r'\1', text)

        # 6. Remove code blocks ```
        text = re.sub(r'```[\s\S]*?```', '', text)
        text = re.sub(r'~~~[\s\S]*?~~~', '', text)

        # 7. Remove blockquotes (> text)
        text = re.sub(r'^>\s+', '', text, flags=re.MULTILINE)

        # 8. Remove bullet lists (-, *, +)
        text = re.sub(r'^[\*\-\+]\s+', '', text, flags=re.MULTILINE)

        # 9. Remove numbered lists (1. text)
        text = re.sub(r'^\d+\.\s+', '', text, flags=re.MULTILINE)

        # 10. Remove horizontal rules (---, ***, ___)
        text = re.sub(r'^[\-\*_]{3,}$', '', text, flags=re.MULTILINE)

        # 11. Remove markdown tables (lines with |)
        text = re.sub(r'^\|.*\|$', '', text, flags=re.MULTILINE)

        # 12. Remove HTML tags if present
        text = re.sub(r'<[^>]+>', '', text)

        # 13. Replace multiple spaces with single space
        text = re.sub(r'  +', ' ', text)

        # 14. Replace multiple newlines with max two (paragraphs)
        text = re.sub(r'\n{3,}', '\n\n', text)

        # 15. Clean leading/trailing spaces on lines
        text = '\n'.join(line.strip() for line in text.split('\n'))

        # 16. Remove empty lines at beginning and end
        text = text.strip()

        cleaned_length = len(text)
        logger.info(f"Markdown cleaned: {original_length} → {cleaned_length} characters")

        return text

    def get_voice_for_language(self, language: str, gender: str = "female") -> str:
        """
        Get the appropriate voice for a language.

        Args:
            language: Language code (fr, en)
            gender: Voice gender (female, male)

        Returns:
            edge-tts voice identifier
        """
        lang_code = language.lower()[:2]  # Take first 2 characters

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

        # Fallback to French if language not supported
        if lang_code not in voices:
            logger.warning(f"Language {language} not supported, using French")
            lang_code = "fr"

        # Fallback to female if gender not supported
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
        Convert text to audio with edge-tts.

        Args:
            text: Text to convert to audio
            output_path: Output audio file path (.mp3)
            language: Text language (fr, en)
            voice: Specific voice to use (optional, auto-detected if None)
            rate: Speech rate (e.g., "+20%" for 20% faster, "-10%" for 10% slower)
            volume: Volume (e.g., "+10%" for 10% louder, "-10%" for 10% quieter)
            clean_markdown: If True, clean markdown before conversion (default: True)

        Returns:
            TTSResult with the synthesis result
        """
        if not EDGE_TTS_AVAILABLE:
            return TTSResult(
                success=False,
                error="edge-tts is not installed. Run: uv add edge-tts"
            )

        if not text or not text.strip():
            return TTSResult(
                success=False,
                error="Empty text provided"
            )

        try:
            # Clean markdown if requested
            if clean_markdown:
                text = self.clean_markdown(text)

            # Verify text remains after cleaning
            if not text or not text.strip():
                return TTSResult(
                    success=False,
                    error="Empty text after markdown cleaning"
                )

            # Select voice
            selected_voice = voice or self.get_voice_for_language(language)

            logger.info(f"TTS generation with voice {selected_voice} (rate: {rate}, volume: {volume})")
            logger.info(f"Text to convert: {len(text)} characters")

            # Create output directory if needed
            output_path_obj = Path(output_path)
            output_path_obj.parent.mkdir(parents=True, exist_ok=True)

            # Create edge-tts communication
            communicate = edge_tts.Communicate(
                text=text,
                voice=selected_voice,
                rate=rate,
                volume=volume
            )

            # Save audio
            await communicate.save(str(output_path_obj))

            # Verify file was created
            if not output_path_obj.exists():
                return TTSResult(
                    success=False,
                    error="Audio file was not created"
                )

            file_size = output_path_obj.stat().st_size
            logger.info(f"Audio generated successfully: {output_path} ({file_size} bytes)")

            # Estimate duration (approximation: ~150 words/minute, ~5 characters/word)
            words = len(text) / 5
            estimated_duration = (words / 150) * 60  # in seconds

            return TTSResult(
                success=True,
                audio_path=str(output_path_obj),
                duration=estimated_duration,
                voice=selected_voice,
                language=language
            )

        except Exception as e:
            logger.error(f"Error during text-to-speech: {e}", exc_info=True)
            return TTSResult(
                success=False,
                error=str(e)
            )

    def get_available_voices(self) -> list[dict]:
        """
        Return the list of available TTS voices.

        Returns:
            List of dictionaries with voice information
        """
        return self.AVAILABLE_VOICES

    async def list_all_voices_from_edge(self) -> list[dict]:
        """
        List all available voices directly from edge-tts (for reference).

        Returns:
            List of dictionaries with voice information
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
            logger.error(f"Error retrieving voices: {e}")
            return []


# Singleton instance
_tts_service: Optional[TTSService] = None


def get_tts_service() -> TTSService:
    """Get the singleton TTS service instance."""
    global _tts_service
    if _tts_service is None:
        _tts_service = TTSService()
    return _tts_service
