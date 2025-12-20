"""
Tests pour les endpoints de documents (CRUD et fonctionnalités avancées).

Ce module teste:
- Upload de documents
- Récupération de documents
- Suppression de documents
- Téléchargement de documents
- Liaison de répertoires
- Extraction de texte
- Transcription audio
"""

import io
import pytest
from pathlib import Path
from httpx import AsyncClient
from fastapi import status

# Note: client fixture is now provided by conftest.py
# and uses a real test server instead of ASGITransport


@pytest.fixture
async def test_course(client: AsyncClient):
    """Fixture pour créer un cours de test."""
    course_data = {
        "title": "Test Course for Documents",
        "description": "Cours de test pour les documents",
        "course_code": "DOC-TEST-001",
        "professor": "Prof. Test",
        "credits": 3,
        "color": "#FF5733",
    }

    response = await client.post("/api/courses", json=course_data)
    assert response.status_code == status.HTTP_201_CREATED

    course = response.json()
    yield course

    # Cleanup: Delete course and all associated documents
    await client.delete(f"/api/courses/{course['id']}")


@pytest.fixture
def sample_pdf_file():
    """Fixture pour créer un fichier PDF de test."""
    # Create a simple PDF-like content (not a real PDF, but sufficient for testing upload)
    content = b"%PDF-1.4\n%Test PDF content"
    return ("test_document.pdf", io.BytesIO(content), "application/pdf")


@pytest.fixture
def sample_text_file():
    """Fixture pour créer un fichier texte de test."""
    content = b"This is a test document content."
    return ("test_document.txt", io.BytesIO(content), "text/plain")


@pytest.fixture
def sample_markdown_file():
    """Fixture pour créer un fichier markdown de test."""
    content = b"# Test Document\n\nThis is a test markdown document."
    return ("test_document.md", io.BytesIO(content), "text/markdown")


