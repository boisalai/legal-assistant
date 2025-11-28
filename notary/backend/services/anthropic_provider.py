"""
Provider Anthropic pour utiliser l'API Claude.

Claude est excellent pour l'analyse de documents juridiques grâce à:
- Contexte de 200k tokens (peut lire des documents très longs)
- Excellente compréhension du français
- Raisonnement nuancé pour les cas complexes
"""

import logging
from typing import Any, Optional

from services.llm_provider import LLMProvider, LLMMessage, LLMResponse

logger = logging.getLogger(__name__)


class AnthropicProvider(LLMProvider):
    """
    Provider pour l'API Anthropic (Claude).

    Utilise l'API REST d'Anthropic pour accéder aux modèles Claude.
    Nécessite une clé API (ANTHROPIC_API_KEY).
    """

    def __init__(
        self,
        model_name: str = "claude-3-5-sonnet-20241022",
        api_key: Optional[str] = None,
        **kwargs
    ):
        """
        Initialise le provider Anthropic.

        Args:
            model_name: Nom du modèle Claude à utiliser
                - claude-3-5-sonnet-20241022 (recommandé - meilleur rapport qualité/prix)
                - claude-3-opus-20240229 (le plus puissant)
                - claude-3-haiku-20240307 (le plus rapide/économique)
            api_key: Clé API Anthropic (ou via variable d'environnement)
            **kwargs: Configuration additionnelle
        """
        super().__init__(model_name, **kwargs)

        self.api_key = api_key
        self.client = None

        # Configuration par défaut
        self.default_max_tokens = kwargs.get("max_tokens", 4096)
        self.default_temperature = kwargs.get("temperature", 0.7)

        logger.info(f"AnthropicProvider initialisé avec modèle: {model_name}")

    def _init_client(self):
        """
        Initialise le client Anthropic.

        Cette méthode est appelée lors de la première génération
        pour éviter d'importer anthropic si non utilisé.
        """
        if self.client is not None:
            return

        try:
            from anthropic import Anthropic
            import os

            # Utiliser la clé fournie ou celle de l'environnement
            api_key = self.api_key or os.getenv("ANTHROPIC_API_KEY")

            if not api_key:
                raise ValueError(
                    "Clé API Anthropic manquante. "
                    "Définissez ANTHROPIC_API_KEY dans .env ou passez api_key au constructeur."
                )

            self.client = Anthropic(api_key=api_key)
            logger.info("✓ Client Anthropic initialisé")

        except ImportError:
            raise RuntimeError(
                "Le package 'anthropic' n'est pas installé. "
                "Installez-le avec: uv add anthropic"
            )
        except Exception as e:
            logger.error(f"❌ Erreur lors de l'initialisation du client Anthropic: {e}")
            raise

    def generate(
        self,
        messages: list[LLMMessage],
        max_tokens: int = 4096,
        temperature: float = 0.7,
        **kwargs
    ) -> LLMResponse:
        """
        Génère une réponse avec l'API Claude.

        Args:
            messages: Liste de messages de la conversation
            max_tokens: Nombre maximum de tokens à générer
            temperature: Température (0.0 = déterministe, 1.0 = créatif)
            **kwargs: Paramètres additionnels (top_p, top_k, etc.)

        Returns:
            LLMResponse avec la réponse générée
        """
        # Initialiser le client si nécessaire
        if self.client is None:
            self._init_client()

        # Convertir nos messages au format Anthropic
        anthropic_messages = self._convert_messages(messages)

        # Extraire le message système s'il existe
        system_message = None
        filtered_messages = []

        for msg in anthropic_messages:
            if msg["role"] == "system":
                system_message = msg["content"]
            else:
                filtered_messages.append(msg)

        logger.debug(
            f"Génération avec Claude (max_tokens={max_tokens}, temp={temperature})"
        )

        try:
            # Appel à l'API Anthropic
            api_params = {
                "model": self.model_name,
                "messages": filtered_messages,
                "max_tokens": max_tokens,
                "temperature": temperature,
            }

            # Ajouter le message système si présent
            if system_message:
                api_params["system"] = system_message

            # Ajouter les paramètres optionnels
            if "top_p" in kwargs:
                api_params["top_p"] = kwargs["top_p"]
            if "top_k" in kwargs:
                api_params["top_k"] = kwargs["top_k"]
            if "stop_sequences" in kwargs:
                api_params["stop_sequences"] = kwargs["stop_sequences"]

            response = self.client.messages.create(**api_params)

            # Extraire le texte de la réponse
            content = response.content[0].text if response.content else ""

            return LLMResponse(
                content=content,
                model=response.model,
                tokens_used=response.usage.input_tokens + response.usage.output_tokens,
                finish_reason=response.stop_reason,
                metadata={
                    "provider": "anthropic",
                    "input_tokens": response.usage.input_tokens,
                    "output_tokens": response.usage.output_tokens,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                }
            )

        except Exception as e:
            logger.error(f"❌ Erreur lors de la génération avec Claude: {e}")
            raise RuntimeError(f"Erreur de génération Claude: {e}")

    def _convert_messages(self, messages: list[LLMMessage]) -> list[dict]:
        """
        Convertit nos messages au format Anthropic.

        Format Anthropic:
        [
            {"role": "user", "content": "..."},
            {"role": "assistant", "content": "..."},
        ]

        Note: Les messages système sont gérés via le paramètre 'system' séparé.
        """
        converted = []

        for msg in messages:
            # Les messages système sont gérés séparément
            if msg.role == "system":
                converted.append({"role": "system", "content": msg.content})
            elif msg.role in ["user", "assistant"]:
                converted.append({"role": msg.role, "content": msg.content})
            else:
                logger.warning(f"Rôle de message inconnu: {msg.role}")

        return converted

    def is_available(self) -> bool:
        """
        Vérifie si l'API Anthropic est disponible.

        Returns:
            True si la clé API est configurée et le package installé
        """
        try:
            import anthropic
            import os

            # Vérifier qu'une clé API est disponible
            api_key = self.api_key or os.getenv("ANTHROPIC_API_KEY")

            if not api_key:
                logger.warning(
                    "Clé API Anthropic manquante. "
                    "Définissez ANTHROPIC_API_KEY dans .env"
                )
                return False

            return True

        except ImportError:
            logger.warning(
                "Le package 'anthropic' n'est pas installé. "
                "Installez-le avec: uv add anthropic"
            )
            return False
        except Exception as e:
            logger.error(f"Anthropic non disponible: {e}")
            return False

    def get_info(self) -> dict[str, Any]:
        """
        Retourne les informations sur ce provider.

        Returns:
            Dictionnaire avec les informations
        """
        import os

        has_api_key = bool(self.api_key or os.getenv("ANTHROPIC_API_KEY"))

        return {
            "name": "Anthropic Provider",
            "model": self.model_name,
            "available": self.is_available(),
            "has_api_key": has_api_key,
            "platform": "API Cloud (Anthropic)",
            "config": {
                "max_tokens": self.default_max_tokens,
                "temperature": self.default_temperature,
                **self.config
            }
        }


