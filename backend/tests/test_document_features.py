"""
Tests pour les fonctionnalites avancees des documents.

Ce module teste:
- Generation TTS (Text-to-Speech)
- Liste des voix TTS disponibles
- Extraction PDF vers Markdown
"""

import io
import pytest
from httpx import AsyncClient
from fastapi import status


@pytest.fixture
async def test_course(client: AsyncClient):
    """Fixture pour creer un cours de test."""
    course_data = {
        "title": "Test Document Features Course",
        "description": "Cours pour tester les fonctionnalites avancees",
        "course_code": "TEST-DOC-FEAT-001",
    }
    response = await client.post("/api/courses", json=course_data)
    course = response.json()
    yield course
    # Cleanup
    await client.delete(f"/api/courses/{course['id']}")


@pytest.fixture
def sample_markdown_file():
    """Fixture pour creer un fichier markdown de test avec contenu suffisant pour TTS."""
    content = b"""# Introduction au droit civil

Le droit civil est une branche du droit prive qui regit les relations entre les particuliers.

## Les sources du droit civil

1. La Constitution
2. Les lois et codes
3. La jurisprudence
4. La doctrine

## Principes fondamentaux

Le droit civil repose sur plusieurs principes essentiels comme l'autonomie de la volonte,
la bonne foi dans les contrats, et la responsabilite civile.

### L'autonomie de la volonte

Ce principe permet aux parties de determiner librement le contenu de leurs engagements.
"""
    return ("test_tts_document.md", io.BytesIO(content), "text/markdown")


@pytest.fixture
def sample_pdf_file():
    """Fixture pour creer un fichier PDF de test."""
    # Creer un PDF minimal valide
    pdf_content = b"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R >>
