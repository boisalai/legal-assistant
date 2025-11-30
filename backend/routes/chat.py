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
from tools.transcription_tool import transcribe_audio, transcribe_audio_streaming, get_tools_description

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


class ChatResponse(BaseModel):
    """Response from chat endpoint."""
    message: str
    model_used: str
    document_created: bool = False  # Indicates if a new document was created during the chat


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Send a message to the AI assistant.

    The assistant can respond to general questions or questions about a specific case
    if a case_id is provided.
    """
    logger.info(f"Chat request: model={request.model_id}, case_id={request.case_id}")

    try:
        # Create the model
        model = create_model(request.model_id)

        # Get tools description
        tools_desc = get_tools_description()

        # System prompt
        system_content = f"""Tu es un assistant juridique expert. Tu aides les utilisateurs avec leurs questions juridiques de manière professionnelle et précise.

Directives:
- Réponds toujours en français
- Sois concis mais complet
- Si tu n'es pas sûr de quelque chose, dis-le clairement
- Ne donne jamais de conseils juridiques définitifs - recommande de consulter un avocat pour les questions importantes

{tools_desc}

Si l'utilisateur demande de transcrire un fichier audio, utilise l'outil transcribe_audio avec l'identifiant du dossier actuel."""

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
                            system_content += f"""
- Nombre de documents: {len(documents)}
- Documents:"""
                            # Collect document contents for context
                            doc_contents = []
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
                                is_audio = doc_type in ["MP3", "WAV", "M4A", "OGG", "WEBM"]
                                texte_extrait = doc.get("texte_extrait", "")

                                # Build status note
                                if is_transcription:
                                    status_note = " [Transcription audio]"
                                elif is_audio and not texte_extrait:
                                    status_note = " [Audio non transcrit]"
                                elif texte_extrait:
                                    status_note = " [Contenu disponible]"
                                else:
                                    status_note = ""

                                system_content += f"""
  - {doc_name} ({doc_type}, {size_str}){status_note}"""

                                # Collect extracted text for later inclusion
                                if texte_extrait:
                                    doc_contents.append({
                                        "name": doc_name,
                                        "content": texte_extrait,
                                        "is_transcription": is_transcription
                                    })
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

        # Create an Agent with the transcription tool
        # Pass case_id in the context for the tool to use
        agent = Agent(
            name="LegalAssistant",
            model=model,
            instructions=system_content,
            tools=[transcribe_audio],
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
            document_created=document_created
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
        system_content = f"""Tu es un assistant juridique expert. Tu aides les utilisateurs avec leurs questions juridiques de manière professionnelle et précise.

Directives:
- Réponds toujours en français
- Sois concis mais complet
- Si tu n'es pas sûr de quelque chose, dis-le clairement

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
