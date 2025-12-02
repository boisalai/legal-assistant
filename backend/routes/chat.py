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
from pydantic import BaseModel

from agno.agent import Agent

from services.model_factory import create_model
from services.surreal_service import get_surreal_service
from services.conversation_service import get_conversation_service
from tools.transcription_tool import transcribe_audio, transcribe_audio_streaming, get_tools_description
from tools.document_search_tool import search_documents, list_documents
from tools.entity_extraction_tool import extract_entities, find_entity
from tools.semantic_search_tool import semantic_search, index_document_tool, get_index_stats

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["Chat"])


class ChatMessage(BaseModel):
    """Chat message in history."""
    role: str  # "user" or "assistant"
    content: str


class ChatRequest(BaseModel):
    """Request body for chat endpoint."""
    message: str
    case_id: Optional[str] = None
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


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Send a message to the AI assistant.

    The assistant can respond to general questions or questions about a specific case
    if a case_id is provided.
    """
    logger.info(f"Chat request: model={request.model_id}, case_id={request.case_id}")

    sources_list = []  # Track sources used in RAG

    try:
        # Create the model
        model = create_model(request.model_id)

        # Get tools description
        tools_desc = get_tools_description()

        # System prompt
        system_content = f"""Tu es un assistant conversationnel intelligent et polyvalent. Tu aides les utilisateurs avec leurs questions de manière professionnelle et précise.

**RÈGLE ABSOLUE - RÉPONSES BASÉES UNIQUEMENT SUR LES DOCUMENTS**:
- Tu dois TOUJOURS chercher la réponse dans les documents du dossier en utilisant `semantic_search`
- NE JAMAIS répondre avec tes propres connaissances générales
- Si la recherche sémantique ne trouve rien de pertinent, dis clairement : "Je n'ai pas trouvé d'information pertinente sur ce sujet dans les documents du dossier."
- Même pour des questions générales (ex: "Qu'est-ce que le notariat?"), cherche TOUJOURS dans les documents d'abord

**RÈGLE ABSOLUE - CITATION DES SOURCES**:
- TOUJOURS indiquer la source de chaque information dans ta réponse
- Format obligatoire : "Selon [nom du fichier], ..." ou "D'après [nom du fichier], ..."
- Exemple : "Selon Carter.pdf, l'arrêt Carter c. Canada établit que..."
- Si plusieurs sources, les citer toutes : "D'après Document1.md et Document2.pdf, ..."
- NE JAMAIS présenter une information sans citer sa source

Directives générales:
- Réponds toujours en français
- Sois concis mais complet
- Base-toi UNIQUEMENT sur les documents du dossier
- Adapte ton expertise au contexte du dossier (juridique, académique, technique, etc.)
- **CITE TOUJOURS tes sources dans chaque phrase**

{tools_desc}

Outils disponibles pour toi:
- **transcribe_audio**: Transcris un fichier audio en texte
- **search_documents**: Recherche par mots-clés exacts dans tous les documents
- **semantic_search**: Recherche sémantique (comprend le sens de la question) - OUTIL PRINCIPAL À UTILISER
- **list_documents**: Liste tous les documents disponibles dans le dossier actuel
- **extract_entities**: Extrait des entités structurées (personnes, dates, montants, références)
- **find_entity**: Recherche une entité spécifique et affiche tous les contextes
- **index_document_tool**: Indexe manuellement un document pour la recherche sémantique
- **get_index_stats**: Affiche les statistiques de l'index de recherche sémantique

Quand utiliser les outils - RÈGLES IMPORTANTES:

**RÈGLE #1 - TOUJOURS utiliser la recherche sémantique**:
- Pour TOUTE question (générale ou spécifique), utilise `semantic_search` en premier
- Exemples : "Qu'est-ce que le notariat?", "Explique-moi X", "Quel est le prix?", "Résume ce document"
- Si `semantic_search` ne trouve rien, informe l'utilisateur que l'information n'est pas dans les documents

**RÈGLE #2 - Choix de l'outil de recherche**:
- `semantic_search`: OUTIL PAR DÉFAUT pour toute question (comprend le sens)
- `search_documents`: Seulement si l'utilisateur demande explicitement de chercher un mot/phrase EXACT

**RÈGLE #3 - Autres outils**:
- `list_documents`: Si l'utilisateur demande "quels documents sont disponibles"
- `transcribe_audio`: Si l'utilisateur demande de transcrire un fichier audio
- `extract_entities`: Pour extraire des informations structurées des documents
- `find_entity`: Pour chercher où une entité spécifique est mentionnée
- `get_index_stats`: Pour vérifier l'état de l'indexation