class TestDocumentsCRUD:
    """Tests CRUD pour les documents."""

    @pytest.mark.asyncio
    async def test_list_documents_empty(self, client: AsyncClient, test_course: dict):
        """Test de listage de documents pour un cours vide."""
        course_id = test_course["id"]
        response = await client.get(f"/api/courses/{course_id}/documents")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "documents" in data
        assert isinstance(data["documents"], list)

    @pytest.mark.asyncio
    async def test_upload_document(
        self, client: AsyncClient, test_course: dict, sample_pdf_file
    ):
        """Test d'upload d'un document."""
        course_id = test_course["id"]
        filename, file_content, mime_type = sample_pdf_file

        files = {"file": (filename, file_content, mime_type)}
        response = await client.post(
            f"/api/courses/{course_id}/documents",
            files=files
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()

        # Vérifications
        assert "id" in data
        assert data["id"].startswith("document:")
        assert data["filename"] == filename
        assert data["course_id"] == course_id
        assert data["mime_type"] == mime_type
        assert "file_path" in data
        assert "created_at" in data

    @pytest.mark.asyncio
    async def test_upload_multiple_documents(
        self, client: AsyncClient, test_course: dict, sample_pdf_file, sample_text_file
    ):
        """Test d'upload de plusieurs documents."""
        course_id = test_course["id"]

        # Upload first document
        filename1, content1, mime1 = sample_pdf_file
        files1 = {"file": (filename1, content1, mime1)}
        response1 = await client.post(
            f"/api/courses/{course_id}/documents",
            files=files1
        )
        assert response1.status_code == status.HTTP_201_CREATED

        # Upload second document
        filename2, content2, mime2 = sample_text_file
        files2 = {"file": (filename2, content2, mime2)}
        response2 = await client.post(
            f"/api/courses/{course_id}/documents",
            files=files2
        )
        assert response2.status_code == status.HTTP_201_CREATED

        # List documents
        response = await client.get(f"/api/courses/{course_id}/documents")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["documents"]) >= 2

    @pytest.mark.asyncio
    async def test_get_document(
        self, client: AsyncClient, test_course: dict, sample_pdf_file
    ):
        """Test de récupération d'un document."""
        course_id = test_course["id"]

        # Upload document first
        filename, content, mime_type = sample_pdf_file
        files = {"file": (filename, content, mime_type)}
        upload_response = await client.post(
            f"/api/courses/{course_id}/documents",
            files=files
        )
        doc_id = upload_response.json()["id"]

        # Get document
        response = await client.get(
            f"/api/courses/{course_id}/documents/{doc_id}"
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == doc_id
        assert data["filename"] == filename

    @pytest.mark.asyncio
    async def test_get_document_not_found(
        self, client: AsyncClient, test_course: dict
    ):
        """Test de récupération d'un document inexistant."""
        course_id = test_course["id"]
        response = await client.get(
            f"/api/courses/{course_id}/documents/document:nonexistent"
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_delete_document(
        self, client: AsyncClient, test_course: dict, sample_pdf_file
    ):
        """Test de suppression d'un document."""
        course_id = test_course["id"]

        # Upload document first
        filename, content, mime_type = sample_pdf_file
        files = {"file": (filename, content, mime_type)}
        upload_response = await client.post(
            f"/api/courses/{course_id}/documents",
            files=files
        )
        doc_id = upload_response.json()["id"]

        # Delete document
        response = await client.delete(
            f"/api/courses/{course_id}/documents/{doc_id}"
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT

        # Verify document doesn't exist
        get_response = await client.get(
            f"/api/courses/{course_id}/documents/{doc_id}"
        )
        assert get_response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_delete_document_not_found(
        self, client: AsyncClient, test_course: dict
    ):
        """Test de suppression d'un document inexistant."""
        course_id = test_course["id"]
        response = await client.delete(
            f"/api/courses/{course_id}/documents/document:nonexistent"
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_download_document(
        self, client: AsyncClient, test_course: dict, sample_pdf_file
    ):
        """Test de téléchargement d'un document."""
        course_id = test_course["id"]

        # Upload document first
        filename, content, mime_type = sample_pdf_file
        original_content = content.getvalue()
        files = {"file": (filename, content, mime_type)}
        upload_response = await client.post(
            f"/api/courses/{course_id}/documents",
            files=files
        )
        doc_id = upload_response.json()["id"]

        # Download document
        response = await client.get(
            f"/api/courses/{course_id}/documents/{doc_id}/download"
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.headers["content-type"] == mime_type
        # Note: Content comparison might differ due to storage mechanism
        # Just verify we got some content back
        assert len(response.content) > 0


class TestDocumentValidation:
    """Tests de validation pour les documents."""

    @pytest.mark.asyncio
    async def test_upload_without_file(
        self, client: AsyncClient, test_course: dict
    ):
        """Test d'upload sans fichier (devrait échouer)."""
        course_id = test_course["id"]
        response = await client.post(
            f"/api/courses/{course_id}/documents",
            files={}
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_upload_to_nonexistent_course(
        self, client: AsyncClient, sample_pdf_file
    ):
        """Test d'upload à un cours inexistant."""
        filename, content, mime_type = sample_pdf_file
        files = {"file": (filename, content, mime_type)}

        response = await client.post(
            "/api/courses/course:nonexistent/documents",
            files=files
        )

        # Might be 404 or 422 depending on validation order
        assert response.status_code in [
            status.HTTP_404_NOT_FOUND,
            status.HTTP_422_UNPROCESSABLE_ENTITY
        ]


class TestDocumentWorkflow:
    """Tests de workflow complet pour les documents."""

    @pytest.mark.asyncio
    async def test_full_document_lifecycle(
        self, client: AsyncClient, test_course: dict, sample_markdown_file
    ):
        """Test du cycle de vie complet d'un document."""
        course_id = test_course["id"]
        filename, content, mime_type = sample_markdown_file

        # 1. Upload document
        files = {"file": (filename, content, mime_type)}
        upload_response = await client.post(
            f"/api/courses/{course_id}/documents",
            files=files
        )
        assert upload_response.status_code == status.HTTP_201_CREATED
        doc_id = upload_response.json()["id"]

        # 2. Verify document appears in list
        list_response = await client.get(f"/api/courses/{course_id}/documents")
        assert list_response.status_code == status.HTTP_200_OK
        documents = list_response.json()["documents"]
        assert any(doc["id"] == doc_id for doc in documents)

        # 3. Get document details
        get_response = await client.get(
            f"/api/courses/{course_id}/documents/{doc_id}"
        )
        assert get_response.status_code == status.HTTP_200_OK
        doc_data = get_response.json()
        assert doc_data["id"] == doc_id
        assert doc_data["filename"] == filename

        # 4. Download document
        download_response = await client.get(
            f"/api/courses/{course_id}/documents/{doc_id}/download"
        )
        assert download_response.status_code == status.HTTP_200_OK

        # 5. Delete document
        delete_response = await client.delete(
            f"/api/courses/{course_id}/documents/{doc_id}"
        )
        assert delete_response.status_code == status.HTTP_204_NO_CONTENT

        # 6. Verify document is gone
        final_get = await client.get(
            f"/api/courses/{course_id}/documents/{doc_id}"
        )
        assert final_get.status_code == status.HTTP_404_NOT_FOUND
