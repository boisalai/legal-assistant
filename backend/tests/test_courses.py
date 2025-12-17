"""
Tests pour les endpoints de cours (CRUD).

Ce module teste:
- Création de cours
- Récupération de cours
- Mise à jour de cours
- Suppression de cours
"""

import pytest
from httpx import AsyncClient, ASGITransport
from fastapi import status

from main import app


@pytest.fixture
async def client(auth_token):
    """Fixture pour le client HTTP asynchrone avec authentification."""
    headers = {}
    if auth_token:
        headers["Authorization"] = f"Bearer {auth_token}"

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers=headers
    ) as client:
        yield client


@pytest.fixture
def course_data():
    """Fixture pour les données de test d'un cours."""
    return {
        "title": "Test Course - Introduction au droit",
        "description": "Cours de test pour les tests automatisés",
        "course_code": "TEST-101",
        "professor": "Prof. Test",
        "credits": 3,
        "color": "#FF5733",
        "semester": "Automne",
        "year": 2025,
    }


class TestCoursesCRUD:
    """Tests CRUD pour les cours."""

    @pytest.mark.asyncio
    async def test_create_course(self, client: AsyncClient, course_data: dict):
        """Test de création d'un cours."""
        # Création du cours
        response = await client.post("/api/courses", json=course_data)

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()

        # Vérifications
        assert "id" in data
        assert data["id"].startswith("course:")
        assert data["title"] == course_data["title"]
        assert data["description"] == course_data["description"]
        assert data["course_code"] == course_data["course_code"]
        assert data["professor"] == course_data["professor"]
        assert data["credits"] == course_data["credits"]
        assert data["color"] == course_data["color"]
        assert "created_at" in data
        assert "updated_at" in data

        # Retourner l'ID pour les autres tests
        return data["id"]

    @pytest.mark.asyncio
    async def test_create_course_minimal(self, client: AsyncClient):
        """Test de création d'un cours avec données minimales."""
        minimal_data = {
            "title": "Cours minimal",
        }

        response = await client.post("/api/courses", json=minimal_data)

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["title"] == minimal_data["title"]
        assert data["credits"] == 3  # Valeur par défaut

    @pytest.mark.asyncio
    async def test_get_course(self, client: AsyncClient, course_data: dict):
        """Test de récupération d'un cours."""
        # Créer un cours d'abord
        create_response = await client.post("/api/courses", json=course_data)
        course_id = create_response.json()["id"]

        # Récupérer le cours
        response = await client.get(f"/api/courses/{course_id}")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == course_id
        assert data["title"] == course_data["title"]

    @pytest.mark.asyncio
    async def test_get_course_not_found(self, client: AsyncClient):
        """Test de récupération d'un cours inexistant."""
        response = await client.get("/api/courses/course:nonexistent")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_update_course(self, client: AsyncClient, course_data: dict):
        """Test de mise à jour d'un cours."""
        # Créer un cours d'abord
        create_response = await client.post("/api/courses", json=course_data)
        course_id = create_response.json()["id"]

        # Mettre à jour le cours
        update_data = {
            "title": "Cours mis à jour",
            "professor": "Prof. Updated",
            "credits": 4,
        }

        response = await client.put(f"/api/courses/{course_id}", json=update_data)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["title"] == update_data["title"]
        assert data["professor"] == update_data["professor"]
        assert data["credits"] == update_data["credits"]
        # Les champs non mis à jour doivent rester inchangés
        assert data["course_code"] == course_data["course_code"]

    @pytest.mark.asyncio
    async def test_update_course_not_found(self, client: AsyncClient):
        """Test de mise à jour d'un cours inexistant."""
        update_data = {"title": "Test"}
        response = await client.put("/api/courses/course:nonexistent", json=update_data)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_delete_course(self, client: AsyncClient, course_data: dict):
        """Test de suppression d'un cours."""
        # Créer un cours d'abord
        create_response = await client.post("/api/courses", json=course_data)
        course_id = create_response.json()["id"]

        # Supprimer le cours
        response = await client.delete(f"/api/courses/{course_id}")

        assert response.status_code == status.HTTP_204_NO_CONTENT

        # Vérifier que le cours n'existe plus
        get_response = await client.get(f"/api/courses/{course_id}")
        assert get_response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_delete_course_not_found(self, client: AsyncClient):
        """Test de suppression d'un cours inexistant."""
        response = await client.delete("/api/courses/course:nonexistent")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_list_courses(self, client: AsyncClient, course_data: dict):
        """Test de listage des cours."""
        # Créer quelques cours
        for i in range(3):
            data = course_data.copy()
            data["title"] = f"Cours {i}"
            data["course_code"] = f"TEST-{i:03d}"
            await client.post("/api/courses", json=data)

        # Lister les cours
        response = await client.get("/api/courses")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "courses" in data
        assert len(data["courses"]) >= 3  # Au moins les 3 qu'on vient de créer

    @pytest.mark.asyncio
    async def test_full_crud_workflow(self, client: AsyncClient):
        """Test du workflow complet CRUD."""
        # 1. Créer un cours
        create_data = {
            "title": "Workflow Test Course",
            "description": "Test du workflow complet",
            "course_code": "WF-001",
            "professor": "Prof. Workflow",
            "credits": 3,
            "color": "#123456",
        }

        create_response = await client.post("/api/courses", json=create_data)
        assert create_response.status_code == status.HTTP_201_CREATED
        course_id = create_response.json()["id"]

        # 2. Lire le cours
        read_response = await client.get(f"/api/courses/{course_id}")
        assert read_response.status_code == status.HTTP_200_OK
        assert read_response.json()["title"] == create_data["title"]

        # 3. Mettre à jour le cours
        update_data = {
            "title": "Updated Workflow Course",
            "credits": 4,
        }
        update_response = await client.put(f"/api/courses/{course_id}", json=update_data)
        assert update_response.status_code == status.HTTP_200_OK
        updated = update_response.json()
        assert updated["title"] == update_data["title"]
        assert updated["credits"] == update_data["credits"]
        assert updated["professor"] == create_data["professor"]  # Inchangé

        # 4. Supprimer le cours
        delete_response = await client.delete(f"/api/courses/{course_id}")
        assert delete_response.status_code == status.HTTP_204_NO_CONTENT

        # 5. Vérifier que le cours n'existe plus
        final_response = await client.get(f"/api/courses/{course_id}")
        assert final_response.status_code == status.HTTP_404_NOT_FOUND


class TestCoursesValidation:
    """Tests de validation pour les cours."""

    @pytest.mark.asyncio
    async def test_create_course_without_title(self, client: AsyncClient):
        """Test de création sans titre (devrait échouer ou utiliser valeur par défaut)."""
        data = {
            "description": "Cours sans titre",
        }

        response = await client.post("/api/courses", json=data)

        # Le backend devrait soit rejeter, soit créer avec titre par défaut
        assert response.status_code in [
            status.HTTP_422_UNPROCESSABLE_ENTITY,  # Rejeté
            status.HTTP_201_CREATED,  # Accepté avec défaut
        ]

    @pytest.mark.asyncio
    async def test_create_course_invalid_credits(self, client: AsyncClient):
        """Test de création avec crédits invalides."""
        data = {
            "title": "Test",
            "credits": 20,  # > 12, hors limites
        }

        response = await client.post("/api/courses", json=data)

        # Devrait échouer la validation
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
