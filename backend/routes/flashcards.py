"""
Routes pour la gestion des fiches de révision (flashcards).

Endpoints:
- POST /api/courses/{course_id}/flashcard-decks - Créer un deck
- GET /api/courses/{course_id}/flashcard-decks - Lister les decks d'un cours
- GET /api/flashcard-decks/{deck_id} - Détails d'un deck
- DELETE /api/flashcard-decks/{deck_id} - Supprimer un deck
- GET /api/flashcard-decks/{deck_id}/cards - Lister les fiches d'un deck
- GET /api/flashcard-decks/{deck_id}/study - Session de révision
- PATCH /api/flashcards/{card_id}/review - Enregistrer résultat révision
- POST /api/flashcards/{card_id}/tts - Générer audio TTS
"""

import logging
import uuid
from typing import Optional

from fastapi import APIRouter, HTTPException, status, Query
from fastapi.responses import FileResponse

from services.surreal_service import get_surreal_service
from models.flashcard_models import (
    FlashcardDeckCreate,
    FlashcardDeckResponse,
    FlashcardDeckListResponse,
    FlashcardResponse,
    FlashcardListResponse,
    StudySessionResponse,
    ReviewRequest,
    ReviewResponse,
    TTSRequest,
    TTSResponse,
    SourceDocument,
    CardStatus,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Flashcards"])


# ============================================================================
# Helper Functions
# ============================================================================

def generate_hex_id() -> str:
    """Génère un ID hexadécimal court compatible SurrealDB."""
    return uuid.uuid4().hex[:8]


async def get_deck_by_id(service, deck_id: str) -> Optional[dict]:
    """Récupère un deck par son ID."""
    record_id = deck_id.replace("flashcard_deck:", "")

    result = await service.query(
        "SELECT * FROM flashcard_deck WHERE id = type::thing('flashcard_deck', $record_id)",
        {"record_id": record_id}
    )

    # SurrealDB retourne une liste de dicts directement
    if result and len(result) > 0:
        return result[0]
    return None


async def get_deck_statistics(service, deck_id: str) -> dict:
    """Calcule les statistiques d'un deck."""
    record_id = deck_id.replace("flashcard_deck:", "")

    # Compter les fiches par statut
    result = await service.query(
        """
        SELECT
            count() as total,
            count(status = 'new' OR status = null) as new_cards,
            count(status = 'learning') as learning_cards,
            count(status = 'mastered') as mastered_cards
        FROM flashcard
        WHERE deck_id = type::thing('flashcard_deck', $record_id)
        GROUP ALL
        """,
        {"record_id": record_id}
    )

    # SurrealDB retourne une liste de dicts directement
    if result and len(result) > 0:
        stats = result[0]
        total = stats.get("total", 0)
        mastered = stats.get("mastered_cards", 0)
        return {
            "total_cards": total,
            "new_cards": stats.get("new_cards", 0),
            "learning_cards": stats.get("learning_cards", 0),
            "mastered_cards": mastered,
            "progress_percent": round((mastered / total * 100) if total > 0 else 0, 1)
        }

    return {
        "total_cards": 0,
        "new_cards": 0,
        "learning_cards": 0,
        "mastered_cards": 0,
        "progress_percent": 0.0
    }


def format_deck_response(deck: dict, stats: dict) -> FlashcardDeckResponse:
    """Formate un deck pour la réponse API."""
    # Parser source_documents
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

    # Formatter dates
    created_at = deck.get("created_at", "")
    if hasattr(created_at, "isoformat"):
        created_at = created_at.isoformat()

    last_studied = deck.get("last_studied")
    if last_studied and hasattr(last_studied, "isoformat"):
        last_studied = last_studied.isoformat()

    deck_id = deck.get("id", "")
    if hasattr(deck_id, "__str__"):
        deck_id = str(deck_id)

    return FlashcardDeckResponse(
        id=deck_id,
        course_id=str(deck.get("course_id", "")),
        name=deck.get("name", ""),
        source_documents=source_docs,
        card_types=deck.get("card_types", []),
        total_cards=stats.get("total_cards", 0),
        mastered_cards=stats.get("mastered_cards", 0),
        learning_cards=stats.get("learning_cards", 0),
        new_cards=stats.get("new_cards", 0),
        progress_percent=stats.get("progress_percent", 0.0),
        created_at=created_at,
        last_studied=last_studied
    )


def format_card_response(card: dict) -> FlashcardResponse:
    """Formate une fiche pour la réponse API."""
    created_at = card.get("created_at", "")
    if hasattr(created_at, "isoformat"):
        created_at = created_at.isoformat()

    last_reviewed = card.get("last_reviewed")
    if last_reviewed and hasattr(last_reviewed, "isoformat"):
        last_reviewed = last_reviewed.isoformat()

    card_id = card.get("id", "")
    if hasattr(card_id, "__str__"):
        card_id = str(card_id)

    return FlashcardResponse(
        id=card_id,
        deck_id=str(card.get("deck_id", "")),
        document_id=str(card.get("document_id", "")),
        card_type=card.get("card_type", "question"),
        front=card.get("front", ""),
        back=card.get("back", ""),
        source_excerpt=card.get("source_excerpt"),
        source_location=card.get("source_location"),
        status=card.get("status", "new"),
        review_count=card.get("review_count", 0),
        last_reviewed=last_reviewed,
        created_at=created_at
    )


# ============================================================================
# Deck Endpoints
# ============================================================================

@router.post(
    "/api/courses/{course_id}/flashcard-decks",
    response_model=FlashcardDeckResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Créer un deck de révision"
)
async def create_flashcard_deck(course_id: str, request: FlashcardDeckCreate):
    """
    Crée un nouveau deck de fiches de révision.

    Les fiches seront générées ultérieurement via l'endpoint de génération.
    """
    service = get_surreal_service()

    # Vérifier que le cours existe
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

    # Récupérer les informations des documents sources
    source_documents = []
    for doc_id in request.source_document_ids:
        doc_record_id = doc_id.replace("document:", "")
        doc_result = await service.query(
            "SELECT id, filename, linked_source FROM document WHERE id = type::thing('document', $record_id)",
            {"record_id": doc_record_id}
        )

        # SurrealDB retourne une liste de dicts directement
        if doc_result and len(doc_result) > 0:
            doc = doc_result[0]
            relative_path = None
            linked_source = doc.get("linked_source")
            if linked_source:
                relative_path = linked_source.get("relative_path")

            # Utiliser le filename ou le relative_path comme nom
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

    # Créer le deck
    deck_id = generate_hex_id()

    deck_data = {
        "course_id": f"course:{course_record_id}",
        "name": request.name,
        "source_documents": source_documents,
        "card_types": [ct.value for ct in request.card_types],
        "card_count_requested": request.card_count
        # created_at et last_studied ont des valeurs par défaut dans le schéma
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
    stats = await get_deck_statistics(service, f"flashcard_deck:{deck_id}")

    logger.info(f"Deck créé: {deck_id} pour cours {course_id} avec {len(source_documents)} documents")

    return format_deck_response(created_deck, stats)


@router.get(
    "/api/courses/{course_id}/flashcard-decks",
    response_model=FlashcardDeckListResponse,
    summary="Lister les decks d'un cours"
)
async def list_flashcard_decks(course_id: str):
    """Liste tous les decks de révision d'un cours."""
    service = get_surreal_service()

    # Normaliser le course_id (avec ou sans préfixe)
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
            stats = await get_deck_statistics(service, deck_id)
            decks.append(format_deck_response(deck, stats))

    return FlashcardDeckListResponse(decks=decks, total=len(decks))


@router.get(
    "/api/flashcard-decks/{deck_id}",
    response_model=FlashcardDeckResponse,
    summary="Détails d'un deck"
)
async def get_flashcard_deck(deck_id: str):
    """Récupère les détails d'un deck avec ses statistiques."""
    service = get_surreal_service()

    deck = await get_deck_by_id(service, deck_id)
    if not deck:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Deck non trouvé: {deck_id}"
        )

    stats = await get_deck_statistics(service, deck_id)
    return format_deck_response(deck, stats)


@router.delete(
    "/api/flashcard-decks/{deck_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Supprimer un deck"
)
async def delete_flashcard_deck(deck_id: str):
    """Supprime un deck et toutes ses fiches."""
    service = get_surreal_service()

    deck = await get_deck_by_id(service, deck_id)
    if not deck:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Deck non trouvé: {deck_id}"
        )

    record_id = deck_id.replace("flashcard_deck:", "")

    # Supprimer toutes les fiches du deck
    await service.query(
        "DELETE flashcard WHERE deck_id = type::thing('flashcard_deck', $deck_id)",
        {"deck_id": record_id}
    )

    # Supprimer le deck
    await service.query(
        "DELETE flashcard_deck WHERE id = type::thing('flashcard_deck', $deck_id)",
        {"deck_id": record_id}
    )

    logger.info(f"Deck supprimé: {deck_id}")
    return None