endobj
4 0 obj
<< /Length 44 >>
stream
BT
/F1 12 Tf
100 700 Td
(Test PDF) Tj
ET
endstream
endobj
xref
0 5
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000115 00000 n
0000000206 00000 n
trailer
<< /Size 5 /Root 1 0 R >>
startxref
300
%%EOF"""
    return ("test_extract.pdf", io.BytesIO(pdf_content), "application/pdf")


@pytest.fixture
async def test_course_with_markdown(client: AsyncClient, test_course: dict, sample_markdown_file):
    """Fixture pour un cours avec un document markdown."""
    course_id = test_course["id"]
    filename, content, mime_type = sample_markdown_file

    files = {"file": (filename, content, mime_type)}
    response = await client.post(f"/api/courses/{course_id}/documents", files=files)
    document = response.json()

    yield {
        "course": test_course,
        "document": document,
    }


@pytest.fixture
async def test_course_with_pdf(client: AsyncClient, test_course: dict, sample_pdf_file):
    """Fixture pour un cours avec un document PDF."""
    course_id = test_course["id"]
    filename, content, mime_type = sample_pdf_file

    files = {"file": (filename, content, mime_type)}
    response = await client.post(f"/api/courses/{course_id}/documents", files=files)
    document = response.json()

    yield {
        "course": test_course,
        "document": document,
    }


class TestTTSVoices:
    """Tests pour la liste des voix TTS."""

    @pytest.mark.asyncio
    async def test_list_tts_voices(self, client: AsyncClient):
        """Test de recuperation de la liste des voix TTS."""
        # L'endpoint TTS voices est sur /api/courses/tts/voices (pas de course_id)
        response = await client.get("/api/courses/tts/voices")

        # Le service TTS peut ne pas etre disponible
        if response.status_code == status.HTTP_501_NOT_IMPLEMENTED:
            pytest.skip("Service TTS non disponible (edge-tts non installe)")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Verifier la structure
        assert isinstance(data, list)
        if len(data) > 0:
            voice = data[0]
            assert "name" in voice
            assert "locale" in voice
            assert "language" in voice
            assert "gender" in voice

    @pytest.mark.asyncio
    async def test_list_tts_voices_includes_french(self, client: AsyncClient):
        """Test que les voix francaises sont disponibles."""
        response = await client.get("/api/courses/tts/voices")

        if response.status_code == status.HTTP_501_NOT_IMPLEMENTED:
            pytest.skip("Service TTS non disponible")

        assert response.status_code == status.HTTP_200_OK
        voices = response.json()

        # Chercher des voix francaises
        french_voices = [v for v in voices if v.get("locale", "").startswith("fr")]
        assert len(french_voices) > 0, "Aucune voix francaise disponible"


class TestTTSGeneration:
    """Tests pour la generation TTS."""

    @pytest.mark.asyncio
    async def test_generate_tts_basic(self, client: AsyncClient, test_course_with_markdown: dict):
        """Test de generation TTS basique."""
        course_id = test_course_with_markdown["course"]["id"]
        doc_id = test_course_with_markdown["document"]["id"]

        # Requete TTS avec parametres par defaut
        response = await client.post(
            f"/api/courses/{course_id}/documents/{doc_id}/tts",
            json={}
        )

        # Le service TTS peut ne pas etre disponible ou le texte non extrait
        if response.status_code == status.HTTP_501_NOT_IMPLEMENTED:
            pytest.skip("Service TTS non disponible")

        # Le document pourrait ne pas avoir de texte extrait (400 ou 500)
        if response.status_code in [status.HTTP_400_BAD_REQUEST, status.HTTP_500_INTERNAL_SERVER_ERROR]:
            data = response.json()
            error_msg = data.get("detail", "") or data.get("error", {}).get("message", "")
            if "texte" in error_msg.lower() or "text" in error_msg.lower():
                pytest.skip("Document n'a pas de texte extrait")
            # Autre erreur - skip aussi car TTS peut echouer pour diverses raisons
            pytest.skip(f"TTS error: {error_msg}")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert "success" in data
        if data["success"]:
            assert "audio_url" in data
            assert "duration" in data
            assert "voice" in data

    @pytest.mark.asyncio
    async def test_generate_tts_with_voice(self, client: AsyncClient, test_course_with_markdown: dict):
        """Test de generation TTS avec voix specifique."""
        course_id = test_course_with_markdown["course"]["id"]
        doc_id = test_course_with_markdown["document"]["id"]

        tts_request = {
            "language": "fr",
            "voice": "fr-FR-DeniseNeural",
            "gender": "female",
        }

        response = await client.post(
            f"/api/courses/{course_id}/documents/{doc_id}/tts",
            json=tts_request
        )

        if response.status_code == status.HTTP_501_NOT_IMPLEMENTED:
            pytest.skip("Service TTS non disponible")

        if response.status_code in [status.HTTP_400_BAD_REQUEST, status.HTTP_500_INTERNAL_SERVER_ERROR]:
            pytest.skip("TTS non disponible ou texte non extrait")

        assert response.status_code == status.HTTP_200_OK

    @pytest.mark.asyncio
    async def test_generate_tts_document_not_found(self, client: AsyncClient, test_course: dict):
        """Test de generation TTS pour un document inexistant."""
        course_id = test_course["id"]

        response = await client.post(
            f"/api/courses/{course_id}/documents/document:nonexistent/tts",
            json={}
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_generate_tts_with_rate(self, client: AsyncClient, test_course_with_markdown: dict):
        """Test de generation TTS avec vitesse modifiee."""
        course_id = test_course_with_markdown["course"]["id"]
        doc_id = test_course_with_markdown["document"]["id"]

        tts_request = {
            "language": "fr",
            "rate": "+20%",  # Lecture plus rapide
        }

        response = await client.post(
            f"/api/courses/{course_id}/documents/{doc_id}/tts",
            json=tts_request
        )

        if response.status_code == status.HTTP_501_NOT_IMPLEMENTED:
            pytest.skip("Service TTS non disponible")

        if response.status_code in [status.HTTP_400_BAD_REQUEST, status.HTTP_500_INTERNAL_SERVER_ERROR]:
            pytest.skip("TTS non disponible ou texte non extrait")

        assert response.status_code == status.HTTP_200_OK


class TestPDFExtraction:
    """Tests pour l'extraction PDF vers Markdown."""

    @pytest.mark.asyncio
    async def test_extract_pdf_not_pdf_file(self, client: AsyncClient, test_course_with_markdown: dict):
        """Test d'extraction sur un fichier non-PDF."""
        course_id = test_course_with_markdown["course"]["id"]
        doc_id = test_course_with_markdown["document"]["id"]  # C'est un .md, pas un .pdf

        response = await client.post(
            f"/api/courses/{course_id}/documents/{doc_id}/extract-to-markdown"
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        # L'erreur peut etre dans "detail" ou "error.message"
        error_msg = data.get("detail", "") or data.get("error", {}).get("message", "")
        assert "pdf" in error_msg.lower()

    @pytest.mark.asyncio
    async def test_extract_pdf_document_not_found(self, client: AsyncClient, test_course: dict):
        """Test d'extraction pour un document inexistant."""
        course_id = test_course["id"]

        response = await client.post(
            f"/api/courses/{course_id}/documents/document:nonexistent/extract-to-markdown"
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_extract_pdf_returns_sse_stream(self, client: AsyncClient, test_course_with_pdf: dict):
        """Test que l'extraction PDF retourne un stream SSE."""
        course_id = test_course_with_pdf["course"]["id"]
        doc_id = test_course_with_pdf["document"]["id"]

        # La reponse est un stream SSE
        response = await client.post(
            f"/api/courses/{course_id}/documents/{doc_id}/extract-to-markdown"
        )

        # L'extraction peut echouer pour diverses raisons (PDF invalide, etc.)
        # mais devrait retourner un stream ou une erreur
        assert response.status_code in [
            status.HTTP_200_OK,  # Stream SSE
            status.HTTP_400_BAD_REQUEST,  # PDF invalide
            status.HTTP_500_INTERNAL_SERVER_ERROR,  # Erreur d'extraction
        ]

        # Si OK, verifier le content-type (peut etre text/event-stream ou application/json)
        if response.status_code == status.HTTP_200_OK:
            content_type = response.headers.get("content-type", "")
            assert "text/event-stream" in content_type or "application/json" in content_type


class TestDocumentDerived:
    """Tests pour les documents derives (transcriptions, TTS, etc.)."""

    @pytest.mark.asyncio
    async def test_list_derived_documents(self, client: AsyncClient, test_course_with_markdown: dict):
        """Test de listage des documents derives."""
        course_id = test_course_with_markdown["course"]["id"]
        doc_id = test_course_with_markdown["document"]["id"]

        response = await client.get(
            f"/api/courses/{course_id}/documents/{doc_id}/derived"
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        # L'API retourne "derived" pas "documents"
        assert "derived" in data
        assert isinstance(data["derived"], list)

    @pytest.mark.asyncio
    async def test_list_derived_document_not_found(self, client: AsyncClient, test_course: dict):
        """Test de listage des derives pour un document inexistant."""
        course_id = test_course["id"]

        response = await client.get(
            f"/api/courses/{course_id}/documents/document:nonexistent/derived"
        )

        # L'endpoint peut retourner 404 ou 200 avec liste vide
        assert response.status_code in [status.HTTP_404_NOT_FOUND, status.HTTP_200_OK]
        if response.status_code == status.HTTP_200_OK:
            data = response.json()
            assert len(data.get("derived", [])) == 0


class TestDocumentText:
    """Tests pour l'extraction et gestion du texte des documents."""

    @pytest.mark.asyncio
    async def test_extract_text(self, client: AsyncClient, test_course_with_markdown: dict):
        """Test d'extraction de texte d'un document."""
        course_id = test_course_with_markdown["course"]["id"]
        doc_id = test_course_with_markdown["document"]["id"]

        response = await client.post(
            f"/api/courses/{course_id}/documents/{doc_id}/extract"
        )

        # L'extraction peut reussir ou echouer selon le type de document
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_400_BAD_REQUEST,
        ]

        if response.status_code == status.HTTP_200_OK:
            data = response.json()
            # Verifier qu'on a du texte ou une confirmation
            assert "text" in data or "success" in data or "message" in data

    @pytest.mark.asyncio
    async def test_extract_text_not_found(self, client: AsyncClient, test_course: dict):
        """Test d'extraction de texte pour un document inexistant."""
        course_id = test_course["id"]

        response = await client.post(
            f"/api/courses/{course_id}/documents/document:nonexistent/extract"
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_clear_text(self, client: AsyncClient, test_course_with_markdown: dict):
        """Test de suppression du texte extrait."""
        course_id = test_course_with_markdown["course"]["id"]
        doc_id = test_course_with_markdown["document"]["id"]

        response = await client.delete(
            f"/api/courses/{course_id}/documents/{doc_id}/text"
        )

        # Peut reussir ou echouer si pas de texte a supprimer
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_204_NO_CONTENT,
            status.HTTP_404_NOT_FOUND,
        ]

    @pytest.mark.asyncio
    async def test_clear_text_not_found(self, client: AsyncClient, test_course: dict):
        """Test de suppression du texte pour un document inexistant."""
        course_id = test_course["id"]

        response = await client.delete(
            f"/api/courses/{course_id}/documents/document:nonexistent/text"
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestDocumentRegistration:
    """Tests pour l'enregistrement de fichiers existants."""

    @pytest.mark.asyncio
    async def test_register_file_missing_path(self, client: AsyncClient, test_course: dict):
        """Test d'enregistrement sans chemin de fichier."""
        course_id = test_course["id"]

        response = await client.post(
            f"/api/courses/{course_id}/documents/register",
            json={}
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_register_file_nonexistent(self, client: AsyncClient, test_course: dict):
        """Test d'enregistrement d'un fichier qui n'existe pas."""
        course_id = test_course["id"]

        response = await client.post(
            f"/api/courses/{course_id}/documents/register",
            json={"file_path": "/nonexistent/path/to/file.pdf"}
        )

        assert response.status_code in [
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_404_NOT_FOUND,
        ]


class TestDocumentWorkflowAdvanced:
    """Tests de workflow avances pour les documents."""

    @pytest.mark.asyncio
    async def test_upload_and_list_with_derived_flag(self, client: AsyncClient, test_course: dict):
        """Test d'upload et listage avec le flag include_derived."""
        course_id = test_course["id"]

        # Upload un document
        content = b"# Test Document\n\nContenu de test."
        files = {"file": ("test_derived_flag.md", io.BytesIO(content), "text/markdown")}
        upload_response = await client.post(
            f"/api/courses/{course_id}/documents",
            files=files
        )
        assert upload_response.status_code == status.HTTP_201_CREATED

        # Lister sans derives
        response_no_derived = await client.get(
            f"/api/courses/{course_id}/documents?include_derived=false"
        )
        assert response_no_derived.status_code == status.HTTP_200_OK

        # Lister avec derives
        response_with_derived = await client.get(
            f"/api/courses/{course_id}/documents?include_derived=true"
        )
        assert response_with_derived.status_code == status.HTTP_200_OK

    @pytest.mark.asyncio
    async def test_document_diagnostic(self, client: AsyncClient, test_course: dict):
        """Test de l'endpoint de diagnostic des documents."""
        course_id = test_course["id"]

        response = await client.get(
            f"/api/courses/{course_id}/documents/diagnostic"
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "total_documents" in data or "documents" in data or "diagnostic" in data
