"""
Tests pour la liaison de répertoires.

Ce module teste:
- Liaison de fichiers individuels
- Liaison de répertoires complets
- Tracking des fichiers liés
- Mises à jour de fichiers liés
- Suppression de fichiers liés
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
async def test_course(client: AsyncClient):
    """Fixture pour créer un cours de test."""
    course_data = {
        "title": "Test Course for Linked Directories",
        "description": "Cours de test pour les répertoires liés",
        "course_code": "LINK-TEST-001",
        "professor": "Prof. Test",
    }

    response = await client.post("/api/courses", json=course_data)
    assert response.status_code == status.HTTP_201_CREATED

    course = response.json()
    yield course

    # Cleanup
    await client.delete(f"/api/courses/{course['id']}")


@pytest.fixture
def temp_directory_with_files():
    """Fixture pour créer un répertoire temporaire avec des fichiers."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)

        # Create test files
        (tmpdir_path / "document1.md").write_text("# Document 1\n\nContenu du premier document.")
        (tmpdir_path / "document2.txt").write_text("Contenu du deuxième document.")
        (tmpdir_path / "notes.md").write_text("# Notes\n\n- Note 1\n- Note 2")

        # Create subdirectory with files
        subdir = tmpdir_path / "subdir"
        subdir.mkdir()
        (subdir / "subdoc.md").write_text("# Sous-document\n\nContenu du sous-document.")

        yield tmpdir_path


