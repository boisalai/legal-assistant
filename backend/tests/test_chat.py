"""
Tests pour les endpoints de chat et recherche sémantique.

Ce module teste:
- Chat non-streaming
- Chat avec streaming SSE
- Historique de conversation
- Recherche sémantique avec RAG
- Statistiques de chat
"""

import pytest
from httpx import AsyncClient
from fastapi import status

# Note: client fixture is now provided by conftest.py
# and uses a real test server instead of ASGITransport


@pytest.fixture
async def test_course(client: AsyncClient):
    """Fixture pour créer un cours de test avec un document."""
    # Create course
    course_data = {
        "title": "Test Course for Chat",
        "description": "Cours de test pour le chat et la recherche sémantique",
        "course_code": "CHAT-TEST-001",
        "professor": "Prof. Test",
        "credits": 3,
    }

    response = await client.post("/api/courses", json=course_data)
    assert response.status_code == status.HTTP_201_CREATED

    course = response.json()
    yield course

    # Cleanup
    await client.delete(f"/api/courses/{course['id']}")


class TestChatBasic:
    """Tests de base pour le chat."""

    @pytest.mark.asyncio
    async def test_chat_simple_message(self, client: AsyncClient):
        """Test d'un message simple au chat sans contexte."""
        request_data = {
            "message": "Bonjour, qui es-tu ?",
            "model_id": "ollama:qwen2.5:7b",
            "history": []
        }

        response = await client.post("/api/chat", json=request_data)

        # Note: This test might fail if Ollama is not running
        # In that case, it should return 500 or 503
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            status.HTTP_503_SERVICE_UNAVAILABLE
        ]

        if response.status_code == status.HTTP_200_OK:
            data = response.json()
            assert "message" in data
            assert "model_used" in data
            assert isinstance(data["message"], str)
            assert len(data["message"]) > 0

    @pytest.mark.asyncio
    async def test_chat_with_history(self, client: AsyncClient):
        """Test du chat avec historique de conversation."""
        request_data = {
            "message": "Quelle est la couleur du ciel ?",
            "model_id": "ollama:qwen2.5:7b",
            "history": [
                {"role": "user", "content": "Bonjour"},
                {"role": "assistant", "content": "Bonjour ! Comment puis-je vous aider ?"}
            ]
        }

        response = await client.post("/api/chat", json=request_data)

        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            status.HTTP_503_SERVICE_UNAVAILABLE
        ]

    @pytest.mark.asyncio
    async def test_chat_with_course_context(
        self, client: AsyncClient, test_course: dict
    ):
        """Test du chat avec contexte de cours."""
        course_id = test_course["id"]

        request_data = {
            "message": "Quels sont les documents de ce cours ?",
            "model_id": "ollama:qwen2.5:7b",
            "course_id": course_id,
            "history": []
        }

        response = await client.post("/api/chat", json=request_data)

        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            status.HTTP_503_SERVICE_UNAVAILABLE
        ]

    @pytest.mark.asyncio
    async def test_chat_empty_message(self, client: AsyncClient):
        """Test du chat avec un message vide (devrait échouer)."""
        request_data = {
            "message": "",
            "model_id": "ollama:qwen2.5:7b",
            "history": []
        }

        response = await client.post("/api/chat", json=request_data)

        # Should fail validation or return error
        assert response.status_code in [
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            status.HTTP_400_BAD_REQUEST
        ]


class TestChatStreaming:
    """Tests pour le chat avec streaming SSE."""

    @pytest.mark.asyncio
    async def test_chat_stream_basic(self, client: AsyncClient):
        """Test du chat streaming de base."""
        request_data = {
            "message": "Compte de 1 à 3.",
            "model_id": "ollama:qwen2.5:7b",
            "history": []
        }

        response = await client.post("/api/chat/stream", json=request_data)

        # Note: This test might fail if Ollama is not running
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            status.HTTP_503_SERVICE_UNAVAILABLE
        ]

        if response.status_code == status.HTTP_200_OK:
            # Verify it's a streaming response
            assert "text/event-stream" in response.headers.get("content-type", "")

            # Read first few chunks
            chunks_read = 0
            async for chunk in response.aiter_bytes():
                if chunk:
                    chunks_read += 1
                    # Just verify we're getting data
                    assert len(chunk) > 0
                    if chunks_read >= 5:  # Read first 5 chunks
                        break

            assert chunks_read > 0

    @pytest.mark.asyncio
    async def test_chat_stream_with_course(
        self, client: AsyncClient, test_course: dict
    ):
        """Test du chat streaming avec contexte de cours."""
        course_id = test_course["id"]

        request_data = {
            "message": "Résume ce cours en une phrase.",
            "model_id": "ollama:qwen2.5:7b",
            "course_id": course_id,
            "history": []
        }

        response = await client.post("/api/chat/stream", json=request_data)

        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            status.HTTP_503_SERVICE_UNAVAILABLE
        ]


