"""
Tests pour les endpoints de flashcards.

Ce module teste:
- Création de decks
- Récupération de decks
- Suppression de decks
- Listage des cartes
- Sessions d'étude
"""

import pytest
from httpx import AsyncClient
from fastapi import status
from io import BytesIO


@pytest.fixture
async def test_course(client: AsyncClient):
    """Fixture pour créer un cours de test."""
    course_data = {
        "title": "Test Flashcards Course",
        "description": "Cours pour tester les flashcards",
        "course_code": "TEST-FLASH-001",
    }
    response = await client.post("/api/courses", json=course_data)
    course = response.json()
    yield course
    # Cleanup
    await client.delete(f"/api/courses/{course['id']}")


@pytest.fixture
async def test_course_with_document(client: AsyncClient, test_course: dict):
    """Fixture pour un cours avec un document markdown."""
    # Upload a markdown document
    course_id = test_course["id"]
    content = b"""# Module 1: Introduction au droit

## Concepts fondamentaux

Le droit est un ensemble de regles qui regissent les rapports entre les personnes.

### Definitions importantes

- **Droit objectif**: Ensemble des regles juridiques
- **Droit subjectif**: Prerogatives individuelles

## Sources du droit

1. La Constitution
2. Les lois
3. Les reglements
4. La jurisprudence
"""

    files = {"file": ("test_flashcard_doc.md", BytesIO(content), "text/markdown")}
    response = await client.post(f"/api/courses/{course_id}/documents", files=files)
    document = response.json()

    yield {
        "course": test_course,
        "document": document,
    }


