"""
Routes for flashcard management.

Endpoints:
- POST /api/courses/{course_id}/flashcard-decks - Create a deck
- GET /api/courses/{course_id}/flashcard-decks - List course decks
- GET /api/flashcard-decks/{deck_id} - Deck details
- DELETE /api/flashcard-decks/{deck_id} - Delete a deck
- POST /api/flashcard-decks/{deck_id}/generate - Generate cards (streaming SSE)
- GET /api/flashcard-decks/{deck_id}/cards - List deck cards
- GET /api/flashcard-decks/{deck_id}/study - Study session
- POST /api/flashcards/{card_id}/tts - Generate TTS audio
"""

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional, List

from fastapi import APIRouter, HTTPException, status, Query
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel

from services.surreal_service import get_surreal_service
from services.flashcard_service import get_flashcard_service
from models.flashcard_models import (
    FlashcardDeckCreate,
    FlashcardDeckResponse,
    FlashcardDeckListResponse,
    FlashcardResponse,
    FlashcardListResponse,
    StudySessionResponse,
    TTSRequest,
    TTSResponse,
    SourceDocument,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Flashcards"])


# ============================================================================
# Helper Functions
# ============================================================================

def generate_hex_id() -> str:
    """Generate a short hexadecimal ID compatible with SurrealDB."""
    return uuid.uuid4().hex[:8]


async def get_deck_by_id(service, deck_id: str) -> Optional[dict]:
    """Retrieve a deck by its ID."""
    record_id = deck_id.replace("flashcard_deck:", "")

    result = await service.query(
        "SELECT * FROM flashcard_deck WHERE id = type::thing('flashcard_deck', $record_id)",
        {"record_id": record_id}
    )

    # SurrealDB returns a list of dicts directly
    if result and len(result) > 0:
        return result[0]
    return None


async def get_deck_card_count(service, deck_id: str) -> int:
    """Count the number of cards in a deck."""
    # Normalize deck_id (with prefix)
    if not deck_id.startswith("flashcard_deck:"):
        deck_id = f"flashcard_deck:{deck_id}"

    result = await service.query(
        "SELECT count() as total FROM flashcard WHERE deck_id = $deck_id GROUP ALL",
        {"deck_id": deck_id}
    )

    if result and len(result) > 0:
        return result[0].get("total", 0)
    return 0


def format_deck_response(deck: dict, total_cards: int) -> FlashcardDeckResponse:
    """Format a deck for API response."""
    # Parse source_documents
    source_docs = []
    raw_sources = deck.get("source_documents", [])
    if raw_sources:
        for src in raw_sources:
            if isinstance(src, dict):
                source_docs.append(SourceDocument(
                    doc_id=src.get("doc_id", ""),
                    name=src.get("name", ""),
                    relative_path=src.get("relative_path")
                ))

    # Format dates
    created_at = deck.get("created_at", "")
    if hasattr(created_at, "isoformat"):
        created_at = created_at.isoformat()

    deck_id = deck.get("id", "")
    if hasattr(deck_id, "__str__"):
        deck_id = str(deck_id)

    # Check if summary audio exists
    summary_audio_path = deck.get("summary_audio_path")
    has_summary_audio = bool(summary_audio_path)

    return FlashcardDeckResponse(
        id=deck_id,
        course_id=str(deck.get("course_id", "")),
        name=deck.get("name", ""),
        source_documents=source_docs,
        total_cards=total_cards,
        created_at=created_at,
        has_summary_audio=has_summary_audio
    )


def format_card_response(card: dict) -> FlashcardResponse:
    """Format a card for API response."""
    created_at = card.get("created_at", "")
    if hasattr(created_at, "isoformat"):
        created_at = created_at.isoformat()

    card_id = card.get("id", "")
    if hasattr(card_id, "__str__"):
        card_id = str(card_id)

    return FlashcardResponse(
        id=card_id,
        deck_id=str(card.get("deck_id", "")),
        document_id=str(card.get("document_id", "")),
        front=card.get("front", ""),
        back=card.get("back", ""),
        source_excerpt=card.get("source_excerpt"),
        source_location=card.get("source_location"),
        created_at=created_at
    )


# ============================================================================
# Deck Endpoints
# ============================================================================

@router.post(
    "/api/courses/{course_id}/flashcard-decks",
    response_model=FlashcardDeckResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a study deck"
)
async def create_flashcard_deck(course_id: str, request: FlashcardDeckCreate):
    """
    Create a new flashcard deck.

    Cards will be generated later via the generation endpoint.
    """
    service = get_surreal_service()

    # Verify that the course exists
    course_record_id = course_id.replace("course:", "")
    course_result = await service.query(
        "SELECT id FROM course WHERE id = type::thing('course', $record_id)",
        {"record_id": course_record_id}
    )

    if not course_result or len(course_result) == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cours non trouvé: {course_id}"
        )

    # Retrieve source document information
    source_documents = []
    for doc_id in request.source_document_ids:
        doc_record_id = doc_id.replace("document:", "")
        doc_result = await service.query(
            "SELECT id, filename, linked_source FROM document WHERE id = type::thing('document', $record_id)",
            {"record_id": doc_record_id}
        )

        # SurrealDB returns a list of dicts directly
        if doc_result and len(doc_result) > 0:
            doc = doc_result[0]
            relative_path = None
            linked_source = doc.get("linked_source")
            if linked_source:
                relative_path = linked_source.get("relative_path")

            # Use filename or relative_path as name
            filename = doc.get("filename") or relative_path or doc_id

            source_documents.append({
                "doc_id": str(doc.get("id", doc_id)),
                "name": filename,
                "relative_path": relative_path
            })

    if not source_documents:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Aucun document source valide trouvé"
        )

    # Create the deck
    deck_id = generate_hex_id()
    now = datetime.now(timezone.utc)

    deck_data = {
        "course_id": f"course:{course_record_id}",
        "name": request.name,
        "source_documents": source_documents,
        "card_count_requested": request.card_count,
        "generate_audio": request.generate_audio,
        "created_at": now.isoformat(),
        "last_studied": None
    }

    result = await service.query(
        f"CREATE flashcard_deck:{deck_id} CONTENT $data",
        {"data": deck_data}
    )

    if not result or len(result) == 0:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de la création du deck"
        )

    created_deck = result[0]
    total_cards = await get_deck_card_count(service, f"flashcard_deck:{deck_id}")

    logger.info(f"Deck created: {deck_id} for course {course_id} with {len(source_documents)} documents")

    return format_deck_response(created_deck, total_cards)