# ============================================================================
# Card Endpoints
# ============================================================================

@router.get(
    "/api/flashcard-decks/{deck_id}/cards",
    response_model=FlashcardListResponse,
    summary="Lister les fiches d'un deck"
)
async def list_flashcards(
    deck_id: str,
    status_filter: Optional[str] = Query(None, alias="status"),
    card_type: Optional[str] = Query(None)
):
    """Liste toutes les fiches d'un deck avec filtres optionnels."""
    service = get_surreal_service()

    deck = await get_deck_by_id(service, deck_id)
    if not deck:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Deck non trouvé: {deck_id}"
        )

    record_id = deck_id.replace("flashcard_deck:", "")

    # Construire la requête avec filtres
    query = "SELECT * FROM flashcard WHERE deck_id = type::thing('flashcard_deck', $deck_id)"
    params = {"deck_id": record_id}

    if status_filter:
        query += " AND status = $status"
        params["status"] = status_filter

    if card_type:
        query += " AND card_type = $card_type"
        params["card_type"] = card_type

    query += " ORDER BY created_at ASC"

    result = await service.query(query, params)

    cards = []
    if result and len(result) > 0:
        for card in result:
            cards.append(format_card_response(card))

    return FlashcardListResponse(cards=cards, total=len(cards))


@router.get(
    "/api/flashcard-decks/{deck_id}/study",
    response_model=StudySessionResponse,
    summary="Démarrer une session de révision"
)
async def start_study_session(
    deck_id: str,
    limit: int = Query(default=20, ge=1, le=100)
):
    """
    Récupère les fiches pour une session de révision.

    Priorité: new > learning > mastered
    """
    service = get_surreal_service()

    deck = await get_deck_by_id(service, deck_id)
    if not deck:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Deck non trouvé: {deck_id}"
        )

    record_id = deck_id.replace("flashcard_deck:", "")

    # Récupérer les fiches avec priorité
    result = await service.query(
        """
        SELECT * FROM flashcard
        WHERE deck_id = type::thing('flashcard_deck', $deck_id)
        ORDER BY
            (status = 'new' OR status = null) DESC,
            status = 'learning' DESC,
            last_reviewed ASC
        LIMIT $limit
        """,
        {"deck_id": record_id, "limit": limit}
    )

    cards = []
    new_count = 0
    learning_count = 0

    if result and len(result) > 0:
        for card in result:
            formatted = format_card_response(card)
            cards.append(formatted)

            card_status = card.get("status", "new")
            if card_status == "new" or card_status is None:
                new_count += 1
            elif card_status == "learning":
                learning_count += 1

    # Mettre à jour last_studied sur le deck
    await service.query(
        """
        UPDATE flashcard_deck
        SET last_studied = time::now()
        WHERE id = type::thing('flashcard_deck', $deck_id)
        """,
        {"deck_id": record_id}
    )

    return StudySessionResponse(
        deck_id=deck_id,
        deck_name=deck.get("name", ""),
        cards=cards,
        total_cards=len(cards),
        new_cards=new_count,
        learning_cards=learning_count,
        review_cards=len(cards) - new_count - learning_count
    )


