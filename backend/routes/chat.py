"""
Chat API routes for Legal Assistant.

Provides conversational AI chat endpoint for case discussions.
Uses Agno Agent with tools for enhanced capabilities.
"""

import asyncio
import json
import logging
import time
from typing import Optional, AsyncGenerator

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from agno.agent import Agent

from services.model_factory import create_model
from services.surreal_service import get_surreal_service
from services.conversation_service import get_conversation_service
from services.model_server_manager import ensure_model_server
from services.user_activity_service import get_activity_service
from tools.transcription_tool import transcribe_audio, transcribe_audio_streaming, get_tools_description
from tools.document_search_tool import search_documents, list_documents
from tools.entity_extraction_tool import extract_entities, find_entity
from tools.semantic_search_tool import semantic_search, index_document_tool, get_index_stats
from tools.caij_search_tool import search_caij_jurisprudence
from tools.tutor_tools import generate_summary, generate_mindmap, generate_quiz, explain_concept

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["Chat"])


class ChatMessage(BaseModel):
    """Chat message in history."""
    role: str  # "user" or "assistant"
    content: str


class ChatRequest(BaseModel):
    """Request body for chat endpoint."""
    message: str = Field(..., min_length=1, description="Message cannot be empty")
    course_id: Optional[str] = None
    model_id: str = "ollama:qwen2.5:7b"
    history: list[ChatMessage] = []


class DocumentSource(BaseModel):
    """Information about a document source used in the response."""
    name: str
    type: str
    word_count: int
    is_transcription: bool = False


class ChatResponse(BaseModel):
    """Response from chat endpoint."""
    message: str
    model_used: str
    document_created: bool = False  # Indicates if a new document was created during the chat
    sources: list[DocumentSource] = []  # Sources consulted for RAG


# Helper functions for tutor mode

def _get_current_document_from_activities(activities: list) -> Optional[str]:
    """
    Parse activities to find the currently open document.

    Args:
        activities: List of activity dictionaries (newest first)

    Returns:
        document_id if a document is open, None otherwise
    """
    for activity in activities:
        action_type = activity.get("action_type")
        metadata = activity.get("metadata", {})

        if action_type == "view_document":
            # Found most recent view_document → document is open
            return metadata.get("document_id")
        elif action_type == "close_document":
            # User closed a document, so no document is currently open
            return None

    return None  # No document viewing activity found


def _parse_surreal_record(record: dict) -> Optional[dict]:
    """
    Parse a SurrealDB record response.

    Args:
        record: SurrealDB record response

    Returns:
        Parsed record data or None
    """
    if isinstance(record, dict):
        if "result" in record and isinstance(record["result"], list) and len(record["result"]) > 0:
            return record["result"][0]
        elif "id" in record or "nom_fichier" in record:
            # Direct record result
            return record
    elif isinstance(record, list) and len(record) > 0:
        return record[0]

    return None


