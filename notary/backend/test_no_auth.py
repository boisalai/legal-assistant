#!/usr/bin/env python3
"""
Test SurrealDB sans authentification (--allow-all)
Ce script teste la connexion à SurrealDB configuré avec --allow-all
"""

from surrealdb import Surreal
from config.settings import settings

def test_no_auth():
    """Test connexion sans authentification"""

    print("=" * 80)
    print("TEST SURREALDB SANS AUTHENTIFICATION (--allow-all)")
    print("=" * 80)
    print()

    try:
        # 1. Connexion (pas de signin!)
        print("1. Connexion à SurrealDB...")
        db = Surreal(settings.surreal_url)
        print("✅ Connecté")
        print()

        # 2. Sélection namespace directement (sans signin)
        print("2. Sélection namespace/database...")
        db.use(settings.surreal_namespace, settings.surreal_database)
        print(f"✅ Namespace sélectionné: {settings.surreal_namespace}/{settings.surreal_database}")
        print()

        # 3. Test écriture dans namespace 'notary'
        print("3. Test d'écriture dans namespace 'notary'...")
        test_record = db.create("test_no_auth", {
            "message": "Test sans authentification",
            "timestamp": "2025-11-20T12:00:00Z",
            "config": "--allow-all"
        })
        print(f"✅ Record créé: {test_record}")
        print()

        # 4. Test lecture
        print("4. Test de lecture...")
        records = db.select("test_no_auth")
        print(f"✅ {len(records)} record(s) trouvé(s)")
        print()

        # 5. Test namespace 'agno'
        print("5. Test namespace 'agno'...")
        db.use("agno", settings.surreal_database)
        print("✅ Namespace 'agno' accessible")

        # 6. Test écriture dans 'agno'
        print("6. Test d'écriture dans namespace 'agno'...")
        agno_record = db.create("test_agno_access", {
            "message": "Test namespace agno",
            "timestamp": "2025-11-20T12:00:00Z"
        })
        print(f"✅ Record créé dans 'agno': {agno_record}")
        print()

        print("=" * 80)
        print("✅ TOUS LES TESTS RÉUSSIS!")
        print("=" * 80)
        print()
        print("Résultat:")
        print("  ✅ Connexion sans authentification fonctionne")
        print("  ✅ Écriture dans namespace 'notary' fonctionne")
        print("  ✅ Écriture dans namespace 'agno' fonctionne")
        print()
        print("SurrealDB est correctement configuré avec --allow-all")
        print()

    except Exception as e:
        print(f"❌ Erreur: {e}")
        print()
        print("=" * 80)
        print("VÉRIFICATIONS À FAIRE")
        print("=" * 80)
        print()
        print("1. SurrealDB est-il démarré?")
        print("   docker compose ps")
        print()
        print("2. Avez-vous redémarré SurrealDB après modification de docker-compose.yml?")
        print("   docker compose down")
        print("   docker compose up -d surrealdb")
        print("   sleep 10")
        print()
        print("3. Vérifiez les logs SurrealDB:")
        print("   docker compose logs surrealdb | tail -20")
        print()
        print("4. Vérifiez que docker-compose.yml contient bien --allow-all:")
        print("   grep 'allow-all' docker-compose.yml")
        print()

if __name__ == "__main__":
    test_no_auth()
