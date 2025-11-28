"""
Factory pour créer des modèles Agno selon la configuration.

Ce module fournit des fonctions helpers pour créer des instances
de modèles Agno compatibles avec Agent, Team et Workflow.

Patterns officiels Agno:
- Ollama: agno.models.ollama.Ollama
- Claude: agno.models.anthropic.Claude
- MLX: agno.models.openai.OpenAILike (OpenAI-compatible API)

Usage:
    from services.model_factory import create_model

    # Ollama
    model = create_model("ollama:mistral")

    # Claude
    model = create_model("anthropic:claude-sonnet-4-5-20250929")

    # MLX (via OpenAI-compatible server)
    model = create_model("mlx:mlx-community/Phi-3-mini-4k-instruct-4bit")

    # Utiliser dans un agent
    agent = Agent(name="Test", model=model)
"""

import logging
import os
from typing import Any, Optional

from config.models import (
    DEFAULT_CLAUDE_MODEL,
    DEFAULT_MLX_MODEL,
    DEFAULT_MLX_SERVER_URL,
    DEFAULT_OLLAMA_MODEL,
)
from config.settings import settings

logger = logging.getLogger(__name__)


def create_model(model_string: str, **kwargs) -> Any:
    """
    Crée une instance de modèle Agno à partir d'une string.

    Format de la string:
        - "ollama:MODEL_NAME" → Ollama local
        - "anthropic:MODEL_ID" → Claude API
        - "mlx:MODEL_PATH" → MLX via OpenAI-compatible API
        - "openai:MODEL_ID" → OpenAI API (bonus)

    Args:
        model_string: String de configuration du modèle
        **kwargs: Paramètres additionnels (api_key, base_url, etc.)

    Returns:
        Instance de modèle Agno (Ollama, Claude, OpenAILike, etc.)

    Examples:
        >>> model = create_model("ollama:mistral")
        >>> model = create_model("anthropic:claude-sonnet-4-5-20250929", api_key="sk-ant-...")
        >>> model = create_model("mlx:mlx-community/Phi-3-mini-4k-instruct-4bit")

    Raises:
        ValueError: Si le format est invalide ou le provider non supporté
    """
    if ":" not in model_string:
        raise ValueError(
            f"Format invalide: '{model_string}'. "
            f"Format attendu: 'provider:model' (ex: 'ollama:mistral')"
        )

    provider, model_id = model_string.split(":", 1)
    provider = provider.lower().strip()
    model_id = model_id.strip()

    logger.info(f"Creating model: provider={provider}, model={model_id}")

    if provider == "ollama":
        return _create_ollama_model(model_id, **kwargs)
    elif provider == "anthropic":
        return _create_claude_model(model_id, **kwargs)
    elif provider == "mlx":
        return _create_mlx_model(model_id, **kwargs)
    elif provider == "openai":
        return _create_openai_model(model_id, **kwargs)
    else:
        raise ValueError(
            f"Provider non supporté: '{provider}'. "
            f"Providers supportés: ollama, anthropic, mlx, openai"
        )


def _create_ollama_model(model_id: str, **kwargs) -> Any:
    """
    Crée un modèle Ollama.

    Args:
        model_id: Nom du modèle Ollama (ex: "mistral", "llama3.2")
        **kwargs: Paramètres additionnels (host, timeout, etc.)

    Returns:
        Instance de agno.models.ollama.Ollama
    """
    try:
        from agno.models.ollama import Ollama
    except ImportError as e:
        raise ImportError(
            "Le package 'ollama' n'est pas installé. "
            "Installez-le avec: uv sync --extra ollama"
        ) from e

    # Configuration par défaut
    host = kwargs.pop("host", None)  # None = utilise la valeur par défaut d'Ollama

    if host:
        logger.info(f"✅ Creating Ollama model: {model_id} (host={host})")
    else:
        logger.info(f"✅ Creating Ollama model: {model_id} (default host)")

    return Ollama(
        id=model_id,
        host=host,
        **kwargs
    )


def _create_claude_model(model_id: str, **kwargs) -> Any:
    """
    Crée un modèle Claude (Anthropic).

    Args:
        model_id: ID du modèle Claude (ex: "claude-sonnet-4-5-20250929")
        **kwargs: Paramètres additionnels (api_key, etc.)

    Returns:
        Instance de agno.models.anthropic.Claude
    """
    try:
        from agno.models.anthropic import Claude
    except ImportError as e:
        raise ImportError(
            "Le package 'anthropic' n'est pas installé. "
            "Installez-le avec: uv add anthropic"
        ) from e

    # Récupérer la clé API
    api_key = kwargs.pop("api_key", None) or settings.anthropic_api_key

    if not api_key:
        logger.warning(
            "⚠️  ANTHROPIC_API_KEY non configurée. "
            "Le modèle sera créé mais échouera à l'exécution."
        )

    logger.info(f"✅ Creating Claude model: {model_id}")

    return Claude(
        id=model_id,
        api_key=api_key,
        **kwargs
    )


