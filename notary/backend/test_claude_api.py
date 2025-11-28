#!/usr/bin/env python3
"""
Script de test pour valider la connexion à l'API Claude.

Usage:
    uv run python test_claude_api.py
"""

import os
import sys
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

def test_api_key_configured():
    """Vérifie que la clé API est configurée."""
    print("🔍 Vérification de la clé API...")

    api_key = os.getenv("ANTHROPIC_API_KEY")

    if not api_key:
        print("❌ ANTHROPIC_API_KEY non configurée")
        print("\n💡 Solution:")
        print("   1. Lancer: chmod +x configure_claude.sh")
        print("   2. Lancer: ./configure_claude.sh")
        print("   OU ajouter manuellement dans .env:")
        print("   ANTHROPIC_API_KEY=sk-ant-xxxxx")
        return False

    if not api_key.startswith("sk-ant-"):
        print("❌ Format de clé API invalide (doit commencer par 'sk-ant-')")
        return False

    # Masquer la clé pour affichage
    masked_key = api_key[:10] + "..." + api_key[-4:]
    print(f"✅ Clé API configurée: {masked_key}")
    return True


def test_anthropic_import():
    """Teste l'import du package anthropic."""
    print("\n🔍 Vérification du package anthropic...")

    try:
        import anthropic
        print(f"✅ Package anthropic installé (version {anthropic.__version__})")
        return True
    except ImportError:
        print("❌ Package anthropic non installé")
        print("\n💡 Solution:")
        print("   uv add anthropic")
        return False


def test_api_connection():
    """Teste la connexion à l'API Claude."""
    print("\n🔍 Test de connexion à l'API Claude...")

    try:
        import anthropic

        client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

        # Requête de test simple
        message = client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=100,
            messages=[
                {
                    "role": "user",
                    "content": "Réponds juste 'OK' si tu reçois ce message."
                }
            ]
        )

        response_text = message.content[0].text
        print(f"✅ Connexion réussie!")
        print(f"   Réponse de Claude: {response_text}")
        print(f"   Tokens utilisés: {message.usage.input_tokens} input, {message.usage.output_tokens} output")

        return True

    except anthropic.AuthenticationError:
        print("❌ Erreur d'authentification: Clé API invalide")
        print("\n💡 Vérifiez que votre clé API est correcte sur:")
        print("   https://console.anthropic.com/settings/keys")
        return False

    except anthropic.RateLimitError:
        print("❌ Limite de taux dépassée")
        print("\n💡 Attendez quelques minutes avant de réessayer")
        return False

    except anthropic.APIError as e:
        print(f"❌ Erreur API: {e}")
        return False

    except Exception as e:
        print(f"❌ Erreur inattendue: {e}")
        return False


def test_agno_claude():
    """Teste l'import du workflow Agno avec Claude."""
    print("\n🔍 Test du workflow Agno avec Claude...")

    try:
        from workflows.analyse_dossier import get_claude_model, agent_extracteur

        model = get_claude_model()
        print(f"✅ Workflow chargé avec succès")
        print(f"   Modèle: {model.id}")
        print(f"   Provider: {model.provider}")
        print(f"   Agent extracteur: {agent_extracteur.name}")

        return True

    except Exception as e:
        print(f"❌ Erreur lors du chargement du workflow: {e}")
        return False


def main():
    """Fonction principale."""
    print("=" * 70)
    print("🧪 TEST DE CONFIGURATION CLAUDE API")
    print("=" * 70)

    tests = [
        ("Configuration clé API", test_api_key_configured),
        ("Package anthropic", test_anthropic_import),
        ("Connexion API", test_api_connection),
        ("Workflow Agno", test_agno_claude),
    ]

    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ Erreur dans {test_name}: {e}")
            results.append((test_name, False))

    # Résumé
    print("\n" + "=" * 70)
    print("📊 RÉSUMÉ DES TESTS")
    print("=" * 70)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")

    print(f"\nRésultat: {passed}/{total} tests réussis")

    if passed == total:
        print("\n🎉 Tous les tests sont passés!")
        print("\n✨ Prochaines étapes:")
        print("   1. Créer des PDFs de test réalistes")
        print("   2. Lancer le workflow d'analyse sur un dossier")
        print("   3. Valider la qualité des extractions")
        return 0
    else:
        print("\n⚠️  Certains tests ont échoué. Corrigez les erreurs ci-dessus.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
