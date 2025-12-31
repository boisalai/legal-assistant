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


# Prompt template for flashcard generation - simplified for better JSON compliance
FLASHCARD_GENERATION_PROMPT = """Génère exactement {card_count} fiches de révision en JSON pour un étudiant en droit.

FORMAT JSON REQUIS (copie exactement cette structure):
{{"cards": [{{"card_type": "definition", "front": "Question", "back": "Réponse"}}]}}

Types possibles: {card_types}

Règles:
- definition: terme juridique → définition
- concept: question sur conditions/éléments → explication
- case: jurisprudence → ratio decidendi
- question: question analytique → réponse argumentée

CONTENU SOURCE:
{content}

INSTRUCTIONS:
- front = question courte et claire
- back = réponse en 1-3 phrases maximum
- Réponds UNIQUEMENT avec le JSON
- Commence par {{ et termine par }}

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

        # Combine all content
        combined_content = "\n\n---\n\n".join(all_content)

        # Truncate if too long (keep ~15000 chars for context)
        max_content_length = 15000
        if len(combined_content) > max_content_length:
            combined_content = combined_content[:max_content_length] + "\n\n[... contenu tronqué ...]"

        yield {
            "status": "generating",
            "message": f"Génération de {card_count} fiches en cours..."
        }

        # Format card types for prompt
        card_types_str = ", ".join(card_types)

        # Build prompt
        prompt = FLASHCARD_GENERATION_PROMPT.format(
            card_count=card_count,
            card_types=card_types_str,
            content=combined_content
        )

        try:
            # For Ollama, call directly for better JSON compliance
            # Agno's agent adds extra context that confuses the model
            if "ollama" in model_id.lower():
                response_text = await self._call_ollama_direct(
                    model_id=model_id.replace("ollama:", ""),
                    prompt=prompt,
                    card_count=card_count
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
            logger.info(f"LLM Response length: {len(response_text)} chars")
            logger.info(f"LLM Response preview: {response_text[:1000]}...")
            if len(response_text) > 1000:
                logger.debug(f"LLM Full response: {response_text}")

            yield {
                "status": "parsing",
                "message": "Analyse de la réponse..."
            }

            # Parse JSON from response
            cards = self._parse_cards_json(response_text)

            if not cards:
                # Include preview of response in error for debugging
                preview = response_text[:200] if response_text else "empty"
                logger.error(f"Failed to parse cards from response: {preview}...")
                yield {
                    "status": "error",
                    "message": f"Impossible de parser les fiches générées. Réponse: {preview[:100]}..."
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

        except Exception as e:
            logger.error(f"Error generating flashcards: {e}")
            yield {
                "status": "error",
                "message": f"Erreur lors de la génération: {str(e)}"
            }

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

        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": model_id,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.2,  # Low for consistent JSON
                        "num_predict": 8000  # Enough for 10+ detailed cards
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
            return str(audio_path)

        except Exception as e:
            logger.error(f"Error generating summary audio: {e}", exc_info=True)
            return None


# Singleton instance
_flashcard_service: Optional[FlashcardService] = None


def get_flashcard_service() -> FlashcardService:
    """Get or create the flashcard service singleton."""
    global _flashcard_service
    if _flashcard_service is None:
        _flashcard_service = FlashcardService()
    return _flashcard_service