@router.get(
    "/api/courses/{course_id}/flashcard-decks",
    response_model=FlashcardDeckListResponse,
    summary="List course decks"
)
async def list_flashcard_decks(course_id: str):
    """List all study decks for a course."""
    service = get_surreal_service()

    # Normalize course_id (with or without prefix)
    if not course_id.startswith("course:"):
        course_id = f"course:{course_id}"

    result = await service.query(
        """
        SELECT * FROM flashcard_deck
        WHERE course_id = $course_id
        ORDER BY created_at DESC
        """,
        {"course_id": course_id}
    )

    decks = []
    if result and len(result) > 0:
        for deck in result:
            deck_id = str(deck.get("id", ""))
            total_cards = await get_deck_card_count(service, deck_id)
            decks.append(format_deck_response(deck, total_cards))

    return FlashcardDeckListResponse(decks=decks, total=len(decks))


@router.get(
    "/api/flashcard-decks/{deck_id}",
    response_model=FlashcardDeckResponse,
    summary="Deck details"
)
async def get_flashcard_deck(deck_id: str):
    """Retrieve deck details."""
    service = get_surreal_service()

    deck = await get_deck_by_id(service, deck_id)
    if not deck:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Deck non trouvé: {deck_id}"
        )

    total_cards = await get_deck_card_count(service, deck_id)
    return format_deck_response(deck, total_cards)


@router.delete(
    "/api/flashcard-decks/{deck_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a deck"
)
async def delete_flashcard_deck(deck_id: str):
    """Delete a deck and all its cards."""
    import os

    service = get_surreal_service()

    deck = await get_deck_by_id(service, deck_id)
    if not deck:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Deck non trouvé: {deck_id}"
        )

    record_id = deck_id.replace("flashcard_deck:", "")

    # Normalize deck_id for string comparison
    full_deck_id = f"flashcard_deck:{record_id}"

    # Delete all cards from the deck (deck_id is stored as string)
    await service.query(
        "DELETE flashcard WHERE deck_id = $deck_id",
        {"deck_id": full_deck_id}
    )

    # Delete associated audio document if it exists
    summary_audio_doc_id = deck.get("summary_audio_document_id")
    if summary_audio_doc_id:
        doc_record_id = summary_audio_doc_id.replace("document:", "")
        await service.query(
            "DELETE document WHERE id = type::thing('document', $doc_id)",
            {"doc_id": doc_record_id}
        )
        logger.info(f"Audio document deleted: {summary_audio_doc_id}")

    # Delete audio file from disk if it exists
    summary_audio_path = deck.get("summary_audio_path")
    if summary_audio_path and os.path.exists(summary_audio_path):
        try:
            os.remove(summary_audio_path)
            logger.info(f"Audio file deleted: {summary_audio_path}")
        except Exception as e:
            logger.warning(f"Error deleting audio file: {e}")

    # Delete the deck
    await service.query(
        "DELETE flashcard_deck WHERE id = type::thing('flashcard_deck', $deck_id)",
        {"deck_id": record_id}
    )

    logger.info(f"Deck deleted: {deck_id}")
    return None