class TestLinkSingleFile:
    """Tests pour la liaison de fichiers individuels."""

    @pytest.mark.asyncio
    async def test_link_single_file(
        self, client: AsyncClient, test_course: dict, temp_directory_with_files: Path
    ):
        """Test de liaison d'un fichier unique."""
        course_id = test_course["id"]
        file_path = str(temp_directory_with_files / "document1.md")

        request_data = {
            "path": file_path
        }

        response = await client.post(
            f"/api/courses/{course_id}/documents/link",
            json=request_data
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()

        # Verify response structure
        assert "success" in data
        assert data["success"] is True
        assert "linked_count" in data
        assert data["linked_count"] == 1
        assert "documents" in data
        assert len(data["documents"]) == 1

        # Verify document details
        document = data["documents"][0]
        assert document["filename"] == "document1.md"
        assert "linked_source" in document
        assert document["linked_source"]["original_path"] == file_path

    @pytest.mark.asyncio
    async def test_link_nonexistent_file(
        self, client: AsyncClient, test_course: dict
    ):
        """Test de liaison d'un fichier inexistant."""
        course_id = test_course["id"]

        request_data = {
            "path": "/path/to/nonexistent/file.md"
        }

        response = await client.post(
            f"/api/courses/{course_id}/documents/link",
            json=request_data
        )

        # Should fail with 404 or 400
        assert response.status_code in [
            status.HTTP_404_NOT_FOUND,
            status.HTTP_400_BAD_REQUEST
        ]

    @pytest.mark.asyncio
    async def test_link_file_twice(
        self, client: AsyncClient, test_course: dict, temp_directory_with_files: Path
    ):
        """Test de liaison du même fichier deux fois."""
        course_id = test_course["id"]
        file_path = str(temp_directory_with_files / "document1.md")

        request_data = {
            "path": file_path
        }

        # Link first time
        response1 = await client.post(
            f"/api/courses/{course_id}/documents/link",
            json=request_data
        )
        assert response1.status_code == status.HTTP_201_CREATED

        # Link second time (should handle gracefully)
        response2 = await client.post(
            f"/api/courses/{course_id}/documents/link",
            json=request_data
        )

        # Should either succeed (update) or return 409 conflict
        assert response2.status_code in [
            status.HTTP_201_CREATED,
            status.HTTP_200_OK,
            status.HTTP_409_CONFLICT
        ]


class TestLinkDirectory:
    """Tests pour la liaison de répertoires complets."""

    @pytest.mark.asyncio
    async def test_link_directory(
        self, client: AsyncClient, test_course: dict, temp_directory_with_files: Path
    ):
        """Test de liaison d'un répertoire complet."""
        course_id = test_course["id"]
        dir_path = str(temp_directory_with_files)

        request_data = {
            "path": dir_path
        }

        response = await client.post(
            f"/api/courses/{course_id}/documents/link",
            json=request_data
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()

        # Verify multiple files were linked
        assert data["success"] is True
        assert data["linked_count"] >= 3  # At least document1.md, document2.txt, notes.md
        assert len(data["documents"]) >= 3

        # Verify all documents have linked_source
        for doc in data["documents"]:
            assert "linked_source" in doc
            assert "original_path" in doc["linked_source"]

    @pytest.mark.asyncio
    async def test_link_empty_directory(
        self, client: AsyncClient, test_course: dict
    ):
        """Test de liaison d'un répertoire vide."""
        course_id = test_course["id"]

        with tempfile.TemporaryDirectory() as tmpdir:
            request_data = {
                "path": tmpdir
            }

            response = await client.post(
                f"/api/courses/{course_id}/documents/link",
                json=request_data
            )

            # Should succeed but link 0 files
            if response.status_code == status.HTTP_201_CREATED:
                data = response.json()
                assert data["linked_count"] == 0
                assert len(data["documents"]) == 0

    @pytest.mark.asyncio
    async def test_link_directory_with_subdirectories(
        self, client: AsyncClient, test_course: dict, temp_directory_with_files: Path
    ):
        """Test de liaison d'un répertoire avec sous-répertoires."""
        course_id = test_course["id"]
        dir_path = str(temp_directory_with_files)

        request_data = {
            "path": dir_path
        }

        response = await client.post(
            f"/api/courses/{course_id}/documents/link",
            json=request_data
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()

        # Should include files from subdirectories
        # At least: document1.md, document2.txt, notes.md, subdir/subdoc.md
        assert data["linked_count"] >= 4


class TestLinkedFileTracking:
    """Tests pour le tracking des fichiers liés."""

    @pytest.mark.asyncio
    async def test_linked_files_in_document_list(
        self, client: AsyncClient, test_course: dict, temp_directory_with_files: Path
    ):
        """Test que les fichiers liés apparaissent dans la liste des documents."""
        course_id = test_course["id"]
        file_path = str(temp_directory_with_files / "document1.md")

        # Link file
        link_request = {
            "path": file_path
        }
        link_response = await client.post(
            f"/api/courses/{course_id}/documents/link",
            json=link_request
        )
        assert link_response.status_code == status.HTTP_201_CREATED

        # List documents
        list_response = await client.get(
            f"/api/courses/{course_id}/documents"
        )
        assert list_response.status_code == status.HTTP_200_OK

        data = list_response.json()
        assert "documents" in data

        # Find our linked document
        linked_docs = [
            doc for doc in data["documents"]
            if doc.get("source_type") == "linked"
        ]
        assert len(linked_docs) >= 1

        # Verify linked_source metadata
        linked_doc = linked_docs[0]
        assert "linked_source" in linked_doc
        assert linked_doc["linked_source"]["original_path"] == file_path

    @pytest.mark.asyncio
    async def test_linked_file_hash_tracking(
        self, client: AsyncClient, test_course: dict, temp_directory_with_files: Path
    ):
        """Test du tracking du hash des fichiers liés."""
        course_id = test_course["id"]
        file_path = str(temp_directory_with_files / "document1.md")

        # Link file
        link_request = {
            "path": file_path
        }
        link_response = await client.post(
            f"/api/courses/{course_id}/documents/link",
            json=link_request
        )
        assert link_response.status_code == status.HTTP_201_CREATED

        document = link_response.json()["documents"][0]

        # Verify hash is stored
        assert "linked_source" in document
        assert "file_hash" in document["linked_source"]
        assert len(document["linked_source"]["file_hash"]) == 64  # SHA-256 hash


class TestLinkedFileUpdates:
    """Tests pour les mises à jour de fichiers liés."""

    @pytest.mark.asyncio
    async def test_detect_modified_linked_file(
        self, client: AsyncClient, test_course: dict, temp_directory_with_files: Path
    ):
        """Test de détection d'un fichier lié modifié."""
        course_id = test_course["id"]
        file_path = temp_directory_with_files / "document1.md"

        # Link file
        link_request = {
            "path": str(file_path)
        }
        link_response = await client.post(
            f"/api/courses/{course_id}/documents/link",
            json=link_request
        )
        assert link_response.status_code == status.HTTP_201_CREATED

        original_hash = link_response.json()["documents"][0]["linked_source"]["file_hash"]

        # Modify file
        file_path.write_text("# Document 1 Modified\n\nNouveau contenu.")

        # Re-link to detect changes
        relink_response = await client.post(
            f"/api/courses/{course_id}/documents/link",
            json=link_request
        )

        # Should detect change
        if relink_response.status_code == status.HTTP_201_CREATED:
            new_hash = relink_response.json()["documents"][0]["linked_source"]["file_hash"]
            # Hash should be different
            assert new_hash != original_hash


class TestLinkedFileValidation:
    """Tests de validation pour les fichiers liés."""

    @pytest.mark.asyncio
    async def test_link_invalid_path(
        self, client: AsyncClient, test_course: dict
    ):
        """Test de liaison avec un chemin invalide."""
        course_id = test_course["id"]

        request_data = {
            "path": ""  # Empty path
        }

        response = await client.post(
            f"/api/courses/{course_id}/documents/link",
            json=request_data
        )

        assert response.status_code in [
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_422_UNPROCESSABLE_ENTITY
        ]

    @pytest.mark.asyncio
    async def test_link_unsupported_file_type(
        self, client: AsyncClient, test_course: dict
    ):
        """Test de liaison d'un type de fichier non supporté."""
        course_id = test_course["id"]

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create unsupported file type
            unsupported_file = Path(tmpdir) / "test.xyz"
            unsupported_file.write_text("Unsupported content")

            request_data = {
                "path": str(unsupported_file)
            }

            response = await client.post(
                f"/api/courses/{course_id}/documents/link",
                json=request_data
            )

            # Should either skip or fail
            # Depending on implementation, might succeed with warning
            # or fail with 400/415
            assert response.status_code in [
                status.HTTP_201_CREATED,  # Succeeded with warning
                status.HTTP_400_BAD_REQUEST,
                status.HTTP_415_UNSUPPORTED_MEDIA_TYPE
            ]
