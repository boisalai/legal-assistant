"""
Flashcard Generation Service for Legal Assistant.

Generates flashcards from course documents using LLM.
"""

import asyncio
import json
import logging
import os
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

logger = logging.getLogger(__name__)


# Prompt template for flashcard generation - optimized for exam preparation
FLASHCARD_GENERATION_PROMPT = """Tu es un expert en pédagogie créant des fiches de révision pour un examen universitaire.

OBJECTIF: Générer {card_count} fiches DIVERSIFIÉES couvrant les concepts clés du contenu ci-dessous.

TYPES DE QUESTIONS À VARIER (utilise au moins 3 types différents):
- DÉFINITION: "Qu'est-ce que [concept]?" → définition précise
- APPLICATION: "Dans quel cas utilise-t-on [concept]?" → contexte pratique
- COMPARAISON: "Quelle différence entre [A] et [B]?" → distinction claire
- CAUSE-EFFET: "Pourquoi [phénomène] se produit-il?" → explication causale
- EXEMPLE: "Donnez un exemple de [concept]" → illustration concrète
- PROCÉDURE: "Quelles sont les étapes de [processus]?" → séquence ordonnée

DOCUMENT SOURCE: {document_name}
---
{content}
---

RÈGLES DE DIVERSITÉ:
1. Couvre TOUS les thèmes/sections importants du document
2. Varie les types de questions (pas 2 définitions consécutives)
3. Priorise les concepts susceptibles d'être à l'examen
4. Évite les questions triviales ou trop évidentes
5. Chaque réponse doit être autonome (compréhensible sans la question)

FORMAT JSON REQUIS:
{{"cards": [
  {{"front": "Question claire?", "back": "Réponse complète en 1-3 phrases.", "theme": "thème/section"}},
  ...
]}}

IMPORTANT:
- Génère EXACTEMENT {card_count} fiches
- Réponds UNIQUEMENT avec le JSON valide
- Inclus le champ "theme" pour chaque fiche

JSON:"""


