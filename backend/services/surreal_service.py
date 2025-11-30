"""
Service SurrealDB - Gestion de la connexion et des opérations de base

Ce service fournit une interface pour interagir avec SurrealDB.
Il gère la connexion, l'authentification et les opérations CRUD de base.
"""

import logging
from typing import Any, Optional, Union
from contextlib import asynccontextmanager

from surrealdb import AsyncSurreal

logger = logging.getLogger(__name__)


class SurrealDBService:
    """
    Service principal pour interagir avec SurrealDB.

    Exemple d'utilisation:
    ```python
    service = SurrealDBService(
        url="ws://localhost:8002/rpc",
        namespace="notary",
        database="notary_db"
    )

    await service.connect()

    # Créer un enregistrement
    user = await service.create("user", {
        "email": "test@example.com",
        "nom": "Test",
        "prenom": "User"
    })

    # Récupérer un enregistrement
    user = await service.select("user:test_user")

    # Requête SurrealQL
    results = await service.query("SELECT * FROM user WHERE email = $email", {
        "email": "test@example.com"
    })

    await service.disconnect()
    ```
    """

    def __init__(
        self,
        url: str,
        namespace: str,
        database: str,
        username: str = "root",
        password: str = "root"
    ):
        """
        Initialise le service SurrealDB.

        Args:
            url: URL de connexion (ws://localhost:8002/rpc pour local)
            namespace: Namespace SurrealDB
            database: Nom de la database
            username: Nom d'utilisateur (défaut: root)
            password: Mot de passe (défaut: root)
        """
        self.url = url
        self.namespace = namespace
        self.database = database
        self.username = username
        self.password = password
        self.db: Optional[AsyncSurreal] = None

        logger.info(f"SurrealDBService initialized - {url} (ns:{namespace}, db:{database})")

    async def connect(self) -> None:
        """
        Établit la connexion à SurrealDB.

        Raises:
            RuntimeError: Si la connexion échoue
        """
        try:
            logger.info("Connecting to SurrealDB...")

            # Dans la nouvelle API, on passe l'URL au constructeur
            self.db = AsyncSurreal(self.url)

            # Note: connect() est appelé automatiquement, pas besoin de l'appeler
            logger.info(f"Connected to {self.url}")

            # Authentification (si credentials fournis)
            if self.username and self.password:
                try:
                    await self.db.signin({"username": self.username, "password": self.password})
                    logger.info(f"Authenticated as {self.username}")
                except Exception as auth_err:
                    # En mode --allow-all, l'auth peut échouer mais la connexion reste valide
                    logger.warning(f"Auth skipped (allow-all mode?): {auth_err}")

            # Sélection du namespace et de la database
            await self.db.use(self.namespace, self.database)
            logger.info(f"Using namespace '{self.namespace}' and database '{self.database}'")

            logger.info("SurrealDB connection established successfully")

        except Exception as e:
            logger.error(f"Failed to connect to SurrealDB: {e}")
            raise RuntimeError(f"SurrealDB connection failed: {e}") from e

    async def disconnect(self) -> None:
        """Ferme la connexion à SurrealDB."""
        if self.db:
            try:
                await self.db.close()
                logger.info("Disconnected from SurrealDB")
            except Exception as e:
                logger.warning(f"Error while disconnecting: {e}")
            finally:
                self.db = None

    def _ensure_connected(self) -> None:
        """Vérifie que la connexion est établie."""
        if not self.db:
            raise RuntimeError(
                "Database not connected. Call connect() first."
            )

    # =========================================================================
    # Opérations CRUD de base
    # =========================================================================

    async def query(
        self,
        query: str,
        params: Optional[dict[str, Any]] = None
    ) -> Any:
        """
        Exécute une requête SurrealQL brute.

        Args:
            query: Requête SurrealQL
            params: Paramètres de la requête (optionnel)

        Returns:
            Résultat de la requête

        Example:
            ```python
            results = await service.query(
                "SELECT * FROM user WHERE email = $email",
                {"email": "test@example.com"}
            )
            ```
        """
        self._ensure_connected()

        try:
            logger.debug(f"Executing query: {query}")
            if params:
                logger.debug(f"With params: {params}")

            result = await self.db.query(query, params)
            return result

        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            raise

    async def create(
        self,
        table: str,
        data: dict[str, Any],
        record_id: Optional[str] = None
    ) -> Any:
        """
        Crée un nouvel enregistrement.

        Args:
            table: Nom de la table
            data: Données de l'enregistrement
            record_id: ID spécifique (optionnel, auto-généré sinon)

        Returns:
            Enregistrement créé

        Example:
            ```python
            # ID auto-généré
            user = await service.create("user", {
                "email": "test@example.com",
                "nom": "Test"
            })

            # ID spécifique
            user = await service.create("user", {
                "email": "admin@example.com",
                "nom": "Admin"
            }, record_id="admin_user")
            ```
        """
        self._ensure_connected()

        try:
            thing = f"{table}:{record_id}" if record_id else table
            logger.debug(f"Creating record in '{thing}': {data}")

            result = await self.db.create(thing, data)
            logger.info(f"Created record: {result}")
            return result

        except Exception as e:
            logger.error(f"Failed to create record: {e}")
            raise

    async def select(self, thing: str) -> Any:
        """
        Récupère un ou plusieurs enregistrements.

        Args:
            thing: Table (ex: "user") ou record spécifique (ex: "user:123")

        Returns:
            Enregistrement(s) trouvé(s)

        Example:
            ```python
            # Tous les users
            users = await service.select("user")

            # User spécifique
            user = await service.select("user:test_user")
            ```
        """
        self._ensure_connected()

        try:
            logger.debug(f"Selecting: {thing}")
            result = await self.db.select(thing)
            return result

        except Exception as e:
            logger.error(f"Failed to select: {e}")
            raise

    async def update(
        self,
        thing: str,
        data: dict[str, Any]
    ) -> Any:
        """
        Met à jour un enregistrement (remplace complètement).

        Args:
            thing: Record à mettre à jour (ex: "user:123")
            data: Nouvelles données complètes

        Returns:
            Enregistrement mis à jour

        Example:
            ```python
            updated = await service.update("user:test_user", {
                "email": "newemail@example.com",
                "nom": "New Name"
            })
            ```
        """
        self._ensure_connected()

        try:
            logger.debug(f"Updating {thing}: {data}")
            result = await self.db.update(thing, data)
            logger.info(f"Updated record: {result}")
            return result

        except Exception as e:
            logger.error(f"Failed to update: {e}")
            raise

    async def merge(
        self,
        thing: str,
        data: dict[str, Any]
    ) -> Any:
        """
        Fusionne des données dans un enregistrement (mise à jour partielle).

        Args:
            thing: Record à modifier (ex: "user:123")
            data: Données à fusionner

        Returns:
            Enregistrement modifié

        Example:
            ```python
            # Met à jour seulement l'email, garde les autres champs
            updated = await service.merge("user:test_user", {
                "email": "newemail@example.com"
            })
            ```
        """
        self._ensure_connected()

        try:
            logger.debug(f"Merging into {thing}: {data}")
            result = await self.db.merge(thing, data)
            logger.info(f"Merged record: {result}")
            return result

        except Exception as e:
            logger.error(f"Failed to merge: {e}")
            raise

    async def delete(self, thing: str) -> Any:
        """
        Supprime un ou plusieurs enregistrements.

        Args:
            thing: Table ou record spécifique

        Returns:
            Enregistrement(s) supprimé(s)

        Example:
            ```python
            # Supprimer un user spécifique
            deleted = await service.delete("user:test_user")

            # Supprimer TOUS les users (attention!)
            deleted = await service.delete("user")
            ```
        """
        self._ensure_connected()

        try:
            logger.debug(f"Deleting: {thing}")
            result = await self.db.delete(thing)
            logger.info(f"Deleted: {result}")
            return result

        except Exception as e:
            logger.error(f"Failed to delete: {e}")
            raise

    # =========================================================================
    # Relations graphe
    # =========================================================================

    async def relate(
        self,
        from_thing: str,
        relation: str,
        to_thing: str,
        data: Optional[dict[str, Any]] = None
    ) -> Any:
        """
        Crée une relation graphe entre deux enregistrements.

        Args:
            from_thing: Record source (ex: "personne:jean")
            relation: Type de relation (ex: "vend")
            to_thing: Record cible (ex: "propriete:maison123")
            data: Données additionnelles de la relation (optionnel)

        Returns:
            Relation créée

        Example:
            ```python
            # Créer une relation simple
            await service.relate(
                "personne:jean",
                "vend",
                "propriete:maison123"
            )

            # Avec des données additionnelles
            await service.relate(
                "personne:jean",
                "vend",
                "propriete:maison123",
                {
                    "prix": 450000,
                    "date_offre": "2025-10-15",
                    "dossier": "dossier:xyz789"
                }
            )
            ```
        """
        self._ensure_connected()

        try:
            # Construire la requête RELATE
            data_clause = ""
            if data:
                # Convertir le dict en format SurrealQL (sans accolades)
                fields = ", ".join([f"{k} = ${k}" for k in data.keys()])
                data_clause = f" SET {fields}"

            query = f"RELATE {from_thing}->{relation}->{to_thing}{data_clause}"

            logger.debug(f"Creating relation: {query}")
            result = await self.query(query, data)
            logger.info(f"Created relation: {result}")
            return result

        except Exception as e:
            logger.error(f"Failed to create relation: {e}")
            raise

    # =========================================================================
    # Live Queries (temps réel)
    # =========================================================================

    async def live(self, query: str, callback: callable) -> str:
        """
        Crée une live query pour suivre les changements en temps réel.

        Args:
            query: Requête SurrealQL à surveiller
            callback: Fonction appelée à chaque changement (action, data)

        Returns:
            UUID de la live query (pour kill() plus tard)

        Example:
            ```python
            def on_change(action, data):
                print(f"Action: {action}, Data: {data}")

            # S'abonner aux changements
            query_uuid = await service.live(
                "SELECT * FROM workflow_execution WHERE status = 'running'",
                on_change
            )

            # Plus tard: se désabonner
            await service.kill(query_uuid)
            ```
        """
        self._ensure_connected()

        try:
            logger.debug(f"Creating live query: {query}")
            query_uuid = await self.db.live(query, callback)
            logger.info(f"Live query created: {query_uuid}")
            return query_uuid

        except Exception as e:
            logger.error(f"Failed to create live query: {e}")
            raise

    async def kill(self, query_uuid: str) -> None:
        """
        Arrête une live query.

        Args:
            query_uuid: UUID de la live query à arrêter
        """
        self._ensure_connected()

        try:
            logger.debug(f"Killing live query: {query_uuid}")
            await self.db.kill(query_uuid)
            logger.info(f"Live query killed: {query_uuid}")

        except Exception as e:
            logger.error(f"Failed to kill live query: {e}")
            raise


