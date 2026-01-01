"""
Flashcard Generation Service for Legal Assistant.

Generates flashcards from course documents using LLM.
"""

import json
import logging
import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import AsyncGenerator, Dict, List, Optional

from agno.agent import Agent

from config.settings import settings
from services.model_factory import create_model
from services.surreal_service import get_surreal_service
from services.tts_service import TTSService

logger = logging.getLogger(__name__)


# Prompt template for flashcard generation - optimized for local models
FLASHCARD_GENERATION_PROMPT = """Tu dois générer exactement {card_count} fiches de révision en JSON.

IMPORTANT: Tu dois retourner un objet JSON avec une clé "cards" contenant un tableau de {card_count} fiches.

Exemple de format attendu (avec 3 fiches):
{{"cards": [
  {{"card_type": "definition", "front": "Question 1?", "back": "Réponse 1"}},
  {{"card_type": "concept", "front": "Question 2?", "back": "Réponse 2"}},
  {{"card_type": "definition", "front": "Question 3?", "back": "Réponse 3"}}
]}}

Types de fiches: {card_types}

Contenu source (résumé):
{content}

RÈGLES STRICTES:
1. Génère EXACTEMENT {card_count} fiches, pas plus, pas moins
2. Chaque fiche DOIT avoir: card_type, front (question), back (réponse)
3. front = question claire et concise
4. back = réponse en 1-2 phrases
5. Réponds UNIQUEMENT avec le JSON, rien d'autre
6. Le JSON doit commencer par {{ et finir par }}

JSON:"""


