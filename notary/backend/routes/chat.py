"""
Routes API pour le chat avec l'assistant IA.

Endpoints:
- POST /api/chat - Envoyer un message à l'assistant
- POST /api/chat/stream - Chat avec réponse en streaming
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List
import logging
import json

from config.models import DEFAULT_OLLAMA_MODEL
from services.model_factory import create_model

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["chat"])


# ========================================
# Modèles Pydantic pour le chat
# ========================================

class ChatMessage(BaseModel):
    """Message dans l'historique de conversation."""
    role: str  # "user", "assistant", "system"
    content: str


class ChatRequest(BaseModel):
    """Requête de chat."""
    message: str
    case_id: Optional[str] = None
    model_id: Optional[str] = None
    history: Optional[List[ChatMessage]] = None


class ChatResponse(BaseModel):
    """Réponse de chat."""
    message: str
    model: str
    usage: Optional[dict] = None


# ========================================
# Prompt système pour l'assistant notarial
# ========================================

SYSTEM_PROMPT = """Tu es un assistant spécialisé en droit notarial québécois. Tu aides les notaires et leurs assistants avec:

- Les transactions immobilières (vente, achat, hypothèque)
- Les documents requis pour différents types de transactions
- Les calculs (droits de mutation/taxe de bienvenue, ajustements de taxes)
- Les procédures et délais typiques
- Les vérifications au registre foncier
- Le Code civil du Québec et la réglementation applicable

Réponds de manière professionnelle, précise et concise. Utilise le français québécois.
Si tu n'es pas sûr d'une information légale, indique-le clairement et suggère de consulter les sources officielles.

Important: Ne fournis jamais de conseils juridiques définitifs - rappelle que seul un notaire peut donner des conseils juridiques."""


# ========================================
# Endpoints
# ========================================

@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Envoie un message à l'assistant IA et reçoit une réponse.

    Paramètres:
    - message: Le message de l'utilisateur
    - case_id: Optionnel - ID du dossier pour contexte
    - model_id: Optionnel - ID du modèle à utiliser (défaut: ollama:qwen2.5:7b)
    - history: Optionnel - Historique de conversation pour contexte
    """
    model_id = request.model_id or f"ollama:{DEFAULT_OLLAMA_MODEL}"

    try:
        # Créer le modèle
        model = create_model(model_id)

        # Obtenir la connexion DB pour persister l'historique
        from services.agno_db_service import get_agno_db_service
        agno_db_service = get_agno_db_service()
        db = agno_db_service.get_agno_db()

        # Utiliser Agent avec historique de conversation
        from agno.agent import Agent

        # Créer l'agent avec support de l'historique
        # Si case_id est fourni, l'utiliser comme session_id pour grouper les conversations
        agent = Agent(
            model=model,
            description="Assistant notarial québécois",
            instructions=[SYSTEM_PROMPT],
            db=db,
            session_id=request.case_id,  # Groupe les conversations par dossier
            add_history_to_context=True,  # Ajoute automatiquement l'historique au contexte
            num_history_runs=10,  # Garde les 10 derniers échanges
        )

        # Exécuter la requête (l'historique est géré automatiquement par Agno)
        response = agent.run(request.message)

        # Extraire la réponse
        response_text = ""
        if hasattr(response, 'content'):
            response_text = response.content
        elif hasattr(response, 'messages') and response.messages:
            for msg in response.messages:
                if hasattr(msg, 'content') and msg.content:
                    response_text = msg.content
                    break
        else:
            response_text = str(response)

        return ChatResponse(
            message=response_text,
            model=model_id,
            usage=None
        )

    except ValueError as e:
        logger.error(f"Erreur création modèle: {e}")
        raise HTTPException(status_code=503, detail=f"Modèle non disponible: {str(e)}")
    except Exception as e:
        logger.error(f"Erreur chat: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur lors du chat: {str(e)}")


@router.post("/stream")
async def chat_stream(request: ChatRequest):
    """
    Chat avec réponse en streaming (Server-Sent Events).
    """
    model_id = request.model_id or f"ollama:{DEFAULT_OLLAMA_MODEL}"

    async def generate():
        try:
            model = create_model(model_id)

            # Obtenir la connexion DB pour persister l'historique
            from services.agno_db_service import get_agno_db_service
            from agno.agent import Agent

            agno_db_service = get_agno_db_service()
            db = agno_db_service.get_agno_db()

            # Créer l'agent avec support de l'historique
            agent = Agent(
                model=model,
                description="Assistant notarial québécois",
                instructions=[SYSTEM_PROMPT],
                db=db,
                session_id=request.case_id,
                add_history_to_context=True,
                num_history_runs=10,
            )

            # Stream la réponse (l'historique est géré automatiquement par Agno)
            response_stream = agent.run(request.message, stream=True)

            for chunk in response_stream:
                if hasattr(chunk, 'content') and chunk.content:
                    data = {"content": chunk.content, "done": False}
                    yield f"data: {json.dumps(data)}\n\n"

            # Signal de fin
            yield f"data: {json.dumps({'content': '', 'done': True, 'model': model_id})}\n\n"

        except Exception as e:
            logger.error(f"Erreur streaming: {e}")
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


@router.get("/health")
async def chat_health():
    """Vérifie l'état du service de chat."""
    return {
        "status": "ok",
        "default_model": f"ollama:{DEFAULT_OLLAMA_MODEL}",
    }
