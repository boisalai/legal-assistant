"""
Tests d'intégration pour les endpoints refactorisés de documents.

Ce module teste les endpoints qui ont été refactorisés pour utiliser DocumentService :
- get_derived_documents : Récupération de documents dérivés
- clear_document_text : Effacement du texte extrait
- extract_document_text : Extraction de texte
- register_document : Enregistrement de documents existants
- link_file_or_folder : Liaison de fichiers/dossiers
- diagnose_documents : Diagnostic de cohérence
"""

import io
import pytest
import tempfile
from pathlib import Path
from httpx import AsyncClient
from fastapi import status


@pytest.fixture
async def test_course(client: AsyncClient):
    """Fixture pour créer un cours de test."""
    course_data = {
        "title": "Test Course Refactored Endpoints",
        "description": "Cours pour tester les endpoints refactorisés",
        "course_code": "TEST-REFACTOR-001",
        "professor": "Prof. Refactor",
        "credits": 3,
        "color": "#4CAF50",
    }

    response = await client.post("/api/courses", json=course_data)
    assert response.status_code == status.HTTP_201_CREATED

    course = response.json()
    yield course

    # Cleanup
    await client.delete(f"/api/courses/{course['id']}")


@pytest.fixture
def sample_markdown_file():
    """Fixture pour créer un fichier markdown de test."""
    content = b"""# Test Document

This is a test markdown document with some content.

## Section 1
Some important text here.

## Section 2
More text content.
"""
    return ("test_refactored.md", io.BytesIO(content), "text/markdown")


