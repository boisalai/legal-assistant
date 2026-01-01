"""
Service pour la gestion des modules d'étude.

Un module est une unité d'organisation au sein d'un cours qui permet de:
- Grouper des documents par thème/chapitre
- Suivre la progression d'apprentissage
- Organiser les révisions (flashcards, quiz)
"""

import logging
import re
import uuid
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any, Tuple

from services.surreal_service import get_surreal_service
from models.module_models import (
    ModuleCreate,
    ModuleUpdate,
    ModuleResponse,
    ModuleWithProgress,
    MasteryLevel,
    DetectedModule,
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
            "description": data.description,
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

        result = await self.db.query(
            "SELECT * FROM module WHERE id = type::thing('module', $record_id)",
            {"record_id": record_id}
        )

        if not result or len(result) == 0:
            return None

        module = result[0]

        # Compter les documents assignés
        doc_count = await self._count_module_documents(module_id)
        module["document_count"] = doc_count

        return self._format_module_response(module)

    async def get_module_with_progress(
        self,
        module_id: str,
        user_id: str = "user:default"
    ) -> Optional[ModuleWithProgress]:
        """
        Récupère un module avec ses métriques de progression.

        Args:
            module_id: ID du module
            user_id: ID de l'utilisateur

        Returns:
            Module avec progression ou None
        """
        module = await self.get_module(module_id)
        if not module:
            return None

        progress = await self._calculate_module_progress(module_id, user_id)

        return ModuleWithProgress(
            **module.model_dump(),
            **progress
        )

    async def list_modules(
        self,
        course_id: str,
        include_progress: bool = False,
        user_id: str = "user:default"
    ) -> Tuple[List[ModuleResponse], int]:
        """
        Liste tous les modules d'un cours.

        Args:
            course_id: ID du cours
            include_progress: Inclure les métriques de progression
            user_id: ID de l'utilisateur (pour progression)

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

                if include_progress:
                    progress = await self._calculate_module_progress(module_id, user_id)
                    formatted = self._format_module_response(module)
                    modules.append(ModuleWithProgress(
                        **formatted.model_dump(),
                        **progress
                    ))
                else:
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
        if data.description is not None:
            update_fields["description"] = data.description
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
    # Auto-detection
    # =========================================================================

    async def auto_detect_modules(
        self,
        course_id: str
    ) -> Tuple[List[DetectedModule], List[str]]:
        """
        Détecte automatiquement les modules à partir des noms de fichiers.

        Patterns reconnus:
        - "Module X - ..." ou "module-X-..."
        - "Chapitre X - ..." ou "chapitre-X-..."
        - "Semaine X - ..." ou "semaine-X-..."
        - Préfixes numériques: "01_...", "1-...", "1_..."

        Args:
            course_id: ID du cours

        Returns:
            Tuple (modules détectés, documents non assignables)
        """
        if not course_id.startswith("course:"):
            course_id = f"course:{course_id}"

        # Récupérer tous les documents du cours
        result = await self.db.query(
            """
            SELECT id, filename, linked_source FROM document
            WHERE course_id = $course_id
            ORDER BY filename ASC
            """,
            {"course_id": course_id}
        )

        if not result:
            return [], []

        # Patterns de détection
        patterns = [
            # Module X - Title ou module-X-title
            (r"[Mm]odule[\s_-]*(\d+)", "Module {num}"),
            # Chapitre X - Title
            (r"[Cc]hapitre[\s_-]*(\d+)", "Chapitre {num}"),
            # Semaine X - Title
            (r"[Ss]emaine[\s_-]*(\d+)", "Semaine {num}"),
            # Préfixe numérique: 01_, 1-, etc.
            (r"^(\d{1,2})[\s_-]", "Section {num}"),
        ]

        # Grouper les documents par module détecté
        module_groups: Dict[str, List[str]] = {}
        unassigned: List[str] = []

        for doc in result:
            doc_id = str(doc.get("id", ""))
            filename = doc.get("filename") or ""

            # Essayer aussi le relative_path si disponible
            linked = doc.get("linked_source")
            if linked and isinstance(linked, dict):
                relative_path = linked.get("relative_path", "")
                if relative_path:
                    filename = relative_path

            detected = False
            for pattern, name_template in patterns:
                match = re.search(pattern, filename)
                if match:
                    num = match.group(1)
                    module_name = name_template.format(num=num)
                    if module_name not in module_groups:
                        module_groups[module_name] = []
                    module_groups[module_name].append(doc_id)
                    detected = True
                    break

            if not detected:
                unassigned.append(doc_id)

        # Convertir en liste de DetectedModule
        detected_modules = []
        for name, doc_ids in sorted(module_groups.items()):
            detected_modules.append(DetectedModule(
                suggested_name=name,
                document_ids=doc_ids,
                document_count=len(doc_ids)
            ))

        return detected_modules, unassigned

    async def create_modules_from_detection(
        self,
        course_id: str,
        detected_modules: List[DetectedModule],
        assign_documents: bool = True
    ) -> List[ModuleResponse]:
        """
        Crée des modules à partir de la détection automatique.

        Args:
            course_id: ID du cours
            detected_modules: Modules détectés
            assign_documents: Assigner automatiquement les documents

        Returns:
            Liste des modules créés
        """
        created = []
        for idx, detected in enumerate(detected_modules):
            module_data = ModuleCreate(
                name=detected.suggested_name,
                order_index=idx
            )

            module = await self.create_module(course_id, module_data)
            created.append(module)

            if assign_documents and detected.document_ids:
                await self.assign_documents(module.id, detected.document_ids)

        return created

    # =========================================================================
    # Progress Calculation
    # =========================================================================

    async def _calculate_module_progress(
        self,
        module_id: str,
        user_id: str
    ) -> Dict[str, Any]:
        """
        Calcule les métriques de progression pour un module.

        Args:
            module_id: ID du module
            user_id: ID de l'utilisateur

        Returns:
            Dict avec les métriques de progression
        """
        if not module_id.startswith("module:"):
            module_id = f"module:{module_id}"

        # Compter les documents
        doc_result = await self.db.query(
            """
            SELECT count() as total FROM document
            WHERE module_id = $module_id
            GROUP ALL
            """,
            {"module_id": module_id}
        )

        documents_total = 0
        if doc_result and len(doc_result) > 0:
            documents_total = doc_result[0].get("total", 0)

        # TODO: Compter les documents complétés (quand document_progress sera implémenté)
        documents_completed = 0
        reading_percent = 0.0

        # Récupérer les stats des flashcards pour ce module
        # Les flashcard_decks peuvent avoir un module_id ou on peut les lier via les documents
        flashcard_result = await self.db.query(
            """
            SELECT
                count() as total,
                count(status = 'mastered') as mastered
            FROM flashcard
            WHERE deck_id IN (
                SELECT id FROM flashcard_deck WHERE module_id = $module_id
            )
            GROUP ALL
            """,
            {"module_id": module_id}
        )

        flashcards_total = 0
        flashcards_mastered = 0
        if flashcard_result and len(flashcard_result) > 0:
            stats = flashcard_result[0]
            flashcards_total = stats.get("total", 0)
            flashcards_mastered = stats.get("mastered", 0)

        flashcard_percent = (flashcards_mastered / flashcards_total * 100) if flashcards_total > 0 else 0.0

        # TODO: Quiz stats (quand quiz_attempt sera implémenté)
        quiz_attempts = 0
        quiz_average_score = 0.0
        quiz_best_score = 0.0

        # Calculer la progression globale
        # Pondération: lecture 20%, flashcards 40%, quiz 40%
        overall_progress = (
            reading_percent * 0.20 +
            flashcard_percent * 0.40 +
            quiz_average_score * 0.40
        )

        # Déterminer le niveau de maîtrise
        if overall_progress >= 85:
            mastery_level = MasteryLevel.MASTERED
        elif overall_progress >= 65:
            mastery_level = MasteryLevel.PROFICIENT
        elif overall_progress >= 25:
            mastery_level = MasteryLevel.LEARNING
        else:
            mastery_level = MasteryLevel.NOT_STARTED

        return {
            "documents_total": documents_total,
            "documents_completed": documents_completed,
            "reading_percent": reading_percent,
            "flashcards_total": flashcards_total,
            "flashcards_mastered": flashcards_mastered,
            "flashcard_percent": flashcard_percent,
            "quiz_attempts": quiz_attempts,
            "quiz_average_score": quiz_average_score,
            "quiz_best_score": quiz_best_score,
            "overall_progress": overall_progress,
            "mastery_level": mastery_level,
            "total_study_time_seconds": 0,  # TODO: Implémenter avec study_session
            "last_activity_at": None,  # TODO: Implémenter avec study_session
        }

    async def get_course_progress_summary(
        self,
        course_id: str,
        user_id: str = "user:default"
    ) -> Dict[str, Any]:
        """
        Récupère un résumé de la progression pour tout le cours.

        Args:
            course_id: ID du cours
            user_id: ID de l'utilisateur

        Returns:
            Dict avec le résumé de progression
        """
        modules, _ = await self.list_modules(course_id, include_progress=True, user_id=user_id)

        if not modules:
            return {
                "course_id": course_id,
                "modules": [],
                "overall_progress": 0.0,
                "recommended_module_id": None,
                "recommendation_message": "Aucun module configuré pour ce cours."
            }

        # Calculer la progression globale pondérée
        total_weight = sum(m.exam_weight or 1.0 for m in modules)
        weighted_progress = sum(
            (m.exam_weight or 1.0) * m.overall_progress
            for m in modules
        ) / total_weight if total_weight > 0 else 0

        # Trouver le module le plus faible
        weakest = min(modules, key=lambda m: m.overall_progress)

        # Générer une recommandation
        if weakest.reading_percent < 50:
            recommendation = f"Continuez la lecture de {weakest.name}"
        elif weakest.flashcard_percent < 50:
            recommendation = f"Révisez les flashcards de {weakest.name}"
        elif weakest.quiz_average_score < 70:
            recommendation = f"Faites un quiz sur {weakest.name}"
        else:
            recommendation = "Vous êtes sur la bonne voie! Continuez à réviser."

        return {
            "course_id": course_id,
            "modules": [m.model_dump() for m in modules],
            "overall_progress": weighted_progress,
            "recommended_module_id": weakest.id,
            "recommendation_message": recommendation
        }

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
