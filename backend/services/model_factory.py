"""
Factory pour créer des modèles Agno selon la configuration.

Ce module fournit des fonctions helpers pour créer des instances
de modèles Agno compatibles avec Agent, Team et Workflow.

Patterns officiels Agno:
- Ollama: agno.models.ollama.Ollama (modèles locaux)
- Claude: agno.models.anthropic.Claude (API Anthropic)
- MLX: agno.models.openai.OpenAILike (modèles HF optimisés Apple Silicon)
- vLLM: agno.models.vllm.VLLM (N'IMPORTE QUEL modèle HF local CPU/GPU)

Usage:
    from services.model_factory import create_model

    # Ollama (modèles locaux cross-platform)
    model = create_model("ollama:mistral")

    # Claude (API Anthropic - meilleure qualité)
    model = create_model("anthropic:claude-sonnet-4-5-20250929")

    # vLLM (N'IMPORTE QUEL modèle HuggingFace local CPU/GPU)
    model = create_model("vllm:Qwen/Qwen2.5-1.5B-Instruct")  # Ultra-léger pour CPU
    model = create_model("vllm:Qwen/Qwen2.5-3B-Instruct")    # Polyvalent CPU/GPU
    # Auto-démarrage du serveur vLLM

    # MLX (modèles HF convertis pour Apple Silicon - plus rapide)
    model = create_model("mlx:mlx-community/Qwen2.5-3B-Instruct-4bit")
    # Auto-démarrage du serveur MLX

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
        - "vllm:MODEL_ID" → vLLM local (N'IMPORTE QUEL modèle HuggingFace CPU/GPU)
        - "mlx:MODEL_PATH" → MLX local (modèles HuggingFace convertis pour Apple Silicon)
        - "openai:MODEL_ID" → OpenAI API

    Args:
        model_string: String de configuration du modèle
        **kwargs: Paramètres additionnels (api_key, base_url, etc.)

    Returns:
        Instance de modèle Agno (Ollama, Claude, VLLM, OpenAILike, etc.)

    Examples:
        >>> model = create_model("ollama:mistral")
        >>> model = create_model("anthropic:claude-sonnet-4-5-20250929", api_key="sk-ant-...")
        >>> model = create_model("vllm:Qwen/Qwen2.5-1.5B-Instruct")  # Ultra-léger pour CPU
        >>> model = create_model("mlx:mlx-community/Qwen2.5-3B-Instruct-4bit")  # Apple Silicon

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

    # Compatibilité : Rediriger huggingface: vers vllm: (migration)
    if provider == "huggingface":
        logger.warning(f"⚠️  Provider 'huggingface:' déprécié - Redirection automatique vers 'vllm:'")
        logger.warning(f"   Ancien: huggingface:{model_id}")
        logger.warning(f"   Nouveau: vllm:{model_id}")
        logger.warning(f"   Mettez à jour votre configuration pour utiliser 'vllm:' directement")
        provider = "vllm"

    logger.info(f"Creating model: provider={provider}, model={model_id}")

    if provider == "ollama":
        return _create_ollama_model(model_id, **kwargs)
    elif provider == "anthropic":
        return _create_claude_model(model_id, **kwargs)
    elif provider == "mlx":
        return _create_mlx_model(model_id, **kwargs)
    elif provider == "vllm":
        return _create_vllm_model(model_id, **kwargs)
    elif provider == "openai":
        return _create_openai_model(model_id, **kwargs)
    else:
        raise ValueError(
            f"Provider non supporté: '{provider}'. "
            f"Providers supportés: ollama, anthropic, mlx, vllm, openai"
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


def _create_vllm_model(model_id: str, **kwargs) -> Any:
    """
    Crée un modèle vLLM pour charger n'importe quel modèle HuggingFace localement.

    vLLM charge les modèles HuggingFace localement avec support MPS/CUDA/CPU.

    Setup requis:
        1. Installer vLLM: pip install vllm
        2. Lancer le serveur: vllm serve MODEL_ID --port 8001 --device mps
           Exemple: vllm serve Qwen/Qwen2.5-3B-Instruct --port 8001 --device mps

    Args:
        model_id: ID du modèle HuggingFace (ex: "Qwen/Qwen2.5-3B-Instruct")
        **kwargs: Paramètres additionnels (base_url, etc.)

    Returns:
        Instance de agno.models.vllm.VLLM configurée pour le serveur local
    """
    try:
        from agno.models.vllm import VLLM
    except ImportError as e:
        raise ImportError(
            "Le package Agno n'est pas correctement installé."
        ) from e

    # Configuration par défaut
    base_url = kwargs.pop("base_url", "http://localhost:8001/v1/")  # Port 8001 pour vLLM
    api_key = kwargs.pop("api_key", "EMPTY")  # vLLM n'a pas besoin de clé

    logger.info(f"✅ Creating vLLM model: {model_id}")
    logger.info(f"   Base URL: {base_url}")
    logger.info(f"   Note: Assurez-vous que le serveur vLLM est lancé!")
    logger.info(f"   Command: vllm serve {model_id} --port 8001 --device mps")

    return VLLM(
        id=model_id,
        name=f"vLLM {model_id.split('/')[-1]}",
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
    """Crée le modèle MLX par défaut (Qwen 2.5 3B 4-bit)."""
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

    valid_providers = ["ollama", "anthropic", "mlx", "vllm", "openai"]
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

    # Test création HuggingFace
    print("\n5. Test création HuggingFace...")
    try:
        model = create_model("huggingface:Qwen/Qwen2.5-3B-Instruct")
        print(f"   ✅ Modèle créé: {model}")
    except Exception as e:
        print(f"   ❌ Erreur: {e}")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    test_model_creation()