class TestDerivedDocuments:
    """Tests pour l'endpoint get_derived_documents."""

    @pytest.mark.asyncio
    async def test_get_derived_documents_empty(
        self, client: AsyncClient, test_course: dict, sample_markdown_file
    ):
        """Test de récupération de documents dérivés (liste vide)."""
        course_id = test_course["id"]

        # Upload a source document
        filename, content, mime_type = sample_markdown_file
        files = {"file": (filename, content, mime_type)}
        upload_response = await client.post(
            f"/api/courses/{course_id}/documents",
            files=files
        )
        assert upload_response.status_code == status.HTTP_201_CREATED
        doc_id = upload_response.json()["id"]

        # Get derived documents (should be empty)
        response = await client.get(
            f"/api/courses/{course_id}/documents/{doc_id}/derived"
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "derived" in data
        assert isinstance(data["derived"], list)
        assert data["total"] == 0
        assert len(data["derived"]) == 0

    @pytest.mark.asyncio
    async def test_get_derived_documents_not_found(
        self, client: AsyncClient, test_course: dict
    ):
        """Test de récupération de documents dérivés pour un document inexistant."""
        course_id = test_course["id"]
        response = await client.get(
            f"/api/courses/{course_id}/documents/document:nonexistent/derived"
        )

        # The endpoint should still return successfully with empty list
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 0


class TestDocumentTextOperations:
    """Tests pour les opérations sur le texte des documents."""

    @pytest.mark.asyncio
    async def test_clear_document_text(
        self, client: AsyncClient, test_course: dict, sample_markdown_file
    ):
        """Test d'effacement du texte extrait d'un document."""
        course_id = test_course["id"]

        # Upload a document
        filename, content, mime_type = sample_markdown_file
        files = {"file": (filename, content, mime_type)}
        upload_response = await client.post(
            f"/api/courses/{course_id}/documents",
            files=files
        )
        assert upload_response.status_code == status.HTTP_201_CREATED
        doc_id = upload_response.json()["id"]

        # Extract text first
        extract_response = await client.post(
            f"/api/courses/{course_id}/documents/{doc_id}/extract"
        )
        assert extract_response.status_code == status.HTTP_200_OK
        assert extract_response.json()["success"] is True

        # Clear the text
        response = await client.delete(
            f"/api/courses/{course_id}/documents/{doc_id}/text"
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert "message" in data

        # Verify text is cleared
        doc_response = await client.get(
            f"/api/courses/{course_id}/documents/{doc_id}"
        )
        assert doc_response.status_code == status.HTTP_200_OK
        # extracted_text should be None or empty
        doc_data = doc_response.json()
        assert doc_data.get("extracted_text") is None or doc_data.get("extracted_text") == ""

    @pytest.mark.asyncio
    async def test_clear_document_text_not_found(
        self, client: AsyncClient, test_course: dict
    ):
        """Test d'effacement du texte d'un document inexistant."""
        course_id = test_course["id"]
        response = await client.delete(
            f"/api/courses/{course_id}/documents/document:nonexistent/text"
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_extract_document_text(
        self, client: AsyncClient, test_course: dict, sample_markdown_file
    ):
        """Test d'extraction de texte d'un document."""
        course_id = test_course["id"]

        # Upload a document
        filename, content, mime_type = sample_markdown_file
        files = {"file": (filename, content, mime_type)}
        upload_response = await client.post(
            f"/api/courses/{course_id}/documents",
            files=files
        )
        assert upload_response.status_code == status.HTTP_201_CREATED
        doc_id = upload_response.json()["id"]

        # Extract text
        response = await client.post(
            f"/api/courses/{course_id}/documents/{doc_id}/extract"
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert "text" in data
        assert len(data["text"]) > 0
        assert "Test Document" in data["text"]
        assert "method" in data

    @pytest.mark.asyncio
    async def test_extract_document_text_not_found(
        self, client: AsyncClient, test_course: dict
    ):
        """Test d'extraction de texte d'un document inexistant."""
        course_id = test_course["id"]
        response = await client.post(
            f"/api/courses/{course_id}/documents/document:nonexistent/extract"
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestDocumentRegistration:
    """Tests pour l'endpoint register_document."""

    @pytest.mark.asyncio
    async def test_register_document(
        self, client: AsyncClient, test_course: dict
    ):
        """Test d'enregistrement d'un document existant."""
        course_id = test_course["id"]

        # Create a temporary file
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.txt', delete=False
        ) as tmp_file:
            tmp_file.write("Test content for registration")
            tmp_path = tmp_file.name

        try:
            # Register the document
            register_data = {
                "file_path": tmp_path,
                "course_id": course_id
            }

            response = await client.post(
                f"/api/courses/{course_id}/documents/register",
                json=register_data
            )

            assert response.status_code == status.HTTP_201_CREATED
            data = response.json()
            assert "id" in data
            assert data["id"].startswith("document:")
            assert data["course_id"] == course_id
            assert data["file_path"] == tmp_path
            # API now returns English field names
            assert "filename" in data

        finally:
            # Cleanup: remove temporary file
            Path(tmp_path).unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_register_document_nonexistent_file(
        self, client: AsyncClient, test_course: dict
    ):
        """Test d'enregistrement d'un fichier inexistant."""
        course_id = test_course["id"]

        register_data = {
            "file_path": "/nonexistent/file.txt",
            "course_id": course_id
        }

        response = await client.post(
            f"/api/courses/{course_id}/documents/register",
            json=register_data
        )

        # Returns 400 Bad Request for nonexistent file (validation error)
        assert response.status_code == status.HTTP_400_BAD_REQUEST


class TestLinkFileOrFolder:
    """Tests pour l'endpoint link_file_or_folder."""

    @pytest.mark.asyncio
    async def test_link_markdown_file(
        self, client: AsyncClient, test_course: dict
    ):
        """Test de liaison d'un fichier markdown."""
        course_id = test_course["id"]

        # Create a temporary markdown file
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.md', delete=False
        ) as tmp_file:
            tmp_file.write("# Test Linked Document\n\nSome content here.")
            tmp_path = tmp_file.name

        try:
            # Link the file
            link_data = {"path": tmp_path}
            response = await client.post(
                f"/api/courses/{course_id}/documents/link",
                json=link_data
            )

            assert response.status_code == status.HTTP_201_CREATED
            data = response.json()
            assert data["success"] is True
            assert data["linked_count"] == 1
            assert "documents" in data
            assert len(data["documents"]) == 1

            doc = data["documents"][0]
            assert "id" in doc
            assert doc["source_type"] == "linked"
            assert "linked_source" in doc
            assert doc["linked_source"]["absolute_path"] == tmp_path

        finally:
            # Cleanup
            Path(tmp_path).unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_link_nonexistent_path(
        self, client: AsyncClient, test_course: dict
    ):
        """Test de liaison d'un chemin inexistant."""
        course_id = test_course["id"]

        link_data = {"path": "/nonexistent/path.md"}
        response = await client.post(
            f"/api/courses/{course_id}/documents/link",
            json=link_data
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST


class TestDiagnostic:
    """Tests pour l'endpoint diagnostic."""

    @pytest.mark.asyncio
    async def test_diagnose_documents_empty(
        self, client: AsyncClient, test_course: dict
    ):
        """Test du diagnostic pour un cours sans documents."""
        course_id = test_course["id"]

        # Client already includes auth headers
        response = await client.get(
            f"/api/courses/{course_id}/documents/diagnostic"
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "total_documents" in data
        assert "missing_files" in data
        assert "ok_count" in data
        assert data["total_documents"] == 0
        assert len(data["missing_files"]) == 0

    @pytest.mark.asyncio
    async def test_diagnose_documents_with_valid_documents(
        self, client: AsyncClient, test_course: dict, sample_markdown_file
    ):
        """Test du diagnostic avec des documents valides."""
        course_id = test_course["id"]

        # Upload a document
        filename, content, mime_type = sample_markdown_file
        files = {"file": (filename, content, mime_type)}
        upload_response = await client.post(
            f"/api/courses/{course_id}/documents",
            files=files
        )
        assert upload_response.status_code == status.HTTP_201_CREATED

        # Run diagnostic (client already includes auth headers)
        response = await client.get(
            f"/api/courses/{course_id}/documents/diagnostic"
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total_documents"] >= 1
        assert data["ok_count"] >= 1
        # All files should be present
        assert len(data["missing_files"]) == 0


class TestRefactoredEndpointsIntegration:
    """Tests d'intégration pour valider que tous les endpoints refactorisés fonctionnent ensemble."""

    @pytest.mark.asyncio
    async def test_complete_workflow_with_refactored_endpoints(
        self, client: AsyncClient, test_course: dict, sample_markdown_file
    ):
        """Test du workflow complet utilisant les endpoints refactorisés."""
        course_id = test_course["id"]

        # 1. Upload a document (refactored)
        filename, content, mime_type = sample_markdown_file
        files = {"file": (filename, content, mime_type)}
        upload_response = await client.post(
            f"/api/courses/{course_id}/documents",
            files=files
        )
        assert upload_response.status_code == status.HTTP_201_CREATED
        doc_id = upload_response.json()["id"]

        # 2. Extract text (refactored)
        extract_response = await client.post(
            f"/api/courses/{course_id}/documents/{doc_id}/extract"
        )
        assert extract_response.status_code == status.HTTP_200_OK
        assert extract_response.json()["success"] is True

        # 3. Get document (refactored)
        get_response = await client.get(
            f"/api/courses/{course_id}/documents/{doc_id}"
        )
        assert get_response.status_code == status.HTTP_200_OK
        doc_data = get_response.json()
        # API now returns English field names
        assert doc_data["extracted_text"] is not None

        # 4. Get derived documents (refactored)
        derived_response = await client.get(
            f"/api/courses/{course_id}/documents/{doc_id}/derived"
        )
        assert derived_response.status_code == status.HTTP_200_OK

        # 5. Download document (refactored)
        download_response = await client.get(
            f"/api/courses/{course_id}/documents/{doc_id}/download"
        )
        assert download_response.status_code == status.HTTP_200_OK

        # 6. Run diagnostic (refactored - client already includes auth)
        diagnostic_response = await client.get(
            f"/api/courses/{course_id}/documents/diagnostic"
        )
        assert diagnostic_response.status_code == status.HTTP_200_OK
        diagnostic_data = diagnostic_response.json()
        assert diagnostic_data["ok_count"] >= 1

        # 7. Clear text (refactored)
        clear_response = await client.delete(
            f"/api/courses/{course_id}/documents/{doc_id}/text"
        )
        assert clear_response.status_code == status.HTTP_200_OK

        # 8. Delete document (refactored)
        delete_response = await client.delete(
            f"/api/courses/{course_id}/documents/{doc_id}"
        )
        assert delete_response.status_code == status.HTTP_204_NO_CONTENT
