"""
Transcription tool for the Agno agent.

This tool allows the AI agent to transcribe audio files using Whisper.
"""

import logging
from pathlib import Path
from typing import Optional

from agno.tools import tool

from services.surreal_service import get_surreal_service

logger = logging.getLogger(__name__)

# Audio file extensions
AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".ogg", ".webm", ".flac", ".aac"}


def _is_audio_file(filename: str) -> bool:
    """Check if a file is an audio file based on its extension."""
    ext = Path(filename).suffix.lower()
    return ext in AUDIO_EXTENSIONS


async def _find_audio_document(judgment_id: str, filename: Optional[str] = None) -> Optional[dict]:
    """
    Find an audio document in the case.

    Args:
        judgment_id: ID of the case
        filename: Optional specific filename to look for

    Returns:
        Document dict or None
    """
    service = get_surreal_service()
    if not service.db:
        await service.connect()

    # Normalize judgment_id
    if not judgment_id.startswith("judgment:"):
        judgment_id = f"judgment:{judgment_id}"

    # Get documents for this case
    docs_result = await service.query(
        "SELECT * FROM document WHERE judgment_id = $judgment_id",
        {"judgment_id": judgment_id}
    )

    documents = []
    if docs_result and len(docs_result) > 0:
        first_item = docs_result[0]
        if isinstance(first_item, dict):
            if "result" in first_item:
                documents = first_item["result"] if isinstance(first_item["result"], list) else []
            elif "id" in first_item or "nom_fichier" in first_item:
                documents = docs_result
        elif isinstance(first_item, list):
            documents = first_item

    if not documents:
        return None

    # Filter audio documents
    audio_docs = [d for d in documents if _is_audio_file(d.get("nom_fichier", ""))]

    if not audio_docs:
        return None

    # If filename specified, find matching document
    if filename:
        for doc in audio_docs:
            doc_name = doc.get("nom_fichier", "")
            if doc_name.lower() == filename.lower():
                return doc
            if filename.lower() in doc_name.lower() or doc_name.lower() in filename.lower():
                return doc

    # Return first untranscribed audio document
    for doc in audio_docs:
        if not doc.get("texte_extrait"):
            return doc

    # All documents are transcribed, return first audio doc
    return audio_docs[0] if audio_docs else None