def _create_mlx_model(model_id: str, **kwargs) -> Any:
    """
    Crée un modèle MLX via OpenAI-compatible API.

    Cette méthode utilise OpenAILike d'Agno pour se connecter à un serveur
    MLX qui expose une API compatible OpenAI.

    Setup requis:
        1. Installer mlx-lm: pip install mlx-lm
        2. Lancer le serveur: mlx_lm.server --model MODEL_PATH --port 8080

    Args:
        model_id: Path du modèle MLX (ex: "mlx-community/Phi-3-mini-4k-instruct-4bit")
        **kwargs: Paramètres additionnels (base_url, api_key, etc.)

    Returns:
        Instance de agno.models.openai.OpenAILike configurée pour MLX
    """
    try:
        from agno.models.openai import OpenAILike
    except ImportError as e:
        raise ImportError(
            "Le package Agno n'est pas correctement installé."
        ) from e

    # Configuration par défaut
    base_url = kwargs.pop("base_url", DEFAULT_MLX_SERVER_URL)
    api_key = kwargs.pop("api_key", "not-provided")  # MLX server n'a pas besoin de clé

    logger.info(f"✅ Creating MLX model via OpenAILike: {model_id}")
    logger.info(f"   Base URL: {base_url}")
    logger.info(f"   Note: Assurez-vous que le serveur MLX est lancé!")
    logger.info(f"   Command: mlx_lm.server --model {model_id} --port 8080")

    return OpenAILike(
        id=model_id,
        name=f"MLX {model_id.split('/')[-1]}",
        provider="mlx",
        base_url=base_url,
        api_key=api_key,
        **kwargs
    )


def _create_openai_model(model_id: str, **kwargs) -> Any:
    """
    Crée un modèle OpenAI (bonus).

    Args:
        model_id: ID du modèle OpenAI (ex: "gpt-4o", "gpt-4o-mini")
        **kwargs: Paramètres additionnels (api_key, etc.)

    Returns:
        Instance de agno.models.openai.OpenAIChat
    """
    try:
        from agno.models.openai import OpenAIChat
    except ImportError as e:
        raise ImportError(
            "Le package 'openai' n'est pas installé. "
            "Installez-le avec: uv add openai"
        ) from e

    # Récupérer la clé API
    api_key = kwargs.pop("api_key", None) or os.getenv("OPENAI_API_KEY")

    if not api_key:
        logger.warning(
            "⚠️  OPENAI_API_KEY non configurée. "
            "Le modèle sera créé mais échouera à l'exécution."
        )

    logger.info(f"✅ Creating OpenAI model: {model_id}")

    return OpenAIChat(
        id=model_id,
        api_key=api_key,
        **kwargs
    )


# ========================================
# Helpers pour créer des modèles par défaut
# ========================================

def create_default_ollama_model(**kwargs) -> Any:
    """Crée le modèle Ollama par défaut (mistral)."""
    return create_model(f"ollama:{DEFAULT_OLLAMA_MODEL}", **kwargs)


def create_default_claude_model(**kwargs) -> Any:
    """Crée le modèle Claude par défaut (Sonnet 4.5)."""
    return create_model(f"anthropic:{DEFAULT_CLAUDE_MODEL}", **kwargs)


def create_default_mlx_model(**kwargs) -> Any:
    """Crée le modèle MLX par défaut (Phi-3 4-bit)."""
    return create_model(f"mlx:{DEFAULT_MLX_MODEL}", **kwargs)


# ========================================
# Validation et tests
# ========================================

def validate_model_string(model_string: str) -> tuple[str, str]:
    """
    Valide une string de modèle et retourne (provider, model_id).

    Args:
        model_string: String à valider

    Returns:
        Tuple (provider, model_id)

    Raises:
        ValueError: Si le format est invalide
    """
    if ":" not in model_string:
        raise ValueError(
            f"Format invalide: '{model_string}'. "
            f"Format attendu: 'provider:model'"
        )

    provider, model_id = model_string.split(":", 1)
    provider = provider.lower().strip()
    model_id = model_id.strip()

    valid_providers = ["ollama", "anthropic", "mlx", "openai"]
    if provider not in valid_providers:
        raise ValueError(
            f"Provider non supporté: '{provider}'. "
            f"Providers supportés: {', '.join(valid_providers)}"
        )

    if not model_id:
        raise ValueError("Le model_id ne peut pas être vide")

    return provider, model_id


def test_model_creation():
    """Teste la création de modèles."""
    print("🧪 Test de création de modèles")
    print("=" * 70)

    # Test validation
    print("\n1. Test validation...")
    try:
        provider, model_id = validate_model_string("ollama:mistral")
        print(f"   ✅ Validation OK: provider={provider}, model={model_id}")
    except ValueError as e:
        print(f"   ❌ Erreur: {e}")

    # Test création Ollama
    print("\n2. Test création Ollama...")
    try:
        model = create_model("ollama:mistral")
        print(f"   ✅ Modèle créé: {model}")
    except Exception as e:
        print(f"   ❌ Erreur: {e}")

    # Test création Claude
    print("\n3. Test création Claude...")
    try:
        model = create_model("anthropic:claude-sonnet-4-5-20250929")
        print(f"   ✅ Modèle créé: {model}")
    except Exception as e:
        print(f"   ❌ Erreur: {e}")

    # Test création MLX
    print("\n4. Test création MLX...")
    try:
        model = create_model("mlx:mlx-community/Phi-3-mini-4k-instruct-4bit")
        print(f"   ✅ Modèle créé: {model}")
    except Exception as e:
        print(f"   ❌ Erreur: {e}")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    test_model_creation()
