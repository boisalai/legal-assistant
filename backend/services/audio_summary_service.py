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
AUDIO_SCRIPT_PROMPT = """Tu es un professeur de droit qui prépare un cours audio pour aider un étudiant à réviser pour son examen final.

CONTENU DU COURS À ENSEIGNER:
\"\"\"
{content}
\"\"\"

OBJECTIF: Créer un script audio PÉDAGOGIQUE et COMPLET qui:
1. ENSEIGNE chaque concept mentionné dans le contenu source
2. EXPLIQUE les définitions avec des exemples concrets
3. DÉTAILLE les distinctions importantes (ex: droit civil vs common law)
4. DÉVELOPPE les principes juridiques pour qu'un étudiant les comprenne et les retienne
5. INCLUT tous les articles de loi, cas jurisprudentiels et références mentionnés

RÈGLES DE CONTENU:
- Couvre TOUS les sujets du document source - ne saute rien
- Pour chaque concept: définition + explication + exemple si pertinent
- Développe les abréviations (C.c.Q. → Code civil du Québec)
- Explique les termes latins (ex: "Ubi societas, ibi jus signifie: là où il y a société, il y a droit")
- Mentionne les cas jurisprudentiels importants avec leur signification
- Cible environ 150 mots par minute de lecture

FORMAT JSON:
{{
  "title": "{document_name}",
  "introduction": "Bienvenue dans cette leçon sur [sujet principal]. Nous allons étudier en détail [liste des thèmes majeurs].",
  "sections": [
    {{"level": "h1", "title": "Titre de section", "content": "Explication pédagogique complète de cette section..."}},
    {{"level": "h2", "title": "Sous-titre", "content": "Développement détaillé du sous-thème..."}},
    {{"level": "body", "content": "Explication approfondie avec exemples..."}}
  ],
  "conclusion": "Récapitulons les points essentiels à retenir pour l'examen. Premièrement, [concept 1 avec définition clé]. Deuxièmement, [concept 2]. [etc.]"
}}

Génère un script LONG et DÉTAILLÉ couvrant TOUTE la matière. JSON:"""

# Prompt for subsequent chunks (no intro/conclusion)
AUDIO_SCRIPT_CHUNK_PROMPT = """Continue le cours audio pédagogique (partie {chunk_num}/{total_chunks}).

CONTENU À ENSEIGNER:
\"\"\"
{content}
\"\"\"

Continue à enseigner ce contenu de manière pédagogique et détaillée.
- Explique chaque concept avec exemples
- Développe les définitions
- Pas d'introduction ni conclusion (partie intermédiaire)

JSON:
{{
  "sections": [
    {{"level": "h1", "title": "Titre", "content": "Explication pédagogique complète..."}},
    {{"level": "h2", "title": "Sous-titre", "content": "Développement détaillé..."}},
    {{"level": "body", "content": "Explication approfondie..."}}
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
        chunk_size = 12000
        if len(merged_content) > chunk_size:
            # Split by headers and process chunks
            all_sections = []
            chunks = self._split_by_headers(merged_content, chunk_size)

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
            return sections

        try:
            data = json.loads(json_match.group())
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON: {e}")
            return sections

        section_idx = 0

        # Build list of available body voices (excluding the title voice for variety)
        body_voices = [v for v in BODY_VOICES if v != voice_titles]
        if not body_voices:
            body_voices = BODY_VOICES  # Fallback if title voice is the only one
        last_body_voice = None  # Track last used voice to avoid repetition

        def get_random_body_voice() -> str:
            """Get a random body voice, avoiding consecutive repetition."""
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

            # Determine voice and pause based on level
            if level in ["h1", "h2", "h3"]:
                voice = voice_titles
                pause_ms = DEFAULT_PAUSE_CONFIG.get(level, DEFAULT_PAUSE_CONFIG["h2"])
            else:
                # Body sections get random voices from fr-CA and fr-FR
                voice = get_random_body_voice()
                pause_ms = DEFAULT_PAUSE_CONFIG["paragraph"]

            # Add title announcement for H1/H2
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

        # Add conclusion
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

    def _split_by_headers(self, content: str, max_chunk_size: int) -> List[str]:
        """Split content by headers while respecting max chunk size."""
        # Split by H1 headers first
        parts = re.split(r'\n(?=# )', content)
        chunks = []
        current_chunk = ""

        for part in parts:
            if len(current_chunk) + len(part) > max_chunk_size:
                if current_chunk:
                    chunks.append(current_chunk)
                current_chunk = part
            else:
                current_chunk += "\n" + part if current_chunk else part

        if current_chunk:
            chunks.append(current_chunk)

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
        """Generate a silent audio segment using ffmpeg."""
        try:
            duration_seconds = duration_ms / 1000.0

            ffmpeg_cmd = [
                "ffmpeg", "-y",
                "-f", "lavfi",
                "-i", f"anullsrc=r=44100:cl=mono",
                "-t", str(duration_seconds),
                "-q:a", "9",
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
        """Concatenate audio segments using ffmpeg."""
        try:
            # Create concat file
            concat_file = os.path.join(temp_dir, "concat.txt")
            with open(concat_file, "w") as f:
                for seg_file in segment_files:
                    escaped_path = seg_file.replace("'", "'\\''")
                    f.write(f"file '{escaped_path}'\n")

            # Concatenate with ffmpeg
            ffmpeg_cmd = [
                "ffmpeg", "-y",
                "-f", "concat",
                "-safe", "0",
                "-i", concat_file,
                "-c", "copy",
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