# French voices for alternating in summary audio (avoiding monotony)
# Using a mix of Canadian, French, Belgian and Swiss voices
FRENCH_VOICES_FOR_ALTERNATING = [
    "fr-CA-SylvieNeural",      # Female - Canada
    "fr-CA-ThierryNeural",     # Male - Canada
    "fr-CA-AntoineNeural",     # Male - Canada
    "fr-FR-DeniseNeural",      # Female - France
    "fr-FR-HenriNeural",       # Male - France
    "fr-BE-CharlineNeural",    # Female - Belgium
    "fr-CH-ArianeNeural",      # Female - Switzerland
    "fr-FR-EloiseNeural",      # Female - France
]


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
        card_count: int = 50,
        model_id: Optional[str] = None
    ) -> AsyncGenerator[Dict, None]:
        """
        Generate flashcards from documents using LLM.

        Processes each document individually to maintain source attribution
        and ensure diverse coverage across all source materials.

        Args:
            deck_id: ID of the deck to add cards to
            source_document_ids: List of document IDs to generate from
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

        # Collect document contents with metadata
        documents_data = []
        source_docs_info = []
        total_content_length = 0

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

            doc_data = {
                "doc_id": str(doc.get("id", doc_id)),
                "name": filename,
                "content": content,
                "length": len(content)
            }
            documents_data.append(doc_data)
            total_content_length += len(content)

            source_docs_info.append({
                "doc_id": doc_data["doc_id"],
                "name": filename
            })

            yield {
                "status": "loading",
                "message": f"Document chargé: {filename}"
            }

        if not documents_data:
            yield {
                "status": "error",
                "message": "Aucun contenu trouvé dans les documents sélectionnés"
            }
            return

        logger.info(f"Loaded {len(documents_data)} documents, total {total_content_length} chars")

        # Distribute cards proportionally across documents based on content length
        # Minimum 3 cards per document to ensure coverage
        cards_distribution = self._distribute_cards_by_document(
            documents_data, card_count, min_cards_per_doc=3
        )

        yield {
            "status": "generating",
            "message": f"Génération de {card_count} fiches depuis {len(documents_data)} documents..."
        }

        # Generate cards for each document separately
        all_cards = []
        docs_processed = 0

        for doc_data, doc_card_count in zip(documents_data, cards_distribution):
            docs_processed += 1
            doc_name = doc_data["name"]
            doc_id = doc_data["doc_id"]

            yield {
                "status": "generating",
                "message": f"Document {docs_processed}/{len(documents_data)}: {doc_name} ({doc_card_count} fiches)..."
            }

            # Split document content into chunks if needed
            chunk_size = 6000  # Slightly larger chunks for better context
            chunks = self._split_content_into_chunks(doc_data["content"], chunk_size)

            # Distribute this document's cards across its chunks
            cards_per_chunk = max(3, min(15, doc_card_count // max(1, len(chunks))))
            remaining_doc_cards = doc_card_count

            for chunk_idx, chunk_content in enumerate(chunks):
                if remaining_doc_cards <= 0:
                    break

                # Last chunk gets remaining cards
                chunk_cards = min(cards_per_chunk, remaining_doc_cards)
                if chunk_idx == len(chunks) - 1:
                    chunk_cards = remaining_doc_cards
                remaining_doc_cards -= chunk_cards

                # Build prompt with document name for context
                prompt = FLASHCARD_GENERATION_PROMPT.format(
                    card_count=chunk_cards,
                    document_name=doc_name,
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
                            instructions="Tu génères des fiches de révision diversifiées en JSON.",
                            markdown=False
                        )
                        response = await agent.arun(prompt)
                        response_text = response.content if hasattr(response, "content") else str(response)

                    # Parse JSON from response
                    chunk_parsed_cards = self._parse_cards_json(response_text)

                    if chunk_parsed_cards:
                        # Add source document info to each card
                        for card in chunk_parsed_cards:
                            card["source_doc_id"] = doc_id
                            card["source_doc_name"] = doc_name
                        all_cards.extend(chunk_parsed_cards)
                        logger.info(f"Doc '{doc_name}' chunk {chunk_idx + 1}: {len(chunk_parsed_cards)} cards")
                    else:
                        logger.warning(f"Doc '{doc_name}' chunk {chunk_idx + 1}: No cards parsed")

                except Exception as e:
                    logger.error(f"Error generating cards for {doc_name} chunk {chunk_idx + 1}: {e}")

        yield {
            "status": "deduplicating",
            "message": f"Déduplication de {len(all_cards)} fiches..."
        }

        # Deduplicate similar cards
        unique_cards = self._deduplicate_cards(all_cards)
        duplicates_removed = len(all_cards) - len(unique_cards)

        if duplicates_removed > 0:
            logger.info(f"Removed {duplicates_removed} duplicate cards")
            yield {
                "status": "deduplicating",
                "message": f"{duplicates_removed} doublons supprimés, {len(unique_cards)} fiches uniques"
            }

        if not unique_cards:
            logger.error("No cards generated from any document")
            yield {
                "status": "error",
                "message": "Impossible de générer des fiches depuis le contenu fourni"
            }
            return

        yield {
            "status": "saving",
            "message": f"Sauvegarde de {len(unique_cards)} fiches..."
        }

        # Save cards to database
        service = get_surreal_service()
        deck_record_id = deck_id.replace("flashcard_deck:", "")

        saved_count = 0
        for card in unique_cards:
            try:
                card_id = uuid.uuid4().hex[:8]

                card_data = {
                    "deck_id": f"flashcard_deck:{deck_record_id}",
                    "document_id": card.get("source_doc_id", ""),
                    "document_name": card.get("source_doc_name", ""),
                    "front": card.get("front", ""),
                    "back": card.get("back", ""),
                    "theme": card.get("theme"),  # New field for topic tracking
                    "source_excerpt": card.get("source_excerpt"),
                    "source_location": card.get("source_location"),
                    "created_at": datetime.now(timezone.utc).isoformat()
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
                SET source_documents = $source_docs
                WHERE id = type::thing('flashcard_deck', $deck_id)
                """,
                {
                    "deck_id": deck_record_id,
                    "source_docs": source_docs_info
                }
            )
        except Exception as e:
            logger.warning(f"Could not update deck metadata: {e}")

        yield {
            "status": "completed",
            "message": f"Génération terminée: {saved_count} fiches créées depuis {len(documents_data)} documents",
            "cards_generated": saved_count
        }

    def _distribute_cards_by_document(
        self,
        documents_data: List[Dict],
        total_cards: int,
        min_cards_per_doc: int = 3
    ) -> List[int]:
        """
        Distribute cards proportionally across documents based on content length.

        Ensures each document gets at least min_cards_per_doc cards for coverage.

        Args:
            documents_data: List of document data with 'length' field
            total_cards: Total number of cards to generate
            min_cards_per_doc: Minimum cards per document

        Returns:
            List of card counts, one per document
        """
        num_docs = len(documents_data)
        if num_docs == 0:
            return []

        # Ensure minimum cards per document
        min_total = min_cards_per_doc * num_docs
        if total_cards < min_total:
            # Distribute evenly if not enough cards for minimum
            base = total_cards // num_docs
            remainder = total_cards % num_docs
            return [base + (1 if i < remainder else 0) for i in range(num_docs)]

        # Calculate proportional distribution
        total_length = sum(d["length"] for d in documents_data)
        distribution = []

        for doc in documents_data:
            proportion = doc["length"] / total_length if total_length > 0 else 1 / num_docs
            doc_cards = max(min_cards_per_doc, int(total_cards * proportion))
            distribution.append(doc_cards)

        # Adjust to match total_cards exactly
        current_total = sum(distribution)
        diff = total_cards - current_total

        if diff > 0:
            # Add extra cards to largest documents
            sorted_indices = sorted(range(num_docs), key=lambda i: documents_data[i]["length"], reverse=True)
            for i in range(diff):
                distribution[sorted_indices[i % num_docs]] += 1
        elif diff < 0:
            # Remove cards from smallest documents (but keep minimum)
            sorted_indices = sorted(range(num_docs), key=lambda i: documents_data[i]["length"])
            for i in range(-diff):
                idx = sorted_indices[i % num_docs]
                if distribution[idx] > min_cards_per_doc:
                    distribution[idx] -= 1

        return distribution

    def _deduplicate_cards(self, cards: List[Dict], similarity_threshold: float = 0.8) -> List[Dict]:
        """
        Remove duplicate or very similar cards based on question similarity.

        Uses simple word overlap ratio for efficiency.

        Args:
            cards: List of card dictionaries
            similarity_threshold: Threshold for considering cards as duplicates (0-1)

        Returns:
            List of unique cards
        """
        if not cards:
            return []

        unique_cards = []
        seen_questions = []

        for card in cards:
            question = card.get("front", "").lower().strip()
            if not question:
                continue

            # Check similarity with existing questions
            is_duplicate = False
            question_words = set(question.split())

            for seen_q in seen_questions:
                seen_words = set(seen_q.split())

                # Calculate Jaccard similarity
                if question_words and seen_words:
                    intersection = len(question_words & seen_words)
                    union = len(question_words | seen_words)
                    similarity = intersection / union if union > 0 else 0

                    if similarity >= similarity_threshold:
                        is_duplicate = True
                        logger.debug(f"Duplicate found: '{question[:50]}...' similar to '{seen_q[:50]}...'")
                        break

            if not is_duplicate:
                unique_cards.append(card)
                seen_questions.append(question)

        return unique_cards

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
        normalized["source_excerpt"] = card.get("source_excerpt", card.get("extrait", card.get("excerpt")))
        normalized["source_location"] = card.get("source_location", card.get("source", card.get("location")))

        # Handle theme field (for tracking topic diversity)
        # Note: "topic" is excluded as it may be used for front field
        theme_aliases = ["theme", "thème", "section", "chapitre", "chapter", "category", "catégorie"]
        for alias in theme_aliases:
            if alias in card:
                normalized["theme"] = str(card[alias])
                break

        return normalized

    async def generate_summary_audio(
        self,
        deck_id: str,
        deck_name: str,
        course_id: str
    ) -> Optional[str]:
        """
        Generate a summary audio file for all cards in a deck with alternating voices.

        The audio presents all questions with their answers in format:
        "Question 1 : [front] Réponse : [back]. Question 2 : ..."

        Each question uses a different voice from the pool to avoid monotony.

        Args:
            deck_id: ID of the deck
            deck_name: Name of the deck for the audio file
            course_id: Course ID for storage path

        Returns:
            Path to the generated audio file, or None on error
        """
        temp_dir = None
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

            logger.info(f"Generating summary audio for {len(result)} cards with alternating voices")

            # Generate audio using TTS service
            tts_service = TTSService()

            # Create output directory
            course_record_id = course_id.replace("course:", "")
            deck_record_id = deck_id.replace("flashcard_deck:", "")

            audio_dir = Path(settings.upload_dir) / "courses" / course_record_id / "flashcards"
            audio_dir.mkdir(parents=True, exist_ok=True)

            # Create temp directory for audio segments
            temp_dir = tempfile.mkdtemp(prefix="flashcard_audio_")
            segment_files = []

            # Generate intro segment
            intro_text = f"Révision du jeu : {deck_name}."
            intro_path = os.path.join(temp_dir, "000_intro.mp3")
            intro_result = await tts_service.text_to_speech(
                text=intro_text,
                output_path=intro_path,
                voice=FRENCH_VOICES_FOR_ALTERNATING[0],
                language="fr",
                clean_markdown=False
            )
            if intro_result.success:
                segment_files.append(intro_path)

            # Generate audio segments for each Q&A with alternating voices
            num_voices = len(FRENCH_VOICES_FOR_ALTERNATING)

            for i, card in enumerate(result, 1):
                front = card.get("front", "").strip()
                back = card.get("back", "").strip()

                if not front or not back:
                    continue

                # Select voice for this question (rotate through voices)
                voice = FRENCH_VOICES_FOR_ALTERNATING[i % num_voices]

                # Generate question segment
                question_text = f"Question {i}. {front}"
                question_path = os.path.join(temp_dir, f"{i:03d}_q.mp3")
                q_result = await tts_service.text_to_speech(
                    text=question_text,
                    output_path=question_path,
                    voice=voice,
                    language="fr",
                    clean_markdown=False
                )
                if q_result.success:
                    segment_files.append(question_path)

                # Generate answer segment (same voice for coherence)
                answer_text = f"Réponse. {back}"
                answer_path = os.path.join(temp_dir, f"{i:03d}_a.mp3")
                a_result = await tts_service.text_to_speech(
                    text=answer_text,
                    output_path=answer_path,
                    voice=voice,
                    language="fr",
                    clean_markdown=False
                )
                if a_result.success:
                    segment_files.append(answer_path)

            # Generate outro segment
            outro_text = "Fin de la révision."
            outro_path = os.path.join(temp_dir, "999_outro.mp3")
            outro_result = await tts_service.text_to_speech(
                text=outro_text,
                output_path=outro_path,
                voice=FRENCH_VOICES_FOR_ALTERNATING[0],
                language="fr",
                clean_markdown=False
            )
            if outro_result.success:
                segment_files.append(outro_path)

            if len(segment_files) < 2:
                logger.error("Not enough audio segments generated")
                return None

            logger.info(f"Generated {len(segment_files)} audio segments, concatenating with ffmpeg")

            # Create concat file for ffmpeg
            concat_file = os.path.join(temp_dir, "concat.txt")
            with open(concat_file, "w") as f:
                for seg_file in segment_files:
                    # Escape single quotes in path for ffmpeg
                    escaped_path = seg_file.replace("'", "'\\''")
                    f.write(f"file '{escaped_path}'\n")

            # Generate final filename
            safe_name = re.sub(r'[^\w\s-]', '', deck_name).strip().replace(' ', '_')[:50]
            audio_filename = f"{deck_record_id}_{safe_name}_revision.mp3"
            audio_path = audio_dir / audio_filename

            # Concatenate with ffmpeg
            ffmpeg_cmd = [
                "ffmpeg", "-y",  # Overwrite output
                "-f", "concat",
                "-safe", "0",
                "-i", concat_file,
                "-c", "copy",  # Copy codec (no re-encoding)
                str(audio_path)
            ]

            proc = await asyncio.create_subprocess_exec(
                *ffmpeg_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            stdout, stderr = await proc.communicate()

            if proc.returncode != 0:
                logger.error(f"ffmpeg concatenation failed: {stderr.decode()}")
                return None

            logger.info(f"Summary audio generated with alternating voices: {audio_path}")

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

        finally:
            # Clean up temp directory
            if temp_dir and os.path.exists(temp_dir):
                try:
                    shutil.rmtree(temp_dir)
                except Exception as cleanup_error:
                    logger.warning(f"Failed to clean up temp dir: {cleanup_error}")

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