# ============================================================================
# Card Endpoints
# ============================================================================

@router.get(
    "/api/flashcard-decks/{deck_id}/cards",
    response_model=FlashcardListResponse,
    summary="List deck cards"
)
async def list_flashcards(deck_id: str):
    """List all cards in a deck."""
    service = get_surreal_service()

    deck = await get_deck_by_id(service, deck_id)
    if not deck:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Deck non trouvé: {deck_id}"
        )

    # Normalize deck_id
    if not deck_id.startswith("flashcard_deck:"):
        deck_id = f"flashcard_deck:{deck_id}"

    result = await service.query(
        "SELECT * FROM flashcard WHERE deck_id = $deck_id ORDER BY created_at ASC",
        {"deck_id": deck_id}
    )

    cards = []
    if result and len(result) > 0:
        for card in result:
            cards.append(format_card_response(card))

    return FlashcardListResponse(cards=cards, total=len(cards))


@router.get(
    "/api/flashcard-decks/{deck_id}/study",
    response_model=StudySessionResponse,
    summary="Start a study session"
)
async def start_study_session(deck_id: str):
    """Retrieve cards for a study session."""
    service = get_surreal_service()

    deck = await get_deck_by_id(service, deck_id)
    if not deck:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Deck non trouvé: {deck_id}"
        )

    # Normalize deck_id (with prefix)
    if not deck_id.startswith("flashcard_deck:"):
        deck_id = f"flashcard_deck:{deck_id}"

    # Retrieve all cards
    result = await service.query(
        "SELECT * FROM flashcard WHERE deck_id = $deck_id ORDER BY created_at ASC",
        {"deck_id": deck_id}
    )

    cards = []
    if result and len(result) > 0:
        for card in result:
            cards.append(format_card_response(card))

    return StudySessionResponse(
        deck_id=deck_id,
        deck_name=deck.get("name", ""),
        cards=cards,
        total_cards=len(cards)
    )


# ============================================================================
# TTS Endpoint
# ============================================================================

@router.post(
    "/api/flashcards/{card_id}/tts",
    response_model=TTSResponse,
    summary="Generate card audio"
)
async def generate_flashcard_tts(card_id: str, request: TTSRequest):
    """
    Generate TTS audio for the front or back of a card.

    Available voices (Canadian French):
    - fr-CA-SylvieNeural (female, default)
    - fr-CA-AntoineNeural (male)
    - fr-CA-JeanNeural (male)
    - fr-CA-ThierryNeural (male)
    """
    service = get_surreal_service()

    record_id = card_id.replace("flashcard:", "")

    # Retrieve the card
    result = await service.query(
        "SELECT * FROM flashcard WHERE id = type::thing('flashcard', $card_id)",
        {"card_id": record_id}
    )

    if not result or len(result) == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Fiche non trouvée: {card_id}"
        )

    card = result[0]

    # Get the text to synthesize
    if request.side == "front":
        text = card.get("front", "")
    else:
        text = card.get("back", "")

    if not text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Pas de texte à synthétiser pour le côté {request.side}"
        )

    # Generate audio with TTS service
    try:
        from services.tts_service import TTSService

        tts_service = TTSService()

        # Create a temporary file for audio
        import tempfile
        import os

        temp_dir = tempfile.gettempdir()
        audio_filename = f"flashcard_{record_id}_{request.side}.mp3"
        audio_path = os.path.join(temp_dir, audio_filename)

        # Generate audio
        tts_result = await tts_service.text_to_speech(
            text=text,
            output_path=audio_path,
            voice=request.voice,
            language="fr",
            clean_markdown=False  # Flashcard text is not markdown
        )

        if not tts_result.success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Erreur TTS: {tts_result.error}"
            )

        # Return relative URL for frontend
        # Note: In production, could use a CDN or S3 storage
        return TTSResponse(
            audio_url=f"/api/flashcards/{card_id}/audio/{request.side}",
            voice=request.voice,
            duration=tts_result.duration
        )

    except ImportError:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Service TTS non disponible"
        )
    except Exception as e:
        logger.error(f"TTS error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la génération audio: {str(e)}"
        )


