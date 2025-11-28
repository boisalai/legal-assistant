#!/usr/bin/env python3
"""
Script de test pour vérifier que MLX fonctionne correctement.

Ce script:
1. Vérifie que MLX est disponible
2. Télécharge un modèle léger si nécessaire
3. Teste une génération simple
4. Affiche les performances

Usage:
    uv run python test_mlx.py
"""

import sys
import time
import logging

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def test_mlx_availability():
    """Teste si MLX est disponible sur ce système."""
    print("\n" + "="*70)
    print("TEST 1: Vérification de la disponibilité de MLX")
    print("="*70)

    try:
        import platform
        import mlx.core as mx

        print(f"✓ Système: {platform.system()}")
        print(f"✓ Architecture: {platform.machine()}")
        print(f"✓ MLX importé avec succès")

        # Test simple de calcul
        arr = mx.array([1, 2, 3, 4, 5])
        result = mx.sum(arr)
        print(f"✓ Test de calcul MLX: sum([1,2,3,4,5]) = {result}")

        if platform.system() != "Darwin" or platform.machine() != "arm64":
            print("\n⚠️  ATTENTION: MLX est optimisé pour macOS + Apple Silicon")
            print("   Performances réduites sur cette plateforme")

        print("\n✅ MLX est disponible et fonctionnel\n")
        return True

    except ImportError as e:
        print(f"\n❌ MLX n'est pas installé: {e}")
        print("   Installez avec: uv sync --extra mlx\n")
        return False
    except Exception as e:
        print(f"\n❌ Erreur lors du test MLX: {e}\n")
        return False


def test_model_loading():
    """Teste le chargement d'un modèle MLX."""
    print("\n" + "="*70)
    print("TEST 2: Téléchargement et chargement du modèle")
    print("="*70)

    try:
        from mlx_lm import load

        # Utiliser un modèle léger pour le test
        # Phi-3-mini est petit (~2GB) et rapide
        model_name = "mlx-community/Phi-3-mini-4k-instruct-4bit"

        print(f"\nModèle: {model_name}")
        print("Taille: ~2GB")
        print("\n⏳ Téléchargement et chargement en cours...")
        print("   (Cela peut prendre quelques minutes la première fois)\n")

        start_time = time.time()

        model, tokenizer = load(model_name)

        load_time = time.time() - start_time

        print(f"✅ Modèle chargé en {load_time:.2f} secondes\n")

        return model, tokenizer

    except Exception as e:
        print(f"\n❌ Erreur lors du chargement du modèle: {e}\n")
        return None, None


def test_generation(model, tokenizer):
    """Teste la génération de texte."""
    print("\n" + "="*70)
    print("TEST 3: Génération de texte")
    print("="*70)

    if model is None or tokenizer is None:
        print("\n❌ Modèle non chargé, test ignoré\n")
        return False

    try:
        from mlx_lm import generate

        # Prompt simple pour tester
        prompt = """<|user|>
Réponds en français en maximum 2 phrases: Qu'est-ce qu'un notaire?
<|assistant|>"""

        print(f"\nPrompt:\n{prompt}\n")
        print("⏳ Génération en cours...\n")

        start_time = time.time()

        response = generate(
            model=model,
            tokenizer=tokenizer,
            prompt=prompt,
            max_tokens=100,
            verbose=False
        )

        gen_time = time.time() - start_time

        # Nettoyer la réponse (enlever le prompt)
        if response.startswith(prompt):
            response = response[len(prompt):].strip()

        print(f"Réponse:\n{response}\n")
        print(f"✅ Génération complétée en {gen_time:.2f} secondes")
        print(f"   (~{100/gen_time:.1f} tokens/seconde)\n")

        return True

    except Exception as e:
        print(f"\n❌ Erreur lors de la génération: {e}\n")
        import traceback
        traceback.print_exc()
        return False


def test_llm_service():
    """Teste le service LLM complet."""
    print("\n" + "="*70)
    print("TEST 4: Service LLM (intégration)")
    print("="*70)

    try:
        from services import get_llm_service

        print("\n⏳ Initialisation du service LLM...\n")

        service = get_llm_service()

        # Vérifier que le service est prêt
        info = service.get_provider_info()

        print(f"Provider: {info.get('name')}")
        print(f"Modèle: {info.get('model')}")
        print(f"Disponible: {info.get('available')}")
        print(f"Chargé: {info.get('loaded')}\n")

        if not service.is_ready():
            print("❌ Service non prêt\n")
            return False

        # Test simple
        print("⏳ Test de génération via le service...\n")

        response = service.generate(
            prompt="Quelle est la capitale du Canada? Réponds en un mot.",
            max_tokens=50,
            temperature=0.1
        )

        print(f"Réponse: {response}\n")

        print("✅ Service LLM fonctionnel\n")
        return True

    except Exception as e:
        print(f"\n❌ Erreur lors du test du service: {e}\n")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Fonction principale."""
    print("\n")
    print("╔" + "═"*68 + "╗")
    print("║" + " "*20 + "TEST MLX - NOTARY ASSISTANT" + " "*21 + "║")
    print("╚" + "═"*68 + "╝")

    results = {
        "mlx_available": False,
        "model_loaded": False,
        "generation_works": False,
        "service_works": False
    }

    # Test 1: Disponibilité MLX
    results["mlx_available"] = test_mlx_availability()

    if not results["mlx_available"]:
        print("\n⚠️  MLX n'est pas disponible. Tests arrêtés.\n")
        sys.exit(1)

    # Test 2: Chargement du modèle
    model, tokenizer = test_model_loading()
    results["model_loaded"] = (model is not None)

    # Test 3: Génération
    if results["model_loaded"]:
        results["generation_works"] = test_generation(model, tokenizer)

    # Test 4: Service LLM
    results["service_works"] = test_llm_service()

    # Résumé
    print("\n" + "="*70)
    print("RÉSUMÉ DES TESTS")
    print("="*70 + "\n")

    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {test_name}")

    all_passed = all(results.values())

    if all_passed:
        print("\n🎉 Tous les tests ont réussi!")
        print("   MLX est prêt à être utilisé pour le projet.\n")
        sys.exit(0)
    else:
        print("\n⚠️  Certains tests ont échoué.")
        print("   Vérifiez les erreurs ci-dessus.\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
