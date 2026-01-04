"""
Tests pour les endpoints de modules.

Ce module teste:
- Creation de modules
- Recuperation de modules
- Mise a jour de modules
- Suppression de modules
- Assignation de documents aux modules
"""

import pytest
from httpx import AsyncClient
from fastapi import status
from io import BytesIO


@pytest.fixture
async def test_course(client: AsyncClient):
    """Fixture pour creer un cours de test."""
    course_data = {
        "title": "Test Modules Course",
        "description": "Cours pour tester les modules",
        "course_code": "TEST-MOD-001",
    }
    response = await client.post("/api/courses", json=course_data)
    course = response.json()
    yield course
    # Cleanup
    await client.delete(f"/api/courses/{course['id']}")


@pytest.fixture
async def test_course_with_documents(client: AsyncClient, test_course: dict):
    """Fixture pour un cours avec des documents."""
    course_id = test_course["id"]

    # Upload multiple documents
    documents = []
    for i in range(3):
        content = f"# Document {i}\n\nContenu du document {i} pour les tests.".encode()
        files = {"file": (f"test_doc_{i}.md", BytesIO(content), "text/markdown")}
        response = await client.post(f"/api/courses/{course_id}/documents", files=files)
        documents.append(response.json())

    yield {
        "course": test_course,
        "documents": documents,
    }