@router.get(
    "/api/flashcards/{card_id}/audio/{side}",
    summary="Get card audio"
)
async def get_flashcard_audio(card_id: str, side: str):
    """Return the generated audio file for a card."""
    import tempfile
    import os

    if side not in ["front", "back"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Le côté doit être 'front' ou 'back'"
        )

    record_id = card_id.replace("flashcard:", "")
    temp_dir = tempfile.gettempdir()
    audio_path = os.path.join(temp_dir, f"flashcard_{record_id}_{side}.mp3")

    if not os.path.exists(audio_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Audio non trouvé. Veuillez d'abord générer l'audio."
        )

    return FileResponse(
        audio_path,
        media_type="audio/mpeg",
        filename=f"flashcard_{record_id}_{side}.mp3"
    )


@router.get(
    "/api/flashcard-decks/{deck_id}/summary-audio",
    summary="Get deck summary audio"
)
async def get_deck_summary_audio(deck_id: str):
    """Return the summary audio file for a deck (all Q&A)."""
    service = get_surreal_service()

    deck = await get_deck_by_id(service, deck_id)
    if not deck:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Deck non trouvé: {deck_id}"
        )

    audio_path = deck.get("summary_audio_path")
    if not audio_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Aucun audio récapitulatif généré pour ce deck"
        )

    import os
    if not os.path.exists(audio_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Fichier audio non trouvé sur le serveur"
        )

    deck_name = deck.get("name", "revision")
    safe_name = deck_name.replace(" ", "_")[:30]

    return FileResponse(
        audio_path,
        media_type="audio/mpeg",
        filename=f"{safe_name}_revision.mp3"
    )


# ============================================================================
# Generation Endpoint
# ============================================================================

class GenerateRequest(BaseModel):
    """Request for generating flashcards."""
    model_id: Optional[str] = None


@router.post(
    "/api/flashcard-decks/{deck_id}/generate",
    summary="Generate deck cards"
)
async def generate_flashcards(deck_id: str, request: Optional[GenerateRequest] = None):
    """
    Generate flashcards for an existing deck.

    Uses LLM to analyze source documents and create cards.
    Returns an SSE stream with progress.
    """
    service = get_surreal_service()

    # Retrieve the deck
    deck = await get_deck_by_id(service, deck_id)
    if not deck:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Deck non trouvé: {deck_id}"
        )

    # Retrieve deck information
    source_docs = deck.get("source_documents", [])
    card_count = deck.get("card_count_requested", 50)
    generate_audio = deck.get("generate_audio", False)
    deck_name = deck.get("name", "Review")
    course_id = deck.get("course_id", "")

    # If no source_documents, retrieve from creation
    if not source_docs:
        logger.warning(f"No source_documents in deck {deck_id}, using fallback")

    # Extract doc_ids
    source_doc_ids = []
    if source_docs:
        for doc in source_docs:
            if isinstance(doc, dict):
                source_doc_ids.append(doc.get("doc_id", ""))
            elif isinstance(doc, str):
                source_doc_ids.append(doc)

    if not source_doc_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Aucun document source trouvé pour ce deck"
        )

    # Model ID
    model_id = request.model_id if request else None

    async def event_stream():
        """Generate SSE events for progress updates."""
        flashcard_service = get_flashcard_service()
        generation_success = False
        cards_generated = 0

        try:
            async for update in flashcard_service.generate_flashcards(
                deck_id=deck_id,
                source_document_ids=source_doc_ids,
                card_count=card_count,
                model_id=model_id
            ):
                yield f"data: {json.dumps(update)}\n\n"

                # Track completion status
                if update.get("status") == "completed":
                    generation_success = True
                    cards_generated = update.get("cards_generated", 0)

            # Generate summary audio if requested and generation was successful
            if generate_audio and generation_success and cards_generated > 0:
                yield f"data: {json.dumps({'status': 'audio', 'message': 'Génération de l audio récapitulatif...'})}\n\n"

                try:
                    audio_path = await flashcard_service.generate_summary_audio(
                        deck_id=deck_id,
                        deck_name=deck_name,
                        course_id=course_id
                    )

                    if audio_path:
                        yield f"data: {json.dumps({'status': 'audio_complete', 'message': 'Audio récapitulatif généré', 'audio_path': audio_path})}\n\n"
                    else:
                        yield f"data: {json.dumps({'status': 'audio_error', 'message': 'Erreur lors de la génération audio'})}\n\n"

                except Exception as audio_error:
                    logger.error(f"Error generating summary audio: {audio_error}")
                    yield f"data: {json.dumps({'status': 'audio_error', 'message': str(audio_error)})}\n\n"

        except Exception as e:
            logger.error(f"Error in generation stream: {e}")
            yield f"data: {json.dumps({'status': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