# ========================================
# Modèles Claude recommandés
# ========================================

CLAUDE_MODELS = {
    "sonnet": {
        "name": "claude-3-5-sonnet-20241022",
        "description": "Meilleur rapport qualité/prix - Recommandé pour la production",
        "context": "200k tokens",
        "speed": "Rapide",
        "cost": "$$"
    },
    "opus": {
        "name": "claude-3-opus-20240229",
        "description": "Le plus puissant - Pour les tâches les plus complexes",
        "context": "200k tokens",
        "speed": "Lent",
        "cost": "$$$$"
    },
    "haiku": {
        "name": "claude-3-haiku-20240307",
        "description": "Le plus rapide et économique - Pour les tâches simples",
        "context": "200k tokens",
        "speed": "Très rapide",
        "cost": "$"
    }
}


def get_claude_model(preference: str = "balanced") -> str:
    """
    Retourne un modèle Claude recommandé selon la préférence.

    Args:
        preference: "fast" (haiku), "balanced" (sonnet), "quality" (opus)

    Returns:
        Nom du modèle Claude
    """
    if preference == "fast":
        return CLAUDE_MODELS["haiku"]["name"]
    elif preference == "quality":
        return CLAUDE_MODELS["opus"]["name"]
    else:  # balanced
        return CLAUDE_MODELS["sonnet"]["name"]
