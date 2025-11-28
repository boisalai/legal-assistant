#!/usr/bin/env python3
"""
Test SurrealDB avec authentification (--user root --pass root)
Config identique à l'exemple Agno officiel
"""

from surrealdb import Surreal
from config.settings import settings

def test_with_auth():
    """Test connexion avec authentification root"""

    print("=" * 80)
    print("TEST SURREALDB AVEC AUTHENTIFICATION (--user root --pass root)")
    print("=" * 80)
    print()

    try:
        # 1. Connexion
        print("1. Connexion à SurrealDB...")
        db = Surreal(settings.surreal_url)
        print("✅ Connecté")
        print()

        # 2. Authentification ROOT
        print("2. Authentification ROOT...")
        db.signin({"username": "root", "password": "root"})
        print("✅ Authentifié")
        print()

        # 3. Sélection namespace
        print("3. Sélection namespace/database...")
        db.use(settings.surreal_namespace, settings.surreal_database)
        print(f"✅ Namespace sélectionné: {settings.surreal_namespace}/{settings.surreal_database}")
        print()

        # 4. Test écriture dans 'notary'
        print("4. Test d'écriture dans namespace 'notary'...")
        test_record = db.create("test_with_auth", {
            "message": "Test avec authentification root",
            "timestamp": "2025-11-20T12:00:00Z",
            "config": "--user root --pass root"
        })
        print(f"✅ Record créé: {test_record}")
        print()

        # 5. Test namespace 'agno'
        print("5. Test namespace 'agno'...")
        db.use("agno", settings.surreal_database)
        print("✅ Namespace 'agno' accessible")
        print()

        # 6. Test écriture dans 'agno'
        print("6. Test d'écriture dans namespace 'agno'...")
        agno_record = db.create("test_agno_with_auth", {
            "message": "Test namespace agno avec auth",
            "timestamp": "2025-11-20T12:00:00Z"
        })
        print(f"✅ Record créé dans 'agno': {agno_record}")
        print()

        print("=" * 80)
        print("✅ TOUS LES TESTS RÉUSSIS!")
        print("=" * 80)
        print()
        print("Configuration fonctionnelle:")
        print("  ✅ --user root --pass root")
        print("  ✅ signin() avant use()")
        print("  ✅ Écriture dans 'notary' fonctionne")
        print("  ✅ Écriture dans 'agno' fonctionne")
        print()

    except Exception as e:
        print(f"❌ Erreur: {e}")
        print()
        import traceback
        traceback.print_exc()
        print()
        print("Vérifiez les logs SurrealDB:")
        print("  docker compose logs surrealdb | tail -20")
        print()

if __name__ == "__main__":
    test_with_auth()
