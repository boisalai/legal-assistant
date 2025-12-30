"""
Flashcard Generation Service for Legal Assistant.

Generates flashcards from course documents using LLM.
"""

import json
import logging
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import AsyncGenerator, Dict, List, Optional

from agno.agent import Agent

from config.settings import settings
from services.model_factory import create_model
from services.surreal_service import get_surreal_service

logger = logging.getLogger(__name__)


# Prompt template for flashcard generation
FLASHCARD_GENERATION_PROMPT = """Tu es un expert en création de fiches de révision pour des étudiants en droit.

À partir du contenu suivant, génère exactement {card_count} fiches de révision de haute qualité.

**Types de fiches demandés**: {card_types}

**Instructions par type de fiche**:

1. **definition**: Terme juridique → Définition précise avec source
   - Recto: "Qu'est-ce que [terme] ?"
   - Verso: Définition claire et concise

2. **concept**: Question conceptuelle → Explication structurée
   - Recto: Question sur un concept (conditions, éléments, critères)
   - Verso: Liste numérotée ou explication structurée

3. **case**: Jurisprudence → Ratio decidendi
   - Recto: "Quel est le ratio de [nom de l'arrêt] ?"
   - Verso: Principe juridique établi par la décision

4. **question**: Question de compréhension → Réponse argumentée
   - Recto: Question analytique ou de mise en situation
   - Verso: Réponse avec raisonnement juridique

**RÈGLES IMPORTANTES**:
- Chaque fiche doit être autonome et compréhensible sans contexte
- Le verso doit être concis mais complet (max 3-4 phrases)
- Inclure la source (nom du fichier, section) quand possible
- Varier les niveaux de difficulté
- Privilégier les concepts clés et fréquemment testés en examen

**FORMAT DE SORTIE** (JSON strict):
```json
{{
  "cards": [
    {{
      "card_type": "definition|concept|case|question",
      "front": "Question ou terme (recto)",
      "back": "Réponse ou définition (verso)",
      "source_excerpt": "Citation courte du texte source (optionnel)",
      "source_location": "Nom du fichier ou section"
    }}
  ]
}}
```

**CONTENU SOURCE**:
---
{content}
---

Génère maintenant exactement {card_count} fiches de révision en JSON. Réponds UNIQUEMENT avec le JSON, sans texte avant ou après."""


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
            # Create model and agent
            model = create_model(model_id)

            agent = Agent(
                name="FlashcardGenerator",
                model=model,
                instructions="Tu génères des fiches de révision en JSON. Réponds uniquement avec du JSON valide.",
                markdown=False
            )

            # Run the agent
            response = await agent.arun(prompt)

            # Extract response content
            response_text = ""
            if hasattr(response, "content"):
                response_text = response.content
            elif isinstance(response, str):
                response_text = response
            else:
                response_text = str(response)

            yield {
                "status": "parsing",
                "message": "Analyse de la réponse..."
            }

            # Parse JSON from response
            cards = self._parse_cards_json(response_text)

            if not cards:
                yield {
                    "status": "error",
                    "message": "Impossible de parser les fiches générées"
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

    def _parse_cards_json(self, response_text: str) -> List[Dict]:
        """
        Parse cards from LLM response.

        Handles various formats including markdown code blocks.

        Args:
            response_text: Raw LLM response

        Returns:
            List of card dictionaries
        """
        # Try to extract JSON from code blocks
        json_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", response_text, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
        else:
            # Try to find JSON object directly
            json_match = re.search(r"\{[\s\S]*\}", response_text)
            if json_match:
                json_str = json_match.group(0)
            else:
                logger.error("No JSON found in response")
                return []

        try:
            data = json.loads(json_str)

            # Handle different response formats
            if isinstance(data, dict):
                if "cards" in data:
                    return data["cards"]
                elif "flashcards" in data:
                    return data["flashcards"]
                else:
                    # Single card format
                    return [data]
            elif isinstance(data, list):
                return data

            return []

        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error: {e}")
            logger.debug(f"Raw JSON string: {json_str[:500]}")
            return []


# Singleton instance
_flashcard_service: Optional[FlashcardService] = None


def get_flashcard_service() -> FlashcardService:
    """Get or create the flashcard service singleton."""
    global _flashcard_service
    if _flashcard_service is None:
        _flashcard_service = FlashcardService()
    return _flashcard_service