class FlashcardService:
    """Service for generating flashcards from documents."""

    def __init__(self):
        """Initialize the flashcard service."""
        self.default_model = settings.model_id

    async def get_document_content(self, document_id: str) -> Optional[Dict]:
        """
        Retrieve document content from database.

        Args:
            document_id: Document ID (with or without prefix)

        Returns:
            Document data with file path and content
        """
        try:
            service = get_surreal_service()

            # Normalize ID
            if not document_id.startswith("document:"):
                document_id = f"document:{document_id}"

            result = await service.query(f"SELECT * FROM {document_id}")

            if result and len(result) > 0:
                doc_data = result[0]
                if isinstance(doc_data, dict):
                    return doc_data

            return None

        except Exception as e:
            logger.error(f"Error retrieving document {document_id}: {e}")
            return None

    async def read_document_text(self, document: Dict) -> Optional[str]:
        """
        Read the text content of a document.

        Tries extracted_text first, then reads from file if markdown.

        Args:
            document: Document dict from database

        Returns:
            Text content or None
        """
        # Try extracted text first
        extracted = document.get("extracted_text") or document.get("texte_extrait")
        if extracted and len(extracted) > 100:
            return extracted

        # Try to read from file path
        file_path = document.get("file_path") or document.get("chemin_fichier")
        if not file_path:
            # Try linked_source
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

    async def generate_flashcards(
        self,
        deck_id: str,
        source_document_ids: List[str],
        card_types: List[str],
        card_count: int = 50,
        model_id: Optional[str] = None
    ) -> AsyncGenerator[Dict, None]:
        """
        Generate flashcards from documents using LLM.

        Args:
            deck_id: ID of the deck to add cards to
            source_document_ids: List of document IDs to generate from
            card_types: Types of cards to generate
            card_count: Target number of cards
            model_id: LLM model to use (optional)

        Yields:
            Progress updates and generated cards
        """
        model_id = model_id or self.default_model

        yield {
            "status": "starting",
            "message": f"Démarrage de la génération avec {model_id}..."
        }

        # Collect document contents
        all_content = []
        source_docs_info = []

        for doc_id in source_document_ids:
            doc = await self.get_document_content(doc_id)
            if not doc:
                logger.warning(f"Document not found: {doc_id}")
                continue

            content = await self.read_document_text(doc)
            if not content:
                logger.warning(f"No content for document: {doc_id}")
                continue

            # Get document name
            filename = doc.get("filename") or doc.get("nom_fichier")
            if not filename:
                linked = doc.get("linked_source", {})
                filename = linked.get("relative_path", doc_id)

            all_content.append(f"## Document: {filename}\n\n{content}")
            source_docs_info.append({
                "doc_id": str(doc.get("id", doc_id)),
                "name": filename
            })

            yield {
                "status": "loading",
                "message": f"Document chargé: {filename}"
            }

        if not all_content:
            yield {
                "status": "error",
                "message": "Aucun contenu trouvé dans les documents sélectionnés"
            }
            return

        # Combine all content (no truncation - we'll chunk it)
        combined_content = "\n\n---\n\n".join(all_content)
        total_content_length = len(combined_content)
        logger.info(f"Total content length: {total_content_length} chars")

        # Split content into manageable chunks for the LLM
        # Each chunk should be ~5000 chars for reliable generation
        chunk_size = 5000
        chunks = self._split_content_into_chunks(combined_content, chunk_size)
        total_chunks = len(chunks)

        logger.info(f"Content split into {total_chunks} chunks")

        # Calculate cards per chunk (minimum 3 per chunk for quality)
        cards_per_chunk = max(3, min(10, card_count // max(1, total_chunks)))

        # Calculate how many chunks we actually need
        chunks_needed = min(total_chunks, (card_count + cards_per_chunk - 1) // cards_per_chunk)

        logger.info(f"Will use {chunks_needed} chunks to generate {card_count} cards ({cards_per_chunk} per chunk)")

        remaining_cards = card_count

        yield {
            "status": "generating",
            "message": f"Génération de {card_count} fiches en {chunks_needed} parties..."
        }

        # Format card types for prompt
        card_types_str = ", ".join(card_types)

        # Generate cards for each chunk (only process chunks we need)
        all_cards = []
        chunks_processed = 0
        for chunk_idx, chunk_content in enumerate(chunks):
            if remaining_cards <= 0:
                break

            chunks_processed += 1

            # Calculate how many cards for this chunk
            if chunks_processed >= chunks_needed:
                # Last needed chunk gets remaining cards
                chunk_cards = remaining_cards
            else:
                chunk_cards = min(cards_per_chunk, remaining_cards)

            remaining_cards -= chunk_cards

            yield {
                "status": "generating",
                "message": f"Partie {chunks_processed}/{chunks_needed}: génération de {chunk_cards} fiches..."
            }

            # Build prompt for this chunk
            prompt = FLASHCARD_GENERATION_PROMPT.format(
                card_count=chunk_cards,
                card_types=card_types_str,
                content=chunk_content
            )

            try:
                # For Ollama, call directly for better JSON compliance
                if "ollama" in model_id.lower():
                    response_text = await self._call_ollama_direct(
                        model_id=model_id.replace("ollama:", ""),
                        prompt=prompt,
                        card_count=chunk_cards
                    )
                else:
                    # Use Agno for other providers (Claude, etc.)
                    model = create_model(model_id)
                    agent = Agent(
                        name="FlashcardGenerator",
                        model=model,
                        instructions="Tu génères des fiches de révision en JSON.",
                        markdown=False
                    )
                    response = await agent.arun(prompt)
                    response_text = response.content if hasattr(response, "content") else str(response)

                # Log the raw response for debugging
                logger.info(f"Chunk {chunk_idx + 1} response length: {len(response_text)} chars")
                logger.debug(f"Chunk {chunk_idx + 1} response preview: {response_text[:500]}...")

                # Parse JSON from response
                chunk_parsed_cards = self._parse_cards_json(response_text)

                if chunk_parsed_cards:
                    all_cards.extend(chunk_parsed_cards)
                    logger.info(f"Chunk {chunk_idx + 1}: {len(chunk_parsed_cards)} cards parsed")
                else:
                    logger.warning(f"Chunk {chunk_idx + 1}: No cards parsed from response")

            except Exception as e:
                logger.error(f"Error generating cards for chunk {chunk_idx + 1}: {e}")
                # Continue with next chunk

        yield {
            "status": "parsing",
            "message": f"Analyse terminée: {len(all_cards)} fiches extraites"
        }

        cards = all_cards

        if not cards:
            logger.error("No cards generated from any chunk")
            yield {
                "status": "error",
                "message": "Impossible de générer des fiches depuis le contenu fourni"
            }
            return

        yield {
            "status": "saving",
            "message": f"Sauvegarde de {len(cards)} fiches..."
        }

        # Save cards to database
        service = get_surreal_service()
        deck_record_id = deck_id.replace("flashcard_deck:", "")

        saved_count = 0
        for card in cards:
            try:
                card_id = uuid.uuid4().hex[:8]

                # Determine source document
                source_doc_id = source_document_ids[0] if source_document_ids else ""

                card_data = {
                    "deck_id": f"flashcard_deck:{deck_record_id}",
                    "document_id": source_doc_id,
                    "card_type": card.get("card_type", "question"),
                    "front": card.get("front", ""),
                    "back": card.get("back", ""),
                    "source_excerpt": card.get("source_excerpt"),
                    "source_location": card.get("source_location"),
                    "status": "new",
                    "review_count": 0,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "last_reviewed": None
                }

                await service.query(
                    f"CREATE flashcard:{card_id} CONTENT $data",
                    {"data": card_data}
                )
                saved_count += 1

            except Exception as e:
                logger.error(f"Error saving card: {e}")

        # Update deck with source documents info
        try:
            await service.query(
                """
                UPDATE flashcard_deck
                SET source_documents = $source_docs,
                    card_types = $card_types
                WHERE id = type::thing('flashcard_deck', $deck_id)
                """,
                {
                    "deck_id": deck_record_id,
                    "source_docs": source_docs_info,
                    "card_types": card_types
                }
            )
        except Exception as e:
            logger.warning(f"Could not update deck metadata: {e}")

        yield {
            "status": "completed",
            "message": f"Génération terminée: {saved_count} fiches créées",
            "cards_generated": saved_count
        }

    def _split_content_into_chunks(self, content: str, chunk_size: int = 5000) -> List[str]:
        """
        Split content into chunks of approximately chunk_size characters.

        Tries to split at paragraph boundaries to maintain context.

        Args:
            content: The full content to split
            chunk_size: Target size for each chunk

        Returns:
            List of content chunks
        """
        if len(content) <= chunk_size:
            return [content]

        chunks = []
        current_pos = 0

        while current_pos < len(content):
            # Find the end position for this chunk
            end_pos = min(current_pos + chunk_size, len(content))

            if end_pos < len(content):
                # Try to find a good break point (paragraph or sentence)
                # Look for double newline (paragraph break)
                break_pos = content.rfind("\n\n", current_pos, end_pos)

                if break_pos == -1 or break_pos <= current_pos:
                    # Try single newline
                    break_pos = content.rfind("\n", current_pos, end_pos)

                if break_pos == -1 or break_pos <= current_pos:
                    # Try period followed by space
                    break_pos = content.rfind(". ", current_pos, end_pos)
                    if break_pos != -1:
                        break_pos += 1  # Include the period

                if break_pos != -1 and break_pos > current_pos:
                    end_pos = break_pos

            chunk = content[current_pos:end_pos].strip()
            if chunk:
                chunks.append(chunk)

            current_pos = end_pos

        return chunks if chunks else [content]

    async def _call_ollama_direct(
        self,
        model_id: str,
        prompt: str,
        card_count: int
    ) -> str:
        """
        Call Ollama directly without Agno for better JSON compliance.

        Agno's agent adds system prompts that can confuse the model
        when generating structured JSON output.

        Args:
            model_id: Ollama model name (e.g., "qwen2.5:7b")
            prompt: The generation prompt
            card_count: Number of cards requested (for timeout calculation)

        Returns:
            Raw response text from Ollama
        """
        import httpx

        # Calculate timeout based on card count (more cards = more time)
        timeout = max(120.0, card_count * 15.0)

        logger.info(f"Calling Ollama directly: {model_id} (timeout={timeout}s)")

        # Calculate num_predict based on card count (each card ~200 tokens)
        num_predict = max(4000, card_count * 400)

        logger.info(f"Ollama request: model={model_id}, num_predict={num_predict}, prompt_len={len(prompt)}")

        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": model_id,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.3,  # Slightly higher for variety
                        "num_predict": num_predict,
                        "num_ctx": 8192  # Increase context window
                    }
                }
            )

            if response.status_code != 200:
                logger.error(f"Ollama error: {response.status_code} - {response.text}")
                raise Exception(f"Ollama returned status {response.status_code}")

            result = response.json()
            return result.get("response", "")

    def _parse_cards_json(self, response_text: str) -> List[Dict]:
        """
        Parse cards from LLM response.

        Handles various formats including markdown code blocks.
        Normalizes field names and filters out invalid cards.

        Args:
            response_text: Raw LLM response

        Returns:
            List of card dictionaries with normalized field names
        """
        logger.info(f"Parsing LLM response ({len(response_text)} chars)")
        logger.debug(f"Response preview: {response_text[:500]}...")

        # Try to extract JSON from code blocks
        json_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", response_text, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
            logger.debug("Found JSON in code block")
        else:
            # Try to find JSON object directly
            json_match = re.search(r"\{[\s\S]*\}", response_text)
            if json_match:
                json_str = json_match.group(0)
                logger.debug("Found JSON object directly")
            else:
                logger.error("No JSON found in response")
                logger.error(f"Full response: {response_text}")
                return []

        try:
            data = json.loads(json_str)

            # Handle different response formats
            raw_cards = []
            if isinstance(data, dict):
                if "cards" in data:
                    raw_cards = data["cards"]
                elif "flashcards" in data:
                    raw_cards = data["flashcards"]
                elif "fiches" in data:
                    raw_cards = data["fiches"]
                else:
                    # Single card format
                    raw_cards = [data]
            elif isinstance(data, list):
                raw_cards = data

            logger.info(f"Found {len(raw_cards)} raw cards in response")

            # Normalize and validate cards
            valid_cards = []
            for i, card in enumerate(raw_cards):
                if not isinstance(card, dict):
                    logger.warning(f"Card {i} is not a dict: {type(card)}")
                    continue

                # Normalize field names (handle aliases)
                normalized = self._normalize_card_fields(card)

                # Validate required fields
                front = normalized.get("front", "").strip()
                back = normalized.get("back", "").strip()

                if not front or not back:
                    logger.warning(f"Card {i} has empty front or back, skipping. Keys: {list(card.keys())}")
                    logger.debug(f"Card {i} raw data: {card}")
                    continue

                valid_cards.append(normalized)

            logger.info(f"Validated {len(valid_cards)} cards out of {len(raw_cards)}")
            return valid_cards

        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error: {e}")
            logger.error(f"Raw JSON string: {json_str[:1000]}")
            return []

    def _normalize_card_fields(self, card: Dict) -> Dict:
        """
        Normalize card field names from various formats.

        Handles aliases like:
        - question/answer -> front/back
        - recto/verso -> front/back
        - q/a -> front/back
        - topic/content -> front/back (nested format)

        Args:
            card: Raw card dictionary

        Returns:
            Normalized card dictionary
        """
        # Field mappings (alias -> standard name)
        # LLM sometimes uses creative field names - handle them all
        front_aliases = ["front", "recto", "question", "q", "terme", "term", "topic", "titre", "title", "nom", "name", "sujet", "subject"]
        back_aliases = ["back", "verso", "answer", "a", "reponse", "réponse", "response", "definition", "définition", "content", "contenu", "explanation", "explication", "resume", "résumé", "summary", "description"]

        normalized = {}

        # Find front field
        for alias in front_aliases:
            if alias in card:
                value = card[alias]
                # Handle nested content (e.g., {"topic": "X", "content": [...]})
                if isinstance(value, list):
                    # Join list items
                    normalized["front"] = " ".join(str(v) for v in value)
                else:
                    normalized["front"] = str(value)
                break

        # Find back field
        for alias in back_aliases:
            if alias in card:
                value = card[alias]
                # Handle nested content (e.g., {"content": [{"point": "..."}]})
                if isinstance(value, list):
                    # Extract text from list of dicts or strings
                    parts = []
                    for item in value:
                        if isinstance(item, dict):
                            # Try common keys
                            for key in ["point", "text", "description", "value"]:
                                if key in item:
                                    parts.append(str(item[key]))
                                    break
                            else:
                                # Use first string value
                                for v in item.values():
                                    if isinstance(v, str):
                                        parts.append(v)
                                        break
                        else:
                            parts.append(str(item))
                    normalized["back"] = "\n".join(parts)
                else:
                    normalized["back"] = str(value)
                break

        # Copy other fields as-is
        normalized["card_type"] = card.get("card_type", card.get("type", "question"))
        normalized["source_excerpt"] = card.get("source_excerpt", card.get("extrait", card.get("excerpt")))
        normalized["source_location"] = card.get("source_location", card.get("source", card.get("location")))

        return normalized

    async def generate_summary_audio(
        self,
        deck_id: str,
        deck_name: str,
        course_id: str
    ) -> Optional[str]:
        """
        Generate a summary audio file for all cards in a deck.

        The audio presents all questions with their answers in format:
        "Question 1 : [front] Réponse : [back]. Question 2 : ..."

        Args:
            deck_id: ID of the deck
            deck_name: Name of the deck for the audio file
            course_id: Course ID for storage path

        Returns:
            Path to the generated audio file, or None on error
        """
        try:
            service = get_surreal_service()

            # Normalize deck_id
            if not deck_id.startswith("flashcard_deck:"):
                deck_id = f"flashcard_deck:{deck_id}"

            # Fetch all cards for this deck
            result = await service.query(
                """
                SELECT * FROM flashcard
                WHERE deck_id = $deck_id
                ORDER BY created_at ASC
                """,
                {"deck_id": deck_id}
            )

            if not result or len(result) == 0:
                logger.warning(f"No cards found for deck {deck_id}")
                return None

            # Build the script text
            script_parts = [f"Révision du jeu : {deck_name}.\n\n"]

            for i, card in enumerate(result, 1):
                front = card.get("front", "").strip()
                back = card.get("back", "").strip()

                if front and back:
                    script_parts.append(f"Question {i} : {front}\n")
                    script_parts.append(f"Réponse : {back}\n\n")

            script_parts.append("Fin de la révision.")
            script_text = "".join(script_parts)

            logger.info(f"Generated script with {len(result)} questions ({len(script_text)} chars)")

            # Generate audio using TTS service
            tts_service = TTSService()

            # Create output directory
            course_record_id = course_id.replace("course:", "")
            deck_record_id = deck_id.replace("flashcard_deck:", "")

            audio_dir = Path(settings.upload_dir) / "courses" / course_record_id / "flashcards"
            audio_dir.mkdir(parents=True, exist_ok=True)

            # Generate filename
            safe_name = re.sub(r'[^\w\s-]', '', deck_name).strip().replace(' ', '_')[:50]
            audio_filename = f"{deck_record_id}_{safe_name}_revision.mp3"
            audio_path = audio_dir / audio_filename

            # Generate TTS
            tts_result = await tts_service.text_to_speech(
                text=script_text,
                output_path=str(audio_path),
                voice="fr-CA-SylvieNeural",  # Canadian French voice
                language="fr",
                clean_markdown=False  # Already plain text
            )

            if not tts_result.success:
                logger.error(f"TTS generation failed: {tts_result.error}")
                return None

            # Store audio path in deck
            await service.query(
                """
                UPDATE flashcard_deck
                SET summary_audio_path = $audio_path
                WHERE id = type::thing('flashcard_deck', $deck_id)
                """,
                {
                    "deck_id": deck_record_id,
                    "audio_path": str(audio_path)
                }
            )

            logger.info(f"Summary audio generated: {audio_path}")

            # Create a document record for the audio file so it appears in the documents list
            await self._create_audio_document(
                course_id=course_id,
                deck_name=deck_name,
                audio_path=str(audio_path),
                deck_id=deck_id
            )

            return str(audio_path)

        except Exception as e:
            logger.error(f"Error generating summary audio: {e}", exc_info=True)
            return None

    async def _create_audio_document(
        self,
        course_id: str,
        deck_name: str,
        audio_path: str,
        deck_id: str
    ) -> Optional[str]:
        """
        Create a document record for the flashcard audio file.

        This makes the audio appear in the course's document list,
        allowing users to download it for offline listening.

        Args:
            course_id: Course ID
            deck_name: Name of the flashcard deck
            audio_path: Path to the audio file
            deck_id: Deck ID for reference

        Returns:
            Created document ID or None on error
        """
        try:
            service = get_surreal_service()

            # Normalize IDs
            if not course_id.startswith("course:"):
                course_id = f"course:{course_id}"

            # Get file size
            file_size = Path(audio_path).stat().st_size

            # Generate document ID
            doc_id = uuid.uuid4().hex[:16]

            # Create filename
            safe_name = re.sub(r'[^\w\s-]', '', deck_name).strip().replace(' ', '_')[:30]
            filename = f"Révision audio - {safe_name}.mp3"

            doc_data = {
                "course_id": course_id,
                "nom_fichier": filename,
                "type_fichier": "mp3",
                "type_mime": "audio/mpeg",
                "taille": file_size,
                "file_path": audio_path,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "source_type": "flashcard_audio",
                "is_derived": False,  # Not derived - standalone audio for flashcards
                "indexed": False,
                "flashcard_deck_id": deck_id  # Reference to the deck
            }

            result = await service.query(
                f"CREATE document:{doc_id} CONTENT $data",
                {"data": doc_data}
            )

            if result and len(result) > 0:
                logger.info(f"Created audio document document:{doc_id} for deck {deck_id}")

                # Store document ID in deck for reference
                deck_record_id = deck_id.replace("flashcard_deck:", "")
                await service.query(
                    """
                    UPDATE flashcard_deck
                    SET summary_audio_document_id = $doc_id
                    WHERE id = type::thing('flashcard_deck', $deck_id)
                    """,
                    {
                        "deck_id": deck_record_id,
                        "doc_id": f"document:{doc_id}"
                    }
                )

                return f"document:{doc_id}"

            return None

        except Exception as e:
            logger.error(f"Error creating audio document: {e}", exc_info=True)
            return None


# Singleton instance
_flashcard_service: Optional[FlashcardService] = None


def get_flashcard_service() -> FlashcardService:
    """Get or create the flashcard service singleton."""
    global _flashcard_service
    if _flashcard_service is None:
        _flashcard_service = FlashcardService()
    return _flashcard_service
