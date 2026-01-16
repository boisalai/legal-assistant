"""
Audio Summary Service for Legal Assistant.

Converts markdown course documents to structured audio files with:
- LLM-based content restructuring for audio optimization
- Voice assignment per section (H1/H2 headers)
- Pause markers between sections
- FFmpeg concatenation for final output
"""

import asyncio
import json
import json5
import logging
import os
import random
import re
import shutil
import subprocess
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import AsyncGenerator, Dict, List, Optional

from agno.agent import Agent

from config.settings import settings
from services.model_factory import create_model
from services.surreal_service import get_surreal_service
from services.tts_service import TTSService

from models.audio_summary_models import (
    AudioSourceDocument,
    ScriptSection,
    ScriptData,
    DEFAULT_PAUSE_CONFIG,
    BODY_VOICES,
)

logger = logging.getLogger(__name__)


# Prompt template for audio script generation (single document or first chunk)
AUDIO_SCRIPT_PROMPT = """Tu es un professeur de droit qui REFORMULE un document écrit en script audio pour qu'un étudiant puisse l'écouter et réviser.

DOCUMENT SOURCE À REFORMULER POUR L'AUDIO:
\"\"\"
{content}
\"\"\"

MISSION: REFORMULATION ORALE COMPLÈTE (PAS UN RÉSUMÉ)
Tu dois REFORMULER INTÉGRALEMENT le document ci-dessus en version parlée. Ce n'est PAS un résumé.
- Le script audio doit contenir TOUTES les informations du document source
- Chaque phrase, chaque concept, chaque détail doit être présent dans ta reformulation
- Tu AJOUTES des transitions orales, des clarifications, des développements d'acronymes
- Le script final doit être PLUS LONG que le document source (car tu ajoutes des explications orales)

ADAPTATIONS POUR L'ORAL:
- Transforme les listes à puces en phrases fluides ("Premièrement... Deuxièmement... Ensuite...")
- Développe les acronymes (C.c.Q. → "le Code civil du Québec")
- Explique les termes latins ("Ubi societas, ibi jus, ce qui signifie: là où il y a société, il y a droit")
- Remplace les références de pages/articles par des formulations orales
- Ajoute des transitions entre les sections ("Passons maintenant à...", "Examinons ensuite...")
- Reformule le texte écrit en langage naturel parlé

INTERDIT:
- NE RÉSUME PAS - reformule tout le contenu
- NE CONDENSE PAS - garde tous les détails
- NE SAUTE RIEN - chaque information du source doit apparaître
- Si le document liste 10 éléments, les 10 doivent être dans le script

FORMAT JSON:
{{
  "title": "{document_name}",
  "introduction": "Bienvenue. Nous allons parcourir ensemble [sujet]. Ce cours couvre [thèmes principaux].",
  "sections": [
    {{"level": "h1", "title": "Titre de section", "content": "Reformulation orale complète de cette section..."}},
    {{"level": "h2", "title": "Sous-titre", "content": "Reformulation orale du sous-thème..."}},
    {{"level": "body", "content": "Suite de la reformulation..."}}
  ],
  "conclusion": "Voilà qui conclut notre cours. Retenez les points suivants: [récapitulatif des concepts clés]."
}}

Reformule INTÉGRALEMENT le document source en script audio. JSON:"""

# Prompt for subsequent chunks (no intro/conclusion)
AUDIO_SCRIPT_CHUNK_PROMPT = """Continue la REFORMULATION ORALE du document (partie {chunk_num}/{total_chunks}).

SUITE DU DOCUMENT À REFORMULER:
\"\"\"
{content}
\"\"\"

RAPPEL: REFORMULATION COMPLÈTE, PAS UN RÉSUMÉ
- Reformule TOUT ce contenu en version parlée
- Chaque information doit être présente
- Ajoute les transitions orales et développe les acronymes
- Ne condense pas, ne résume pas

JSON (sections uniquement, pas d'intro/conclusion):
{{
  "sections": [
    {{"level": "h1", "title": "Titre", "content": "Reformulation orale complète..."}},
    {{"level": "h2", "title": "Sous-titre", "content": "Reformulation orale..."}},
    {{"level": "body", "content": "Suite..."}}
  ]
}}"""


