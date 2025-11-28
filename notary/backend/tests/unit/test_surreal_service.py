"""
Tests unitaires pour le service SurrealDB.

Tests:
- Connexion/déconnexion
- Opérations CRUD basiques
- Gestion d'erreurs
- Conversion RecordID
"""

import pytest
from surrealdb import RecordID

from services.surreal_service import SurrealDBService


@pytest.mark.unit
@pytest.mark.asyncio
class TestSurrealDBService:
    """Tests pour SurrealDBService."""

    async def test_connect_disconnect(self, db_service):
        """Test de connexion et déconnexion."""
        # La fixture db_service connecte automatiquement
        assert db_service.client is not None

        # Vérifier qu'on peut faire une requête
        result = await db_service.query("SELECT * FROM user LIMIT 1")
        assert result is not None

    async def test_create_record(self, db_service):
        """Test de création d'un enregistrement."""
        # Créer un utilisateur de test
        user_data = {
            "email": "test@example.com",
            "nom": "Test User",
            "role": "notaire",
        }

        result = await db_service.create("user", user_data, record_id="test_user_123")

        assert result is not None
        assert "id" in result
        assert str(result["id"]) == "user:test_user_123"
        assert result["email"] == "test@example.com"
        assert result["nom"] == "Test User"

    async def test_select_record(self, db_service):
        """Test de sélection d'un enregistrement."""
        # Créer un enregistrement
        user_data = {
            "email": "select_test@example.com",
            "nom": "Select Test",
            "role": "assistant",
        }
        await db_service.create("user", user_data, record_id="select_test")

        # Sélectionner l'enregistrement
        result = await db_service.select("user:select_test")

        assert result is not None
        assert len(result) == 1
        assert result[0]["email"] == "select_test@example.com"

    async def test_update_record(self, db_service):
        """Test de mise à jour d'un enregistrement."""
        # Créer un enregistrement
        user_data = {
            "email": "update_test@example.com",
            "nom": "Update Test",
            "role": "notaire",
        }
        await db_service.create("user", user_data, record_id="update_test")

        # Mettre à jour
        updates = {"nom": "Updated Name"}
        result = await db_service.merge("user:update_test", updates)

        assert result is not None
        assert result["nom"] == "Updated Name"
        assert result["email"] == "update_test@example.com"  # Inchangé

    async def test_delete_record(self, db_service):
        """Test de suppression d'un enregistrement."""
        # Créer un enregistrement
        user_data = {
            "email": "delete_test@example.com",
            "nom": "Delete Test",
            "role": "notaire",
        }
        await db_service.create("user", user_data, record_id="delete_test")

        # Supprimer
        await db_service.delete("user:delete_test")

        # Vérifier qu'il n'existe plus
        result = await db_service.select("user:delete_test")
        assert len(result) == 0

    async def test_query_with_params(self, db_service):
        """Test de requête avec paramètres."""
        # Créer quelques enregistrements
        for i in range(3):
            user_data = {
                "email": f"query_test_{i}@example.com",
                "nom": f"Query Test {i}",
                "role": "notaire" if i % 2 == 0 else "assistant",
            }
            await db_service.create("user", user_data, record_id=f"query_test_{i}")

        # Requête avec paramètre
        query = "SELECT * FROM user WHERE role = $role"
        params = {"role": "notaire"}
        result = await db_service.query(query, params)

        assert result is not None
        assert len(result) > 0
        # Le premier élément du résultat contient les résultats
        users = result[0]
        assert len(users) == 2  # 2 notaires sur 3 utilisateurs

    async def test_record_id_format(self, db_service):
        """Test du format RecordID de SurrealDB."""
        # Créer avec un RecordID explicite
        from surrealdb import RecordID as RecordIDClass

        record_id = RecordIDClass("user", "record_id_test")
        user_data = {
            "email": "recordid@example.com",
            "nom": "RecordID Test",
            "role": "notaire",
        }

        result = await db_service.create("user", user_data, record_id="record_id_test")

        assert result is not None
        assert isinstance(result["id"], RecordIDClass)
        assert str(result["id"]) == "user:record_id_test"

    async def test_error_handling_invalid_table(self, db_service):
        """Test de gestion d'erreur pour une table invalide."""
        with pytest.raises(Exception):
            # Essayer de sélectionner depuis une table qui n'existe pas
            await db_service.select("invalid_table_name:123")