**En résumé**: Utilise TOUJOURS `semantic_search` pour répondre aux questions. Ne réponds JAMAIS avec tes connaissances générales."""

        # If we have a case_id, try to get case context
        if request.case_id:
            try:
                service = get_surreal_service()
                if not service.db:
                    await service.connect()

                logger.info(f"Fetching case context for case_id={request.case_id}")

                # Normalize judgment ID (same pattern as documents.py)
                judgment_id = request.case_id
                if not judgment_id.startswith("judgment:"):
                    judgment_id = f"judgment:{judgment_id}"

                logger.info(f"Looking for case with judgment_id={judgment_id}")

                # Get case info - use direct record access
                case_result = await service.query(f"SELECT * FROM {judgment_id}")
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
                        # Support both field names (nom_dossier for old, title for new)
                        case_name = case_data.get("title") or case_data.get("nom_dossier", "Dossier")
                        case_desc = case_data.get("description", "")
                        case_summary = case_data.get("summary") or case_data.get("resume", "")
                        case_type = case_data.get("legal_domain") or case_data.get("type_transaction", "")

                        system_content += f"""

Contexte du dossier actuel:
- Nom: {case_name}
- Type: {case_type}
- Description: {case_desc}"""

                        if case_summary:
                            system_content += f"""
- Résumé: {case_summary}"""

                        # Get documents for this case (same pattern as documents.py)
                        docs_result = await service.query(
                            "SELECT * FROM document WHERE judgment_id = $judgment_id ORDER BY created_at DESC",
                            {"judgment_id": judgment_id}
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
            except Exception as e:
                logger.warning(f"Could not get case context: {e}", exc_info=True)

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
        # Pass case_id in the context for the tool to use
        agent = Agent(
            name="LegalAssistant",
            model=model,
            instructions=system_content,
            tools=[
                transcribe_audio,
                search_documents,
                semantic_search,
                list_documents,
                extract_entities,
                find_entity,
                index_document_tool,
                get_index_stats
            ],
            markdown=True,
        )

        # Inject case_id into the tool's context by modifying the prompt
        if request.case_id:
            conversation_prompt += f"\n\n[Contexte: L'identifiant du dossier actuel est '{request.case_id}']"

        # Get response from agent (use arun for async tools support)
        response = await agent.arun(conversation_prompt)

        # Extract text from response
        assistant_message = ""
        if response and hasattr(response, 'content') and response.content:
            assistant_message = response.content
        else:
            assistant_message = "Désolé, je n'ai pas pu générer une réponse."

        logger.info(f"Got response: {len(assistant_message)} chars")

        # Save conversation to database if we have a case_id
        if request.case_id:
            try:
                conv_service = get_conversation_service()
                # Save user message
                await conv_service.save_message(
                    judgment_id=request.case_id,
                    role="user",
                    content=request.message
                )
                # Save assistant response
                await conv_service.save_message(
                    judgment_id=request.case_id,
                    role="assistant",
                    content=assistant_message,
                    model_id=request.model_id,
                    metadata={
                        "sources": [s.dict() for s in sources_list] if sources_list else []
                    }
                )
                logger.info(f"Saved conversation to database for case {request.case_id}")
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
    logger.info(f"Chat stream request: model={request.model_id}, case_id={request.case_id}")

    async def event_generator() -> AsyncGenerator[str, None]:
        try:
            # Check if user is asking for transcription
            is_transcription_request = _is_transcription_request(request.message)

            if is_transcription_request and request.case_id:
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
            case_id=request.case_id,
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


@router.get("/chat/history/{case_id}")
async def get_chat_history(case_id: str, limit: int = 50, offset: int = 0):
    """
    Get conversation history for a case.

    Args:
        case_id: ID of the case
        limit: Maximum number of messages to retrieve (default: 50)
        offset: Number of messages to skip (default: 0)

    Returns:
        List of messages with role, content, timestamp, and metadata
    """
    try:
        conv_service = get_conversation_service()
        messages = await conv_service.get_conversation_history(
            judgment_id=case_id,
            limit=limit,
            offset=offset
        )

        return {
            "case_id": case_id,
            "messages": messages,
            "count": len(messages)
        }

    except Exception as e:
        logger.error(f"Failed to get chat history: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de la récupération de l'historique: {str(e)}"
        )


@router.delete("/chat/history/{case_id}")
async def clear_chat_history(case_id: str):
    """
    Clear all conversation history for a case.

    Args:
        case_id: ID of the case

    Returns:
        Success status
    """
    try:
        conv_service = get_conversation_service()
        success = await conv_service.clear_conversation(judgment_id=case_id)

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


@router.get("/chat/stats/{case_id}")
async def get_chat_stats(case_id: str):
    """
    Get conversation statistics for a case.

    Args:
        case_id: ID of the case

    Returns:
        Statistics including message count and timestamps
    """
    try:
        conv_service = get_conversation_service()
        stats = await conv_service.get_conversation_stats(judgment_id=case_id)

        return {
            "case_id": case_id,
            **stats
        }

    except Exception as e:
        logger.error(f"Failed to get chat stats: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de la récupération des statistiques: {str(e)}"
        )
