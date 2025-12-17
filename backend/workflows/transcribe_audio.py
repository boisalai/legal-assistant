"""
Workflow de transcription audio avec Agno Workflow.

Ce workflow utilise l'API Workflow d'Agno pour orchestrer:
1. TranscriberStep - Fonction Python pour transcrire l'audio avec Whisper
2. FormatterAgent - Agent LLM pour formater la transcription en markdown

Usage:
    from workflows.transcribe_audio import TranscriptionWorkflow

    workflow = TranscriptionWorkflow(whisper_model="large-v3-turbo")
    result = await workflow.run(
        audio_path="/path/to/audio.mp3",
        course_id="course:xxx",
        language="fr"
    )
"""

import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional, Callable, Any
from dataclasses import dataclass, field

from agno.agent import Agent
from agno.workflow import Workflow, StepOutput

logger = logging.getLogger(__name__)


@dataclass
class TranscriptionWorkflowResult:
    """Résultat du workflow de transcription."""
    success: bool
    audio_filename: str = ""
    transcript_text: str = ""
    formatted_markdown: str = ""
    document_id: str = ""
    document_path: str = ""
    duration_seconds: float = 0.0
    language: str = ""
    error: Optional[str] = None
    steps_completed: list = field(default_factory=list)


# Prompt pour l'agent de formatage
FORMATTER_INSTRUCTIONS = """Tu es un assistant spécialisé dans le formatage de transcriptions audio.

Tu reçois une transcription brute d'un fichier audio et tu dois:

1. **Nettoyer le texte**: Corriger les erreurs évidentes de transcription, améliorer la ponctuation
2. **Structurer le contenu**: Identifier les différentes parties/sujets abordés
3. **Créer un résumé**: Un résumé exécutif en quelques points clés
4. **Formater en Markdown**: Produire un document bien structuré

Format de sortie attendu (en Markdown):

```
# Transcription: {nom_du_fichier}

## Informations
- **Date de transcription**: {date}
- **Durée**: {durée}
- **Langue**: {langue}

## Résumé
[Résumé en 3-5 points clés]

## Transcription complète

### [Section 1 - Sujet identifié]
[Texte de cette section]

### [Section 2 - Autre sujet]
[Texte de cette section]

---
*Transcription automatique générée par Whisper*
```

IMPORTANT:
- Garde le contenu fidèle à l'original, ne modifie pas le sens
- Identifie les changements de sujet pour créer des sections
- Si c'est une conversation, identifie les interlocuteurs si possible
- Retourne UNIQUEMENT le markdown, sans commentaires additionnels
"""