def _build_tutor_system_prompt(
    case_data: Optional[dict],
    documents: list,
    activity_context: str,
    current_document_id: Optional[str],
    current_document: Optional[dict],
    tools_desc: str
) -> str:
    """
    Build context-aware tutor system prompt.

    Args:
        case_data: Course/case information
        documents: List of documents in the course
        activity_context: Recent activity context
        current_document_id: ID of currently open document (if any)
        current_document: Full document data (if any)
        tools_desc: Description of available tools

    Returns:
        Complete system prompt for tutor mode
    """
    # Base tutor identity
    base_prompt = """Tu es un tuteur pédagogique IA spécialisé dans l'accompagnement d'étudiants en droit.
Ton rôle est d'aider l'étudiant à comprendre, mémoriser et maîtriser le contenu de ses cours."""

    # Context-specific instructions
    context_specific = ""
    if current_document_id and current_document:
        # TUTOR MODE: Document-focused
        doc_name = current_document.get("nom_fichier", "document")
        doc_preview = current_document.get("texte_extrait", "")[:2000]

        context_specific = f"""

📄 **CONTEXTE ACTUEL**: L'étudiant consulte actuellement le document "{doc_name}"

**MODE TUTEUR - DOCUMENT SPÉCIFIQUE**:
- L'étudiant étudie CE document en particulier
- Focalise tes réponses sur le contenu de ce document
- Utilise la méthode socratique: pose des questions pour guider sa réflexion
- Encourage la compréhension active plutôt que la mémorisation passive
- Propose des outils pédagogiques adaptés:
  - 📝 Résumés (use tool: generate_summary)
  - 🗺️ Cartes mentales (use tool: generate_mindmap)
  - ❓ Quiz d'auto-évaluation (use tool: generate_quiz)
  - 💡 Explications de concepts (use tool: explain_concept)

**APPROCHE PÉDAGOGIQUE**:
1. Comprendre d'abord ce que l'étudiant cherche à apprendre
2. Évaluer son niveau de compréhension actuel par des questions
3. Adapter ton niveau d'explication en conséquence
4. Proposer des exemples concrets et des applications pratiques
5. Vérifier la compréhension avant de passer au concept suivant

**RÈGLES SPÉCIFIQUES**:
- Si l'étudiant demande "résume ce document", utilise `generate_summary` avec document_id={current_document_id}
- Si l'étudiant demande une "carte mentale", utilise `generate_mindmap` avec document_id={current_document_id}
- Si l'étudiant veut "tester ses connaissances", utilise `generate_quiz` avec document_id={current_document_id}
- Si l'étudiant demande "explique X", cherche TOUJOURS dans le document ouvert en priorité

**CONTENU DU DOCUMENT ACTUEL** (aperçu):
{doc_preview}...
"""
    else:
        # TUTOR MODE: Course-wide
        course_title = case_data.get("title", "ce cours") if case_data else "ce cours"
        num_docs = len(documents)

        context_specific = f"""

📚 **CONTEXTE ACTUEL**: L'étudiant travaille sur le cours "{course_title}"
Nombre de documents disponibles: {num_docs}

**MODE TUTEUR - COURS COMPLET**:
- L'étudiant étudie l'ensemble du cours
- Aide-le à naviguer entre les différents documents
- Propose une vue d'ensemble des concepts couverts
- Guide-le vers les documents pertinents selon ses questions
- Utilise les outils pédagogiques pour consolider l'apprentissage:
  - 📝 Résumés du cours complet (use tool: generate_summary sans document_id)
  - 🗺️ Carte mentale globale (use tool: generate_mindmap sans document_id)
  - ❓ Quiz global (use tool: generate_quiz sans document_id)

**APPROCHE PÉDAGOGIQUE**:
1. Identifier les lacunes de connaissance
2. Suggérer un parcours d'apprentissage logique
3. Connecter les concepts entre différents documents
4. Créer une vision cohérente du cours

**RÈGLES SPÉCIFIQUES**:
- Si l'étudiant demande "résume le cours", utilise `generate_summary` sans document_id
- Suggère d'ouvrir un document spécifique si la question nécessite une lecture approfondie
- Utilise `semantic_search` pour trouver dans quel document se trouve l'information recherchée
"""

    # Combine all parts
    full_prompt = f"""{base_prompt}

{context_specific}

{activity_context}

**RÈGLE ABSOLUE - RÉPONSES BASÉES UNIQUEMENT SUR LES DOCUMENTS**:
- Tu dois TOUJOURS chercher la réponse dans les documents disponibles en utilisant `semantic_search`
- NE JAMAIS répondre avec tes propres connaissances générales
- Si la recherche sémantique ne trouve rien de pertinent, dis clairement : "Je n'ai pas trouvé d'information pertinente sur ce sujet dans les documents disponibles."

**RÈGLE ABSOLUE - CITATION DES SOURCES**:
- TOUJOURS indiquer la source de chaque information dans ta réponse
- Format obligatoire : "Selon [nom du fichier], ..." ou "D'après [nom du fichier], ..."

{tools_desc}

**OUTILS DISPONIBLES**:
- **generate_summary**: Génère un résumé pédagogique structuré
- **generate_mindmap**: Crée une carte mentale en markdown avec emojis
- **generate_quiz**: Génère un quiz interactif avec explications
- **explain_concept**: Explique un concept de manière détaillée avec exemples
- **semantic_search**: Recherche sémantique (OUTIL PRINCIPAL) - comprend le sens de la question
- **search_documents**: Recherche par mots-clés exacts
- **list_documents**: Liste tous les documents disponibles
- **search_caij_jurisprudence**: Recherche de jurisprudence québécoise sur CAIJ

**MÉTHODE SOCRATIQUE** (à privilégier):
Au lieu de donner directement la réponse, pose des questions qui guident l'étudiant:
- "Qu'est-ce que tu comprends déjà sur ce sujet?"
- "As-tu remarqué que le document mentionne...?"
- "Quelle est la différence entre X et Y selon toi?"
- "Peux-tu identifier les éléments essentiels?"

Sois encourageant, patient et adapte-toi au rythme de l'étudiant.
"""

    return full_prompt


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Send a message to the AI assistant.

    The assistant can respond to general questions or questions about a specific case
    if a course_id is provided.
    """
    logger.info(f"Chat request: model={request.model_id}, course_id={request.course_id}")
    logger.info(f"DEBUG - model_id type: {type(request.model_id)}, value: '{request.model_id}'")
    logger.info(f"DEBUG - Checking if model_id starts with mlx/vllm/huggingface...")

    sources_list = []  # Track sources used in RAG

    try:
        # Auto-start model server if needed (MLX or vLLM)
        # Note: "huggingface:" is deprecated and redirects to "vllm:" in model_factory
        if request.model_id.startswith(("mlx:", "vllm:", "huggingface:")):
            logger.info("DEBUG - Auto-startup condition TRUE")
            if request.model_id.startswith("mlx:"):
                provider = "MLX"
            else:
                # Both "vllm:" and deprecated "huggingface:" use vLLM
                provider = "vLLM"
            logger.info(f"🚀 Modèle {provider} détecté: {request.model_id}")
            logger.info(f"⏳ Démarrage automatique du serveur {provider}...")

            server_ready = await ensure_model_server(request.model_id)

            if not server_ready:
                error_msg = f"❌ Échec du démarrage du serveur {provider}. "
                if provider == "MLX":
                    error_msg += "Vérifiez que mlx-lm est installé (uv sync)."
                else:
                    error_msg += "Vérifiez que vLLM est installé (pip install vllm)."
                logger.error(error_msg)
                raise HTTPException(status_code=500, detail=error_msg)

            logger.info(f"✅ Serveur {provider} prêt")
        else:
            logger.info(f"DEBUG - Auto-startup condition FALSE - model_id: '{request.model_id}'")
            logger.info("DEBUG - This model does not require auto-startup (not MLX/vLLM/huggingface)")

        # Create the model
        logger.info(f"DEBUG - Creating model with model_id: '{request.model_id}'")
        model = create_model(request.model_id)

        # Get tools description
        tools_desc = get_tools_description()

        # Get user activity context if we have a course_id
        activity_context = ""
        if request.course_id:
            try:
                activity_service = get_activity_service()
                activity_context = await activity_service.get_activity_context(
                    course_id=request.course_id,
                    limit=20  # Show last 20 activities for context
                )
            except Exception as e:
                logger.warning(f"Could not get activity context: {e}")

        # Initialize variables for tutor mode
        case_data = None
        documents = []
        current_document_id = None
        current_document = None
        system_content = ""  # Will be built later

        # If we have a course_id, try to get case context
        if request.course_id:
            try:
                service = get_surreal_service()
                if not service.db:
                    await service.connect()

                logger.info(f"Fetching case context for course_id={request.course_id}")

                # Normalize judgment ID (same pattern as documents.py)
                course_id = request.course_id
                if not course_id.startswith("course:"):
                    course_id = f"course:{course_id}"

                logger.info(f"Looking for case with course_id={course_id}")

                # Get case info - use direct record access
                case_result = await service.query(f"SELECT * FROM {course_id}")
                logger.info(f"Case query result: {case_result}")

                if case_result and len(case_result) > 0:
                    # Parse result - handle different SurrealDB response formats
                    case_data = None
                    result = case_result[0]

                    if isinstance(result, dict):
                        if "result" in result and isinstance(result["result"], list) and len(result["result"]) > 0:
                            case_data = result["result"][0]
                        elif "id" in result or "title" in result:
                            # Direct record result
                            case_data = result
                    elif isinstance(result, list) and len(result) > 0:
                        case_data = result[0]

                    logger.info(f"Parsed case_data: {case_data is not None}")

                    if case_data:
                        # Support both field names
                        case_name = case_data.get("title") 
                        case_desc = case_data.get("description", "")
                        case_summary = case_data.get("summary") or case_data.get("resume", "")

                        system_content += f"""