@router.patch(
    "/api/flashcards/{card_id}/review",
    response_model=ReviewResponse,
    summary="Enregistrer le résultat d'une révision"
)
async def review_flashcard(card_id: str, request: ReviewRequest):
    """
    Enregistre le résultat d'une révision et met à jour le statut de la fiche.

    - again: Repasse en "learning"
    - correct: Passe en "learning" si new, reste en "learning" sinon
    - easy: Passe en "mastered"
    """
    service = get_surreal_service()

    record_id = card_id.replace("flashcard:", "")

    # Récupérer la fiche
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
    current_status = card.get("status", "new")
    review_count = card.get("review_count", 0) + 1

    # Déterminer le nouveau statut
    if request.result == "again":
        new_status = "learning"
    elif request.result == "easy":
        new_status = "mastered"
    else:  # correct
        if current_status == "new" or current_status is None:
            new_status = "learning"
        elif current_status == "learning":
            # Après 3 révisions correctes, passer en mastered
            if review_count >= 3:
                new_status = "mastered"
            else:
                new_status = "learning"
        else:
            new_status = current_status

    # Mettre à jour la fiche
    await service.query(
        """
        UPDATE flashcard
        SET status = $status,
            review_count = $review_count,
            last_reviewed = time::now()
        WHERE id = type::thing('flashcard', $card_id)
        """,
        {
            "card_id": record_id,
            "status": new_status,
            "review_count": review_count
        }
    )

    logger.info(f"Fiche {card_id} révisée: {current_status} -> {new_status}")

    return ReviewResponse(
        card_id=card_id,
        new_status=new_status,
        review_count=review_count
    )


