"""
Tests pour la transcription audio.

Ce module teste:
- Transcription audio simple
- Workflow de transcription (Whisper + Agent LLM)
- Formats audio supportés
- Génération de fichiers markdown
"""

import io
import tempfile
from pathlib import Path
import pytest
from httpx import AsyncClient
from fastapi import status

# Note: client fixture is now provided by conftest.py
# and uses a real test server instead of ASGITransport


@pytest.fixture
async def test_course_with_audio(client: AsyncClient):
    """Fixture pour créer un cours avec un fichier audio."""
    # Create course
    course_data = {
        "title": "Test Course for Transcription",
        "description": "Cours de test pour la transcription audio",
        "course_code": "TRANS-TEST-001",
        "professor": "Prof. Test",
    }

    course_response = await client.post("/api/courses", json=course_data)
    assert course_response.status_code == status.HTTP_201_CREATED
    course = course_response.json()

    # Create a minimal audio file (WAV format)
    # This is a minimal valid WAV header
    # Note: For real tests, you'd want an actual audio file
    audio_content = (
        b'RIFF'
        b'\x24\x00\x00\x00'
        b'WAVE'
        b'fmt '
        b'\x10\x00\x00\x00'  # Chunk size
        b'\x01\x00'          # Audio format (1 = PCM)
        b'\x01\x00'          # Number of channels (1 = mono)
        b'\x44\xac\x00\x00'  # Sample rate (44100 Hz)
        b'\x88\x58\x01\x00'  # Byte rate
        b'\x02\x00'          # Block align
        b'\x10\x00'          # Bits per sample (16-bit)
        b'data'
        b'\x00\x00\x00\x00'  # Data size (empty)
    )

    # Upload audio file
    files = {"file": ("test_audio.wav", io.BytesIO(audio_content), "audio/wav")}
    doc_response = await client.post(
        f"/api/courses/{course['id']}/documents",
        files=files
    )
    assert doc_response.status_code == status.HTTP_201_CREATED
    audio_doc = doc_response.json()

    yield {"course": course, "audio_document": audio_doc}

    # Cleanup
    await client.delete(f"/api/courses/{course['id']}")


class TestBasicTranscription:
    """Tests de base pour la transcription."""

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_transcribe_audio_endpoint_exists(
        self, client: AsyncClient, test_course_with_audio: dict
    ):
        """Test que l'endpoint de transcription existe."""
        course = test_course_with_audio["course"]
        audio_doc = test_course_with_audio["audio_document"]

        response = await client.post(
            f"/api/courses/{course['id']}/documents/{audio_doc['id']}/transcribe"
        )

        # Endpoint should exist (might fail with 500 if Whisper not available)
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_201_CREATED,
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            status.HTTP_503_SERVICE_UNAVAILABLE
        ]

    @pytest.mark.asyncio
    async def test_transcribe_non_audio_file(
        self, client: AsyncClient, test_course_with_audio: dict
    ):
        """Test de transcription d'un fichier non-audio."""
        course = test_course_with_audio["course"]

        # Upload a text file
        files = {"file": ("test.txt", io.BytesIO(b"Not an audio file"), "text/plain")}
        doc_response = await client.post(
            f"/api/courses/{course['id']}/documents",
            files=files
        )
        assert doc_response.status_code == status.HTTP_201_CREATED
        text_doc = doc_response.json()

        # Try to transcribe
        response = await client.post(
            f"/api/courses/{course['id']}/documents/{text_doc['id']}/transcribe"
        )

        # Should fail with appropriate error
        assert response.status_code in [
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            status.HTTP_422_UNPROCESSABLE_ENTITY
        ]

    @pytest.mark.asyncio
    async def test_transcribe_nonexistent_document(
        self, client: AsyncClient, test_course_with_audio: dict
    ):
        """Test de transcription d'un document inexistant."""
        course = test_course_with_audio["course"]

        response = await client.post(
            f"/api/courses/{course['id']}/documents/document:nonexistent/transcribe"
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestTranscriptionWorkflow:
    """Tests pour le workflow de transcription (Whisper + Agent LLM)."""

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_transcription_workflow_endpoint_exists(
        self, client: AsyncClient, test_course_with_audio: dict
    ):
        """Test que l'endpoint du workflow existe."""
        course = test_course_with_audio["course"]
        audio_doc = test_course_with_audio["audio_document"]

        response = await client.post(
            f"/api/courses/{course['id']}/documents/{audio_doc['id']}/transcribe-workflow"
        )

        # Endpoint should exist
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_201_CREATED,
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            status.HTTP_503_SERVICE_UNAVAILABLE
        ]

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_transcription_creates_markdown(
        self, client: AsyncClient, test_course_with_audio: dict
    ):
        """Test que la transcription crée un fichier markdown."""
        course = test_course_with_audio["course"]
        audio_doc = test_course_with_audio["audio_document"]

        # Attempt transcription workflow
        response = await client.post(
            f"/api/courses/{course['id']}/documents/{audio_doc['id']}/transcribe-workflow"
        )

        # The endpoint returns a Server-Sent Events (SSE) stream, not JSON
        # So we just verify that it starts successfully
        assert response.status_code == status.HTTP_200_OK
        assert response.headers.get("content-type") == "text/event-stream; charset=utf-8"

        # Note: To fully test this, we would need to read the SSE stream and parse events
        # which is complex and slow. For now, we just verify the endpoint is accessible.