Contexte actuel:
- Titre: {case_name}
- Description: {case_desc}"""

                        if case_summary:
                            system_content += f"""
- Résumé: {case_summary}"""

                        # Get documents for this case (same pattern as documents.py)
                        docs_result = await service.query(
                            "SELECT * FROM document WHERE course_id = $course_id ORDER BY created_at DESC",
                            {"course_id": course_id}
                        )
                        logger.info(f"Documents query result type: {type(docs_result)}, len: {len(docs_result) if docs_result else 0}")

                        documents = []
                        if docs_result and len(docs_result) > 0:
                            # Handle different SurrealDB response formats
                            first_item = docs_result[0]
                            if isinstance(first_item, dict):
                                if "result" in first_item:
                                    # Format: [{"result": [...]}]
                                    documents = first_item["result"] if isinstance(first_item["result"], list) else []
                                elif "id" in first_item or "nom_fichier" in first_item:
                                    # Format: [{doc1}, {doc2}, ...] - direct list of documents
                                    documents = docs_result
                            elif isinstance(first_item, list):
                                # Format: [[doc1, doc2, ...]]
                                documents = first_item

                        logger.info(f"Parsed {len(documents)} documents")

                        if documents:
                            # Build relationship maps FIRST
                            audio_transcription_map = {}  # audio_filename -> transcription_filename
                            pdf_extraction_map = {}  # pdf_filename -> extraction_filename

                            # Map transcriptions to audio sources
                            for doc in documents:
                                if doc.get("is_transcription") and doc.get("source_audio"):
                                    source_audio = doc.get("source_audio")
                                    audio_transcription_map[source_audio] = doc.get("nom_fichier")

                            # Map markdown extractions to PDF sources (heuristic: same base name)
                            from pathlib import Path
                            md_files = [d for d in documents if d.get("nom_fichier", "").lower().endswith(".md") and not d.get("is_transcription")]
                            pdf_files_list = [d for d in documents if d.get("nom_fichier", "").lower().endswith(".pdf")]
                            for md_doc in md_files:
                                md_name = md_doc.get("nom_fichier", "")
                                md_base = Path(md_name).stem
                                for pdf_doc in pdf_files_list:
                                    pdf_name = pdf_doc.get("nom_fichier", "")
                                    pdf_base = Path(pdf_name).stem
                                    if md_base == pdf_base:
                                        pdf_extraction_map[pdf_name] = md_name
                                        break

                            system_content += f"""