async def transcribe_audio_streaming(
    case_id: str,
    audio_filename: Optional[str] = None,
    language: str = "fr",
    raw_mode: bool = False
) -> dict:
    """
    Transcribe audio and return structured result for streaming.

    Returns a dict with:
    - success: bool
    - transcript_text: str (if success)
    - original_filename: str
    - markdown_filename: str (if markdown created)
    - document_id: str (if document created)
    - error: str (if failed)

    Args:
        case_id: ID of the case
        audio_filename: Optional specific filename to transcribe
        language: Language code for transcription
        raw_mode: If True, skip LLM formatting and save raw Whisper output
    """
    try:
        # Find the audio document
        document = await _find_audio_document(case_id, audio_filename)

        if not document:
            if audio_filename:
                return {"success": False, "error": f"Fichier audio '{audio_filename}' non trouvé dans ce dossier."}
            return {"success": False, "error": "Aucun fichier audio trouvé dans ce dossier."}

        doc_name = document.get("nom_fichier", "")
        doc_id = document.get("id", "")
        file_path = document.get("file_path", "")

        # Check if already transcribed
        if document.get("texte_extrait"):
            return {
                "success": True,
                "transcript_text": document["texte_extrait"],
                "original_filename": doc_name,
                "already_transcribed": True
            }

        if not file_path or not Path(file_path).exists():
            return {"success": False, "error": f"Fichier audio '{doc_name}' non accessible."}

        # Normalize judgment_id
        judgment_id = case_id
        if not judgment_id.startswith("judgment:"):
            judgment_id = f"judgment:{judgment_id}"

        # Import and run the transcription workflow
        from workflows.transcribe_audio import TranscriptionWorkflow

        workflow = TranscriptionWorkflow(
            whisper_model="large-v3-turbo"
        )

        result = await workflow.run(
            audio_path=file_path,
            judgment_id=judgment_id,
            language=language,
            create_markdown_doc=True,
            original_filename=doc_name,
            raw_mode=raw_mode
        )

        if result.success:
            # Note: We no longer store transcription in the audio source document
            # The transcription is stored in the markdown file created by the workflow

            md_filename = f"{Path(doc_name).stem}.md"

            return {
                "success": True,
                "transcript_text": result.transcript_text,
                "original_filename": doc_name,
                "markdown_filename": md_filename,
                "document_id": result.document_id if hasattr(result, 'document_id') else None,
                "raw_mode": raw_mode
            }
        else:
            return {"success": False, "error": result.error or "Erreur inconnue"}

    except ImportError as e:
        if "whisper" in str(e).lower():
            return {"success": False, "error": "Whisper n'est pas installé. Exécutez: uv sync --extra whisper"}
        raise
    except Exception as e:
        logger.error(f"Transcription streaming error: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


@tool(name="transcribe_audio")
async def transcribe_audio(
    case_id: str,
    audio_filename: Optional[str] = None,
    language: str = "fr"
) -> str:
    """
    Transcrit un fichier audio en texte en utilisant Whisper.

    Cet outil permet de transcrire un fichier audio associé à un dossier juridique.
    La transcription utilise Whisper (OpenAI) pour la reconnaissance vocale.

    Args:
        case_id: L'identifiant du dossier (ex: "1f9fc70e" ou "judgment:1f9fc70e")
        audio_filename: Nom du fichier audio à transcrire (optionnel - si non spécifié,
                       utilise le premier fichier audio non transcrit du dossier)
        language: Langue de l'audio ("fr" pour français, "en" pour anglais, etc.)

    Returns:
        Un message décrivant le résultat de la transcription avec un aperçu du contenu
    """
    try:
        # Find the audio document
        document = await _find_audio_document(case_id, audio_filename)

        if not document:
            if audio_filename:
                return f"Je n'ai pas trouvé de fichier audio nommé '{audio_filename}' dans ce dossier."
            return "Je n'ai pas trouvé de fichier audio dans ce dossier."

        doc_name = document.get("nom_fichier", "")
        doc_id = document.get("id", "")
        file_path = document.get("file_path", "")

        # Check if already transcribed
        if document.get("texte_extrait"):
            return f"Le fichier '{doc_name}' a déjà été transcrit. Voici un aperçu:\n\n{document['texte_extrait'][:500]}..."

        if not file_path or not Path(file_path).exists():
            return f"Le fichier audio '{doc_name}' n'est pas accessible sur le disque."

        # Normalize judgment_id
        judgment_id = case_id
        if not judgment_id.startswith("judgment:"):
            judgment_id = f"judgment:{judgment_id}"

        # Import and run the transcription workflow
        from workflows.transcribe_audio import TranscriptionWorkflow

        workflow = TranscriptionWorkflow(
            whisper_model="large-v3-turbo"  # Use high-quality MLX model
        )

        result = await workflow.run(
            audio_path=file_path,
            judgment_id=judgment_id,
            language=language,
            create_markdown_doc=True,
            original_filename=doc_name  # Use original filename, not UUID-based path
        )

        if result.success:
            response = f"J'ai transcrit le fichier audio '{doc_name}'.\n\n"

            # Note: We no longer store transcription in the audio source document
            # The transcription is stored in the markdown file created by the workflow

            if result.formatted_markdown:
                response += f"Un document markdown '{Path(doc_name).stem}.md' a été créé avec le contenu formaté.\n\n"
                response += f"**Aperçu de la transcription:**\n\n{result.transcript_text[:800]}"
                if len(result.transcript_text) > 800:
                    response += "..."
            else:
                response += f"**Transcription:**\n\n{result.transcript_text[:800]}"
                if len(result.transcript_text) > 800:
                    response += "..."

            return response
        else:
            return f"Erreur lors de la transcription de '{doc_name}': {result.error or 'Erreur inconnue'}"

    except ImportError as e:
        if "whisper" in str(e).lower():
            return "La transcription audio n'est pas disponible car Whisper n'est pas installé. Pour activer cette fonctionnalité, exécutez: uv sync --extra whisper"
        raise
    except Exception as e:
        logger.error(f"Transcription error: {e}", exc_info=True)
        return f"Erreur lors de la transcription: {str(e)}"


def get_available_tools() -> list:
    """
    Returns a list of available tools for the agent.

    The agent can use this to inform the user about its capabilities.
    """
    tools = []

    # Check if Whisper is available
    try:
        from services.whisper_service import WHISPER_AVAILABLE
        if WHISPER_AVAILABLE:
            tools.append({
                "name": "transcribe_audio",
                "description": "Transcrit des fichiers audio en texte (MP3, WAV, M4A, etc.) en utilisant Whisper",
                "available": True
            })
        else:
            tools.append({
                "name": "transcribe_audio",
                "description": "Transcription audio (non disponible - Whisper non installé)",
                "available": False
            })
    except ImportError:
        tools.append({
            "name": "transcribe_audio",
            "description": "Transcription audio (non disponible - Whisper non installé)",
            "available": False
        })

    return tools


def get_tools_description() -> str:
    """
    Returns a description of available tools for the system prompt.
    """
    tools = get_available_tools()

    if not tools:
        return "Aucun outil spécialisé n'est disponible."

    available = [t for t in tools if t["available"]]
    unavailable = [t for t in tools if not t["available"]]

    description = ""

    if available:
        description += "**Outils disponibles:**\n"
        for t in available:
            description += f"- {t['name']}: {t['description']}\n"

    if unavailable:
        if description:
            description += "\n"
        description += "**Outils non disponibles:**\n"
        for t in unavailable:
            description += f"- {t['name']}: {t['description']}\n"

    return description
