"""
Interface abstraite pour les fournisseurs de LLM.

Cette architecture permet de changer facilement de provider (MLX, Anthropic, etc.)
sans modifier le code des workflows.
"""

from abc import ABC, abstractmethod
from typing import Any, Optional
from dataclasses import dataclass


@dataclass
class LLMMessage:
    """
    Représente un message dans une conversation.
    """
    role: str  # "system", "user", "assistant"
    content: str


@dataclass
class LLMResponse:
    """
    Réponse d'un LLM.
    """
    content: str
    model: str
    tokens_used: Optional[int] = None
    finish_reason: Optional[str] = None
    metadata: Optional[dict[str, Any]] = None


class LLMProvider(ABC):
    """
    Classe abstraite pour tous les providers LLM.

    Chaque provider (MLX, Anthropic, OpenAI, etc.) doit implémenter
    cette interface pour assurer la compatibilité.
    """

    def __init__(self, model_name: str, **kwargs):
        """
        Initialise le provider.

        Args:
            model_name: Nom du modèle à utiliser
            **kwargs: Configuration spécifique au provider
        """
        self.model_name = model_name
        self.config = kwargs

    @abstractmethod
    def generate(
        self,
        messages: list[LLMMessage],
        max_tokens: int = 2000,
        temperature: float = 0.7,
        **kwargs
    ) -> LLMResponse:
        """
        Génère une réponse basée sur les messages.

        Args:
            messages: Liste de messages de la conversation
            max_tokens: Nombre maximum de tokens à générer
            temperature: Température (0.0 = déterministe, 1.0 = créatif)
            **kwargs: Paramètres additionnels spécifiques au provider

        Returns:
            LLMResponse contenant la réponse générée
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """
        Vérifie si le provider est disponible et fonctionnel.

        Returns:
            True si le provider peut être utilisé
        """
        pass

    @abstractmethod
    def get_info(self) -> dict[str, Any]:
        """
        Retourne les informations sur le provider.

        Returns:
            Dictionnaire avec:
            - name: Nom du provider
            - model: Modèle utilisé
            - available: Si disponible
            - config: Configuration
        """
        pass

    def format_messages(self, messages: list[LLMMessage]) -> str:
        """
        Formate les messages en un seul prompt texte.

        Utile pour les modèles qui n'ont pas de format de conversation natif.

        Args:
            messages: Liste de messages

        Returns:
            Prompt texte formaté
        """
        formatted = []

        for msg in messages:
            if msg.role == "system":
                formatted.append(f"<|system|>\n{msg.content}\n")
            elif msg.role == "user":
                formatted.append(f"<|user|>\n{msg.content}\n")
            elif msg.role == "assistant":
                formatted.append(f"<|assistant|>\n{msg.content}\n")

        return "\n".join(formatted) + "<|assistant|>\n"

    def create_system_message(self, content: str) -> LLMMessage:
        """Helper pour créer un message système."""
        return LLMMessage(role="system", content=content)

    def create_user_message(self, content: str) -> LLMMessage:
        """Helper pour créer un message utilisateur."""
        return LLMMessage(role="user", content=content)

    def create_assistant_message(self, content: str) -> LLMMessage:
        """Helper pour créer un message assistant."""
        return LLMMessage(role="assistant", content=content)