- Nombre de documents: {len(documents)}

**IMPORTANT - Comprendre les relations entre documents:**
- Les fichiers .md avec "[Transcription de X]" sont des versions TEXTE de fichiers audio X - L'AUDIO A DÉJÀ ÉTÉ TRANSCRIT
- Les fichiers audio avec "[DÉJÀ TRANSCRIT → voir Y]" ont été traités - NE PAS RE-TRANSCRIRE
- Les fichiers PDF avec "[DÉJÀ EXTRAIT → voir Z]" ont été traités - NE PAS RE-EXTRAIRE
- Si un fichier audio montre "[DÉJÀ TRANSCRIT → voir Y]", cela signifie que le contenu audio est disponible dans Y
- RÈGLE ABSOLUE: Si tu vois "[DÉJÀ TRANSCRIT]" ou "[DÉJÀ EXTRAIT]", NE JAMAIS proposer de refaire l'opération

- Documents (liste résumée - utilise l'outil `list_documents` pour plus de détails):"""
                            # Collect document contents for context
                            doc_contents = []
                            sources_list = []  # Track sources for response
                            for doc in documents:
                                doc_name = doc.get("nom_fichier", "Document inconnu")
                                doc_type = doc.get("type_fichier", "").upper()
                                doc_size = doc.get("taille", 0)
                                # Format size
                                if doc_size < 1024:
                                    size_str = f"{doc_size} B"
                                elif doc_size < 1024 * 1024:
                                    size_str = f"{doc_size / 1024:.1f} KB"
                                else:
                                    size_str = f"{doc_size / (1024 * 1024):.1f} MB"

                                # Check if this is a transcription or audio file
                                is_transcription = doc.get("is_transcription", False)
                                source_audio = doc.get("source_audio", "")
                                is_audio = doc_type in ["MP3", "WAV", "M4A", "OGG", "WEBM"]
                                is_pdf = doc_type == "PDF"
                                texte_extrait = doc.get("texte_extrait", "")

                                # Build status note with relationships
                                if is_transcription and source_audio:
                                    status_note = f" [Transcription de {source_audio}]"
                                elif is_audio:
                                    transcription_file = audio_transcription_map.get(doc_name)
                                    if transcription_file:
                                        status_note = f" [DÉJÀ TRANSCRIT → voir {transcription_file}]"
                                    else:
                                        status_note = " [Non transcrit]"
                                elif is_pdf:
                                    extraction_file = pdf_extraction_map.get(doc_name)
                                    if extraction_file:
                                        status_note = f" [DÉJÀ EXTRAIT → voir {extraction_file}]"
                                    else:
                                        status_note = " [PDF non extrait]"
                                elif texte_extrait and doc_name in pdf_extraction_map.values():
                                    # This is a PDF extraction
                                    source_pdf = [k for k, v in pdf_extraction_map.items() if v == doc_name]
                                    if source_pdf:
                                        status_note = f" [Extraction de {source_pdf[0]}]"
                                    else:
                                        status_note = " [Contenu disponible]"
                                elif texte_extrait:
                                    status_note = " [Contenu disponible]"
                                else:
                                    status_note = ""

                                system_content += f"""
  - {doc_name} ({doc_type}, {size_str}){status_note}"""

                                # Collect extracted text for later inclusion
                                if texte_extrait:
                                    word_count = len(texte_extrait.split())
                                    doc_contents.append({
                                        "name": doc_name,
                                        "content": texte_extrait,
                                        "is_transcription": is_transcription
                                    })
                                    # Track this source
                                    sources_list.append(DocumentSource(
                                        name=doc_name,
                                        type=doc_type,
                                        word_count=word_count,
                                        is_transcription=is_transcription
                                    ))
                                elif is_audio:
                                    # Add a note that this audio file hasn't been transcribed
                                    doc_contents.append({
                                        "name": doc_name,
                                        "content": "[Ce fichier audio n'a pas encore été transcrit. Pour obtenir un résumé, veuillez d'abord transcrire le fichier audio.]",
                                        "is_transcription": False,
                                        "is_pending": True
                                    })

                            # Add document contents to the context
                            if doc_contents:
                                system_content += """

Contenu des documents:"""
                                for doc_info in doc_contents:
                                    content_type = "Transcription" if doc_info["is_transcription"] else "Contenu"
                                    # Limit content length to avoid context overflow
                                    content = doc_info["content"]
                                    if len(content) > 4000:
                                        content = content[:4000] + "... [contenu tronqué]"
                                    system_content += f"""

### {doc_info["name"]} ({content_type}):
{content}"""
                        else:
                            system_content += """
- Nombre de documents: 0"""

                        logger.info(f"Added case context for {case_name} with {len(documents)} documents")

                        # NEW: Detect currently open document from activities
                        current_document_id = None
                        current_document = None

                        if activity_context:
                            try:
                                # Get raw activities to parse
                                activities_raw = await activity_service.get_recent_activities(
                                    course_id=request.course_id,
                                    limit=20
                                )
                                current_document_id = _get_current_document_from_activities(activities_raw)

                                # If document is open, fetch full document data
                                if current_document_id:
                                    doc_result = await service.query(f"SELECT * FROM {current_document_id}")
                                    if doc_result and len(doc_result) > 0:
                                        current_document = _parse_surreal_record(doc_result[0])
                                        logger.info(f"✅ Tutor mode: Document '{current_document.get('nom_fichier')}' is currently open")
                                else:
                                    logger.info("✅ Tutor mode: No document open, course-wide context")
                            except Exception as e:
                                logger.warning(f"Could not detect current document: {e}")

                        # Replace system_content with tutor-aware prompt
                        system_content = _build_tutor_system_prompt(
                            case_data=case_data,
                            documents=documents,
                            activity_context=activity_context,
                            current_document_id=current_document_id,
                            current_document=current_document,
                            tools_desc=tools_desc
                        )

            except Exception as e:
                logger.warning(f"Could not get case context: {e}", exc_info=True)
        else:
            # No course_id provided - build tutor prompt without course context
            logger.info("No course_id provided - using tutor mode without course context")
            system_content = _build_tutor_system_prompt(
                case_data=None,
                documents=[],
                activity_context=activity_context,
                current_document_id=None,
                current_document=None,
                tools_desc=tools_desc
            )

        # Build the conversation prompt
        conversation_prompt = ""

        # Add conversation history
        for msg in request.history:
            role_name = "Utilisateur" if msg.role == "user" else "Assistant"
            conversation_prompt += f"\n{role_name}: {msg.content}\n"

        # Add current user message
        conversation_prompt += f"\nUtilisateur: {request.message}"

        logger.info(f"Sending conversation to agent with {len(request.history)} history messages")

        # Create an Agent with all available tools
        # Pass course_id in the context for the tool to use
        agent = Agent(
            name="LegalAssistant",
            model=model,
            instructions=system_content,
            tools=[
                # Existing tools
                transcribe_audio,
                search_documents,
                semantic_search,
                list_documents,
                extract_entities,
                find_entity,
                index_document_tool,  # Tool name: "index_document"
                get_index_stats,
                search_caij_jurisprudence,  # Recherche jurisprudence québécoise
                # NEW: Tutor tools for pedagogical support
                generate_summary,         # Generate pedagogical summaries
                generate_mindmap,         # Create mind maps with emojis
                generate_quiz,            # Generate interactive quizzes
                explain_concept,          # Explain legal concepts in detail
            ],
            markdown=True,
        )

        # Inject course_id into the tool's context by modifying the prompt
        if request.course_id:
            conversation_prompt += f"\n\n[Contexte: L'identifiant du cours actuel est '{request.course_id}']"

        # Get response from agent (use arun for async tools support)
        response = await agent.arun(conversation_prompt)

        # Extract text from response
        assistant_message = ""
        if response and hasattr(response, 'content') and response.content:
            assistant_message = response.content
        else:
            assistant_message = "Désolé, je n'ai pas pu générer une réponse."

        logger.info(f"Got response: {len(assistant_message)} chars")

        # Save conversation to database if we have a course_id
        if request.course_id:
            try:
                conv_service = get_conversation_service()
                # Save user message
                await conv_service.save_message(
                    course_id=request.course_id,
                    role="user",
                    content=request.message
                )
                # Save assistant response
                await conv_service.save_message(
                    course_id=request.course_id,
                    role="assistant",
                    content=assistant_message,
                    model_id=request.model_id,
                    metadata={
                        "sources": [s.dict() for s in sources_list] if sources_list else []
                    }
                )
                logger.info(f"Saved conversation to database for case {request.course_id}")
            except Exception as e:
                logger.warning(f"Failed to save conversation: {e}")

        # Detect if a document was created (transcription completed successfully)
        # Check for successful transcription phrases in the response
        document_created = False
        transcription_success_phrases = [
            "J'ai transcrit le fichier audio",
            "Un document markdown",
            "a été créé avec le contenu formaté",
        ]
        for phrase in transcription_success_phrases:
            if phrase in assistant_message:
                document_created = True
                break

        return ChatResponse(
            message=assistant_message,
            model_used=request.model_id,
            document_created=document_created,
            sources=sources_list
        )

    except Exception as e:
        logger.error(f"Chat error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de la génération de la réponse: {str(e)}"
        )


@router.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    """
    Stream chat messages with progressive responses.

    Uses SSE (Server-Sent Events) to send multiple messages:
    - message: Regular text message parts
    - complete_message: A complete standalone message
    - document_created: Notification when a document is created
    - done: Final event when streaming is complete
    """
    logger.info(f"Chat stream request: model={request.model_id}, course_id={request.course_id}")

    async def event_generator() -> AsyncGenerator[str, None]:
        try:
            # Check if user is asking for transcription
            is_transcription_request = _is_transcription_request(request.message)

            if is_transcription_request and request.course_id:
                # Handle transcription with streaming messages
                async for event in _handle_transcription_stream(request):
                    yield event
            else:
                # Regular chat - just stream the response
                async for event in _handle_regular_chat_stream(request):
                    yield event

        except Exception as e:
            logger.error(f"Chat stream error: {e}", exc_info=True)
            yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"

        yield "event: done\ndata: {}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


def _is_transcription_request(message: str) -> bool:
    """Check if the message is asking for audio transcription."""
    message_lower = message.lower()
    transcription_keywords = [
        "transcri", "transcrire", "transcription",
        "audio", "fichier audio", "enregistrement",
        "dictée", "voix", "parole",
    ]
    return any(kw in message_lower for kw in transcription_keywords)


async def _handle_transcription_stream(request: ChatRequest) -> AsyncGenerator[str, None]:
    """Handle transcription request with streaming progress messages."""
    # Find audio filename in the message
    audio_filename = _extract_audio_filename(request.message)

    # Send immediate acknowledgment (Message 1)
    if audio_filename:
        ack_message = f"Je vais transcrire le fichier audio **{audio_filename}** pour vous. Veuillez patienter un instant..."
    else:
        ack_message = "Je vais transcrire le fichier audio pour vous. Veuillez patienter un instant..."

    yield f"event: complete_message\ndata: {json.dumps({'content': ack_message, 'role': 'assistant'})}\n\n"

    # Start transcription with timing
    start_time = time.time()

    try:
        # Run the transcription
        result = await transcribe_audio_streaming(
            course_id=request.course_id,
            audio_filename=audio_filename,
            language="fr"
        )

        elapsed_time = time.time() - start_time

        if result.get("success"):
            # Send completion notification (Message 2)
            doc_name = result.get("original_filename", audio_filename or "audio")
            md_filename = result.get("markdown_filename", f"{doc_name.rsplit('.', 1)[0]}.md")
            completion_message = f"La transcription du fichier audio **{doc_name}** a été complétée avec succès en **{elapsed_time:.0f} secondes**. Le fichier **{md_filename}** a été créé."

            yield f"event: complete_message\ndata: {json.dumps({'content': completion_message, 'role': 'assistant'})}\n\n"
            yield f"event: document_created\ndata: {json.dumps({'document_id': result.get('document_id')})}\n\n"

            # Send summary (Message 3)
            transcript_text = result.get("transcript_text", "")
            if transcript_text:
                # Generate a brief summary
                summary = _generate_transcript_summary(transcript_text)
                summary_message = f"**Résumé de la transcription:**\n\n{summary}"
                yield f"event: complete_message\ndata: {json.dumps({'content': summary_message, 'role': 'assistant'})}\n\n"
        else:
            error_message = result.get("error", "Erreur inconnue lors de la transcription")
            yield f"event: complete_message\ndata: {json.dumps({'content': f'Erreur: {error_message}', 'role': 'assistant'})}\n\n"

    except Exception as e:
        logger.error(f"Transcription stream error: {e}", exc_info=True)
        yield f"event: complete_message\ndata: {json.dumps({'content': f'Erreur lors de la transcription: {str(e)}', 'role': 'assistant'})}\n\n"


def _extract_audio_filename(message: str) -> Optional[str]:
    """Extract audio filename from user message."""
    import re
    # Look for common audio file patterns
    patterns = [
        r'["\']([^"\']+\.(mp3|wav|m4a|ogg|webm|flac|aac))["\']',  # Quoted filename
        r'\b(\S+\.(mp3|wav|m4a|ogg|webm|flac|aac))\b',  # Unquoted filename
    ]
    for pattern in patterns:
        match = re.search(pattern, message, re.IGNORECASE)
        if match:
            return match.group(1)
    return None


def _generate_transcript_summary(text: str, max_length: int = 500) -> str:
    """Generate a brief summary of the transcript."""
    # For now, just return the first part of the transcript
    # TODO: Use LLM to generate proper summary
    if len(text) <= max_length:
        return text

    # Find a good break point
    truncated = text[:max_length]
    last_period = truncated.rfind('.')
    last_newline = truncated.rfind('\n')

    break_point = max(last_period, last_newline)
    if break_point > max_length // 2:
        return truncated[:break_point + 1] + "\n\n*[Transcription complète disponible dans le fichier]*"

    return truncated + "...\n\n*[Transcription complète disponible dans le fichier]*"


async def _handle_regular_chat_stream(request: ChatRequest) -> AsyncGenerator[str, None]:
    """Handle regular chat with streaming response."""
    try:
        # Auto-start model server if needed (MLX or vLLM)
        # Note: "huggingface:" is deprecated and redirects to "vllm:" in model_factory
        if request.model_id.startswith(("mlx:", "vllm:", "huggingface:")):
            if request.model_id.startswith("mlx:"):
                provider = "MLX"
                emoji = "🍎"
            else:
                # Both "vllm:" and deprecated "huggingface:" use vLLM
                provider = "vLLM"
                emoji = "🚀"

            logger.info(f"{emoji} Modèle {provider} détecté: {request.model_id}")
            logger.info(f"⏳ Démarrage automatique du serveur {provider}...")

            # Envoyer un message de statut à l'utilisateur
            yield f"event: message\ndata: {json.dumps({'content': f'{emoji} Démarrage du serveur {provider}...'})}\n\n"

            # Démarrer le serveur approprié
            from services.model_server_manager import ensure_model_server
            server_ready = await ensure_model_server(request.model_id)

            if not server_ready:
                error_msg = f"❌ Échec du démarrage du serveur {provider}. "
                if provider == "MLX":
                    error_msg += "Vérifiez que mlx-lm est installé (uv sync)."
                else:
                    error_msg += "Vérifiez que vLLM est installé (pip install vllm)."
                logger.error(error_msg)
                yield f"event: error\ndata: {json.dumps({'error': error_msg})}\n\n"
                return

            yield f"event: message\ndata: {json.dumps({'content': f'✅ Serveur {provider} prêt\\n\\n'})}\n\n"

        # Create the model
        model = create_model(request.model_id)

        # Get tools description
        tools_desc = get_tools_description()

        # System prompt (simplified version)
        system_content = f"""Tu es un assistant conversationnel intelligent et polyvalent. Tu aides les utilisateurs avec leurs questions de manière professionnelle et précise.

Directives:
- Réponds toujours en français
- Sois concis mais complet
- Si tu n'es pas sûr de quelque chose, dis-le clairement
- Adapte ton expertise au contexte (juridique, académique, technique, etc.)

{tools_desc}"""

        # Build conversation
        conversation_prompt = ""
        for msg in request.history:
            role_name = "Utilisateur" if msg.role == "user" else "Assistant"
            conversation_prompt += f"\n{role_name}: {msg.content}\n"
        conversation_prompt += f"\nUtilisateur: {request.message}"

        # Create agent without tools for regular chat
        agent = Agent(
            name="LegalAssistant",
            model=model,
            instructions=system_content,
            markdown=True,
        )

        # Get response
        response = await agent.arun(conversation_prompt)

        if response and hasattr(response, 'content') and response.content:
            yield f"event: complete_message\ndata: {json.dumps({'content': response.content, 'role': 'assistant'})}\n\n"
        else:
            error_msg = "Désolé, je n'ai pas pu générer une réponse."
            yield f"event: complete_message\ndata: {json.dumps({'content': error_msg, 'role': 'assistant'})}\n\n"

    except Exception as e:
        logger.error(f"Regular chat stream error: {e}", exc_info=True)
        yield f"event: complete_message\ndata: {json.dumps({'content': f'Erreur: {str(e)}', 'role': 'assistant'})}\n\n"


@router.get("/chat/history/{course_id}")
async def get_chat_history(course_id: str, limit: int = 50, offset: int = 0):
    """
    Get conversation history for a case.

    Args:
        course_id: ID of the case
        limit: Maximum number of messages to retrieve (default: 50)
        offset: Number of messages to skip (default: 0)

    Returns:
        List of messages with role, content, timestamp, and metadata
    """
    try:
        conv_service = get_conversation_service()
        messages = await conv_service.get_conversation_history(
            case_id=course_id,  # Service expects case_id parameter
            limit=limit,
            offset=offset
        )

        return {
            "course_id": course_id,
            "messages": messages,
            "count": len(messages)
        }

    except Exception as e:
        logger.error(f"Failed to get chat history: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de la récupération de l'historique: {str(e)}"
        )


@router.delete("/chat/history/{course_id}")
async def clear_chat_history(course_id: str):
    """
    Clear all conversation history for a case.

    Args:
        course_id: ID of the case

    Returns:
        Success status
    """
    try:
        conv_service = get_conversation_service()
        success = await conv_service.clear_conversation(case_id=course_id)  # Service expects case_id parameter

        if success:
            return {"success": True, "message": "Historique effacé avec succès"}
        else:
            raise HTTPException(
                status_code=500,
                detail="Erreur lors de l'effacement de l'historique"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to clear chat history: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de l'effacement de l'historique: {str(e)}"
        )


@router.get("/chat/stats/{course_id}")
async def get_chat_stats(course_id: str):
    """
    Get conversation statistics for a case.

    Args:
        course_id: ID of the case

    Returns:
        Statistics including message count and timestamps
    """
    try:
        conv_service = get_conversation_service()
        stats = await conv_service.get_conversation_stats(case_id=course_id)  # Service expects case_id parameter

        return {
            "course_id": course_id,
            **stats
        }

    except Exception as e:
        logger.error(f"Failed to get chat stats: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de la récupération des statistiques: {str(e)}"
        )
