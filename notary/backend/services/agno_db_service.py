"""
Service unifié pour SurrealDB avec pattern officiel Agno.

Ce service combine:
- Persistance automatique des workflows Agno (tables auto-créées)
- Tables métier personnalisées (user, dossier, document, checklist)

Architecture basée sur les exemples officiels:
- https://github.com/agno-agi/agno/blob/main/cookbook/db/surrealdb/surrealdb_for_workflow.py
- https://github.com/agno-agi/agno/blob/main/cookbook/db/surrealdb/surrealdb_for_agent.py
"""

import logging
from typing import Any, Optional
from datetime import datetime

from config import settings

logger = logging.getLogger(__name__)


class AgnoDBService:
    """
    Service unifié pour SurrealDB avec pattern officiel Agno.

    Pattern:
    - Une seule connexion SurrealDB pour tout
    - Agno crée automatiquement ses tables (workflow_runs, agent_sessions, etc.)
    - On crée manuellement les tables métier (dossier, document, user, checklist)

    Exemple d'utilisation:
    ```python
    # Initialiser le service
    service = AgnoDBService()

    # Pour Agno Workflow
    workflow = Workflow(
        name="analyse_dossier",
        db=service.get_agno_db(),  # ✅ Persistance automatique
    )

    # Pour tables métier
    dossier = await service.create_dossier(
        nom_dossier="Test",
        user_id="user:test"
    )
    ```
    """

    def __init__(self):
        """
        Initialise le service avec configuration Agno officielle.

        La connexion utilise:
        - ws://localhost:8001/rpc (WebSocket SurrealDB)
        - Credentials root/root
        - Namespace "agno" (pattern officiel Agno - fixé)
        - Database selon settings

        Note: Le namespace "agno" est utilisé par Agno pour stocker:
        - workflow_runs
        - workflow_sessions
        - agent_sessions
        - team_sessions

        Les tables métier (dossier, document, etc.) restent dans namespace "notary"
        via SurrealDBService.
        """
        self._db = None
        self._initialized = False

        # Configuration depuis settings
        self.url = settings.surreal_url
        # IMPORTANT: Utiliser namespace "agno" (pattern officiel Agno)
        # Les tables Agno (workflow_runs, agent_sessions, etc.) sont dans ce namespace
        self.namespace = "agno"  # Forcé à "agno" pour compatibilité Agno
        self.database = settings.surreal_database
        self.creds = {
            "username": settings.surreal_username,
            "password": settings.surreal_password
        }

        logger.info(
            f"AgnoDBService initialized - "
            f"URL: {self.url}, "
            f"NS: {self.namespace}, "
            f"DB: {self.database}"
        )

    def _ensure_initialized(self):
        """
        Initialise la connexion SurrealDB (lazy).

        Pattern officiel Agno:
        from agno.db.surrealdb import SurrealDb

        db = SurrealDb(
            None,  # session
            "ws://localhost:8000",
            {"user": "root", "pass": "root"},
            "agno",
            "notary_db"
        )
        """
        if not self._initialized:
            try:
                from agno.db.surrealdb import SurrealDb

                self._db = SurrealDb(
                    None,  # session (None = auto)
                    self.url,
                    self.creds,
                    self.namespace,
                    self.database
                )

                self._initialized = True
                logger.info("✅ Connexion SurrealDB Agno établie")

            except Exception as e:
                logger.error(f"❌ Erreur initialisation SurrealDB: {e}")
                raise

    def get_agno_db(self):
        """
        Retourne la connexion SurrealDB pour Agno.

        À utiliser dans les Workflows/Agents/Teams:
        ```python
        workflow = Workflow(
            name="analyse",
            db=service.get_agno_db()  # ✅ Persistance automatique
        )
        ```

        Returns:
            SurrealDb: Instance de connexion Agno
        """
        self._ensure_initialized()
        return self._db

    # =========================================================================
    # Tables Métier (CRUD Manuel)
    # =========================================================================

    async def create_record(
        self,
        table: str,
        data: dict[str, Any],
        record_id: Optional[str] = None
    ) -> dict[str, Any]:
        """
        Crée un enregistrement dans une table métier.

        Args:
            table: Nom de la table (ex: "dossier", "user")
            data: Données à insérer
            record_id: ID optionnel (auto-généré si None)

        Returns:
            L'enregistrement créé
        """
        self._ensure_initialized()

        # Ajouter timestamp
        data["created_at"] = datetime.utcnow()

        # Utiliser l'API SurrealDB sous-jacente
        # Note: La classe SurrealDb d'Agno wraps surrealdb.Surreal
        #       On accède au client via .client
        try:
            # Accéder au client SurrealDB sous-jacent via .client
            surreal_client = self._db.client

            if record_id:
                result = await surreal_client.create(f"{table}:{record_id}", data)
            else:
                result = await surreal_client.create(table, data)

            logger.info(f"✅ Created {table} record: {result}")
            return result

        except Exception as e:
            logger.error(f"❌ Error creating {table}: {e}")
            raise

    async def query(
        self,
        query: str,
        variables: Optional[dict[str, Any]] = None
    ) -> list[Any]:
        """
        Exécute une requête SurrealQL.

        Args:
            query: Requête SurrealQL
            variables: Variables de la requête

        Returns:
            Résultats de la requête
        """
        self._ensure_initialized()

        try:
            # Accéder au client SurrealDB sous-jacent via .client
            surreal_client = self._db.client
            result = await surreal_client.query(query, variables or {})

            return result

        except Exception as e:
            logger.error(f"❌ Error executing query: {e}")
            raise

    async def select(self, table_or_id: str) -> list[Any]:
        """
        Sélectionne un ou plusieurs enregistrements.

        Args:
            table_or_id: Nom de table ou RecordID (ex: "dossier" ou "dossier:abc")

        Returns:
            Liste d'enregistrements
        """
        self._ensure_initialized()

        try:
            from surrealdb import RecordID

            # Convertir string en RecordID si nécessaire
            if ":" in table_or_id:
                table, identifier = table_or_id.split(":", 1)
                record_id = RecordID(table, identifier)
            else:
                record_id = table_or_id

            # Accéder au client SurrealDB sous-jacent via .client
            surreal_client = self._db.client
            result = await surreal_client.select(record_id)

            return result if isinstance(result, list) else [result] if result else []

        except Exception as e:
            logger.error(f"❌ Error selecting {table_or_id}: {e}")
            raise

    async def update(
        self,
        table_or_id: str,
        data: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Met à jour un enregistrement.

        Args:
            table_or_id: RecordID (ex: "dossier:abc")
            data: Données à mettre à jour

        Returns:
            L'enregistrement mis à jour
        """
        self._ensure_initialized()

        # Ajouter timestamp
        data["updated_at"] = datetime.utcnow()

        try:
            from surrealdb import RecordID

            # Convertir en RecordID
            if ":" in table_or_id:
                table, identifier = table_or_id.split(":", 1)
                record_id = RecordID(table, identifier)
            else:
                raise ValueError(f"Invalid RecordID format: {table_or_id}")

            # Accéder au client SurrealDB sous-jacent via .client
            surreal_client = self._db.client
            result = await surreal_client.merge(record_id, data)

            logger.info(f"✅ Updated {table_or_id}")
            return result

        except Exception as e:
            logger.error(f"❌ Error updating {table_or_id}: {e}")
            raise

    async def delete(self, table_or_id: str) -> bool:
        """
        Supprime un enregistrement.

        Args:
            table_or_id: RecordID (ex: "dossier:abc")

        Returns:
            True si supprimé
        """
        self._ensure_initialized()

        try:
            from surrealdb import RecordID

            # Convertir en RecordID
            if ":" in table_or_id:
                table, identifier = table_or_id.split(":", 1)
                record_id = RecordID(table, identifier)
            else:
                raise ValueError(f"Invalid RecordID format: {table_or_id}")

            # Accéder au client SurrealDB sous-jacent via .client
            surreal_client = self._db.client
            await surreal_client.delete(record_id)

            logger.info(f"✅ Deleted {table_or_id}")
            return True

        except Exception as e:
            logger.error(f"❌ Error deleting {table_or_id}: {e}")
            raise

    async def close(self):
        """Ferme la connexion SurrealDB."""
        if self._initialized and self._db:
            try:
                # SurrealDb d'Agno gère sa propre connexion
                # On peut simplement marquer comme fermé
                self._initialized = False
                logger.info("✅ Connexion SurrealDB fermée")
            except Exception as e:
                logger.error(f"❌ Erreur fermeture connexion: {e}")

    # =========================================================================
    # Helpers pour Workflow History
    # =========================================================================

    async def get_workflow_history(
        self,
        dossier_id: Optional[str] = None,
        limit: int = 10
    ) -> list[dict[str, Any]]:
        """
        Récupère l'historique des exécutions de workflows.

        Args:
            dossier_id: Filtrer par dossier (optionnel)
            limit: Nombre max de résultats

        Returns:
            Liste des workflow runs
        """
        if dossier_id:
            query = """
                SELECT * FROM workflow_runs
                WHERE metadata.dossier_id = $dossier_id
                ORDER BY created_at DESC
                LIMIT $limit
            """
            variables = {"dossier_id": dossier_id, "limit": limit}
        else:
            query = """
                SELECT * FROM workflow_runs
                ORDER BY created_at DESC
                LIMIT $limit
            """
            variables = {"limit": limit}

        results = await self.query(query, variables)

        # Extraire les résultats de la réponse SurrealDB
        if results and len(results) > 0:
            return results[0] if isinstance(results[0], list) else results

        return []


# =========================================================================
# Singleton Global
# =========================================================================

_agno_db_service: Optional[AgnoDBService] = None


def get_agno_db_service() -> AgnoDBService:
    """
    Retourne l'instance singleton du AgnoDBService.

    Usage:
    ```python
    service = get_agno_db_service()
    db = service.get_agno_db()
    ```
    """
    global _agno_db_service

    if _agno_db_service is None:
        _agno_db_service = AgnoDBService()

    return _agno_db_service
