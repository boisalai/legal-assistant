"""
Service métier pour la gestion des dossiers notariaux.

Ce service gère:
- CRUD des dossiers
- Upload et gestion des documents
- Orchestration de l'analyse via Agno
- Génération de checklists
"""

import hashlib
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Optional
from uuid import uuid4

from models import (
    Dossier,
    DossierCreate,
    DossierUpdate,
    Document,
    DocumentCreate,
    Checklist,
)
from services.surreal_service import SurrealDBService

logger = logging.getLogger(__name__)


class DossierService:
    """
    Service principal pour gérer les dossiers notariaux.

    Architecture hybride (Sprint 1 - Migration SurrealDB):
    - Utilise SurrealDBService pour CRUD des tables métier
    - Utilise AgnoDBService (optionnel) pour persistance automatique des workflows

    Exemple d'utilisation:
    ```python
    service = DossierService(
        db_service,
        upload_dir="/path/to/uploads",
        agno_db_service=agno_service  # Pour persistance workflow
    )

    # Créer un dossier
    dossier = await service.create_dossier(
        nom_dossier="Vente 123 rue Principale",
        user_id="user:test_notaire"
    )

    # Ajouter un document
    doc = await service.add_document(
        dossier_id=dossier.id,
        file_content=pdf_bytes,
        filename="offre_achat.pdf"
    )

    # Lancer l'analyse (avec persistance Agno si agno_db_service fourni)
    checklist = await service.analyser_dossier(dossier.id)
    ```
    """

    def __init__(
        self,
        db: SurrealDBService,
        upload_dir: str | Path,
        agno_db_service=None
    ):
        """
        Initialise le service des dossiers.

        Args:
            db: Instance du service SurrealDB (pour CRUD)
            upload_dir: Répertoire de stockage des fichiers uploadés
            agno_db_service: Instance AgnoDBService (optionnel, pour workflow)
        """
        self.db = db
        self.agno_db_service = agno_db_service
        self.upload_dir = Path(upload_dir)
        self.upload_dir.mkdir(parents=True, exist_ok=True)

        logger.info(
            f"DossierService initialized - "
            f"Upload dir: {self.upload_dir}, "
            f"Agno persistence: {'enabled' if agno_db_service else 'disabled'}"
        )

    # =========================================================================
    # CRUD Dossiers
    # =========================================================================

    async def create_dossier(
        self,
        nom_dossier: str,
        user_id: str,
        type_transaction: Optional[str] = None,
    ) -> Dossier:
        """
        Crée un nouveau dossier.

        Args:
            nom_dossier: Nom du dossier
            user_id: ID de l'utilisateur propriétaire (format: "user:xxx")
            type_transaction: Type de transaction (optionnel)

        Returns:
            Le dossier créé
        """
        logger.info(f"Creating dossier: {nom_dossier} for user {user_id}")

        # Générer un ID unique (juste l'identifiant, pas le préfixe de table)
        dossier_id = uuid4().hex[:12]

        # Convertir user_id en RecordID si nécessaire
        from surrealdb import RecordID as RecordIDClass

        if isinstance(user_id, str):
            # Extraire table et id de la string "user:xxx"
            if ":" in user_id:
                table_name, identifier = user_id.split(":", 1)
                user_id_obj = RecordIDClass(table_name, identifier)
            else:
                user_id_obj = RecordIDClass("user", user_id)
        else:
            user_id_obj = user_id

        # Données du dossier
        dossier_data = {
            "nom_dossier": nom_dossier,
            "user_id": user_id_obj,
            "type_transaction": type_transaction,
            "statut": "nouveau",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }

        # Créer dans SurrealDB
        result = await self.db.create("dossier", dossier_data, record_id=dossier_id)

        logger.info(f"Dossier created: {result}")

        # Retourner le modèle Pydantic
        return Dossier(**self._format_result(result))

    async def get_dossier(self, dossier_id: str) -> Optional[Dossier]:
        """
        Récupère un dossier par son ID.

        Args:
            dossier_id: ID du dossier (format: "dossier:xxx" ou "dossier_xxx")

        Returns:
            Le dossier ou None si introuvable
        """
        from surrealdb import RecordID as RecordIDClass

        # Normaliser l'ID
        if not dossier_id.startswith("dossier:"):
            dossier_id = f"dossier:{dossier_id}"

        # Parser l'ID: "dossier:858fde5e5f23" → table="dossier", record_id="858fde5e5f23"
        table, record_id = dossier_id.split(":", 1)

        # Utiliser RecordID selon la documentation officielle SurrealDB
        # https://surrealdb.com/docs/sdk/python/methods/select
        result = await self.db.select(RecordIDClass(table, record_id))

        if not result:
            return None

        return Dossier(**self._format_result(result))

    async def list_dossiers(
        self, user_id: Optional[str] = None, limit: int = 50
    ) -> list[Dossier]:
        """
        Liste les dossiers, optionnellement filtrés par utilisateur.

        Args:
            user_id: ID de l'utilisateur (optionnel)
            limit: Nombre max de résultats

        Returns:
            Liste de dossiers
        """
        if user_id:
            query = "SELECT * FROM dossier WHERE user_id = $user_id ORDER BY created_at DESC LIMIT $limit"
            params = {"user_id": user_id, "limit": limit}
        else:
            query = "SELECT * FROM dossier ORDER BY created_at DESC LIMIT $limit"
            params = {"limit": limit}

        results = await self.db.query(query, params)

        if not results or len(results) == 0:
            return []

        # results est une liste de listes
        dossiers_data = results[0] if isinstance(results[0], list) else results

        return [Dossier(**self._format_result(d)) for d in dossiers_data]

    async def update_dossier(
        self, dossier_id: str, updates: DossierUpdate
    ) -> Optional[Dossier]:
        """
        Met à jour un dossier.

        Args:
            dossier_id: ID du dossier
            updates: Données à mettre à jour

        Returns:
            Le dossier mis à jour ou None si introuvable
        """
        # Normaliser l'ID
        if not dossier_id.startswith("dossier:"):
            dossier_id = f"dossier:{dossier_id}"

        # Construire les données à mettre à jour (exclure les champs non modifiables)
        update_data = updates.model_dump(exclude_unset=True, exclude_none=True)

        # Ne jamais modifier created_at
        if "created_at" in update_data:
            del update_data["created_at"]

        # Toujours mettre à jour updated_at
        if update_data:  # Seulement si on a des champs à modifier
            update_data["updated_at"] = datetime.utcnow()

        # Mettre à jour
        result = await self.db.merge(dossier_id, update_data)

        if not result:
            return None

        return Dossier(**self._format_result(result))

    async def toggle_pin_dossier(self, dossier_id: str) -> Optional[Dossier]:
        """
        Épingle ou dé-épingle un dossier.

        Args:
            dossier_id: ID du dossier

        Returns:
            Le dossier mis à jour ou None si introuvable
        """
        # Normaliser l'ID
        if not dossier_id.startswith("dossier:"):
            dossier_id = f"dossier:{dossier_id}"

        # Récupérer le dossier actuel
        dossier = await self.get_dossier(dossier_id)
        if not dossier:
            return None

        # Inverser le statut pinned
        new_pinned_status = not getattr(dossier, "pinned", False)

        # Mettre à jour
        update_data = {
            "pinned": new_pinned_status,
            "updated_at": datetime.utcnow(),
        }
        result = await self.db.merge(dossier_id, update_data)

        if not result:
            return None

        return Dossier(**self._format_result(result))

    async def delete_dossier(self, dossier_id: str) -> bool:
        """
        Supprime un dossier (et ses documents associés).

        Args:
            dossier_id: ID du dossier

        Returns:
            True si supprimé, False sinon
        """
        # Normaliser l'ID
        if not dossier_id.startswith("dossier:"):
            dossier_id = f"dossier:{dossier_id}"

        # Supprimer les documents associés
        docs = await self.list_documents(dossier_id)
        for doc in docs:
            await self.delete_document(doc.id)

        # Supprimer le dossier
        await self.db.delete(dossier_id)
        return True

    # =========================================================================
    # CRUD Documents
    # =========================================================================

    async def add_document(
        self,
        dossier_id: str,
        file_content: bytes,
        filename: str,
        content_type: str = "application/pdf",
        file_type: str = "pdf",
        use_ocr: bool = False,
        document_type: Optional[str] = None,
        language: str = "fr",
        is_recording: bool = False,
        identify_speakers: bool = False,
    ) -> Document:
        """
        Ajoute un document à un dossier.

        Args:
            dossier_id: ID du dossier
            file_content: Contenu du fichier (bytes)
            filename: Nom du fichier
            content_type: Type MIME du fichier
            file_type: Type simplifié (pdf, doc, txt, audio, etc.)
            use_ocr: Utiliser l'OCR pour l'extraction
            document_type: Type de document (certificat, contrat, etc.)
            language: Langue du document (pour transcription)
            is_recording: Est-ce un enregistrement audio
            identify_speakers: Identifier les interlocuteurs (audio)

        Returns:
            Le document créé
        """
        logger.info(f"Adding document {filename} to dossier {dossier_id} (type: {file_type})")

        # Normaliser l'ID du dossier
        if not dossier_id.startswith("dossier:"):
            dossier_id = f"dossier:{dossier_id}"

        # Calculer le hash du fichier
        file_hash = hashlib.sha256(file_content).hexdigest()

        # Générer un ID unique pour le document (juste l'identifiant, pas le préfixe)
        doc_id = uuid4().hex[:12]

        # Créer le répertoire pour ce dossier
        dossier_dir = self.upload_dir / dossier_id.replace(":", "_")
        dossier_dir.mkdir(parents=True, exist_ok=True)

        # Sauvegarder le fichier
        file_path = dossier_dir / f"{doc_id}_{filename}"
        file_path.write_bytes(file_content)

        logger.info(f"File saved to: {file_path}")

        # Convertir dossier_id en RecordID
        from surrealdb import RecordID as RecordIDClass

        if isinstance(dossier_id, str):
            if ":" in dossier_id:
                table_name, identifier = dossier_id.split(":", 1)
                dossier_id_obj = RecordIDClass(table_name, identifier)
            else:
                dossier_id_obj = RecordIDClass("dossier", dossier_id)
        else:
            dossier_id_obj = dossier_id

        # Créer l'enregistrement dans la DB
        doc_data = {
            "nom_fichier": filename,
            "chemin_fichier": str(file_path),
            "type_mime": content_type,
            "type_fichier": file_type,
            "taille_bytes": len(file_content),
            "dossier_id": dossier_id_obj,
            "hash_sha256": file_hash,
            "document_type": document_type,
            "language": language,
            "use_ocr": use_ocr,
            "is_recording": is_recording,
            "identify_speakers": identify_speakers,
            "texte_extrait": None,  # Sera rempli après extraction
            "transcription": None,  # Sera rempli après transcription (audio)
            "extraction_status": "pending",  # pending, processing, completed, error
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }

        result = await self.db.create("document", doc_data, record_id=doc_id)

        logger.info(f"Document created: {result}")

        return Document(**self._format_result(result))

    async def get_document(self, document_id: str) -> Optional[Document]:
        """Récupère un document par son ID."""
        from surrealdb import RecordID as RecordIDClass

        if not document_id.startswith("document:"):
            document_id = f"document:{document_id}"

        # Parser l'ID et utiliser RecordID (pattern officiel)
        table, record_id = document_id.split(":", 1)
        result = await self.db.select(RecordIDClass(table, record_id))

        if not result:
            return None

        return Document(**self._format_result(result))

    async def list_documents(self, dossier_id: str) -> list[Document]:
        """Liste les documents d'un dossier."""
        # Normaliser l'ID
        if not dossier_id.startswith("dossier:"):
            dossier_id = f"dossier:{dossier_id}"

        # Convertir en RecordID pour la comparaison
        from surrealdb import RecordID as RecordIDClass
        table_name, identifier = dossier_id.split(":", 1)
        dossier_id_obj = RecordIDClass(table_name, identifier)

        query = "SELECT * FROM document WHERE dossier_id = $dossier_id ORDER BY created_at"
        params = {"dossier_id": dossier_id_obj}

        results = await self.db.query(query, params)

        if not results or len(results) == 0:
            return []

        docs_data = results[0] if isinstance(results[0], list) else results

        return [Document(**self._format_result(d)) for d in docs_data]

    async def delete_document(self, document_id: str) -> bool:
        """Supprime un document (fichier + DB)."""
        # Récupérer le document pour avoir le chemin du fichier
        doc = await self.get_document(document_id)

        if not doc:
            return False

        # Supprimer le fichier physique
        file_path = Path(doc.chemin_fichier)
        if file_path.exists():
            file_path.unlink()
            logger.info(f"File deleted: {file_path}")

        # Supprimer l'enregistrement DB
        if not document_id.startswith("document:"):
            document_id = f"document:{document_id}"

        await self.db.delete(document_id)
        return True

    # =========================================================================
    # Analyse de dossier (placeholder)
    # =========================================================================

    async def analyser_dossier(
        self,
        dossier_id: str,
        progress_callback: Optional[Any] = None,
        model_id: Optional[str] = None,
        extraction_method: Optional[str] = "pypdf",
        use_ocr: Optional[bool] = False,
    ) -> Optional[Checklist]:
        """
        Lance l'analyse d'un dossier via le workflow Agno.

        Args:
            dossier_id: ID du dossier à analyser
            progress_callback: Callback async pour émettre les événements de progression
            model_id: ID du modèle LLM à utiliser (ex: "ollama:qwen2.5:7b")
            extraction_method: Méthode d'extraction PDF (pypdf, docling-standard, docling-vlm)
            use_ocr: Activer l'OCR pour les PDFs scannés

        Returns:
            La checklist générée ou None si erreur
        """
        from datetime import datetime
        from workflows.analyse_dossier import WorkflowAnalyseDossier
        import os

        logger.info(f"Starting analysis for dossier {dossier_id}")
        logger.info(f"Parameters: model_id={model_id}, extraction_method={extraction_method}, use_ocr={use_ocr}")

        # Normaliser l'ID
        if not dossier_id.startswith("dossier:"):
            dossier_id = f"dossier:{dossier_id}"

        try:
            # 1. Charger les documents du dossier
            documents = await self.list_documents(dossier_id)

            if not documents:
                logger.error(f"No documents found for dossier {dossier_id}")
                return None

            logger.info(f"Found {len(documents)} documents to analyze")

            # Préparer la liste des fichiers (chemins string, pas Path)
            fichiers_pdf = [doc.chemin_fichier for doc in documents]

            # 2. Déterminer le modèle à utiliser
            # Priorité: Paramètre > Variable d'environnement > Claude Anthropic > Ollama
            final_model_id = model_id  # Utiliser le paramètre si fourni
            if not final_model_id:
                model_env = os.getenv("LLM_MODEL")
                if model_env:
                    final_model_id = model_env
                    logger.info(f"Using model from LLM_MODEL env: {final_model_id}")
                elif os.getenv("ANTHROPIC_API_KEY"):
                    # Claude Anthropic si clé configurée
                    final_model_id = "anthropic:claude-sonnet-4-5-20250929"
                    logger.info("Using Claude Anthropic (ANTHROPIC_API_KEY found)")
                else:
                    # Ollama par défaut pour le développement
                    final_model_id = "ollama:qwen2.5:7b"
                    logger.info("Using Ollama qwen2.5:7b (default for development)")
            else:
                logger.info(f"Using model from parameter: {final_model_id}")

            # 3. Créer et lancer le workflow Agno
            # Pattern officiel: passer db pour persistance automatique
            if self.agno_db_service:
                agno_db = self.agno_db_service.get_agno_db()
                workflow = WorkflowAnalyseDossier(
                    model=final_model_id,
                    db=agno_db  # ✅ Persistance automatique Agno
                )
                logger.info(f"Running Agno workflow with model={final_model_id} and persistence...")
            else:
                workflow = WorkflowAnalyseDossier(model=final_model_id)
                logger.info(f"Running Agno workflow with model={final_model_id} (no persistence)...")
            start_time = datetime.utcnow()

            # Lancer l'analyse
            metadata = {
                "dossier_id": dossier_id,
                "nb_documents": len(documents),
                "extraction_method": extraction_method or "pypdf",
                "use_ocr": use_ocr or False,
            }

            logger.info(f"Workflow metadata: extraction_method={metadata['extraction_method']}, use_ocr={metadata['use_ocr']}")

            # Passer le progress_callback au workflow via metadata
            if progress_callback:
                metadata["_progress_callback"] = progress_callback

            # Exécuter le workflow de manière asynchrone
            workflow_output = await workflow.arun(
                fichiers_pdf=fichiers_pdf,
                metadata=metadata,
            )

            duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            logger.info(f"Workflow completed in {duration_ms}ms")

            # Extraire le contenu du WorkflowRunOutput
            # Agno retourne un WorkflowRunOutput, le résultat est dans .content
            resultat = workflow_output.content if hasattr(workflow_output, 'content') else workflow_output

            # 4. Sauvegarder les résultats dans SurrealDB
            if resultat.get("success"):
                # Sauvegarder les exécutions d'agents
                for agent_name, agent_result in resultat.get("agents", {}).items():
                    await self._save_agent_execution(
                        dossier_id=dossier_id,
                        agent_name=agent_name,
                        agent_result=agent_result,
                    )

                # Créer la checklist
                checklist_data = resultat.get("checklist", {})
                checklist = await self._create_checklist(
                    dossier_id=dossier_id,
                    checklist_data=checklist_data,
                )

                logger.info(f"Checklist created: {checklist.id}")
                return checklist
            else:
                logger.error(f"Workflow failed: {resultat.get('erreur_message')}")
                return None

        except Exception as e:
            logger.exception(f"Error analyzing dossier: {e}")
            return None

    async def _save_agent_execution(
        self,
        dossier_id: str,
        agent_name: str,
        agent_result: dict[str, Any],
    ) -> None:
        """Sauvegarde l'exécution d'un agent dans la DB."""
        execution_data = {
            "dossier_id": dossier_id,
            "agent_name": agent_name,
            "status": "completed" if agent_result.get("success") else "failed",
            "input": agent_result.get("input", {}),
            "output": agent_result.get("output", {}),
            "error": agent_result.get("error"),
            "prompt_used": agent_result.get("prompt"),
            "llm_response": agent_result.get("llm_response"),
            "tokens_used": agent_result.get("tokens_used"),
            "duration_ms": agent_result.get("duration_ms"),
            "created_at": datetime.utcnow(),
            "completed_at": datetime.utcnow(),
        }

        await self.db.create("agent_execution", execution_data)

    async def _create_checklist(
        self,
        dossier_id: str,
        checklist_data: dict[str, Any],
    ) -> Checklist:
        """Crée une checklist dans la DB."""
        from models import ChecklistItem
        from uuid import uuid4
        from surrealdb import RecordID as RecordIDClass

        # Convertir dossier_id en RecordID
        if isinstance(dossier_id, str):
            if ":" in dossier_id:
                table_name, identifier = dossier_id.split(":", 1)
                dossier_id_obj = RecordIDClass(table_name, identifier)
            else:
                dossier_id_obj = RecordIDClass("dossier", dossier_id)
        else:
            dossier_id_obj = dossier_id

        # Convertir les items en format ChecklistItem
        items = []
        for item in checklist_data.get("checklist", []):
            items.append({
                "titre": item.get("item", ""),
                "description": item.get("description"),
                "statut": "complete" if item.get("complete") else "a_verifier",
                "priorite": item.get("priorite", "normale"),
            })

        checklist_id = uuid4().hex[:12]

        data = {
            "dossier_id": dossier_id_obj,
            "items": items,
            "score_confiance": checklist_data.get("score_confiance", 0.5),
            "points_attention": checklist_data.get("points_attention", []),
            "documents_manquants": checklist_data.get("documents_a_obtenir", []),
            "generated_by": "agno_workflow",
            "created_at": datetime.utcnow(),
        }

        result = await self.db.create("checklist", data, record_id=checklist_id)

        return Checklist(**self._format_result(result))

    async def get_checklist(self, dossier_id: str) -> Optional[Checklist]:
        """
        Récupère la checklist d'un dossier.

        Args:
            dossier_id: ID du dossier

        Returns:
            La checklist ou None si pas trouvée
        """
        from surrealdb import RecordID as RecordIDClass

        # Convertir dossier_id en RecordID
        if isinstance(dossier_id, str):
            if ":" in dossier_id:
                table_name, identifier = dossier_id.split(":", 1)
                dossier_id_obj = RecordIDClass(table_name, identifier)
            else:
                dossier_id_obj = RecordIDClass("dossier", dossier_id)
        else:
            dossier_id_obj = dossier_id

        # Requête pour trouver la checklist de ce dossier
        query = """
            SELECT * FROM checklist
            WHERE dossier_id = $dossier_id
            ORDER BY created_at DESC
            LIMIT 1
        """

        results = await self.db.query(query, {"dossier_id": dossier_id_obj})

        if not results or not results[0]:
            return None

        checklist_data = results[0][0] if isinstance(results[0], list) else results[0]

        return Checklist(**self._format_result(checklist_data))

    # =========================================================================
    # Helpers
    # =========================================================================

    def _format_result(self, result: dict[str, Any]) -> dict[str, Any]:
        """
        Formate un résultat SurrealDB pour le rendre compatible avec Pydantic.

        SurrealDB retourne les IDs au format RecordID, on doit les convertir en string.
        """
        formatted = result.copy()

        # Convertir l'ID en string
        if "id" in formatted:
            formatted["id"] = str(formatted["id"])

        # Convertir les références (user_id, dossier_id, etc.)
        for key in ["user_id", "dossier_id"]:
            if key in formatted and formatted[key]:
                formatted[key] = str(formatted[key])

        return formatted