class TestModuleCRUD:
    """Tests CRUD pour les modules."""

    @pytest.mark.asyncio
    async def test_create_module(self, client: AsyncClient, test_course: dict):
        """Test de creation d'un module."""
        course_id = test_course["id"]

        module_data = {
            "name": "Module 1: Introduction",
            "order_index": 0,
            "exam_weight": 0.2,
        }

        response = await client.post(
            f"/api/courses/{course_id}/modules",
            json=module_data
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()

        assert "id" in data
        assert data["name"] == module_data["name"]
        assert data["order_index"] == module_data["order_index"]
        assert data["exam_weight"] == module_data["exam_weight"]
        assert data["document_count"] == 0

    @pytest.mark.asyncio
    async def test_create_module_minimal(self, client: AsyncClient, test_course: dict):
        """Test de creation d'un module avec donnees minimales."""
        course_id = test_course["id"]

        module_data = {
            "name": "Module Minimal",
        }

        response = await client.post(
            f"/api/courses/{course_id}/modules",
            json=module_data
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["name"] == module_data["name"]
        assert data["order_index"] == 0  # Valeur par defaut

    @pytest.mark.asyncio
    async def test_create_module_invalid_course(self, client: AsyncClient):
        """Test de creation d'un module pour un cours inexistant."""
        module_data = {
            "name": "Test Module",
        }

        response = await client.post(
            "/api/courses/course:nonexistent/modules",
            json=module_data
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_list_modules(self, client: AsyncClient, test_course: dict):
        """Test de listage des modules d'un cours."""
        course_id = test_course["id"]

        # Creer quelques modules
        for i in range(3):
            module_data = {
                "name": f"Module {i}",
                "order_index": i,
            }
            await client.post(f"/api/courses/{course_id}/modules", json=module_data)

        # Lister
        response = await client.get(f"/api/courses/{course_id}/modules")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "modules" in data
        assert data["total"] >= 3

    @pytest.mark.asyncio
    async def test_get_module(self, client: AsyncClient, test_course: dict):
        """Test de recuperation d'un module."""
        course_id = test_course["id"]

        # Creer un module
        module_data = {
            "name": "Get Module Test",
            "order_index": 0,
        }
        create_response = await client.post(
            f"/api/courses/{course_id}/modules",
            json=module_data
        )
        module_id = create_response.json()["id"]

        # Normaliser l'ID
        module_id_normalized = module_id.replace("module:", "")

        # Recuperer le module
        response = await client.get(f"/api/modules/{module_id_normalized}")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["name"] == module_data["name"]

    @pytest.mark.asyncio
    async def test_get_module_not_found(self, client: AsyncClient):
        """Test de recuperation d'un module inexistant."""
        response = await client.get("/api/modules/nonexistent")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_update_module(self, client: AsyncClient, test_course: dict):
        """Test de mise a jour d'un module."""
        course_id = test_course["id"]

        # Creer un module
        module_data = {
            "name": "Module Original",
            "order_index": 0,
        }
        create_response = await client.post(
            f"/api/courses/{course_id}/modules",
            json=module_data
        )
        module_id = create_response.json()["id"]
        module_id_normalized = module_id.replace("module:", "")

        # Mettre a jour
        update_data = {
            "name": "Module Mis a Jour",
            "order_index": 5,
            "exam_weight": 0.3,
        }

        response = await client.patch(
            f"/api/modules/{module_id_normalized}",
            json=update_data
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["name"] == update_data["name"]
        assert data["order_index"] == update_data["order_index"]
        assert data["exam_weight"] == update_data["exam_weight"]

    @pytest.mark.asyncio
    async def test_update_module_not_found(self, client: AsyncClient):
        """Test de mise a jour d'un module inexistant."""
        update_data = {"name": "Test"}
        response = await client.patch("/api/modules/nonexistent", json=update_data)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_delete_module(self, client: AsyncClient, test_course: dict):
        """Test de suppression d'un module."""
        course_id = test_course["id"]

        # Creer un module
        module_data = {
            "name": "Module a Supprimer",
        }
        create_response = await client.post(
            f"/api/courses/{course_id}/modules",
            json=module_data
        )
        module_id = create_response.json()["id"]
        module_id_normalized = module_id.replace("module:", "")

        # Supprimer
        response = await client.delete(f"/api/modules/{module_id_normalized}")
        assert response.status_code == status.HTTP_204_NO_CONTENT

        # Verifier suppression
        get_response = await client.get(f"/api/modules/{module_id_normalized}")
        assert get_response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_delete_module_not_found(self, client: AsyncClient):
        """Test de suppression d'un module inexistant."""
        response = await client.delete("/api/modules/nonexistent")

        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestModuleBulkCreate:
    """Tests pour la creation en masse de modules."""

    @pytest.mark.asyncio
    async def test_bulk_create_modules(self, client: AsyncClient, test_course: dict):
        """Test de creation de plusieurs modules a la fois."""
        course_id = test_course["id"]

        bulk_data = {
            "modules": [
                {"name": "Module 1", "order_index": 0, "exam_weight": 0.2},
                {"name": "Module 2", "order_index": 1, "exam_weight": 0.3},
                {"name": "Module 3", "order_index": 2, "exam_weight": 0.5},
            ]
        }

        response = await client.post(
            f"/api/courses/{course_id}/modules/bulk",
            json=bulk_data
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["created_count"] == 3
        assert len(data["modules"]) == 3

    @pytest.mark.asyncio
    async def test_bulk_create_empty_list(self, client: AsyncClient, test_course: dict):
        """Test de creation en masse avec liste vide."""
        course_id = test_course["id"]

        bulk_data = {"modules": []}

        response = await client.post(
            f"/api/courses/{course_id}/modules/bulk",
            json=bulk_data
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestModuleDocumentAssignment:
    """Tests pour l'assignation de documents aux modules."""

    @pytest.mark.asyncio
    async def test_assign_documents(self, client: AsyncClient, test_course_with_documents: dict):
        """Test d'assignation de documents a un module."""
        course_id = test_course_with_documents["course"]["id"]
        documents = test_course_with_documents["documents"]
        doc_ids = [doc["id"] for doc in documents]

        # Creer un module
        module_data = {"name": "Module avec Documents"}
        create_response = await client.post(
            f"/api/courses/{course_id}/modules",
            json=module_data
        )
        module_id = create_response.json()["id"]
        module_id_normalized = module_id.replace("module:", "")

        # Assigner les documents
        assign_data = {"document_ids": doc_ids}
        response = await client.post(
            f"/api/modules/{module_id_normalized}/documents",
            json=assign_data
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["assigned_count"] == len(doc_ids)
        assert data["module_id"] == module_id_normalized

    @pytest.mark.asyncio
    async def test_get_module_documents(self, client: AsyncClient, test_course_with_documents: dict):
        """Test de recuperation des documents d'un module."""
        course_id = test_course_with_documents["course"]["id"]
        documents = test_course_with_documents["documents"]
        doc_ids = [doc["id"] for doc in documents]

        # Creer un module et assigner des documents
        module_data = {"name": "Module Docs Test"}
        create_response = await client.post(
            f"/api/courses/{course_id}/modules",
            json=module_data
        )
        module_id = create_response.json()["id"]
        module_id_normalized = module_id.replace("module:", "")

        # Assigner
        assign_data = {"document_ids": doc_ids}
        await client.post(f"/api/modules/{module_id_normalized}/documents", json=assign_data)

        # Recuperer les documents
        response = await client.get(f"/api/modules/{module_id_normalized}/documents")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "documents" in data
        assert data["total"] == len(doc_ids)

    @pytest.mark.asyncio
    async def test_get_module_documents_not_found(self, client: AsyncClient):
        """Test de recuperation des documents d'un module inexistant."""
        response = await client.get("/api/modules/nonexistent/documents")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_unassign_documents(self, client: AsyncClient, test_course_with_documents: dict):
        """Test de desassignation de documents d'un module."""
        course_id = test_course_with_documents["course"]["id"]
        documents = test_course_with_documents["documents"]
        doc_ids = [doc["id"] for doc in documents]

        # Creer un module et assigner des documents
        module_data = {"name": "Module Unassign Test"}
        create_response = await client.post(
            f"/api/courses/{course_id}/modules",
            json=module_data
        )
        module_id = create_response.json()["id"]
        module_id_normalized = module_id.replace("module:", "")

        # Assigner
        assign_data = {"document_ids": doc_ids}
        await client.post(f"/api/modules/{module_id_normalized}/documents", json=assign_data)

        # Desassigner un document (DELETE avec body necessite request())
        unassign_data = {"document_ids": [doc_ids[0]]}
        response = await client.request(
            "DELETE",
            f"/api/modules/{module_id_normalized}/documents",
            json=unassign_data
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["unassigned_count"] == 1

    @pytest.mark.asyncio
    async def test_get_unassigned_documents(self, client: AsyncClient, test_course_with_documents: dict):
        """Test de recuperation des documents non assignes."""
        course_id = test_course_with_documents["course"]["id"]

        response = await client.get(f"/api/courses/{course_id}/documents/unassigned")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "documents" in data
        assert "total" in data


class TestModuleWorkflow:
    """Tests du workflow complet des modules."""

    @pytest.mark.asyncio
    async def test_full_workflow(self, client: AsyncClient, test_course_with_documents: dict):
        """Test du workflow complet: creer, assigner, mettre a jour, supprimer."""
        course_id = test_course_with_documents["course"]["id"]
        documents = test_course_with_documents["documents"]

        # 1. Creer un module
        module_data = {
            "name": "Workflow Module",
            "order_index": 0,
            "exam_weight": 0.25,
        }
        create_response = await client.post(
            f"/api/courses/{course_id}/modules",
            json=module_data
        )
        assert create_response.status_code == status.HTTP_201_CREATED
        module = create_response.json()
        module_id = module["id"]
        module_id_normalized = module_id.replace("module:", "")

        # 2. Verifier dans la liste
        list_response = await client.get(f"/api/courses/{course_id}/modules")
        assert list_response.status_code == status.HTTP_200_OK
        modules = list_response.json()["modules"]
        module_ids = [m["id"] for m in modules]
        assert module_id in module_ids

        # 3. Assigner des documents
        doc_ids = [doc["id"] for doc in documents[:2]]  # 2 premiers documents
        assign_response = await client.post(
            f"/api/modules/{module_id_normalized}/documents",
            json={"document_ids": doc_ids}
        )
        assert assign_response.status_code == status.HTTP_200_OK

        # 4. Verifier les documents assignes
        docs_response = await client.get(f"/api/modules/{module_id_normalized}/documents")
        assert docs_response.status_code == status.HTTP_200_OK
        assert docs_response.json()["total"] == 2

        # 5. Mettre a jour le module
        update_response = await client.patch(
            f"/api/modules/{module_id_normalized}",
            json={"name": "Module Workflow Mis a Jour", "exam_weight": 0.5}
        )
        assert update_response.status_code == status.HTTP_200_OK
        assert update_response.json()["name"] == "Module Workflow Mis a Jour"

        # 6. Supprimer le module
        delete_response = await client.delete(f"/api/modules/{module_id_normalized}")
        assert delete_response.status_code == status.HTTP_204_NO_CONTENT

        # 7. Verifier la suppression
        final_response = await client.get(f"/api/modules/{module_id_normalized}")
        assert final_response.status_code == status.HTTP_404_NOT_FOUND


class TestModuleValidation:
    """Tests de validation des modules."""

    @pytest.mark.asyncio
    async def test_create_module_empty_name(self, client: AsyncClient, test_course: dict):
        """Test de creation d'un module avec un nom vide."""
        course_id = test_course["id"]

        module_data = {
            "name": "",
            "order_index": 0,
        }

        response = await client.post(
            f"/api/courses/{course_id}/modules",
            json=module_data
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_create_module_invalid_exam_weight(self, client: AsyncClient, test_course: dict):
        """Test de creation d'un module avec un poids d'examen invalide."""
        course_id = test_course["id"]

        # Poids > 1
        module_data = {
            "name": "Test Module",
            "exam_weight": 1.5,
        }

        response = await client.post(
            f"/api/courses/{course_id}/modules",
            json=module_data
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        # Poids < 0
        module_data["exam_weight"] = -0.1

        response = await client.post(
            f"/api/courses/{course_id}/modules",
            json=module_data
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_create_module_invalid_order_index(self, client: AsyncClient, test_course: dict):
        """Test de creation d'un module avec un index negatif."""
        course_id = test_course["id"]

        module_data = {
            "name": "Test Module",
            "order_index": -1,
        }

        response = await client.post(
            f"/api/courses/{course_id}/modules",
            json=module_data
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
