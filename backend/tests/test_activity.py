"""
Tests pour les endpoints d'activity tracking.

Ce module teste:
- Tracking d'activites utilisateur
- Recuperation des activites recentes
- Suppression de l'historique d'activites
- Contexte d'activite pour l'IA
"""

import pytest
from httpx import AsyncClient
from fastapi import status


@pytest.fixture
async def test_course(client: AsyncClient):
    """Fixture pour creer un cours de test."""
    course_data = {
        "title": "Test Activity Course",
        "description": "Cours pour tester l'activity tracking",
        "course_code": "TEST-ACT-001",
    }
    response = await client.post("/api/courses", json=course_data)
    course = response.json()
    yield course
    # Cleanup
    await client.delete(f"/api/courses/{course['id']}")


class TestActivityTracking:
    """Tests pour le tracking d'activites."""

    @pytest.mark.asyncio
    async def test_track_activity_view_case(self, client: AsyncClient, test_course: dict):
        """Test de tracking d'une vue de cours."""
        course_id = test_course["id"]

        activity_data = {
            "action_type": "view_case",
            "metadata": {"source": "sidebar"},
        }

        response = await client.post(
            f"/api/courses/{course_id}/activity",
            json=activity_data
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert "activity_id" in data

    @pytest.mark.asyncio
    async def test_track_activity_view_document(self, client: AsyncClient, test_course: dict):
        """Test de tracking d'une vue de document."""
        course_id = test_course["id"]

        activity_data = {
            "action_type": "view_document",
            "metadata": {
                "document_id": "document:test123",
                "document_name": "Test Document.pdf",
            },
        }

        response = await client.post(
            f"/api/courses/{course_id}/activity",
            json=activity_data
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True

    @pytest.mark.asyncio
    async def test_track_activity_view_module(self, client: AsyncClient, test_course: dict):
        """Test de tracking d'une vue de module."""
        course_id = test_course["id"]

        activity_data = {
            "action_type": "view_module",
            "metadata": {
                "module_id": "module:test456",
                "module_name": "Module 1",
            },
        }

        response = await client.post(
            f"/api/courses/{course_id}/activity",
            json=activity_data
        )

        assert response.status_code == status.HTTP_200_OK

    @pytest.mark.asyncio
    async def test_track_activity_view_flashcard_study(self, client: AsyncClient, test_course: dict):
        """Test de tracking d'une session de flashcards."""
        course_id = test_course["id"]

        activity_data = {
            "action_type": "view_flashcard_study",
            "metadata": {
                "deck_id": "flashcard_deck:test789",
                "deck_name": "Revision Module 1",
            },
        }

        response = await client.post(
            f"/api/courses/{course_id}/activity",
            json=activity_data
        )

        assert response.status_code == status.HTTP_200_OK

    @pytest.mark.asyncio
    async def test_track_activity_invalid_type(self, client: AsyncClient, test_course: dict):
        """Test de tracking avec un type d'activite invalide."""
        course_id = test_course["id"]

        activity_data = {
            "action_type": "invalid_activity_type",
            "metadata": {},
        }

        response = await client.post(
            f"/api/courses/{course_id}/activity",
            json=activity_data
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.asyncio
    async def test_track_activity_without_metadata(self, client: AsyncClient, test_course: dict):
        """Test de tracking sans metadata (devrait fonctionner)."""
        course_id = test_course["id"]

        activity_data = {
            "action_type": "view_case",
        }

        response = await client.post(
            f"/api/courses/{course_id}/activity",
            json=activity_data
        )

        assert response.status_code == status.HTTP_200_OK


class TestActivityRetrieval:
    """Tests pour la recuperation d'activites."""

    @pytest.mark.asyncio
    async def test_get_activities(self, client: AsyncClient, test_course: dict):
        """Test de recuperation des activites recentes."""
        course_id = test_course["id"]

        # Creer quelques activites
        for i in range(5):
            await client.post(
                f"/api/courses/{course_id}/activity",
                json={"action_type": "view_case", "metadata": {"index": i}}
            )

        # Recuperer les activites
        response = await client.get(f"/api/courses/{course_id}/activity")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "activities" in data
        assert "count" in data
        assert data["count"] >= 5

    @pytest.mark.asyncio
    async def test_get_activities_with_limit(self, client: AsyncClient, test_course: dict):
        """Test de recuperation avec limite."""
        course_id = test_course["id"]

        # Creer plusieurs activites
        for i in range(10):
            await client.post(
                f"/api/courses/{course_id}/activity",
                json={"action_type": "view_case"}
            )

        # Recuperer avec limite
        response = await client.get(f"/api/courses/{course_id}/activity?limit=5")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["count"] <= 5

    @pytest.mark.asyncio
    async def test_get_activities_empty_course(self, client: AsyncClient, test_course: dict):
        """Test de recuperation pour un cours sans activites (apres nettoyage)."""
        course_id = test_course["id"]

        # D'abord, nettoyer les activites
        await client.delete(f"/api/courses/{course_id}/activity")

        # Recuperer (devrait etre vide)
        response = await client.get(f"/api/courses/{course_id}/activity")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["count"] == 0


class TestActivityContext:
    """Tests pour le contexte d'activite (utilise par l'IA)."""

    @pytest.mark.asyncio
    async def test_get_activity_context(self, client: AsyncClient, test_course: dict):
        """Test de recuperation du contexte d'activite."""
        course_id = test_course["id"]

        # Creer quelques activites variees
        await client.post(
            f"/api/courses/{course_id}/activity",
            json={"action_type": "view_case"}
        )
        await client.post(
            f"/api/courses/{course_id}/activity",
            json={
                "action_type": "view_document",
                "metadata": {"document_name": "Important.pdf"}
            }
        )

        # Recuperer le contexte
        response = await client.get(f"/api/courses/{course_id}/activity/context")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "context" in data
        assert data["case_id"] == course_id

    @pytest.mark.asyncio
    async def test_get_activity_context_with_limit(self, client: AsyncClient, test_course: dict):
        """Test du contexte avec limite personnalisee."""
        course_id = test_course["id"]

        response = await client.get(f"/api/courses/{course_id}/activity/context?limit=10")

        assert response.status_code == status.HTTP_200_OK


class TestActivityClearing:
    """Tests pour la suppression d'activites."""

    @pytest.mark.asyncio
    async def test_clear_activities(self, client: AsyncClient, test_course: dict):
        """Test de suppression de l'historique d'activites."""
        course_id = test_course["id"]

        # Creer quelques activites
        for i in range(3):
            await client.post(
                f"/api/courses/{course_id}/activity",
                json={"action_type": "view_case"}
            )

        # Verifier qu'il y a des activites
        get_response = await client.get(f"/api/courses/{course_id}/activity")
        assert get_response.json()["count"] > 0

        # Supprimer
        response = await client.delete(f"/api/courses/{course_id}/activity")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True

        # Verifier que c'est vide
        final_response = await client.get(f"/api/courses/{course_id}/activity")
        assert final_response.json()["count"] == 0


class TestActivityWorkflow:
    """Tests du workflow complet d'activity tracking."""

    @pytest.mark.asyncio
    async def test_full_workflow(self, client: AsyncClient, test_course: dict):
        """Test du workflow complet: tracker, recuperer, contexte, supprimer."""
        course_id = test_course["id"]

        # 1. D'abord, nettoyer
        await client.delete(f"/api/courses/{course_id}/activity")

        # 2. Tracker plusieurs activites
        activities = [
            {"action_type": "view_case"},
            {"action_type": "view_document", "metadata": {"document_name": "Doc1.pdf"}},
            {"action_type": "view_module", "metadata": {"module_name": "Module 1"}},
            {"action_type": "view_flashcard_study", "metadata": {"deck_name": "Deck 1"}},
        ]

        for activity in activities:
            response = await client.post(
                f"/api/courses/{course_id}/activity",
                json=activity
            )
            assert response.status_code == status.HTTP_200_OK

        # 3. Recuperer les activites
        list_response = await client.get(f"/api/courses/{course_id}/activity")
        assert list_response.status_code == status.HTTP_200_OK
        assert list_response.json()["count"] == len(activities)

        # 4. Recuperer le contexte
        context_response = await client.get(f"/api/courses/{course_id}/activity/context")
        assert context_response.status_code == status.HTTP_200_OK
        context = context_response.json()["context"]
        assert context is not None

        # 5. Supprimer tout
        delete_response = await client.delete(f"/api/courses/{course_id}/activity")
        assert delete_response.status_code == status.HTTP_200_OK

        # 6. Verifier que c'est vide
        final_response = await client.get(f"/api/courses/{course_id}/activity")
        assert final_response.json()["count"] == 0


class TestActivityValidation:
    """Tests de validation pour l'activity tracking."""

    @pytest.mark.asyncio
    async def test_limit_capped_at_100(self, client: AsyncClient, test_course: dict):
        """Test que la limite est plafonnee a 100."""
        course_id = test_course["id"]

        # Demander plus que le max
        response = await client.get(f"/api/courses/{course_id}/activity?limit=200")

        assert response.status_code == status.HTTP_200_OK
        # Le backend devrait plafonner a 100

    @pytest.mark.asyncio
    async def test_all_valid_activity_types(self, client: AsyncClient, test_course: dict):
        """Test que tous les types d'activites valides sont acceptes."""
        course_id = test_course["id"]

        valid_types = [
            "view_case",
            "view_document",
            "close_document",
            "view_module",
            "close_module",
            "view_flashcard_study",
            "view_flashcard_audio",
            "view_directory",
            "send_message",
        ]

        for action_type in valid_types:
            response = await client.post(
                f"/api/courses/{course_id}/activity",
                json={"action_type": action_type}
            )
            assert response.status_code == status.HTTP_200_OK, f"Failed for {action_type}"