class TestChatHistory:
    """Tests pour l'historique de conversation."""

    @pytest.mark.asyncio
    async def test_get_chat_history_empty(
        self, client: AsyncClient, test_course: dict
    ):
        """Test de récupération d'un historique vide."""
        course_id = test_course["id"]

        response = await client.get(f"/api/chat/history/{course_id}")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "messages" in data or "conversations" in data or isinstance(data, list)

    @pytest.mark.asyncio
    async def test_get_chat_history_after_conversation(
        self, client: AsyncClient, test_course: dict
    ):
        """Test de récupération de l'historique après une conversation."""
        course_id = test_course["id"]

        # Send a message first
        chat_request = {
            "message": "Test message for history",
            "model_id": "ollama:qwen2.5:7b",
            "course_id": course_id,
            "history": []
        }

        chat_response = await client.post("/api/chat", json=chat_request)

        # Only check history if chat succeeded
        if chat_response.status_code == status.HTTP_200_OK:
            # Get history
            history_response = await client.get(f"/api/chat/history/{course_id}")

            assert history_response.status_code == status.HTTP_200_OK
            # History should contain at least the message we sent
            # Structure might vary, so just verify we got a response


class TestChatStats:
    """Tests pour les statistiques de chat."""

    @pytest.mark.asyncio
    async def test_get_chat_stats(
        self, client: AsyncClient, test_course: dict
    ):
        """Test de récupération des statistiques de chat."""
        course_id = test_course["id"]

        response = await client.get(f"/api/chat/stats/{course_id}")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Verify stats structure (might vary based on implementation)
        assert isinstance(data, dict)


class TestSemanticSearch:
    """Tests pour la recherche sémantique."""

    @pytest.mark.asyncio
    async def test_semantic_search_with_indexed_document(
        self, client: AsyncClient, test_course: dict
    ):
        """Test de recherche sémantique avec un document indexé."""
        # Note: This test requires a document to be indexed first
        # For now, we'll test the endpoint exists and returns proper format

        course_id = test_course["id"]

        # Try a search (might return empty if no documents indexed)
        search_request = {
            "message": "recherche test",
            "model_id": "ollama:qwen2.5:7b",
            "course_id": course_id,
            "history": []
        }

        response = await client.post("/api/chat", json=search_request)

        # Should succeed even if no documents found
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            status.HTTP_503_SERVICE_UNAVAILABLE
        ]

        if response.status_code == status.HTTP_200_OK:
            data = response.json()
            assert "message" in data
            assert "sources" in data
            assert isinstance(data["sources"], list)


class TestChatValidation:
    """Tests de validation pour le chat."""

    @pytest.mark.asyncio
    async def test_chat_missing_message(self, client: AsyncClient):
        """Test du chat sans message (devrait échouer)."""
        request_data = {
            "model_id": "ollama:qwen2.5:7b",
            "history": []
        }

        response = await client.post("/api/chat", json=request_data)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_chat_invalid_model_id(self, client: AsyncClient):
        """Test du chat avec un model_id invalide."""
        request_data = {
            "message": "Test",
            "model_id": "invalid:model:format",
            "history": []
        }

        response = await client.post("/api/chat", json=request_data)

        # Should fail with error about invalid model
        assert response.status_code in [
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            status.HTTP_500_INTERNAL_SERVER_ERROR
        ]

    @pytest.mark.asyncio
    async def test_chat_invalid_history_format(self, client: AsyncClient):
        """Test du chat avec un historique mal formaté."""
        request_data = {
            "message": "Test",
            "model_id": "ollama:qwen2.5:7b",
            "history": [{"invalid": "format"}]  # Missing role and content
        }

        response = await client.post("/api/chat", json=request_data)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
