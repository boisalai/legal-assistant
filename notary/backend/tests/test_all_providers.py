"""
Test de tous les providers LLM disponibles.

Ce script teste chaque provider LLM (MLX, Hugging Face, Anthropic, Ollama)
pour vérifier leur disponibilité et performance.

Usage:
    uv run python test_all_providers.py
    uv run python test_all_providers.py --provider mlx
    uv run python test_all_providers.py --provider anthropic
"""

import sys
import time
import logging
from typing import Optional

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Test prompt standardisé
TEST_PROMPT = "Réponds en 2-3 phrases: Qu'est-ce qu'un notaire et quel est son rôle?"
SYSTEM_PROMPT = "Tu es un assistant spécialisé en droit notarial québécois."


def test_mlx_provider():
    """Teste le provider MLX (Apple Silicon)."""
    print("\n" + "=" * 60)
    print("🍎 TEST: MLX Provider (Apple Silicon)")
    print("=" * 60)

    try:
        from services.mlx_provider import MLXProvider

        # Créer le provider
        print("⏳ Initialisation du provider MLX...")
        provider = MLXProvider(
            model_name="mlx-community/Phi-3-mini-4k-instruct-4bit"
        )

        # Vérifier disponibilité
        if not provider.is_available():
            print("❌ MLX n'est pas disponible sur ce système")
            print("   MLX nécessite macOS avec Apple Silicon (M1/M2/M3)")
            return False

        # Afficher les infos
        info = provider.get_info()
        print(f"✓ Provider: {info['name']}")
        print(f"✓ Modèle: {info['model']}")
        print(f"✓ Plateforme: {info['platform']}")

        # Tester la génération
        print("\n⏳ Test de génération...")
        from services.llm_provider import LLMMessage

        messages = [
            LLMMessage(role="system", content=SYSTEM_PROMPT),
            LLMMessage(role="user", content=TEST_PROMPT),
        ]

        start = time.time()
        response = provider.generate(messages, max_tokens=200, temperature=0.7)
        duration = time.time() - start

        print(f"\n📝 Réponse ({duration:.2f}s):")
        print(f"{response.content}")
        print(f"\n✓ Modèle: {response.model}")
        print(f"✓ Temps: {duration:.2f}s")

        if response.tokens_used:
            tokens_per_sec = response.tokens_used / duration
            print(f"✓ Tokens: {response.tokens_used} (~{tokens_per_sec:.1f} tokens/sec)")

        print("\n✅ Test MLX réussi!")
        return True

    except ImportError as e:
        print(f"❌ MLX non installé: {e}")
        print("   Installez avec: uv sync --extra mlx")
        return False
    except Exception as e:
        print(f"❌ Erreur lors du test MLX: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_huggingface_provider():
    """Teste le provider Hugging Face."""
    print("\n" + "=" * 60)
    print("🤗 TEST: Hugging Face Provider")
    print("=" * 60)

    try:
        from services.huggingface_provider import HuggingFaceProvider

        # Créer le provider
        print("⏳ Initialisation du provider Hugging Face...")
        print("⚠️  Attention: Le premier chargement peut prendre plusieurs minutes")
        print("    pour télécharger le modèle (~14GB pour Mistral-7B)")

        provider = HuggingFaceProvider(
            model_name="microsoft/Phi-3-mini-4k-instruct",  # Plus petit pour tester
            device="auto",
        )

        # Vérifier disponibilité
        if not provider.is_available():
            print("❌ Hugging Face n'est pas disponible")
            print("   Installez avec: uv sync --extra hf")
            return False

        # Afficher les infos
        info = provider.get_info()
        print(f"✓ Provider: {info['name']}")
        print(f"✓ Modèle: {info['model']}")
        print(f"✓ Device: {info['device']}")

        # Tester la génération
        print("\n⏳ Test de génération...")
        from services.llm_provider import LLMMessage

        messages = [
            LLMMessage(role="system", content=SYSTEM_PROMPT),
            LLMMessage(role="user", content=TEST_PROMPT),
        ]

        start = time.time()
        response = provider.generate(messages, max_tokens=200, temperature=0.7)
        duration = time.time() - start

        print(f"\n📝 Réponse ({duration:.2f}s):")
        print(f"{response.content}")
        print(f"\n✓ Modèle: {response.model}")
        print(f"✓ Temps: {duration:.2f}s")

        if response.tokens_used:
            tokens_per_sec = response.tokens_used / duration
            print(f"✓ Tokens: {response.tokens_used} (~{tokens_per_sec:.1f} tokens/sec)")

        print("\n✅ Test Hugging Face réussi!")
        return True

    except ImportError as e:
        print(f"❌ Hugging Face non installé: {e}")
        print("   Installez avec: uv sync --extra hf")
        return False
    except Exception as e:
        print(f"❌ Erreur lors du test Hugging Face: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_anthropic_provider():
    """Teste le provider Anthropic (Claude)."""
    print("\n" + "=" * 60)
    print("🤖 TEST: Anthropic Provider (Claude)")
    print("=" * 60)

    try:
        from services.anthropic_provider import AnthropicProvider
        import os

        # Vérifier la clé API
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key or api_key.startswith("sk-ant-xxx"):
            print("❌ Clé API Anthropic non configurée")
            print("   Définissez ANTHROPIC_API_KEY dans .env")
            print("   Obtenez une clé sur: https://console.anthropic.com")
            return False

        # Créer le provider
        print("⏳ Initialisation du provider Anthropic...")
        provider = AnthropicProvider(
            model_name="claude-3-5-sonnet-20241022",
            api_key=api_key
        )

        # Vérifier disponibilité
        if not provider.is_available():
            print("❌ Anthropic n'est pas disponible")
            return False

        # Afficher les infos
        info = provider.get_info()
        print(f"✓ Provider: {info['name']}")
        print(f"✓ Modèle: {info['model']}")
        print(f"✓ Plateforme: {info['platform']}")

        # Tester la génération
        print("\n⏳ Test de génération...")
        from services.llm_provider import LLMMessage

        messages = [
            LLMMessage(role="system", content=SYSTEM_PROMPT),
            LLMMessage(role="user", content=TEST_PROMPT),
        ]

        start = time.time()
        response = provider.generate(messages, max_tokens=200, temperature=0.7)
        duration = time.time() - start

        print(f"\n📝 Réponse ({duration:.2f}s):")
        print(f"{response.content}")
        print(f"\n✓ Modèle: {response.model}")
        print(f"✓ Temps: {duration:.2f}s")

        if response.tokens_used:
            print(f"✓ Tokens utilisés: {response.tokens_used}")
            print(f"  - Input: {response.metadata.get('input_tokens', 0)}")
            print(f"  - Output: {response.metadata.get('output_tokens', 0)}")

        print("\n✅ Test Anthropic réussi!")
        return True

    except ImportError as e:
        print(f"❌ Anthropic non installé: {e}")
        print("   Installez avec: uv sync --extra anthropic")
        return False
    except Exception as e:
        print(f"❌ Erreur lors du test Anthropic: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_ollama_provider():
    """Teste le provider Ollama."""
    print("\n" + "=" * 60)
    print("🦙 TEST: Ollama Provider")
    print("=" * 60)

    try:
        from services.ollama_provider import OllamaProvider

        # Créer le provider
        print("⏳ Initialisation du provider Ollama...")
        provider = OllamaProvider(
            model_name="mistral",
            base_url="http://localhost:11434"
        )

        # Vérifier disponibilité
        if not provider.is_available():
            print("❌ Ollama n'est pas disponible")
            print("   1. Installez Ollama depuis: https://ollama.ai")
            print("   2. Démarrez Ollama avec: ollama serve")
            print("   3. Téléchargez un modèle: ollama pull mistral")
            return False

        # Afficher les infos
        info = provider.get_info()
        print(f"✓ Provider: {info['name']}")
        print(f"✓ Modèle: {info['model']}")
        print(f"✓ URL: {info['base_url']}")

        # Lister les modèles installés
        models = provider.list_models()
        if models:
            print(f"\n✓ Modèles installés:")
            for model in models:
                size_mb = model['size'] / (1024 * 1024)
                print(f"  - {model['name']} ({size_mb:.0f} MB)")

        # Tester la génération
        print("\n⏳ Test de génération...")
        from services.llm_provider import LLMMessage

        messages = [
            LLMMessage(role="system", content=SYSTEM_PROMPT),
            LLMMessage(role="user", content=TEST_PROMPT),
        ]

        start = time.time()
        response = provider.generate(messages, max_tokens=200, temperature=0.7)
        duration = time.time() - start

        print(f"\n📝 Réponse ({duration:.2f}s):")
        print(f"{response.content}")
        print(f"\n✓ Modèle: {response.model}")
        print(f"✓ Temps: {duration:.2f}s")

        if response.tokens_used:
            tokens_per_sec = response.tokens_used / duration
            print(f"✓ Tokens: {response.tokens_used} (~{tokens_per_sec:.1f} tokens/sec)")

        print("\n✅ Test Ollama réussi!")
        return True

    except ImportError as e:
        print(f"❌ Requests non installé: {e}")
        print("   Installez avec: uv sync --extra ollama")
        return False
    except Exception as e:
        print(f"❌ Erreur lors du test Ollama: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Fonction principale."""
    print("\n" + "=" * 60)
    print("🧪 TEST DE TOUS LES PROVIDERS LLM")
    print("=" * 60)

    # Parser les arguments
    provider = None
    if len(sys.argv) > 1:
        if sys.argv[1] == "--provider" and len(sys.argv) > 2:
            provider = sys.argv[2].lower()

    # Tests
    results = {}

    if provider is None or provider == "mlx":
        results["MLX"] = test_mlx_provider()

    if provider is None or provider == "huggingface":
        results["Hugging Face"] = test_huggingface_provider()

    if provider is None or provider == "anthropic":
        results["Anthropic"] = test_anthropic_provider()

    if provider is None or provider == "ollama":
        results["Ollama"] = test_ollama_provider()

    # Résumé
    print("\n" + "=" * 60)
    print("📊 RÉSUMÉ DES TESTS")
    print("=" * 60)

    for name, success in results.items():
        status = "✅ Réussi" if success else "❌ Échoué"
        print(f"{name:20} : {status}")

    successful = sum(1 for s in results.values() if s)
    total = len(results)

    print(f"\n{successful}/{total} providers fonctionnels")

    if successful == 0:
        print("\n⚠️  Aucun provider n'est disponible!")
        print("   Installez au moins un provider avec:")
        print("   - uv sync --extra mlx        (Apple Silicon)")
        print("   - uv sync --extra hf         (Cross-platform)")
        print("   - uv sync --extra anthropic  (API Cloud)")
        print("   - uv sync --extra ollama     (Cross-platform)")


if __name__ == "__main__":
    main()