# ============================================================================
# TTS Endpoint
# ============================================================================

@router.post(
    "/api/flashcards/{card_id}/tts",
    response_model=TTSResponse,
    summary="Générer l'audio d'une fiche"
)
async def generate_flashcard_tts(card_id: str, request: TTSRequest):
    """
    Génère l'audio TTS pour le recto ou verso d'une fiche.

    Voix disponibles (canadien-français):
    - fr-CA-SylvieNeural (femme, défaut)
    - fr-CA-AntoineNeural (homme)
    - fr-CA-JeanNeural (homme)
    - fr-CA-ThierryNeural (homme)
    """
    service = get_surreal_service()

    record_id = card_id.replace("flashcard:", "")

    # Récupérer la fiche
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

    # Récupérer le texte à synthétiser
    if request.side == "front":
        text = card.get("front", "")
    else:
        text = card.get("back", "")

    if not text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Pas de texte à synthétiser pour le côté {request.side}"
        )

    # Générer l'audio avec le service TTS
    try:
        from services.tts_service import TTSService

        tts_service = TTSService()

        # Créer un fichier temporaire pour l'audio
        import tempfile
        import os

        temp_dir = tempfile.gettempdir()
        audio_filename = f"flashcard_{record_id}_{request.side}.mp3"
        audio_path = os.path.join(temp_dir, audio_filename)

        # Générer l'audio
        tts_result = await tts_service.synthesize(
            text=text,
            output_path=audio_path,
            voice=request.voice,
            language="fr"
        )

        if not tts_result.success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Erreur TTS: {tts_result.error}"
            )

        # Retourner l'URL relative pour le frontend
        # Note: En production, on pourrait utiliser un CDN ou stockage S3
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
        logger.error(f"Erreur TTS: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la génération audio: {str(e)}"
        )


@router.get(
    "/api/flashcards/{card_id}/audio/{side}",
    summary="Récupérer l'audio d'une fiche"
)
async def get_flashcard_audio(card_id: str, side: str):
    """Retourne le fichier audio généré pour une fiche."""
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