class TranscriptionWorkflow:
    """
    Workflow Agno pour transcrire un fichier audio et créer un document markdown.

    Utilise le pattern Workflow d'Agno avec:
    - Une fonction Python pour la transcription Whisper
    - Un Agent pour le formatage markdown
    """

    def __init__(
        self,
        model: Optional[Any] = None,
        whisper_model: str = "large-v3-turbo",
        on_progress: Optional[Callable[[str, str, int], None]] = None,
        on_step_start: Optional[Callable[[str], None]] = None,
        on_step_complete: Optional[Callable[[str, bool], None]] = None,
    ):
        """
        Initialise le workflow de transcription.

        Args:
            model: Modèle Agno pour le formatage (optionnel, utilise Ollama par défaut)
            whisper_model: Modèle Whisper à utiliser (tiny, base, small, medium, large-v3, large-v3-turbo)
            on_progress: Callback (step_name, message, percentage)
            on_step_start: Callback (step_name)
            on_step_complete: Callback (step_name, success)
        """
        self.model = model
        self.whisper_model = whisper_model
        self.on_progress = on_progress
        self.on_step_start = on_step_start
        self.on_step_complete = on_step_complete

        # État partagé entre les étapes
        self._state = {}

    def _emit_progress(self, step: str, message: str, percentage: int):
        """Émet un événement de progression."""
        if self.on_progress:
            try:
                self.on_progress(step, message, percentage)
            except Exception as e:
                logger.warning(f"Error in progress callback: {e}")

    def _emit_step_start(self, step: str):
        """Émet un événement de début d'étape."""
        if self.on_step_start:
            try:
                self.on_step_start(step)
            except Exception as e:
                logger.warning(f"Error in step_start callback: {e}")

    def _emit_step_complete(self, step: str, success: bool):
        """Émet un événement de fin d'étape."""
        if self.on_step_complete:
            try:
                self.on_step_complete(step, success)
            except Exception as e:
                logger.warning(f"Error in step_complete callback: {e}")

    def _get_model(self):
        """Obtient ou crée le modèle LLM."""
        if self.model is None:
            from services.model_factory import create_model
            self.model = create_model("ollama:qwen2.5:7b")
        return self.model

    def _create_formatter_agent(self) -> Agent:
        """Crée l'agent de formatage."""
        return Agent(
            name="TranscriptionFormatter",
            model=self._get_model(),
            instructions=FORMATTER_INSTRUCTIONS,
            markdown=True,
        )

    async def _transcribe_step(self, audio_path: str, language: str) -> dict:
        """
        Étape 1: Transcription avec Whisper.

        Cette fonction est utilisée comme step dans le workflow.
        """
        self._emit_step_start("transcription")
        self._emit_progress("transcription", "Chargement du modèle Whisper...", 5)

        from services.whisper_service import get_whisper_service, WHISPER_AVAILABLE

        if not WHISPER_AVAILABLE:
            self._emit_step_complete("transcription", False)
            return {
                "success": False,
                "error": "Whisper n'est pas installé. Exécutez: uv sync --extra whisper"
            }

        whisper_service = get_whisper_service(model_name=self.whisper_model)

        self._emit_progress("transcription", "Transcription en cours...", 20)

        transcription = await whisper_service.transcribe(audio_path, language=language)

        if not transcription.success:
            self._emit_step_complete("transcription", False)
            return {
                "success": False,
                "error": transcription.error or "Échec de la transcription"
            }

        self._emit_progress("transcription", "Transcription terminée", 40)
        self._emit_step_complete("transcription", True)

        return {
            "success": True,
            "text": transcription.text,
            "duration": transcription.duration,
            "language": transcription.language or language,
        }

    def _format_step(self, transcription_data: dict, audio_filename: str) -> dict:
        """
        Étape 2: Formatage avec Agent LLM.

        Utilise l'Agent Agno pour formater la transcription.
        """
        self._emit_step_start("formatting")
        self._emit_progress("formatting", "Formatage de la transcription...", 50)

        formatter = self._create_formatter_agent()

        # Préparer le contexte
        duration_str = f"{int(transcription_data['duration'] // 60)}:{int(transcription_data['duration'] % 60):02d}"
        context = f"""
Fichier audio: {audio_filename}
Date de transcription: {datetime.now().strftime('%Y-%m-%d %H:%M')}
Durée: {duration_str}
Langue: {transcription_data['language']}

Transcription brute:
{transcription_data['text']}
"""

        self._emit_progress("formatting", "Analyse et structuration...", 60)

        # Exécuter l'agent de formatage
        try:
            format_result = formatter.run(f"Formate cette transcription:\n\n{context}")

            if hasattr(format_result, 'content') and format_result.content:
                formatted_markdown = format_result.content
                # Strip wrapper markdown code blocks if present
                # The LLM sometimes wraps the entire output in ```markdown ... ```
                formatted_markdown = formatted_markdown.strip()
                if formatted_markdown.startswith("```markdown"):
                    formatted_markdown = formatted_markdown[len("```markdown"):].strip()
                elif formatted_markdown.startswith("```"):
                    formatted_markdown = formatted_markdown[3:].strip()
                if formatted_markdown.endswith("```"):
                    formatted_markdown = formatted_markdown[:-3].strip()
            else:
                # Fallback: créer un markdown basique
                formatted_markdown = self._create_basic_markdown(
                    audio_filename,
                    transcription_data['text'],
                    transcription_data['duration'],
                    transcription_data['language']
                )

            self._emit_progress("formatting", "Formatage terminé", 75)
            self._emit_step_complete("formatting", True)

            return {
                "success": True,
                "formatted_markdown": formatted_markdown
            }

        except Exception as e:
            logger.error(f"Formatting error: {e}")
            self._emit_step_complete("formatting", False)
            return {
                "success": False,
                "error": str(e),
                "formatted_markdown": self._create_basic_markdown(
                    audio_filename,
                    transcription_data['text'],
                    transcription_data['duration'],
                    transcription_data['language']
                )
            }

    def _create_basic_markdown(
        self,
        audio_filename: str,
        text: str,
        duration: float,
        language: str
    ) -> str:
        """Crée un markdown basique si l'agent échoue."""
        duration_str = f"{int(duration // 60)}:{int(duration % 60):02d}"

        return f"""# Transcription: {audio_filename}

## Informations
- **Date de transcription**: {datetime.now().strftime('%Y-%m-%d %H:%M')}
- **Durée**: {duration_str}
- **Langue**: {language}

## Transcription complète

{text}

---
*Transcription automatique générée par Whisper*
"""

    async def _save_step(
        self,
        course_id: str,
        audio_filename: str,
        markdown_content: str,
        duration: float,
        language: str,
        audio_file_path: str = "",
        source_document_id: str = None,
    ) -> Optional[dict]:
        """
        Étape 3: Sauvegarde du document markdown.

        Le fichier markdown est sauvegardé dans le même répertoire que le fichier audio source.
        """
        self._emit_step_start("saving")
        self._emit_progress("saving", "Création du document markdown...", 80)

        try:
            from services.surreal_service import get_surreal_service

            service = get_surreal_service()
            if not service.db:
                await service.connect()

            # Normaliser le course_id
            if not course_id.startswith("course:"):
                course_id = f"course:{course_id}"

            # Générer le nom du fichier markdown
            base_name = Path(audio_filename).stem
            md_filename = f"{base_name}.md"

            # Save in the same directory as the original audio file
            if audio_file_path:
                save_dir = Path(audio_file_path).parent
            else:
                # Fallback to default upload directory if no audio path
                from config.settings import settings
                save_dir = Path(settings.upload_dir) / course_id.replace("course:", "")
                save_dir.mkdir(parents=True, exist_ok=True)

            # Définir le chemin du fichier markdown
            file_path = save_dir / md_filename

            # ============================================================
            # VÉRIFICATION: Fichier markdown existe déjà?
            # ============================================================

            # Note: Nous ne vérifions plus l'existence car:
            # 1. Les fichiers markdown dérivés ne sont plus auto-découverts (fix dans routes/documents.py)
            # 2. Si l'utilisateur veut retranscrire, on écrase simplement l'ancien fichier
            # 3. Cela évite les problèmes de synchronisation entre fichier physique et DB

            # Si le fichier existe déjà, on va le supprimer et le recréer
            if file_path.exists():
                logger.info(f"Fichier markdown '{md_filename}' existe déjà, il sera écrasé")
                # Supprimer l'ancien enregistrement en DB s'il existe
                try:
                    existing_docs_result = await service.query(
                        "SELECT id FROM document WHERE course_id = $course_id AND nom_fichier = $filename",
                        {"course_id": course_id, "filename": md_filename}
                    )
                    if existing_docs_result and len(existing_docs_result) > 0:
                        first_item = existing_docs_result[0]
                        if isinstance(first_item, dict) and "result" in first_item:
                            existing_docs = first_item["result"] if isinstance(first_item["result"], list) else []
                        elif isinstance(first_item, dict) and "id" in first_item:
                            existing_docs = [first_item]
                        elif isinstance(first_item, list):
                            existing_docs = first_item
                        else:
                            existing_docs = []

                        for doc in existing_docs:
                            doc_id = str(doc.get("id", ""))
                            if doc_id:
                                await service.delete(doc_id)
                                logger.info(f"Ancien enregistrement markdown supprimé: {doc_id}")
                except Exception as e:
                    logger.warning(f"Erreur lors de la suppression de l'ancien markdown: {e}")

            # ============================================================
            # SAUVEGARDE: Créer le fichier markdown
            # ============================================================
            file_path.write_text(markdown_content, encoding="utf-8")

            logger.info(f"Markdown file saved: {file_path}")

            # Créer l'enregistrement dans la base de données
            doc_id = str(uuid.uuid4())[:8]
            now = datetime.utcnow().isoformat()

            document_data = {
                "course_id": course_id,
                "nom_fichier": md_filename,
                "type_fichier": "md",
                "type_mime": "text/markdown",
                "taille": len(markdown_content.encode("utf-8")),
                "file_path": str(file_path),
                "texte_extrait": markdown_content,
                "is_transcription": True,
                "source_audio": audio_filename,  # Garder pour compatibilité
                "source_document_id": source_document_id,  # Nouveau champ
                "is_derived": True,
                "derivation_type": "transcription",
                "source_type": "upload",
                "extraction_method": f"whisper-{self.whisper_model}",
                "created_at": now,
                "metadata": {
                    "duration_seconds": duration,
                    "language": language,
                    "transcribed_at": now,
                }
            }

            await service.create("document", document_data, record_id=doc_id)

            logger.info(f"Document record created: document:{doc_id}")

            self._emit_progress("saving", "Document sauvegardé", 90)

            # Index le document pour la recherche sémantique
            try:
                from services.document_indexing_service import get_document_indexing_service

                self._emit_progress("saving", "Indexation pour recherche sémantique...", 92)
                indexing_service = get_document_indexing_service()
                index_result = await indexing_service.index_document(
                    document_id=f"document:{doc_id}",
                    course_id=course_id,
                    text_content=markdown_content,
                    force_reindex=False
                )

                if index_result.get("success"):
                    logger.info(f"Document indexed: {index_result.get('chunks_created', 0)} chunks")
                else:
                    logger.warning(f"Indexing failed: {index_result.get('error', 'Unknown error')}")
            except Exception as e:
                # Ne pas bloquer si l'indexation échoue
                logger.warning(f"Could not index document: {e}")

            self._emit_progress("saving", "Terminé", 100)
            self._emit_step_complete("saving", True)

            return {
                "id": f"document:{doc_id}",
                "file_path": str(file_path),
                "filename": md_filename,
            }

        except Exception as e:
            logger.error(f"Error saving markdown document: {e}", exc_info=True)
            self._emit_step_complete("saving", False)
            return None

    async def run(
        self,
        audio_path: str,
        course_id: str,
        language: str = "fr",
        create_markdown_doc: bool = True,
        original_filename: str = "",
        raw_mode: bool = False,
        source_document_id: str = None,
    ) -> TranscriptionWorkflowResult:
        """
        Exécute le workflow de transcription complet.

        Le workflow enchaîne 3 étapes:
        1. Transcription Whisper (fonction Python)
        2. Formatage markdown (Agent LLM) - sauté si raw_mode=True
        3. Sauvegarde (fonction Python)

        Args:
            audio_path: Chemin vers le fichier audio
            course_id: ID du cours (course:xxx)
            language: Langue de l'audio
            create_markdown_doc: Si True, crée un document markdown dans le cours
            original_filename: Nom original du fichier (si différent du nom sur disque)
            raw_mode: Si True, sauvegarde la transcription brute sans formatage LLM
            source_document_id: ID du document audio source (pour lier le fichier dérivé)

        Returns:
            TranscriptionWorkflowResult avec tous les détails
        """
        audio_filename = original_filename if original_filename else Path(audio_path).name
        result = TranscriptionWorkflowResult(
            success=False,
            audio_filename=audio_filename
        )

        try:
            # ============================================================
            # STEP 1: Transcription avec Whisper
            # ============================================================
            transcription_result = await self._transcribe_step(audio_path, language)

            if not transcription_result["success"]:
                result.error = transcription_result.get("error", "Échec de la transcription")
                return result

            result.transcript_text = transcription_result["text"]
            result.duration_seconds = transcription_result["duration"]
            result.language = transcription_result["language"]
            result.steps_completed.append("transcription")

            # ============================================================
            # STEP 2: Formatage avec Agent LLM (sauté si raw_mode=True)
            # ============================================================
            if raw_mode:
                # Mode brut: utiliser directement le texte Whisper sans formatage
                result.formatted_markdown = transcription_result["text"]
                self._emit_progress("formatting", "Mode brut - pas de formatage LLM", 75)
            else:
                format_result = self._format_step(transcription_result, audio_filename)
                result.formatted_markdown = format_result.get("formatted_markdown", "")
                result.steps_completed.append("formatting")

            # ============================================================
            # STEP 3: Sauvegarde du document markdown
            # ============================================================
            if create_markdown_doc:
                doc_result = await self._save_step(
                    course_id=course_id,
                    audio_filename=audio_filename,
                    markdown_content=result.formatted_markdown,
                    duration=result.duration_seconds,
                    language=result.language,
                    audio_file_path=audio_path,  # Pass original audio path
                    source_document_id=source_document_id,  # Link to source audio document
                )

                if doc_result:
                    result.document_id = doc_result.get("id", "")
                    result.document_path = doc_result.get("file_path", "")
                    result.steps_completed.append("saving")

            # ============================================================
            # Terminé
            # ============================================================
            result.success = True
            self._emit_progress("complete", "Transcription complète!", 100)

            logger.info(f"Transcription workflow completed: {audio_filename}")

            return result

        except Exception as e:
            logger.error(f"Transcription workflow error: {e}", exc_info=True)
            result.error = str(e)
            return result