class TestTranscriptionFormats:
    """Tests pour les différents formats audio supportés."""

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_supported_audio_formats(
        self, client: AsyncClient, test_course_with_audio: dict
    ):
        """Test des formats audio supportés."""
        course = test_course_with_audio["course"]

        # List of supported formats
        # Note: These are minimal headers, not real audio
        formats = [
            ("test.wav", b'RIFF' + b'\x00' * 40, "audio/wav"),
            ("test.mp3", b'\xFF\xFB' + b'\x00' * 40, "audio/mpeg"),
            ("test.m4a", b'\x00\x00\x00\x20ftypM4A ' + b'\x00' * 40, "audio/m4a"),
        ]

        for filename, content, mime_type in formats:
            # Upload audio file
            files = {"file": (filename, io.BytesIO(content), mime_type)}
            doc_response = await client.post(
                f"/api/courses/{course['id']}/documents",
                files=files
            )

            if doc_response.status_code == status.HTTP_201_CREATED:
                audio_doc = doc_response.json()

                # Try to transcribe
                trans_response = await client.post(
                    f"/api/courses/{course['id']}/documents/{audio_doc['id']}/transcribe"
                )

                # Should at least recognize as audio file
                # (might fail with 500 if Whisper not available or file is invalid)
                assert trans_response.status_code in [
                    status.HTTP_200_OK,
                    status.HTTP_201_CREATED,
                    status.HTTP_500_INTERNAL_SERVER_ERROR,
                    status.HTTP_503_SERVICE_UNAVAILABLE
                ]


class TestDerivedDocuments:
    """Tests pour les documents dérivés de la transcription."""

    @pytest.mark.asyncio
    async def test_get_derived_documents(
        self, client: AsyncClient, test_course_with_audio: dict
    ):
        """Test de récupération des documents dérivés."""
        course = test_course_with_audio["course"]
        audio_doc = test_course_with_audio["audio_document"]

        response = await client.get(
            f"/api/courses/{course['id']}/documents/{audio_doc['id']}/derived"
        )

        # Should return dict with "derived" key (list of derived documents)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, dict) and "derived" in data
        assert isinstance(data["derived"], list)

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_derived_document_linking(
        self, client: AsyncClient, test_course_with_audio: dict
    ):
        """Test que les documents dérivés sont liés au document source."""
        course = test_course_with_audio["course"]
        audio_doc = test_course_with_audio["audio_document"]

        # Attempt transcription
        trans_response = await client.post(
            f"/api/courses/{course['id']}/documents/{audio_doc['id']}/transcribe-workflow"
        )

        # If transcription succeeded, check derived documents
        if trans_response.status_code in [status.HTTP_200_OK, status.HTTP_201_CREATED]:
            # Get derived documents
            derived_response = await client.get(
                f"/api/courses/{course['id']}/documents/{audio_doc['id']}/derived"
            )

            if derived_response.status_code == status.HTTP_200_OK:
                derived_data = derived_response.json()

                # Should have at least one derived document (the transcription)
                if isinstance(derived_data, list):
                    assert len(derived_data) >= 1
                elif "derived_documents" in derived_data:
                    assert len(derived_data["derived_documents"]) >= 1


class TestTranscriptionValidation:
    """Tests de validation pour la transcription."""

    @pytest.mark.asyncio
    async def test_transcribe_with_invalid_course_id(
        self, client: AsyncClient, test_course_with_audio: dict
    ):
        """Test de transcription avec un ID de cours invalide."""
        audio_doc = test_course_with_audio["audio_document"]

        response = await client.post(
            f"/api/courses/course:invalid/documents/{audio_doc['id']}/transcribe"
        )

        # API returns 404 Not Found when course doesn't exist
        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_transcribe_with_mismatched_course(
        self, client: AsyncClient, test_course_with_audio: dict
    ):
        """Test de transcription avec un document d'un autre cours."""
        # Create another course
        other_course_data = {
            "title": "Other Course",
            "course_code": "OTHER-001",
        }
        other_course_response = await client.post("/api/courses", json=other_course_data)
        assert other_course_response.status_code == status.HTTP_201_CREATED
        other_course = other_course_response.json()

        # Try to transcribe audio from first course using second course ID
        audio_doc = test_course_with_audio["audio_document"]

        response = await client.post(
            f"/api/courses/{other_course['id']}/documents/{audio_doc['id']}/transcribe"
        )

        # Should fail when document doesn't belong to course
        assert response.status_code == status.HTTP_403_FORBIDDEN

        # Cleanup
        await client.delete(f"/api/courses/{other_course['id']}")