class TestFlashcardDeckCRUD:
    """Tests CRUD pour les decks de flashcards."""

    @pytest.mark.asyncio
    async def test_create_deck(self, client: AsyncClient, test_course_with_document: dict):
        """Test de creation d'un deck."""
        course_id = test_course_with_document["course"]["id"]
        doc_id = test_course_with_document["document"]["id"]

        deck_data = {
            "name": "Revision Module 1",
            "source_document_ids": [doc_id],
            "card_count": 10,
            "generate_audio": False,
        }

        response = await client.post(
            f"/api/courses/{course_id}/flashcard-decks",
            json=deck_data
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()

        assert "id" in data
        assert data["name"] == deck_data["name"]
        assert data["course_id"] == course_id or data["course_id"] == course_id.replace("course:", "")
        assert data["total_cards"] == 0  # Pas encore genere
        assert len(data["source_documents"]) == 1

    @pytest.mark.asyncio
    async def test_create_deck_invalid_course(self, client: AsyncClient):
        """Test de creation d'un deck pour un cours inexistant."""
        deck_data = {
            "name": "Test Deck",
            "source_document_ids": ["document:nonexistent"],
            "card_count": 10,
        }

        response = await client.post(
            "/api/courses/course:nonexistent/flashcard-decks",
            json=deck_data
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_create_deck_no_valid_documents(self, client: AsyncClient, test_course: dict):
        """Test de creation d'un deck sans documents valides."""
        course_id = test_course["id"]

        deck_data = {
            "name": "Test Deck",
            "source_document_ids": ["document:nonexistent"],
            "card_count": 10,
        }

        response = await client.post(
            f"/api/courses/{course_id}/flashcard-decks",
            json=deck_data
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.asyncio
    async def test_list_decks(self, client: AsyncClient, test_course_with_document: dict):
        """Test de listage des decks d'un cours."""
        course_id = test_course_with_document["course"]["id"]
        doc_id = test_course_with_document["document"]["id"]

        # Creer quelques decks
        for i in range(3):
            deck_data = {
                "name": f"Deck {i}",
                "source_document_ids": [doc_id],
                "card_count": 5,
            }
            await client.post(f"/api/courses/{course_id}/flashcard-decks", json=deck_data)

        # Lister
        response = await client.get(f"/api/courses/{course_id}/flashcard-decks")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "decks" in data
        assert data["total"] >= 3

    @pytest.mark.asyncio
    async def test_get_deck(self, client: AsyncClient, test_course_with_document: dict):
        """Test de recuperation d'un deck."""
        course_id = test_course_with_document["course"]["id"]
        doc_id = test_course_with_document["document"]["id"]

        # Creer un deck
        deck_data = {
            "name": "Get Deck Test",
            "source_document_ids": [doc_id],
            "card_count": 10,
        }
        create_response = await client.post(
            f"/api/courses/{course_id}/flashcard-decks",
            json=deck_data
        )
        deck_id = create_response.json()["id"]

        # Recuperer le deck (normaliser l'ID)
        deck_id_normalized = deck_id.replace("flashcard_deck:", "")
        response = await client.get(f"/api/flashcard-decks/{deck_id_normalized}")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["name"] == deck_data["name"]

    @pytest.mark.asyncio
    async def test_get_deck_not_found(self, client: AsyncClient):
        """Test de recuperation d'un deck inexistant."""
        response = await client.get("/api/flashcard-decks/nonexistent")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_delete_deck(self, client: AsyncClient, test_course_with_document: dict):
        """Test de suppression d'un deck."""
        course_id = test_course_with_document["course"]["id"]
        doc_id = test_course_with_document["document"]["id"]

        # Creer un deck
        deck_data = {
            "name": "Delete Deck Test",
            "source_document_ids": [doc_id],
            "card_count": 10,
        }
        create_response = await client.post(
            f"/api/courses/{course_id}/flashcard-decks",
            json=deck_data
        )
        deck_id = create_response.json()["id"]
        deck_id_normalized = deck_id.replace("flashcard_deck:", "")

        # Supprimer
        response = await client.delete(f"/api/flashcard-decks/{deck_id_normalized}")
        assert response.status_code == status.HTTP_204_NO_CONTENT

        # Verifier suppression
        get_response = await client.get(f"/api/flashcard-decks/{deck_id_normalized}")
        assert get_response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_delete_deck_not_found(self, client: AsyncClient):
        """Test de suppression d'un deck inexistant."""
        response = await client.delete("/api/flashcard-decks/nonexistent")

        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestFlashcardCards:
    """Tests pour les cartes de flashcards."""

    @pytest.mark.asyncio
    async def test_list_cards_empty_deck(self, client: AsyncClient, test_course_with_document: dict):
        """Test de listage des cartes d'un deck vide."""
        course_id = test_course_with_document["course"]["id"]
        doc_id = test_course_with_document["document"]["id"]

        # Creer un deck (sans generer les cartes)
        deck_data = {
            "name": "Empty Deck",
            "source_document_ids": [doc_id],
            "card_count": 10,
        }
        create_response = await client.post(
            f"/api/courses/{course_id}/flashcard-decks",
            json=deck_data
        )
        deck_id = create_response.json()["id"]
        deck_id_normalized = deck_id.replace("flashcard_deck:", "")

        # Lister les cartes
        response = await client.get(f"/api/flashcard-decks/{deck_id_normalized}/cards")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "cards" in data
        assert data["total"] == 0

    @pytest.mark.asyncio
    async def test_list_cards_deck_not_found(self, client: AsyncClient):
        """Test de listage des cartes d'un deck inexistant."""
        response = await client.get("/api/flashcard-decks/nonexistent/cards")

        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestFlashcardStudy:
    """Tests pour les sessions d'etude."""

    @pytest.mark.asyncio
    async def test_start_study_session(self, client: AsyncClient, test_course_with_document: dict):
        """Test de demarrage d'une session d'etude."""
        course_id = test_course_with_document["course"]["id"]
        doc_id = test_course_with_document["document"]["id"]

        # Creer un deck
        deck_data = {
            "name": "Study Session Test",
            "source_document_ids": [doc_id],
            "card_count": 10,
        }
        create_response = await client.post(
            f"/api/courses/{course_id}/flashcard-decks",
            json=deck_data
        )
        deck_id = create_response.json()["id"]
        deck_id_normalized = deck_id.replace("flashcard_deck:", "")

        # Demarrer une session d'etude
        response = await client.get(f"/api/flashcard-decks/{deck_id_normalized}/study")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "deck_id" in data
        assert "deck_name" in data
        assert "cards" in data
        assert "total_cards" in data
        assert data["deck_name"] == deck_data["name"]

    @pytest.mark.asyncio
    async def test_study_session_deck_not_found(self, client: AsyncClient):
        """Test de session d'etude pour un deck inexistant."""
        response = await client.get("/api/flashcard-decks/nonexistent/study")

        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestFlashcardWorkflow:
    """Tests du workflow complet des flashcards."""

    @pytest.mark.asyncio
    async def test_full_workflow(self, client: AsyncClient, test_course_with_document: dict):
        """Test du workflow complet: creer, lister, etudier, supprimer."""
        course_id = test_course_with_document["course"]["id"]
        doc_id = test_course_with_document["document"]["id"]

        # 1. Creer un deck
        deck_data = {
            "name": "Workflow Test Deck",
            "source_document_ids": [doc_id],
            "card_count": 5,
            "generate_audio": False,
        }
        create_response = await client.post(
            f"/api/courses/{course_id}/flashcard-decks",
            json=deck_data
        )
        assert create_response.status_code == status.HTTP_201_CREATED
        deck = create_response.json()
        deck_id = deck["id"]
        deck_id_normalized = deck_id.replace("flashcard_deck:", "")

        # 2. Verifier dans la liste
        list_response = await client.get(f"/api/courses/{course_id}/flashcard-decks")
        assert list_response.status_code == status.HTTP_200_OK
        decks = list_response.json()["decks"]
        deck_ids = [d["id"] for d in decks]
        assert deck_id in deck_ids

        # 3. Recuperer le deck
        get_response = await client.get(f"/api/flashcard-decks/{deck_id_normalized}")
        assert get_response.status_code == status.HTTP_200_OK
        assert get_response.json()["name"] == deck_data["name"]

        # 4. Demarrer une session d'etude
        study_response = await client.get(f"/api/flashcard-decks/{deck_id_normalized}/study")
        assert study_response.status_code == status.HTTP_200_OK

        # 5. Supprimer le deck
        delete_response = await client.delete(f"/api/flashcard-decks/{deck_id_normalized}")
        assert delete_response.status_code == status.HTTP_204_NO_CONTENT

        # 6. Verifier la suppression
        final_response = await client.get(f"/api/flashcard-decks/{deck_id_normalized}")
        assert final_response.status_code == status.HTTP_404_NOT_FOUND


class TestFlashcardValidation:
    """Tests de validation des flashcards."""

    @pytest.mark.asyncio
    async def test_create_deck_empty_name(self, client: AsyncClient, test_course_with_document: dict):
        """Test de creation d'un deck avec un nom vide."""
        course_id = test_course_with_document["course"]["id"]
        doc_id = test_course_with_document["document"]["id"]

        deck_data = {
            "name": "",
            "source_document_ids": [doc_id],
            "card_count": 10,
        }

        response = await client.post(
            f"/api/courses/{course_id}/flashcard-decks",
            json=deck_data
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_create_deck_empty_documents(self, client: AsyncClient, test_course: dict):
        """Test de creation d'un deck sans documents."""
        course_id = test_course["id"]

        deck_data = {
            "name": "Test Deck",
            "source_document_ids": [],
            "card_count": 10,
        }

        response = await client.post(
            f"/api/courses/{course_id}/flashcard-decks",
            json=deck_data
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_create_deck_invalid_card_count(self, client: AsyncClient, test_course_with_document: dict):
        """Test de creation d'un deck avec un nombre de cartes invalide."""
        course_id = test_course_with_document["course"]["id"]
        doc_id = test_course_with_document["document"]["id"]

        # Trop peu de cartes
        deck_data = {
            "name": "Test Deck",
            "source_document_ids": [doc_id],
            "card_count": 1,  # min_items = 5
        }

        response = await client.post(
            f"/api/courses/{course_id}/flashcard-decks",
            json=deck_data
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        # Trop de cartes
        deck_data["card_count"] = 500  # max = 200

        response = await client.post(
            f"/api/courses/{course_id}/flashcard-decks",
            json=deck_data
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