# =========================================================================
# Instance globale (singleton pattern)
# =========================================================================

# Cette instance sera initialisée au démarrage de l'application
surreal_service: Optional[SurrealDBService] = None


def get_surreal_service() -> SurrealDBService:
    """
    Récupère l'instance globale du service SurrealDB.

    Returns:
        Instance du service

    Raises:
        RuntimeError: Si le service n'a pas été initialisé
    """
    if surreal_service is None:
        raise RuntimeError(
            "SurrealDB service not initialized. "
            "Call init_surreal_service() first."
        )
    return surreal_service


def init_surreal_service(
    url: str,
    namespace: str,
    database: str,
    username: str = "root",
    password: str = "root"
) -> SurrealDBService:
    """
    Initialise l'instance globale du service SurrealDB.

    Args:
        url: URL de connexion
        namespace: Namespace
        database: Database
        username: Nom d'utilisateur
        password: Mot de passe

    Returns:
        Instance du service initialisée
    """
    global surreal_service
    surreal_service = SurrealDBService(
        url=url,
        namespace=namespace,
        database=database,
        username=username,
        password=password
    )
    return surreal_service


# =========================================================================
# Context manager pour utilisation temporaire
# =========================================================================

@asynccontextmanager
async def get_db_connection(
    url: str = "ws://localhost:8002/rpc",
    namespace: str = "notary",
    database: str = "notary_db"
):
    """
    Context manager pour connexion temporaire à SurrealDB.

    Utile pour les scripts et tests.

    Example:
        ```python
        async with get_db_connection() as db:
            users = await db.select("user")
            print(users)
        ```
    """
    service = SurrealDBService(url, namespace, database)
    await service.connect()

    try:
        yield service
    finally:
        await service.disconnect()
