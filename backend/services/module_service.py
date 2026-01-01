"""
Service pour la gestion des modules d'étude.

Un module est une unité d'organisation au sein d'un cours qui permet de:
- Grouper des documents par thème/chapitre
- Organiser les révisions (flashcards, quiz)
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any, Tuple

from services.surreal_service import get_surreal_service
from models.module_models import (
    ModuleCreate,
    ModuleUpdate,
    ModuleResponse,
)

logger = logging.getLogger(__name__)


def generate_hex_id() -> str:
    """Génère un ID hexadécimal court compatible SurrealDB."""
    return uuid.uuid4().hex[:8]


class ModuleService:
    """Service pour la gestion des modules."""

    def __init__(self):
        self.db = get_surreal_service()

    # =========================================================================
    # CRUD Operations
    # =========================================================================

    async def create_module(
        self,
        course_id: str,
        data: ModuleCreate
    ) -> ModuleResponse:
        """
        Crée un nouveau module pour un cours.

        Args:
            course_id: ID du cours
            data: Données du module

        Returns:
            Module créé
        """
        # Normaliser le course_id
        course_record_id = course_id.replace("course:", "")

        # Vérifier que le cours existe
        course_result = await self.db.query(
            "SELECT id FROM course WHERE id = type::thing('course', $record_id)",
            {"record_id": course_record_id}
        )

        if not course_result or len(course_result) == 0:
            raise ValueError(f"Cours non trouvé: {course_id}")

        # Générer l'ID et les timestamps
        module_id = generate_hex_id()
        now = datetime.now(timezone.utc).isoformat()

        # Créer le module
        module_data = {
            "course_id": f"course:{course_record_id}",
            "name": data.name,
            "order_index": data.order_index,
            "exam_weight": data.exam_weight,
            "created_at": now,
            "updated_at": now,
        }

        result = await self.db.query(
            f"CREATE module:{module_id} CONTENT $data",
            {"data": module_data}
        )

        if not result or len(result) == 0:
            raise RuntimeError("Erreur lors de la création du module")

        created = result[0]
        logger.info(f"Module créé: {module_id} pour cours {course_id}")

        return self._format_module_response(created)

    async def get_module(self, module_id: str) -> Optional[ModuleResponse]:
        """
        Récupère un module par son ID.

        Args:
            module_id: ID du module

        Returns:
            Module ou None si non trouvé
        """
        record_id = module_id.replace("module:", "")
        full_id = f"module:{record_id}"

        # Use direct record reference to handle both string and numeric IDs
        result = await self.db.query(
            f"SELECT * FROM {full_id}"
        )

        if not result or len(result) == 0:
            return None

        module = result[0]

        # Compter les documents assignés
        doc_count = await self._count_module_documents(module_id)
        module["document_count"] = doc_count

        return self._format_module_response(module)

    async def list_modules(
        self,
        course_id: str
    ) -> Tuple[List[ModuleResponse], int]:
        """
        Liste tous les modules d'un cours.

        Args:
            course_id: ID du cours

        Returns:
            Tuple (liste des modules, total)
        """
        # Normaliser le course_id
        if not course_id.startswith("course:"):
            course_id = f"course:{course_id}"

        result = await self.db.query(
            """
            SELECT * FROM module
            WHERE course_id = $course_id
            ORDER BY order_index ASC, created_at ASC
            """,
            {"course_id": course_id}
        )

        modules = []
        if result:
            for module in result:
                # Compter les documents
                module_id = str(module.get("id", ""))
                doc_count = await self._count_module_documents(module_id)
                module["document_count"] = doc_count
                modules.append(self._format_module_response(module))

        return modules, len(modules)

    async def update_module(
        self,
        module_id: str,
        data: ModuleUpdate
    ) -> Optional[ModuleResponse]:
        """
        Met à jour un module.

        Args:
            module_id: ID du module
            data: Données de mise à jour

        Returns:
            Module mis à jour ou None si non trouvé
        """
        record_id = module_id.replace("module:", "")

        # Vérifier que le module existe
        existing = await self.get_module(module_id)
        if not existing:
            return None

        # Construire les champs à mettre à jour
        update_fields = {}
        if data.name is not None:
            update_fields["name"] = data.name
        if data.order_index is not None:
            update_fields["order_index"] = data.order_index
        if data.exam_weight is not None:
            update_fields["exam_weight"] = data.exam_weight

        if not update_fields:
            return existing

        update_fields["updated_at"] = datetime.now(timezone.utc).isoformat()

        # Construire la requête de mise à jour
        set_clauses = ", ".join([f"{k} = ${k}" for k in update_fields.keys()])
        query = f"""
            UPDATE module
            SET {set_clauses}
            WHERE id = type::thing('module', $record_id)
        """
        params = {"record_id": record_id, **update_fields}

        await self.db.query(query, params)

        logger.info(f"Module mis à jour: {module_id}")
        return await self.get_module(module_id)

    async def delete_module(self, module_id: str) -> bool:
        """
        Supprime un module.

        Note: Les documents ne sont pas supprimés, juste désassignés.

        Args:
            module_id: ID du module

        Returns:
            True si supprimé, False si non trouvé
        """
        record_id = module_id.replace("module:", "")

        # Vérifier que le module existe
        existing = await self.get_module(module_id)
        if not existing:
            return False

        # Désassigner les documents (mettre module_id à null)
        full_module_id = f"module:{record_id}"
        await self.db.query(
            """
            UPDATE document
            SET module_id = NONE
            WHERE module_id = $module_id
            """,
            {"module_id": full_module_id}
        )

        # Supprimer le module
        await self.db.query(
            "DELETE module WHERE id = type::thing('module', $record_id)",
            {"record_id": record_id}
        )

        logger.info(f"Module supprimé: {module_id}")
        return True

    # =========================================================================
    # Document Assignment
    # =========================================================================

    async def assign_documents(
        self,
        module_id: str,
        document_ids: List[str]
    ) -> int:
        """
        Assigne des documents à un module.

        Args:
            module_id: ID du module
            document_ids: Liste des IDs de documents

        Returns:
            Nombre de documents assignés
        """
        record_id = module_id.replace("module:", "")
        full_module_id = f"module:{record_id}"

        # Vérifier que le module existe
        existing = await self.get_module(module_id)
        if not existing:
            raise ValueError(f"Module non trouvé: {module_id}")

        assigned_count = 0
        for doc_id in document_ids:
            doc_record_id = doc_id.replace("document:", "")

            result = await self.db.query(
                """
                UPDATE document
                SET module_id = $module_id
                WHERE id = type::thing('document', $doc_id)
                """,
                {"module_id": full_module_id, "doc_id": doc_record_id}
            )

            if result:
                assigned_count += 1

        logger.info(f"Assigné {assigned_count} documents au module {module_id}")
        return assigned_count

    async def unassign_documents(
        self,
        module_id: str,
        document_ids: List[str]
    ) -> int:
        """
        Retire des documents d'un module.

        Args:
            module_id: ID du module
            document_ids: Liste des IDs de documents

        Returns:
            Nombre de documents désassignés
        """
        unassigned_count = 0
        for doc_id in document_ids:
            doc_record_id = doc_id.replace("document:", "")

            result = await self.db.query(
                """
                UPDATE document
                SET module_id = NONE
                WHERE id = type::thing('document', $doc_id)
                """,
                {"doc_id": doc_record_id}
            )

            if result:
                unassigned_count += 1

        logger.info(f"Désassigné {unassigned_count} documents du module {module_id}")
        return unassigned_count

    async def get_module_documents(
        self,
        module_id: str
    ) -> List[Dict[str, Any]]:
        """
        Récupère tous les documents d'un module.

        Args:
            module_id: ID du module

        Returns:
            Liste des documents
        """
        if not module_id.startswith("module:"):
            module_id = f"module:{module_id}"

        result = await self.db.query(
            """
            SELECT * FROM document
            WHERE module_id = $module_id
            ORDER BY filename ASC
            """,
            {"module_id": module_id}
        )

        return result if result else []

    async def get_unassigned_documents(
        self,
        course_id: str
    ) -> List[Dict[str, Any]]:
        """
        Récupère les documents d'un cours qui ne sont assignés à aucun module.

        Args:
            course_id: ID du cours

        Returns:
            Liste des documents non assignés
        """
        if not course_id.startswith("course:"):
            course_id = f"course:{course_id}"

        result = await self.db.query(
            """
            SELECT * FROM document
            WHERE course_id = $course_id
            AND (module_id = NONE OR module_id = NULL)
            ORDER BY filename ASC
            """,
            {"course_id": course_id}
        )

        return result if result else []

    # =========================================================================
    # Helper Methods
    # =========================================================================

    async def _count_module_documents(self, module_id: str) -> int:
        """Compte le nombre de documents dans un module."""
        if not module_id.startswith("module:"):
            module_id = f"module:{module_id}"

        result = await self.db.query(
            """
            SELECT count() as total FROM document
            WHERE module_id = $module_id
            GROUP ALL
            """,
            {"module_id": module_id}
        )

        if result and len(result) > 0:
            return result[0].get("total", 0)
        return 0

    def _format_module_response(self, module: Dict[str, Any]) -> ModuleResponse:
        """Formate un module pour la réponse API."""
        module_id = module.get("id", "")
        if hasattr(module_id, "__str__"):
            module_id = str(module_id)

        created_at = module.get("created_at", "")
        if hasattr(created_at, "isoformat"):
            created_at = created_at.isoformat()

        updated_at = module.get("updated_at")
        if updated_at and hasattr(updated_at, "isoformat"):
            updated_at = updated_at.isoformat()

        return ModuleResponse(
            id=module_id,
            course_id=str(module.get("course_id", "")),
            name=module.get("name", ""),
            order_index=module.get("order_index", 0),
            description=module.get("description"),
            exam_weight=module.get("exam_weight"),
            created_at=created_at,
            updated_at=updated_at,
            document_count=module.get("document_count", 0)
        )


# ============================================================================
# Singleton
# ============================================================================

_module_service: Optional[ModuleService] = None


def get_module_service() -> ModuleService:
    """Get or create the module service singleton."""
    global _module_service
    if _module_service is None:
        _module_service = ModuleService()
    return _module_service
