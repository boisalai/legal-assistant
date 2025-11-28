"""
Tests unitaires pour le service de gestion des dossiers.

Tests:
- CRUD dossiers
- CRUD documents
- Upload de fichiers
- Validation des données
"""

import pytest
from pathlib import Path

from models import DossierUpdate
from services.dossier_service import DossierService


@pytest.mark.unit
@pytest.mark.asyncio
class TestDossierService:
    """Tests pour DossierService."""

    async def test_create_dossier(self, dossier_service, sample_dossier_data):
        """Test de création d'un dossier."""
        dossier = await dossier_service.create_dossier(
            nom_dossier=sample_dossier_data["nom_dossier"],
            user_id=sample_dossier_data["user_id"],
            type_transaction=sample_dossier_data["type_transaction"],
        )

        assert dossier is not None
        assert dossier.id.startswith("dossier:")
        assert dossier.nom_dossier == sample_dossier_data["nom_dossier"]
        assert dossier.type_transaction == "vente"
        assert dossier.statut == "nouveau"

    async def test_get_dossier(self, dossier_service, sample_dossier_data):
        """Test de récupération d'un dossier."""
        # Créer un dossier
        created = await dossier_service.create_dossier(
            nom_dossier=sample_dossier_data["nom_dossier"],
            user_id=sample_dossier_data["user_id"],
            type_transaction=sample_dossier_data["type_transaction"],
        )

        # Récupérer le dossier
        dossier = await dossier_service.get_dossier(created.id)

        assert dossier is not None
        assert dossier.id == created.id
        assert dossier.nom_dossier == created.nom_dossier

    async def test_get_dossier_not_found(self, dossier_service):
        """Test de récupération d'un dossier inexistant."""
        dossier = await dossier_service.get_dossier("dossier:nonexistent")

        assert dossier is None

    async def test_list_dossiers(self, dossier_service, sample_dossier_data):
        """Test de listage des dossiers."""
        # Créer quelques dossiers
        for i in range(3):
            await dossier_service.create_dossier(
                nom_dossier=f"Test Dossier {i}",
                user_id=sample_dossier_data["user_id"],
                type_transaction="vente",
            )

        # Lister les dossiers
        dossiers = await dossier_service.list_dossiers(limit=10)

        assert len(dossiers) >= 3

    async def test_list_dossiers_by_user(self, dossier_service):
        """Test de filtrage des dossiers par utilisateur."""
        # Créer des dossiers pour différents utilisateurs
        await dossier_service.create_dossier(
            nom_dossier="Dossier User1",
            user_id="user:user1",
            type_transaction="vente",
        )
        await dossier_service.create_dossier(
            nom_dossier="Dossier User2",
            user_id="user:user2",
            type_transaction="achat",
        )

        # Filtrer par user1
        dossiers = await dossier_service.list_dossiers(user_id="user:user1")

        assert len(dossiers) == 1
        assert dossiers[0].nom_dossier == "Dossier User1"

    async def test_update_dossier(self, dossier_service, sample_dossier_data):
        """Test de mise à jour d'un dossier."""
        # Créer un dossier
        dossier = await dossier_service.create_dossier(
            nom_dossier=sample_dossier_data["nom_dossier"],
            user_id=sample_dossier_data["user_id"],
            type_transaction=sample_dossier_data["type_transaction"],
        )

        # Mettre à jour le statut
        updates = DossierUpdate(statut="en_analyse")
        updated = await dossier_service.update_dossier(dossier.id, updates)

        assert updated is not None
        assert updated.statut == "en_analyse"
        assert updated.nom_dossier == dossier.nom_dossier  # Inchangé

    async def test_delete_dossier(self, dossier_service, sample_dossier_data):
        """Test de suppression d'un dossier."""
        # Créer un dossier
        dossier = await dossier_service.create_dossier(
            nom_dossier=sample_dossier_data["nom_dossier"],
            user_id=sample_dossier_data["user_id"],
            type_transaction=sample_dossier_data["type_transaction"],
        )

        # Supprimer
        success = await dossier_service.delete_dossier(dossier.id)
        assert success is True

        # Vérifier qu'il n'existe plus
        deleted = await dossier_service.get_dossier(dossier.id)
        assert deleted is None

    async def test_add_document(self, dossier_service, sample_dossier_data, sample_pdf_content):
        """Test d'ajout d'un document à un dossier."""
        # Créer un dossier
        dossier = await dossier_service.create_dossier(
            nom_dossier=sample_dossier_data["nom_dossier"],
            user_id=sample_dossier_data["user_id"],
            type_transaction=sample_dossier_data["type_transaction"],
        )

        # Ajouter un document
        document = await dossier_service.add_document(
            dossier_id=dossier.id,
            file_content=sample_pdf_content,
            filename="test.pdf",
        )

        assert document is not None
        assert document.id.startswith("document:")
        assert document.nom_fichier == "test.pdf"
        assert document.taille_bytes == len(sample_pdf_content)
        assert document.hash_sha256 is not None
        assert len(document.hash_sha256) == 64  # SHA256 = 64 hex chars

        # Vérifier que le fichier existe
        file_path = Path(document.chemin_fichier)
        assert file_path.exists()
        assert file_path.read_bytes() == sample_pdf_content

    async def test_list_documents(self, dossier_service, sample_dossier_data, sample_pdf_content):
        """Test de listage des documents d'un dossier."""
        # Créer un dossier
        dossier = await dossier_service.create_dossier(
            nom_dossier=sample_dossier_data["nom_dossier"],
            user_id=sample_dossier_data["user_id"],
            type_transaction=sample_dossier_data["type_transaction"],
        )

        # Ajouter quelques documents
        for i in range(3):
            await dossier_service.add_document(
                dossier_id=dossier.id,
                file_content=sample_pdf_content,
                filename=f"test_{i}.pdf",
            )

        # Lister les documents
        documents = await dossier_service.list_documents(dossier.id)

        assert len(documents) == 3
        assert all(doc.nom_fichier.startswith("test_") for doc in documents)

    async def test_get_document(self, dossier_service, sample_dossier_data, sample_pdf_content):
        """Test de récupération d'un document."""
        # Créer un dossier
        dossier = await dossier_service.create_dossier(
            nom_dossier=sample_dossier_data["nom_dossier"],
            user_id=sample_dossier_data["user_id"],
            type_transaction=sample_dossier_data["type_transaction"],
        )

        # Ajouter un document
        created = await dossier_service.add_document(
            dossier_id=dossier.id,
            file_content=sample_pdf_content,
            filename="get_test.pdf",
        )

        # Récupérer le document
        document = await dossier_service.get_document(created.id)

        assert document is not None
        assert document.id == created.id
        assert document.nom_fichier == "get_test.pdf"

    async def test_delete_document(self, dossier_service, sample_dossier_data, sample_pdf_content):
        """Test de suppression d'un document."""
        # Créer un dossier
        dossier = await dossier_service.create_dossier(
            nom_dossier=sample_dossier_data["nom_dossier"],
            user_id=sample_dossier_data["user_id"],
            type_transaction=sample_dossier_data["type_transaction"],
        )

        # Ajouter un document
        document = await dossier_service.add_document(
            dossier_id=dossier.id,
            file_content=sample_pdf_content,
            filename="delete_test.pdf",
        )

        file_path = Path(document.chemin_fichier)
        assert file_path.exists()

        # Supprimer le document
        success = await dossier_service.delete_document(document.id)
        assert success is True

        # Vérifier que le fichier est supprimé
        assert not file_path.exists()

        # Vérifier que l'enregistrement est supprimé
        deleted = await dossier_service.get_document(document.id)
        assert deleted is None

    async def test_delete_dossier_cascade(self, dossier_service, sample_dossier_data, sample_pdf_content):
        """Test de suppression en cascade (dossier + documents)."""
        # Créer un dossier avec des documents
        dossier = await dossier_service.create_dossier(
            nom_dossier=sample_dossier_data["nom_dossier"],
            user_id=sample_dossier_data["user_id"],
            type_transaction=sample_dossier_data["type_transaction"],
        )

        # Ajouter 2 documents
        doc1 = await dossier_service.add_document(
            dossier_id=dossier.id,
            file_content=sample_pdf_content,
            filename="cascade_1.pdf",
        )
        doc2 = await dossier_service.add_document(
            dossier_id=dossier.id,
            file_content=sample_pdf_content,
            filename="cascade_2.pdf",
        )

        # Supprimer le dossier
        success = await dossier_service.delete_dossier(dossier.id)
        assert success is True

        # Vérifier que les documents sont supprimés
        assert await dossier_service.get_document(doc1.id) is None
        assert await dossier_service.get_document(doc2.id) is None

        # Vérifier que les fichiers sont supprimés
        assert not Path(doc1.chemin_fichier).exists()
        assert not Path(doc2.chemin_fichier).exists()

    async def test_format_result_converts_record_id(self, dossier_service, sample_dossier_data):
        """Test que _format_result convertit correctement les RecordID en string."""
        # Créer un dossier
        dossier = await dossier_service.create_dossier(
            nom_dossier=sample_dossier_data["nom_dossier"],
            user_id=sample_dossier_data["user_id"],
            type_transaction=sample_dossier_data["type_transaction"],
        )

        # Vérifier que l'ID est une string, pas un RecordID
        assert isinstance(dossier.id, str)
        assert dossier.id.startswith("dossier:")

        # Vérifier que user_id est aussi une string
        assert isinstance(dossier.user_id, str)
        assert dossier.user_id.startswith("user:")