class AudioSummaryService:
    """Service for generating audio summaries from markdown documents."""

    def __init__(self):
        """Initialize the audio summary service."""
        self.tts_service = TTSService()
        self.default_model = settings.model_id

    async def generate_audio_summary(
        self,
        summary_id: str,
        course_id: str,
        source_document_ids: List[str],
        name: str,
        voice_titles: str = "fr-CA-SylvieNeural",
        model_id: Optional[str] = None,
        generate_script_only: bool = False
    ) -> AsyncGenerator[Dict, None]:
        """
        Generate audio summary from documents with SSE progress.

        Args:
            summary_id: ID of the audio summary record
            course_id: Course ID
            source_document_ids: List of source document IDs
            name: Name for the audio summary
            voice_titles: Voice for H1/H2 titles (body uses random voices)
            model_id: LLM model for content restructuring
            generate_script_only: If True, only generate script without audio

        Yields:
            Progress updates as dict
        """
        model_id = model_id or self.default_model
        temp_dir = None

        try:
            yield {
                "status": "loading",
                "message": "Chargement des documents...",
                "percentage": 0.0
            }

            # Load and merge document contents
            documents_data, source_docs_info = await self._load_documents(source_document_ids)

            if not documents_data:
                yield {
                    "status": "error",
                    "message": "Aucun contenu trouvé dans les documents sélectionnés"
                }
                return

            # Calculate content size for progress info
            total_content = "\n\n".join(d["content"] for d in documents_data)
            content_size_kb = len(total_content.encode('utf-8')) / 1024

            yield {
                "status": "loading",
                "message": f"{len(documents_data)} documents chargés ({content_size_kb:.0f} KB)",
                "percentage": 10.0
            }

            yield {
                "status": "restructuring",
                "message": "Préparation du script audio détaillé pour révision d'examen...",
                "percentage": 15.0
            }

            # Restructure content for audio using LLM
            script_data = await self._restructure_content_for_audio(
                documents_data, name, model_id, voice_titles
            )

            if not script_data or not script_data.sections:
                yield {
                    "status": "error",
                    "message": "Impossible de restructurer le contenu pour l'audio"
                }
                return

            # Show accurate estimation after script generation
            script_duration_min = int(script_data.estimated_duration_seconds / 60)
            script_duration_sec = int(script_data.estimated_duration_seconds % 60)

            yield {
                "status": "generating_script",
                "message": f"Script généré: {len(script_data.sections)} sections (~{script_duration_min} min {script_duration_sec} sec)",
                "percentage": 40.0,
                "total_sections": len(script_data.sections),
                "estimated_duration_seconds": script_data.estimated_duration_seconds
            }

            # Save script to files
            service = get_surreal_service()
            summary_record_id = summary_id.replace("audio_summary:", "")
            course_record_id = course_id.replace("course:", "")

            # Create output directory
            audio_dir = Path(settings.upload_dir) / "courses" / course_record_id / "audio_summaries"
            audio_dir.mkdir(parents=True, exist_ok=True)

            # Save script files
            script_md_path = audio_dir / f"{summary_record_id}_script.md"
            script_json_path = audio_dir / f"{summary_record_id}_script.json"

            # Generate human-readable markdown script
            readable_script = self._generate_readable_script(script_data, name, source_docs_info)
            script_md_path.write_text(readable_script, encoding="utf-8")

            # Save structured JSON
            script_json_path.write_text(
                json.dumps(script_data.model_dump(), ensure_ascii=False, indent=2),
                encoding="utf-8"
            )

            # Update database with script info
            await service.query(
                """
                UPDATE audio_summary
                SET script_path = $script_path,
                    script_data = $script_data,
                    section_count = $section_count,
                    estimated_duration_seconds = $estimated_duration,
                    source_documents = $source_docs,
                    status = $status,
                    updated_at = time::now()
                WHERE id = type::thing('audio_summary', $summary_id)
                """,
                {
                    "summary_id": summary_record_id,
                    "script_path": str(script_md_path),
                    "script_data": script_data.model_dump(),
                    "section_count": len(script_data.sections),
                    "estimated_duration": script_data.estimated_duration_seconds,
                    "source_docs": [s.model_dump() for s in source_docs_info],
                    "status": "script_ready" if generate_script_only else "generating"
                }
            )

            if generate_script_only:
                yield {
                    "status": "completed",
                    "message": f"Script généré avec succès: {len(script_data.sections)} sections",
                    "percentage": 100.0,
                    "section_count": len(script_data.sections),
                    "estimated_duration_seconds": script_data.estimated_duration_seconds
                }
                return

            # Generate audio segments
            yield {
                "status": "generating_audio",
                "message": "Génération des segments audio...",
                "percentage": 45.0,
                "current_section": 0,
                "total_sections": len(script_data.sections)
            }

            temp_dir = tempfile.mkdtemp(prefix="audio_summary_")
            segment_files = []

            for i, section in enumerate(script_data.sections):
                yield {
                    "status": "generating_audio",
                    "message": f"Section {i+1}/{len(script_data.sections)}: {section.title or section.level}",
                    "percentage": 45.0 + (45.0 * i / len(script_data.sections)),
                    "current_section": i + 1,
                    "total_sections": len(script_data.sections)
                }

                # Generate pause/silence if needed
                if section.pause_before_ms > 0:
                    silence_path = os.path.join(temp_dir, f"{i:03d}_silence.mp3")
                    await self._generate_silence(silence_path, section.pause_before_ms)
                    if os.path.exists(silence_path):
                        segment_files.append(silence_path)

                # Generate audio for section content
                segment_path = os.path.join(temp_dir, f"{i:03d}_content.mp3")
                result = await self.tts_service.text_to_speech(
                    text=section.content,
                    output_path=segment_path,
                    voice=section.voice,
                    language="fr",
                    clean_markdown=False  # Already cleaned
                )

                if result.success:
                    segment_files.append(segment_path)
                else:
                    logger.warning(f"Failed to generate audio for section {i}: {result.error}")

            if len(segment_files) < 1:
                yield {
                    "status": "error",
                    "message": "Impossible de générer les segments audio"
                }
                return

            # Concatenate segments
            yield {
                "status": "concatenating",
                "message": f"Assemblage de {len(segment_files)} segments...",
                "percentage": 90.0
            }

            # Generate final filename
            safe_name = re.sub(r'[^\w\s-]', '', name).strip().replace(' ', '_')[:50]
            audio_filename = f"{summary_record_id}_{safe_name}.mp3"
            audio_path = audio_dir / audio_filename

            # Concatenate with ffmpeg
            success = await self._concatenate_segments(segment_files, str(audio_path), temp_dir)

            if not success:
                yield {
                    "status": "error",
                    "message": "Erreur lors de l'assemblage des segments audio"
                }
                return

            # Get actual duration
            actual_duration = await self._get_audio_duration(str(audio_path))

            # Update database with final info
            await service.query(
                """
                UPDATE audio_summary
                SET audio_path = $audio_path,
                    actual_duration_seconds = $actual_duration,
                    status = 'completed',
                    updated_at = time::now()
                WHERE id = type::thing('audio_summary', $summary_id)
                """,
                {
                    "summary_id": summary_record_id,
                    "audio_path": str(audio_path),
                    "actual_duration": actual_duration
                }
            )

            yield {
                "status": "completed",
                "message": f"Résumé audio généré: {int(actual_duration/60)} min {int(actual_duration%60)} sec",
                "percentage": 100.0,
                "section_count": len(script_data.sections),
                "actual_duration_seconds": actual_duration
            }

        except Exception as e:
            logger.error(f"Error generating audio summary: {e}", exc_info=True)

            # Update status to error
            try:
                service = get_surreal_service()
                summary_record_id = summary_id.replace("audio_summary:", "")
                await service.query(
                    """
                    UPDATE audio_summary
                    SET status = 'error',
                        error_message = $error,
                        updated_at = time::now()
                    WHERE id = type::thing('audio_summary', $summary_id)
                    """,
                    {
                        "summary_id": summary_record_id,
                        "error": str(e)
                    }
                )
            except Exception:
                pass

            yield {
                "status": "error",
                "message": f"Erreur: {str(e)}"
            }

        finally:
            # Clean up temp directory
            if temp_dir and os.path.exists(temp_dir):
                try:
                    shutil.rmtree(temp_dir)
                except Exception as cleanup_error:
                    logger.warning(f"Failed to clean up temp dir: {cleanup_error}")

    async def generate_audio_from_script(
        self,
        summary_id: str,
    ) -> AsyncGenerator[Dict, None]:
        """
        Generate audio from an existing script (no LLM call).

        This method is used when the script has already been generated and we only
        need to convert it to audio. Useful for re-generating audio or when the
        user has an existing script.

        Args:
            summary_id: ID of the audio summary record with existing script_data

        Yields:
            Progress updates as dict
        """
        temp_dir = None
        service = get_surreal_service()

        try:
            # Normalize summary_id
            summary_record_id = summary_id.replace("audio_summary:", "")

            yield {
                "status": "loading",
                "message": "Chargement du script existant...",
                "percentage": 0.0
            }

            # Load existing summary with script_data
            result = await service.query(
                f"SELECT * FROM audio_summary:{summary_record_id}"
            )

            if not result or len(result) == 0:
                yield {
                    "status": "error",
                    "message": f"Résumé audio non trouvé: {summary_id}"
                }
                return

            summary = result[0]
            script_data_raw = summary.get("script_data")
            course_id = str(summary.get("course_id", ""))
            name = summary.get("name", "audio")

            if not script_data_raw:
                yield {
                    "status": "error",
                    "message": "Aucun script trouvé. Générez d'abord le script avec un modèle LLM."
                }
                return

            # Convert raw dict to ScriptData
            script_data = ScriptData(**script_data_raw)

            if not script_data.sections:
                yield {
                    "status": "error",
                    "message": "Le script ne contient aucune section."
                }
                return

            yield {
                "status": "generating_audio",
                "message": f"Script chargé: {len(script_data.sections)} sections",
                "percentage": 10.0,
                "total_sections": len(script_data.sections)
            }

            # Create output directory
            course_record_id = course_id.replace("course:", "")
            audio_dir = Path(settings.upload_dir) / "courses" / course_record_id / "audio_summaries"
            audio_dir.mkdir(parents=True, exist_ok=True)

            # Update status to generating
            await service.query(
                """
                UPDATE audio_summary
                SET status = 'generating',
                    updated_at = time::now()
                WHERE id = type::thing('audio_summary', $summary_id)
                """,
                {"summary_id": summary_record_id}
            )

            # Generate audio segments
            temp_dir = tempfile.mkdtemp(prefix="audio_summary_")
            segment_files = []

            for i, section in enumerate(script_data.sections):
                yield {
                    "status": "generating_audio",
                    "message": f"Section {i+1}/{len(script_data.sections)}: {section.title or section.level}",
                    "percentage": 10.0 + (80.0 * i / len(script_data.sections)),
                    "current_section": i + 1,
                    "total_sections": len(script_data.sections)
                }

                # Generate pause/silence if needed
                if section.pause_before_ms > 0:
                    silence_path = os.path.join(temp_dir, f"{i:03d}_silence.mp3")
                    await self._generate_silence(silence_path, section.pause_before_ms)
                    if os.path.exists(silence_path):
                        segment_files.append(silence_path)

                # Generate audio for section content
                segment_path = os.path.join(temp_dir, f"{i:03d}_content.mp3")
                result = await self.tts_service.text_to_speech(
                    text=section.content,
                    output_path=segment_path,
                    voice=section.voice,
                    language="fr",
                    clean_markdown=False  # Already cleaned
                )

                if result.success:
                    segment_files.append(segment_path)
                else:
                    logger.warning(f"Failed to generate audio for section {i}: {result.error}")

            if len(segment_files) < 1:
                yield {
                    "status": "error",
                    "message": "Impossible de générer les segments audio"
                }
                return

            # Concatenate segments
            yield {
                "status": "concatenating",
                "message": f"Assemblage de {len(segment_files)} segments...",
                "percentage": 90.0
            }

            # Generate final filename
            safe_name = re.sub(r'[^\w\s-]', '', name).strip().replace(' ', '_')[:50]
            audio_filename = f"{summary_record_id}_{safe_name}.mp3"
            audio_path = audio_dir / audio_filename

            # Concatenate with ffmpeg
            success = await self._concatenate_segments(segment_files, str(audio_path), temp_dir)

            if not success:
                yield {
                    "status": "error",
                    "message": "Erreur lors de l'assemblage des segments audio"
                }
                return

            # Get actual duration
            actual_duration = await self._get_audio_duration(str(audio_path))

            # Update database with final info
            await service.query(
                """
                UPDATE audio_summary
                SET audio_path = $audio_path,
                    actual_duration_seconds = $actual_duration,
                    status = 'completed',
                    updated_at = time::now()
                WHERE id = type::thing('audio_summary', $summary_id)
                """,
                {
                    "summary_id": summary_record_id,
                    "audio_path": str(audio_path),
                    "actual_duration": actual_duration
                }
            )

            yield {
                "status": "completed",
                "message": f"Audio généré: {int(actual_duration/60)} min {int(actual_duration%60)} sec",
                "percentage": 100.0,
                "section_count": len(script_data.sections),
                "actual_duration_seconds": actual_duration
            }

        except Exception as e:
            logger.error(f"Error generating audio from script: {e}", exc_info=True)

            # Update status to error
            try:
                summary_record_id = summary_id.replace("audio_summary:", "")
                await service.query(
                    """
                    UPDATE audio_summary
                    SET status = 'error',
                        error_message = $error,
                        updated_at = time::now()
                    WHERE id = type::thing('audio_summary', $summary_id)
                    """,
                    {
                        "summary_id": summary_record_id,
                        "error": str(e)
                    }
                )
            except Exception:
                pass

            yield {
                "status": "error",
                "message": f"Erreur: {str(e)}"
            }

        finally:
            # Clean up temp directory
            if temp_dir and os.path.exists(temp_dir):
                try:
                    shutil.rmtree(temp_dir)
                except Exception as cleanup_error:
                    logger.warning(f"Failed to clean up temp dir: {cleanup_error}")

    async def import_script_from_markdown(
        self,
        summary_id: str,
        markdown_content: str,
        voice_titles: str = "fr-CA-SylvieNeural"
    ) -> Dict:
        """
        Import and parse an existing markdown script.

        Parses a markdown script (in the format generated by this service)
        and stores it as script_data for later audio generation.

        Args:
            summary_id: ID of the audio summary record
            markdown_content: The markdown script content
            voice_titles: Default voice for titles (used if not specified in script)

        Returns:
            Dict with import result
        """
        service = get_surreal_service()

        try:
            # Normalize summary_id
            summary_record_id = summary_id.replace("audio_summary:", "")

            # Parse the markdown content
            script_data = self._parse_markdown_script(markdown_content, voice_titles)

            if not script_data or not script_data.sections:
                return {
                    "success": False,
                    "error": "Impossible de parser le script markdown. Vérifiez le format."
                }

            # Get course_id from existing summary
            result = await service.query(
                f"SELECT course_id FROM audio_summary:{summary_record_id}"
            )

            if not result or len(result) == 0:
                return {
                    "success": False,
                    "error": f"Résumé audio non trouvé: {summary_id}"
                }

            course_id = str(result[0].get("course_id", ""))
            course_record_id = course_id.replace("course:", "")

            # Create output directory and save script files
            audio_dir = Path(settings.upload_dir) / "courses" / course_record_id / "audio_summaries"
            audio_dir.mkdir(parents=True, exist_ok=True)

            script_md_path = audio_dir / f"{summary_record_id}_script.md"
            script_json_path = audio_dir / f"{summary_record_id}_script.json"

            # Save markdown script
            script_md_path.write_text(markdown_content, encoding="utf-8")

            # Save structured JSON
            script_json_path.write_text(
                json.dumps(script_data.model_dump(), ensure_ascii=False, indent=2),
                encoding="utf-8"
            )

            # Update database
            await service.query(
                """
                UPDATE audio_summary
                SET script_path = $script_path,
                    script_data = $script_data,
                    section_count = $section_count,
                    estimated_duration_seconds = $estimated_duration,
                    status = 'script_ready',
                    updated_at = time::now()
                WHERE id = type::thing('audio_summary', $summary_id)
                """,
                {
                    "summary_id": summary_record_id,
                    "script_path": str(script_md_path),
                    "script_data": script_data.model_dump(),
                    "section_count": len(script_data.sections),
                    "estimated_duration": script_data.estimated_duration_seconds
                }
            )

            logger.info(f"Script imported for summary {summary_id}: {len(script_data.sections)} sections")

            return {
                "success": True,
                "section_count": len(script_data.sections),
                "estimated_duration_seconds": script_data.estimated_duration_seconds
            }

        except Exception as e:
            logger.error(f"Error importing script: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }

    def _parse_markdown_script(
        self,
        markdown_content: str,
        default_voice: str
    ) -> Optional[ScriptData]:
        """
        Parse a markdown script into ScriptData structure.

        Expected format:
        # Title
        ---
        **Informations**
        - **Documents sources:** doc1.md, doc2.md
        - **Durée estimée:** X min Y sec
        ...
        ---
        ## Section Title
        *Voix: VoiceName*
        Content...
        """
        sections = []
        section_idx = 0

        # Build list of available body voices
        body_voices = [v for v in BODY_VOICES if v != default_voice]
        if not body_voices:
            body_voices = BODY_VOICES

        # Extract title from first line
        lines = markdown_content.strip().split('\n')
        title = "Script importé"
        for line in lines:
            if line.startswith('# '):
                title = line[2:].strip()
                break

        # Voice name to full voice ID mapping
        voice_map = {
            "Sylvie": "fr-CA-SylvieNeural",
            "Antoine": "fr-CA-AntoineNeural",
            "Jean": "fr-CA-JeanNeural",
            "Thierry": "fr-CA-ThierryNeural",
            "Denise": "fr-FR-DeniseNeural",
            "Henri": "fr-FR-HenriNeural",
            "Éloïse": "fr-FR-EloiseNeural",
            "Eloise": "fr-FR-EloiseNeural",
            "Charline": "fr-BE-CharlineNeural",
            "Gérard": "fr-BE-GerardNeural",
            "Gerard": "fr-BE-GerardNeural",
            "Ariane": "fr-CH-ArianeNeural",
            "Fabrice": "fr-CH-FabriceNeural",
        }

        # Parse sections using regex
        # Pattern matches: ## or ### or #### followed by title, then *Voix: Name*, then content
        section_pattern = r'(?:^|\n)(#{2,4})\s+([^\n]+)\n+\*Voix:\s*([^*]+)\*\n+([\s\S]*?)(?=\n#{2,4}\s|\n---|\Z)'

        matches = re.findall(section_pattern, markdown_content)

        for heading_marks, section_title, voice_name, content in matches:
            # Determine level from heading marks
            level_map = {"##": "h1", "###": "h2", "####": "h3"}
            level = level_map.get(heading_marks, "h2")

            # Get voice ID from name
            voice_name = voice_name.strip()
            voice_id = voice_map.get(voice_name, default_voice)

            # Clean content
            content = content.strip()
            if not content:
                continue

            # Determine pause
            pause_ms = DEFAULT_PAUSE_CONFIG.get(level, DEFAULT_PAUSE_CONFIG["h2"])

            sections.append(ScriptSection(
                id=f"s{section_idx:03d}",
                level=level,
                title=section_title.strip(),
                content=content,
                voice=voice_id,
                pause_before_ms=pause_ms,
                estimated_duration_seconds=self._estimate_duration_from_text(content)
            ))
            section_idx += 1

        if not sections:
            # Try alternative parsing for simpler format
            sections = self._parse_simple_markdown(markdown_content, default_voice, body_voices)

        if not sections:
            logger.warning("No sections found in markdown script")
            return None

        # Check if all sections have the same voice (old script format)
        # If so, re-assign voices based on level
        unique_voices = set(s.voice for s in sections)
        if len(unique_voices) == 1:
            logger.info("Script has single voice, re-assigning voices based on level")
            last_body_voice = None

            def get_random_body_voice() -> str:
                nonlocal last_body_voice
                available = [v for v in body_voices if v != last_body_voice]
                if not available:
                    available = body_voices
                voice = random.choice(available)
                last_body_voice = voice
                return voice

            for section in sections:
                if section.level in ["h1", "h2", "intro", "outro"]:
                    section.voice = default_voice
                else:
                    section.voice = get_random_body_voice()

        total_duration = sum(s.estimated_duration_seconds for s in sections)

        return ScriptData(
            title=title,
            source_documents=[],
            generated_at=datetime.now(timezone.utc).isoformat(),
            estimated_duration_seconds=total_duration,
            sections=sections
        )

    def _parse_simple_markdown(
        self,
        markdown_content: str,
        default_voice: str,
        body_voices: List[str]
    ) -> List[ScriptSection]:
        """
        Parse simpler markdown format without voice annotations.

        Assigns voices automatically based on heading level.
        """
        sections = []
        section_idx = 0
        last_body_voice = None

        def get_random_body_voice() -> str:
            nonlocal last_body_voice
            available = [v for v in body_voices if v != last_body_voice]
            if not available:
                available = body_voices
            voice = random.choice(available)
            last_body_voice = voice
            return voice

        # Split by headings
        parts = re.split(r'\n(#{2,4})\s+([^\n]+)\n', markdown_content)

        # parts will be: [preamble, ##, title1, content1, ###, title2, content2, ...]
        i = 1  # Skip preamble
        while i < len(parts) - 2:
            heading_marks = parts[i]
            section_title = parts[i + 1]
            content = parts[i + 2] if i + 2 < len(parts) else ""
            i += 3

            # Skip metadata sections
            if section_title.lower() in ["informations", "information"]:
                continue

            # Determine level
            level_map = {"##": "h1", "###": "h2", "####": "h3"}
            level = level_map.get(heading_marks, "h2")

            # Assign voice
            if level in ["h1", "h2"]:
                voice = default_voice
            else:
                voice = get_random_body_voice()

            # Clean content - remove voice annotations if present
            content = re.sub(r'\*Voix:\s*[^*]+\*\n*', '', content).strip()

            if not content:
                continue

            pause_ms = DEFAULT_PAUSE_CONFIG.get(level, DEFAULT_PAUSE_CONFIG["h2"])

            sections.append(ScriptSection(
                id=f"s{section_idx:03d}",
                level=level,
                title=section_title.strip(),
                content=content,
                voice=voice,
                pause_before_ms=pause_ms,
                estimated_duration_seconds=self._estimate_duration_from_text(content)
            ))
            section_idx += 1

        return sections

    async def _load_documents(
        self, document_ids: List[str]
    ) -> tuple[List[Dict], List[AudioSourceDocument]]:
        """Load document contents from database."""
        service = get_surreal_service()
        documents_data = []
        source_docs_info = []

        for doc_id in document_ids:
            # Normalize ID
            if not doc_id.startswith("document:"):
                doc_id = f"document:{doc_id}"

            result = await service.query(f"SELECT * FROM {doc_id}")

            if not result or len(result) == 0:
                logger.warning(f"Document not found: {doc_id}")
                continue

            doc = result[0]

            # Get content
            content = await self._read_document_text(doc)
            if not content:
                logger.warning(f"No content for document: {doc_id}")
                continue

            # Get document name
            filename = doc.get("filename") or doc.get("nom_fichier")
            if not filename:
                linked = doc.get("linked_source", {})
                filename = linked.get("relative_path", doc_id)

            relative_path = None
            if linked := doc.get("linked_source"):
                relative_path = linked.get("relative_path")

            documents_data.append({
                "doc_id": str(doc.get("id", doc_id)),
                "name": filename,
                "content": content,
                "length": len(content)
            })

            source_docs_info.append(AudioSourceDocument(
                doc_id=str(doc.get("id", doc_id)),
                name=filename,
                relative_path=relative_path
            ))

        return documents_data, source_docs_info

    async def _read_document_text(self, document: Dict) -> Optional[str]:
        """Read text content from a document."""
        # Try extracted text first
        extracted = document.get("extracted_text") or document.get("texte_extrait")
        if extracted and len(extracted) > 100:
            return extracted

        # Try to read from file path
        file_path = document.get("file_path") or document.get("chemin_fichier")
        if not file_path:
            linked_source = document.get("linked_source")
            if linked_source:
                file_path = linked_source.get("absolute_path")

        if file_path:
            path = Path(file_path)
            if path.exists() and path.suffix.lower() in [".md", ".txt", ".markdown"]:
                try:
                    return path.read_text(encoding="utf-8")
                except Exception as e:
                    logger.error(f"Error reading file {file_path}: {e}")

        return None

    async def _restructure_content_for_audio(
        self,
        documents_data: List[Dict],
        name: str,
        model_id: str,
        voice_titles: str
    ) -> Optional[ScriptData]:
        """Use LLM to restructure content for audio."""
        # Merge all document contents
        merged_content = ""
        for doc in documents_data:
            merged_content += f"\n\n## Document: {doc['name']}\n\n{doc['content']}"

        # Chunk if too large (process in parts)
        # Claude can handle ~200K tokens, so we use larger chunks for better context
        chunk_size = 50000
        min_chunk_size = 5000  # Minimum chars per chunk to avoid incomplete content
        if len(merged_content) > chunk_size:
            # Split by headers and process chunks
            all_sections = []
            chunks = self._split_by_headers(merged_content, chunk_size, min_chunk_size)

            for chunk_idx, chunk in enumerate(chunks):
                chunk_sections = await self._process_chunk_with_llm(
                    chunk, name, model_id, voice_titles, chunk_idx, len(chunks)
                )
                if chunk_sections:
                    all_sections.extend(chunk_sections)

            if not all_sections:
                return None

            # Build final script data
            total_duration = sum(s.estimated_duration_seconds for s in all_sections)
            return ScriptData(
                title=name,
                source_documents=[d["name"] for d in documents_data],
                generated_at=datetime.now(timezone.utc).isoformat(),
                estimated_duration_seconds=total_duration,
                sections=all_sections
            )
        else:
            return await self._process_chunk_with_llm(
                merged_content, name, model_id, voice_titles, 0, 1, return_script_data=True
            )

    async def _process_chunk_with_llm(
        self,
        content: str,
        name: str,
        model_id: str,
        voice_titles: str,
        chunk_idx: int,
        total_chunks: int,
        return_script_data: bool = False
    ):
        """Process a content chunk with LLM."""
        # Use different prompts for first chunk vs subsequent chunks
        if chunk_idx == 0 or total_chunks == 1:
            prompt = AUDIO_SCRIPT_PROMPT.format(
                document_name=name,
                content=content
            )
        else:
            prompt = AUDIO_SCRIPT_CHUNK_PROMPT.format(
                chunk_num=chunk_idx + 1,
                total_chunks=total_chunks,
                content=content
            )

        try:
            # Log content info for debugging
            logger.info(f"Processing chunk {chunk_idx + 1}/{total_chunks}: {len(content)} chars")
            logger.debug(f"Content preview: {content[:500]}...")

            # Use Agno for LLM call
            model = create_model(model_id)
            agent = Agent(
                name="AudioScriptGenerator",
                model=model,
                instructions="Tu es un professeur qui crée des cours audio pédagogiques détaillés pour préparer des examens. Tu enseignes TOUT le contenu fourni de manière claire et complète.",
                markdown=False
            )

            response = await agent.arun(prompt)
            response_text = response.content if hasattr(response, "content") else str(response)

            # Log response info
            logger.info(f"LLM response length: {len(response_text)} chars")
            logger.debug(f"Response preview: {response_text[:500]}...")

            # Parse JSON response
            sections = self._parse_llm_response(response_text, voice_titles)

            if return_script_data and sections:
                total_duration = sum(s.estimated_duration_seconds for s in sections)
                return ScriptData(
                    title=name,
                    source_documents=[],
                    generated_at=datetime.now(timezone.utc).isoformat(),
                    estimated_duration_seconds=total_duration,
                    sections=sections
                )

            return sections

        except Exception as e:
            logger.error(f"Error processing chunk {chunk_idx + 1}/{total_chunks}: {e}")
            return [] if not return_script_data else None

    def _parse_llm_response(
        self, response_text: str, voice_titles: str
    ) -> List[ScriptSection]:
        """Parse LLM JSON response into script sections."""
        sections = []

        # Extract JSON from response
        json_match = re.search(r'\{[\s\S]*\}', response_text)
        if not json_match:
            logger.error("No JSON found in LLM response")
            # Try fallback extraction
            return self._fallback_extract_sections(response_text, voice_titles)

        json_str = json_match.group()

        # Try multiple parsing strategies
        data = self._try_parse_json(json_str)

        if not data:
            logger.warning("All JSON parsing attempts failed, trying fallback extraction")
            return self._fallback_extract_sections(response_text, voice_titles)

        return self._build_sections_from_data(data, voice_titles)

    def _try_parse_json(self, json_str: str) -> Optional[Dict]:
        """Try multiple strategies to parse JSON."""
        # Strategy 1: Try json5 (most lenient - allows trailing commas, comments, etc.)
        try:
            data = json5.loads(json_str)
            logger.info("JSON parsed successfully with json5")
            return data
        except Exception as e:
            logger.debug(f"json5 parse failed: {e}")

        # Strategy 2: Try standard json
        try:
            data = json.loads(json_str)
            logger.info("JSON parsed successfully with standard json")
            return data
        except json.JSONDecodeError as e:
            logger.debug(f"Standard JSON parse failed: {e}")

        # Strategy 3: Repair and try json5
        repaired = self._repair_json(json_str)
        try:
            data = json5.loads(repaired)
            logger.info("JSON parsed successfully after repair with json5")
            return data
        except Exception as e:
            logger.debug(f"json5 parse after repair failed: {e}")

        # Strategy 4: Repair and try standard json
        try:
            data = json.loads(repaired)
            logger.info("JSON parsed successfully after repair with standard json")
            return data
        except json.JSONDecodeError as e:
            logger.error(f"All JSON parsing strategies failed. Last error: {e}")
            # Log snippet for debugging
            error_pos = e.pos if hasattr(e, 'pos') else 0
            snippet_start = max(0, error_pos - 100)
            snippet_end = min(len(repaired), error_pos + 100)
            logger.error(f"JSON snippet around error: ...{repaired[snippet_start:snippet_end]}...")

        return None

    def _build_sections_from_data(self, data: Dict, voice_titles: str) -> List[ScriptSection]:
        """Build ScriptSection list from parsed JSON data."""
        sections = []
        section_idx = 0

        # Build list of available body voices
        body_voices = [v for v in BODY_VOICES if v != voice_titles]
        if not body_voices:
            body_voices = BODY_VOICES
        last_body_voice = None

        def get_random_body_voice() -> str:
            nonlocal last_body_voice
            available = [v for v in body_voices if v != last_body_voice]
            if not available:
                available = body_voices
            voice = random.choice(available)
            last_body_voice = voice
            return voice

        # Add introduction
        if intro := data.get("introduction"):
            sections.append(ScriptSection(
                id=f"s{section_idx:03d}",
                level="intro",
                title="Introduction",
                content=intro,
                voice=voice_titles,
                pause_before_ms=0,
                estimated_duration_seconds=self._estimate_duration_from_text(intro)
            ))
            section_idx += 1

        # Process sections
        for raw_section in data.get("sections", []):
            level = raw_section.get("level", "body")
            title = raw_section.get("title")
            content = raw_section.get("content", "")

            if not content:
                continue

            # H1 and H2 use the main voice, H3 and body use random voices
            if level in ["h1", "h2"]:
                voice = voice_titles
                pause_ms = DEFAULT_PAUSE_CONFIG.get(level, DEFAULT_PAUSE_CONFIG["h2"])
            else:
                voice = get_random_body_voice()
                pause_ms = DEFAULT_PAUSE_CONFIG.get(level, DEFAULT_PAUSE_CONFIG["paragraph"])

            if title and level in ["h1", "h2"]:
                content = f"{title}. {content}"

            sections.append(ScriptSection(
                id=f"s{section_idx:03d}",
                level=level,
                title=title,
                content=content,
                voice=voice,
                pause_before_ms=pause_ms,
                estimated_duration_seconds=self._estimate_duration_from_text(content)
            ))
            section_idx += 1

        # Add conclusion (uses main voice)
        if conclusion := data.get("conclusion"):
            sections.append(ScriptSection(
                id=f"s{section_idx:03d}",
                level="outro",
                title="Conclusion",
                content=conclusion,
                voice=voice_titles,
                pause_before_ms=DEFAULT_PAUSE_CONFIG["outro"],
                estimated_duration_seconds=self._estimate_duration_from_text(conclusion)
            ))

        return sections

    def _fallback_extract_sections(self, response_text: str, voice_titles: str) -> List[ScriptSection]:
        """Fallback: extract sections using regex when JSON parsing fails completely."""
        sections = []
        section_idx = 0

        body_voices = [v for v in BODY_VOICES if v != voice_titles]
        if not body_voices:
            body_voices = BODY_VOICES

        # Try to extract individual section objects
        # Pattern matches {"level": "...", "title": "...", "content": "..."}
        section_pattern = r'\{\s*"level"\s*:\s*"([^"]+)"\s*,\s*"title"\s*:\s*"([^"]*)"\s*,\s*"content"\s*:\s*"((?:[^"\\]|\\.)*)"\s*\}'

        matches = re.findall(section_pattern, response_text, re.DOTALL)

        if matches:
            logger.info(f"Fallback extraction found {len(matches)} sections")
            for level, title, content in matches:
                # Unescape the content
                content = content.replace('\\n', '\n').replace('\\"', '"').replace('\\\\', '\\')

                if not content.strip():
                    continue

                # H1 and H2 use the main voice, H3 and body use random voices
                if level in ["h1", "h2"]:
                    voice = voice_titles
                    pause_ms = DEFAULT_PAUSE_CONFIG.get(level, DEFAULT_PAUSE_CONFIG["h2"])
                else:
                    voice = random.choice(body_voices)
                    pause_ms = DEFAULT_PAUSE_CONFIG.get(level, DEFAULT_PAUSE_CONFIG["paragraph"])

                if title and level in ["h1", "h2"]:
                    content = f"{title}. {content}"

                sections.append(ScriptSection(
                    id=f"s{section_idx:03d}",
                    level=level,
                    title=title if title else None,
                    content=content,
                    voice=voice,
                    pause_before_ms=pause_ms,
                    estimated_duration_seconds=self._estimate_duration_from_text(content)
                ))
                section_idx += 1
        else:
            logger.error("Fallback extraction found no sections")

        return sections

    def _repair_json(self, json_str: str) -> str:
        """Attempt to repair common JSON issues from LLM responses."""
        repaired = json_str

        # Step 1: Fix unescaped newlines inside strings
        # This is the most common issue - Claude puts actual newlines in string values
        result = []
        in_string = False
        escape_next = False
        i = 0

        while i < len(repaired):
            char = repaired[i]

            if escape_next:
                result.append(char)
                escape_next = False
                i += 1
                continue

            if char == '\\':
                escape_next = True
                result.append(char)
                i += 1
                continue

            if char == '"':
                in_string = not in_string
                result.append(char)
                i += 1
                continue

            if char == '\n' and in_string:
                # Replace actual newline in string with escaped version
                result.append('\\n')
            elif char == '\t' and in_string:
                result.append('\\t')
            else:
                result.append(char)

            i += 1

        repaired = ''.join(result)

        # Step 2: Remove trailing commas before } or ]
        repaired = re.sub(r',(\s*[}\]])', r'\1', repaired)

        # Step 3: Fix missing commas between objects in arrays: }{ -> },{
        repaired = re.sub(r'\}(\s*)\{', r'},\1{', repaired)

        # Step 4: Fix missing commas between array elements: ]["  -> ],["
        repaired = re.sub(r'\](\s*)\[', r'],\1[', repaired)

        # Step 5: Fix missing commas after string values before new keys
        # Pattern: "value" \n "key": -> "value", \n "key":
        repaired = re.sub(r'"(\s*)\n(\s*)"([^"]+)"(\s*):', r'",\1\n\2"\3"\4:', repaired)

        # Step 6: Fix missing commas after } before "key":
        repaired = re.sub(r'\}(\s*)"([^"]+)"(\s*):', r'},\1"\2"\3:', repaired)

        # Step 7: Ensure proper closing brackets at the end
        open_braces = repaired.count('{') - repaired.count('}')
        open_brackets = repaired.count('[') - repaired.count(']')

        if open_braces > 0:
            repaired = repaired.rstrip() + '}' * open_braces
        if open_brackets > 0:
            repaired = repaired.rstrip() + ']' * open_brackets

        return repaired

    def _split_by_headers(self, content: str, max_chunk_size: int, min_chunk_size: int = 5000) -> List[str]:
        """Split content by headers while respecting max and min chunk sizes.

        Args:
            content: The full content to split
            max_chunk_size: Maximum characters per chunk
            min_chunk_size: Minimum characters per chunk (to avoid tiny chunks)
        """
        # Split by H1 and H2 headers for better granularity
        parts = re.split(r'\n(?=##? [^#])', content)
        chunks = []
        current_chunk = ""

        for part in parts:
            if len(current_chunk) + len(part) > max_chunk_size:
                # Only save current chunk if it meets minimum size
                if current_chunk and len(current_chunk) >= min_chunk_size:
                    chunks.append(current_chunk)
                    current_chunk = part
                elif current_chunk:
                    # Current chunk too small, keep accumulating
                    current_chunk += "\n" + part
                else:
                    current_chunk = part
            else:
                current_chunk += "\n" + part if current_chunk else part

        # Handle final chunk
        if current_chunk:
            if chunks and len(current_chunk) < min_chunk_size:
                # Merge small final chunk with previous
                chunks[-1] += "\n" + current_chunk
            else:
                chunks.append(current_chunk)

        # Safety check: if we ended up with no chunks, return the whole content
        if not chunks:
            chunks = [content]

        return chunks

    def _estimate_duration_from_text(self, text: str) -> float:
        """Estimate audio duration from text (~150 words/minute)."""
        WORDS_PER_MINUTE = 150
        CHARS_PER_WORD = 5

        words = len(text) / CHARS_PER_WORD
        return (words / WORDS_PER_MINUTE) * 60

    def _generate_readable_script(
        self,
        script_data: ScriptData,
        name: str,
        source_docs: List[AudioSourceDocument]
    ) -> str:
        """Generate human-readable Markdown script file."""
        lines = []

        # Header
        lines.append(f"# {name}")
        lines.append("")
        lines.append("---")
        lines.append("")
        lines.append("**Informations**")
        lines.append("")
        lines.append(f"- **Documents sources:** {', '.join(d.name for d in source_docs)}")
        duration_min = int(script_data.estimated_duration_seconds / 60)
        duration_sec = int(script_data.estimated_duration_seconds % 60)
        lines.append(f"- **Durée estimée:** {duration_min} min {duration_sec} sec")
        lines.append(f"- **Sections:** {len(script_data.sections)}")
        lines.append(f"- **Généré le:** {script_data.generated_at[:19].replace('T', ' ')}")
        lines.append("")
        lines.append("---")
        lines.append("")

        for section in script_data.sections:
            voice_name = section.voice.split("-")[-1].replace("Neural", "")

            if section.level == "intro":
                lines.append("## Introduction")
                lines.append("")
                lines.append(f"*Voix: {voice_name}*")
                lines.append("")
            elif section.level == "outro":
                lines.append("---")
                lines.append("")
                lines.append("## Conclusion")
                lines.append("")
                lines.append(f"*Voix: {voice_name}*")
                lines.append("")
            elif section.level == "h1":
                lines.append("---")
                lines.append("")
                if section.title:
                    lines.append(f"## {section.title}")
                else:
                    lines.append("## Section")
                lines.append("")
                lines.append(f"*Voix: {voice_name}*")
                lines.append("")
            elif section.level == "h2":
                lines.append("")
                if section.title:
                    lines.append(f"### {section.title}")
                else:
                    lines.append("### Sous-section")
                lines.append("")
                lines.append(f"*Voix: {voice_name}*")
                lines.append("")
            elif section.level == "h3":
                lines.append("")
                if section.title:
                    lines.append(f"#### {section.title}")
                else:
                    lines.append("#### Détail")
                lines.append("")
                lines.append(f"*Voix: {voice_name}*")
                lines.append("")
            else:
                # Body section
                lines.append("")
                lines.append(f"*Voix: {voice_name}*")
                lines.append("")

            lines.append(section.content)
            lines.append("")

        lines.append("---")
        lines.append("")
        lines.append("*Fin du script*")

        return "\n".join(lines)

    async def _generate_silence(self, output_path: str, duration_ms: int) -> bool:
        """Generate a silent audio segment using ffmpeg.

        Uses 24000 Hz mono to match edge-tts output format.
        """
        try:
            duration_seconds = duration_ms / 1000.0

            # Use 24000 Hz mono to match edge-tts output
            ffmpeg_cmd = [
                "ffmpeg", "-y",
                "-f", "lavfi",
                "-i", "anullsrc=r=24000:cl=mono",
                "-t", str(duration_seconds),
                "-b:a", "48k",
                "-acodec", "libmp3lame",
                output_path
            ]

            proc = await asyncio.create_subprocess_exec(
                *ffmpeg_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            await proc.communicate()

            return proc.returncode == 0

        except Exception as e:
            logger.error(f"Error generating silence: {e}")
            return False

    async def _concatenate_segments(
        self, segment_files: List[str], output_path: str, temp_dir: str
    ) -> bool:
        """Concatenate audio segments using ffmpeg.

        Re-encodes to ensure consistent sample rate and format across all segments.
        """
        try:
            # Create concat file
            concat_file = os.path.join(temp_dir, "concat.txt")
            with open(concat_file, "w") as f:
                for seg_file in segment_files:
                    escaped_path = seg_file.replace("'", "'\\''")
                    f.write(f"file '{escaped_path}'\n")

            # Concatenate with ffmpeg - re-encode to ensure consistent output
            # Use 48kHz stereo for better quality and browser compatibility
            ffmpeg_cmd = [
                "ffmpeg", "-y",
                "-f", "concat",
                "-safe", "0",
                "-i", concat_file,
                "-ar", "48000",      # 48kHz sample rate
                "-ac", "2",          # Stereo
                "-b:a", "128k",      # Good quality bitrate
                "-acodec", "libmp3lame",
                output_path
            ]

            proc = await asyncio.create_subprocess_exec(
                *ffmpeg_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            stdout, stderr = await proc.communicate()

            if proc.returncode != 0:
                logger.error(f"ffmpeg concatenation failed: {stderr.decode()}")
                return False

            return os.path.exists(output_path)

        except Exception as e:
            logger.error(f"Error concatenating segments: {e}")
            return False

    async def _get_audio_duration(self, audio_path: str) -> float:
        """Get the duration of an audio file using ffprobe."""
        try:
            ffprobe_cmd = [
                "ffprobe", "-v", "quiet",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                audio_path
            ]

            proc = await asyncio.create_subprocess_exec(
                *ffprobe_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            stdout, _ = await proc.communicate()

            if proc.returncode == 0:
                return float(stdout.decode().strip())

        except Exception as e:
            logger.error(f"Error getting audio duration: {e}")

        return 0.0


# Singleton instance
_audio_summary_service: Optional[AudioSummaryService] = None


def get_audio_summary_service() -> AudioSummaryService:
    """Get the singleton audio summary service instance."""
    global _audio_summary_service
    if _audio_summary_service is None:
        _audio_summary_service = AudioSummaryService()
    return _audio_summary_service
