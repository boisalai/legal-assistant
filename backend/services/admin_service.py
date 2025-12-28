"""
Service d'administration de la base de données SurrealDB.

Ce service fournit les fonctionnalités pour:
- Lister les tables et leurs statistiques
- Consulter les données des tables avec pagination
- Détecter les orphelins (Phase 2)
- Nettoyer les orphelins (Phase 3)
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from services.surreal_service import get_surreal_service
from models.admin_models import TableInfo, TableDataResponse

logger = logging.getLogger(__name__)


# Liste des tables connues dans l'application
KNOWN_TABLES = [
    {"name": "course", "display_name": "Cours"},
    {"name": "document", "display_name": "Documents"},
    {"name": "document_embedding", "display_name": "Embeddings"},
    {"name": "user", "display_name": "Utilisateurs"},
    {"name": "conversation", "display_name": "Conversations"},
    {"name": "summary", "display_name": "Résumés"},
    {"name": "user_activity", "display_name": "Activités"},
    {"name": "workflow_execution", "display_name": "Workflows"},
    # Tables legacy/potentiellement inutilisées
    {"name": "case", "display_name": "Cas (legacy)"},
    {"name": "judgment", "display_name": "Jugements (legacy)"},
    {"name": "analysis_result", "display_name": "Analyses (legacy)"},
    {"name": "embedding_chunk", "display_name": "Chunks (legacy)"},
]


class AdminService:
    """Service pour l'administration de la base de données."""

    def __init__(self):
        """Initialise le service admin."""
        self.db_service = get_surreal_service()

    def _serialize_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convertit un enregistrement SurrealDB en dict sérialisable JSON.

        Args:
            record: Enregistrement SurrealDB

        Returns:
            Dict sérialisable en JSON
        """
        from surrealdb.data.types.record_id import RecordID

        serialized = {}
        for key, value in record.items():
            if isinstance(value, RecordID):
                # Convert RecordID to string (format: "table:id")
                serialized[key] = str(value)
            elif isinstance(value, dict):
                # Recursively serialize nested dicts
                serialized[key] = self._serialize_record(value)
            elif isinstance(value, list):
                # Serialize lists
                serialized[key] = [
                    self._serialize_record(item) if isinstance(item, dict) else str(item) if hasattr(item, "__class__") and item.__class__.__name__ == "RecordID" else item
                    for item in value
                ]
            else:
                serialized[key] = value
        return serialized

    async def get_all_tables(self) -> List[TableInfo]:
        """
        Liste toutes les tables SurrealDB avec leurs statistiques.

        Returns:
            Liste de TableInfo avec row_count pour chaque table

        Raises:
            Exception: Si erreur lors de la récupération des tables
        """
        try:
            # Ensure connection
            if not self.db_service.db:
                await self.db_service.connect()

            tables_info: List[TableInfo] = []

            # Interroger chaque table connue pour obtenir le count
            for table_def in KNOWN_TABLES:
                table_name = table_def["name"]
                display_name = table_def["display_name"]

                try:
                    # Compter les lignes avec COUNT()
                    query = f"SELECT count() AS count FROM {table_name} GROUP ALL"
                    result = await self.db_service.db.query(query)

                    logger.info(f"📊 Count query for {table_name}: {query}")
                    logger.info(f"📊 Raw result: {result}")

                    # Extraire le count du résultat
                    # SurrealDB Python client retourne: [{ count: N }]
                    row_count = 0
                    if result and len(result) > 0:
                        first_item = result[0]
                        if isinstance(first_item, dict):
                            row_count = first_item.get("count", 0)
                            logger.info(f"✅ {table_name}: {row_count} rows")

                    tables_info.append(
                        TableInfo(
                            name=table_name,
                            display_name=display_name,
                            row_count=row_count,
                            has_orphans=False,  # Sera implémenté en Phase 2
                        )
                    )

                except Exception as e:
                    # Si la table n'existe pas, count = 0
                    logger.warning(f"Table {table_name} inaccessible: {e}")
                    tables_info.append(
                        TableInfo(
                            name=table_name,
                            display_name=display_name,
                            row_count=0,
                            has_orphans=False,
                        )
                    )

            return tables_info

        except Exception as e:
            logger.error(f"Erreur lors de la récupération des tables: {e}")
            raise

    async def get_table_data(
        self,
        table_name: str,
        skip: int = 0,
        limit: int = 50,
        sort_field: Optional[str] = None,
        sort_order: str = "asc",
    ) -> TableDataResponse:
        """
        Récupère les données paginées d'une table.

        Args:
            table_name: Nom de la table SurrealDB
            skip: Nombre de lignes à sauter (pagination)
            limit: Nombre de lignes à retourner (max 100)
            sort_field: Champ de tri (optionnel)
            sort_order: Ordre de tri ('asc' ou 'desc')

        Returns:
            TableDataResponse avec les lignes paginées

        Raises:
            ValueError: Si le nom de table est invalide
            Exception: Si erreur lors de la requête
        """
        # Validation: Vérifier que la table est dans la liste connue
        valid_tables = [t["name"] for t in KNOWN_TABLES]
        if table_name not in valid_tables:
            raise ValueError(f"Table invalide: {table_name}")

        # Limiter le nombre de résultats max
        limit = min(limit, 100)

        try:
            # Ensure connection
            if not self.db_service.db:
                await self.db_service.connect()

            # Construire la requête avec pagination
            query_parts = [f"SELECT * FROM {table_name}"]

            # Ajouter le tri si spécifié
            if sort_field:
                order_dir = "ASC" if sort_order.lower() == "asc" else "DESC"
                query_parts.append(f"ORDER BY {sort_field} {order_dir}")

            # Ajouter la pagination
            query_parts.append(f"LIMIT {limit}")
            if skip > 0:
                query_parts.append(f"START {skip}")

            query = " ".join(query_parts)

            # Exécuter la requête pour les données
            result = await self.db_service.db.query(query)

            # Extraire les lignes
            # SurrealDB Python client retourne directement une liste: [{ row1 }, { row2 }, ...]
            rows: List[Dict[str, Any]] = []
            if result and isinstance(result, list):
                # Convert RecordID objects to strings for JSON serialization
                rows = [self._serialize_record(row) for row in result]

            # Compter le total (requête séparée)
            count_query = f"SELECT count() AS count FROM {table_name} GROUP ALL"
            count_result = await self.db_service.db.query(count_query)

            # SurrealDB Python client retourne: [{ count: N }]
            total = 0
            if count_result and len(count_result) > 0:
                first_item = count_result[0]
                if isinstance(first_item, dict):
                    total = first_item.get("count", 0)

            return TableDataResponse(
                table_name=table_name,
                rows=rows,
                total=total,
                skip=skip,
                limit=limit,
            )

        except Exception as e:
            logger.error(
                f"Erreur lors de la récupération des données de {table_name}: {e}"
            )
            raise


# Instance globale du service
_admin_service: Optional[AdminService] = None


def get_admin_service() -> AdminService:
    """
    Retourne l'instance globale du service admin (singleton).

    Returns:
        Instance d'AdminService
    """
    global _admin_service
    if _admin_service is None:
        _admin_service = AdminService()
    return _admin_service