# ============================================================
# Alternative: Workflow déclaratif avec Agno Workflow API
# ============================================================

def create_transcription_workflow_declarative(
    model: Optional[Any] = None,
    whisper_model: str = "large-v3-turbo"
) -> Workflow:
    """
    Crée un workflow de transcription déclaratif avec l'API Workflow d'Agno.

    Cette version montre comment utiliser l'API native Workflow d'Agno
    pour des cas où toutes les étapes sont des Agents.

    Note: Pour notre cas d'usage avec Whisper (non-LLM), la classe
    TranscriptionWorkflow ci-dessus est plus appropriée.

    Example:
        workflow = create_transcription_workflow_declarative()
        # Requires transcript text as input (Whisper step done separately)
        workflow.print_response("Format this transcript: ...", stream=True)
    """
    if model is None:
        from services.model_factory import create_model
        model = create_model("ollama:qwen2.5:7b")

    formatter_agent = Agent(
        name="TranscriptionFormatter",
        model=model,
        instructions=FORMATTER_INSTRUCTIONS,
        markdown=True,
    )

    # Pour un workflow purement LLM, on pourrait chaîner plusieurs agents
    # Exemple: Transcription Summary Agent -> Formatter Agent -> Quality Check Agent

    return Workflow(
        name="Transcription Formatting",
        steps=[formatter_agent],
    )


# ============================================================
# Helper function pour utilisation simple
# ============================================================

async def transcribe_audio_to_markdown(
    audio_path: str,
    course_id: str,
    language: str = "fr",
    model: Optional[Any] = None,
    on_progress: Optional[Callable[[str, str, int], None]] = None,
    raw_mode: bool = False,
) -> TranscriptionWorkflowResult:
    """
    Fonction helper pour transcrire un audio et créer un document markdown.

    Args:
        audio_path: Chemin vers le fichier audio
        course_id: ID du cours (course:xxx)
        language: Langue de l'audio
        model: Modèle LLM optionnel
        on_progress: Callback de progression optionnel
        raw_mode: Si True, sauvegarde la transcription brute sans formatage LLM

    Returns:
        TranscriptionWorkflowResult
    """
    workflow = TranscriptionWorkflow(
        model=model,
        on_progress=on_progress,
    )

    return await workflow.run(
        audio_path=audio_path,
        course_id=course_id,
        language=language,
        raw_mode=raw_mode,
    )
