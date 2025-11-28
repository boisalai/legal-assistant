"""
Wrapper Agno Model pour utiliser notre service MLX local.

Ce wrapper permet d'utiliser le MLXProvider existant comme modèle
compatible avec les agents Agno en héritant de agno.models.base.Model.
"""

import logging
from typing import Any, AsyncIterator, Dict, Iterator, List, Optional, Union

from agno.models.base import Model
from agno.agent import Message

from services.llm_provider import LLMMessage
from services.mlx_provider import MLXProvider

logger = logging.getLogger(__name__)


class AgnoMLXModel(Model):
    """
    Wrapper pour utiliser MLX avec les agents Agno.

    Cette classe adapte notre MLXProvider pour qu'il soit compatible
    avec l'interface Model d'Agno.
    """

    def __init__(
        self,
        model_name: str = "mlx-community/Phi-3-mini-4k-instruct-4bit",
        **kwargs
    ):
        """
        Initialise le wrapper MLX pour Agno.

        Args:
            model_name: Nom du modèle MLX à utiliser
            **kwargs: Configuration additionnelle
        """
        # Extraire les paramètres spécifiques à MLX
        self.max_tokens = kwargs.pop("max_tokens", 2000)
        self.temperature = kwargs.pop("temperature", 0.7)

        # Appeler le constructeur parent de Model avec seulement les kwargs valides
        super().__init__(
            id=model_name,
            name="MLX Local Model",
            provider="mlx",
            **kwargs  # Les kwargs restants après avoir pop max_tokens et temperature
        )

        # Créer l'instance du provider MLX
        self.mlx_provider = MLXProvider(
            model_name=model_name,
            max_tokens=self.max_tokens,
            temperature=self.temperature
        )

        logger.info(f"AgnoMLXModel initialisé avec {model_name}")

    def response(
        self,
        messages: list[dict[str, Any]],
        **kwargs
    ) -> dict[str, Any]:
        """
        Génère une réponse à partir de messages.

        Cette méthode est appelée par les agents Agno.

        Args:
            messages: Liste de messages de conversation
            **kwargs: Paramètres de génération

        Returns:
            Dictionnaire avec la réponse
        """
        # Convertir les messages au format LLMMessage
        llm_messages = []
        for msg in messages:
            llm_messages.append(
                LLMMessage(
                    role=msg.get("role", "user"),
                    content=msg.get("content", "")
                )
            )

        # Extraire les paramètres
        max_tokens = kwargs.get("max_tokens", self.max_tokens)
        temperature = kwargs.get("temperature", self.temperature)

        # Générer la réponse avec MLX
        response = self.mlx_provider.generate(
            messages=llm_messages,
            max_tokens=max_tokens,
            temperature=temperature,
            **kwargs
        )

        # Retourner au format attendu par Agno
        return {
            "content": response.content,
            "model": response.model,
            "role": "assistant",
            "finish_reason": response.finish_reason,
            "usage": {
                "total_tokens": response.tokens_used or 0,
                "prompt_tokens": 0,  # MLX ne fournit pas ces détails
                "completion_tokens": response.tokens_used or 0
            },
            "metadata": response.metadata
        }

    async def aresponse(
        self,
        messages: list[dict[str, Any]],
        **kwargs
    ) -> dict[str, Any]:
        """
        Version asynchrone de response().

        Pour l'instant, on appelle simplement la version synchrone.
        """
        return self.response(messages, **kwargs)

    # ========================================================================
    # Méthodes abstraites requises par agno.models.base.Model
    # ========================================================================

    def invoke(
        self,
        messages: List[Message],
        **kwargs
    ) -> str:
        """
        Génère une réponse (méthode abstraite requise).

        Args:
            messages: Liste de messages Agno
            **kwargs: Paramètres de génération

        Returns:
            Le texte de la réponse
        """
        # Convertir les messages Agno en format dict
        message_dicts = [self._message_to_dict(m) for m in messages]

        # Générer la réponse
        response = self.response(message_dicts, **kwargs)
        return response.get("content", "")

    async def ainvoke(
        self,
        messages: List[Message],
        **kwargs
    ) -> str:
        """
        Version asynchrone de invoke() (méthode abstraite requise).

        Pour l'instant, appelle simplement la version synchrone.
        """
        return self.invoke(messages, **kwargs)

    def invoke_stream(
        self,
        messages: List[Message],
        **kwargs
    ) -> Iterator[str]:
        """
        Génère une réponse en streaming (méthode abstraite requise).

        MLX ne supporte pas nativement le streaming, donc on retourne
        la réponse complète en un seul chunk.

        Args:
            messages: Liste de messages Agno
            **kwargs: Paramètres de génération

        Yields:
            Chunks de texte
        """
        # Pour l'instant, retourner la réponse complète
        response = self.invoke(messages, **kwargs)
        yield response

    async def ainvoke_stream(
        self,
        messages: List[Message],
        **kwargs
    ) -> AsyncIterator[str]:
        """
        Version asynchrone de invoke_stream() (méthode abstraite requise).

        Args:
            messages: Liste de messages Agno
            **kwargs: Paramètres de génération

        Yields:
            Chunks de texte
        """
        # Pour l'instant, retourner la réponse complète
        response = await self.ainvoke(messages, **kwargs)
        yield response

    def _parse_provider_response(
        self,
        response: Any
    ) -> str:
        """
        Parse la réponse du provider (méthode abstraite requise).

        Args:
            response: Réponse brute du provider

        Returns:
            Texte extrait
        """
        if isinstance(response, dict):
            return response.get("content", "")
        return str(response)

    def _parse_provider_response_delta(
        self,
        delta: Any
    ) -> Optional[str]:
        """
        Parse un delta de streaming (méthode abstraite requise).

        Args:
            delta: Delta de réponse

        Returns:
            Texte extrait ou None
        """
        if isinstance(delta, dict):
            return delta.get("content")
        return str(delta) if delta else None

    # ========================================================================
    # Méthodes utilitaires
    # ========================================================================

    def _message_to_dict(self, message: Message) -> dict[str, Any]:
        """
        Convertit un message Agno en dictionnaire.

        Args:
            message: Message Agno

        Returns:
            Dictionnaire avec role et content
        """
        return {
            "role": message.role if hasattr(message, "role") else "user",
            "content": message.content if hasattr(message, "content") else str(message)
        }

    def get_info(self) -> dict[str, Any]:
        """
        Retourne les informations sur ce modèle.

        Returns:
            Dictionnaire avec les informations
        """
        info = self.mlx_provider.get_info()
        info.update({
            "id": self.id,
            "name": self.name,
            "provider": self.provider
        })
        return info

    def __repr__(self) -> str:
        return f"<AgnoMLXModel id={self.id} provider={self.provider}>"


def create_mlx_model(
    model_name: str = "mlx-community/Phi-3-mini-4k-instruct-4bit",
    **kwargs
) -> AgnoMLXModel:
    """
    Factory function pour créer un modèle MLX pour Agno.

    Args:
        model_name: Nom du modèle MLX
        **kwargs: Configuration additionnelle

    Returns:
        Instance de AgnoMLXModel

    Example:
        >>> model = create_mlx_model()
        >>> agent = Agent(name="Test", model=model)
    """
    return AgnoMLXModel(model_name=model_name, **kwargs)
