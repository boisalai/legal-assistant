"""
Script de diagnostic pour les problèmes d'authentification SurrealDB avec Agno.

Ce script teste:
1. La connexion SurrealDB avec les credentials actuels
2. L'accès aux namespaces "notary" et "agno"
3. Les permissions d'écriture dans chaque namespace
4. La configuration Agno

Usage:
    uv run python diagnose_surrealdb_auth.py
"""

import logging
from typing import Any

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def test_surreal_connection():
    """Teste la connexion SurrealDB et diagnostique les problèmes."""

    print("\n" + "="*80)
    print("DIAGNOSTIC SURREALDB AUTHENTICATION - NOTARY ASSISTANT")
    print("="*80 + "\n")

    try:
        from surrealdb import Surreal
        from config import settings

        print("📊 Configuration actuelle:")
        print(f"   URL: {settings.surreal_url}")
        print(f"   Username: {settings.surreal_username}")
        print(f"   Password: {'*' * len(settings.surreal_password)}")
        print(f"   Namespace (settings): {settings.surreal_namespace}")
        print(f"   Database: {settings.surreal_database}")
        print()

        # Test 1: Connexion de base
        print("="*80)
        print("TEST 1: Connexion SurrealDB de base")
        print("="*80)

        # Note: surrealdb 1.0.6 - le constructeur établit déjà la connexion
        db = Surreal(settings.surreal_url)
        print("✅ Connexion WebSocket établie")

        # Test 2: Sélection namespace/database
        print("\n" + "="*80)
        print("TEST 2: Sélection namespace/database")
        print("="*80)

        try:
            # Dans surrealdb 1.0.6, il faut d'abord sélectionner namespace/database
            db.use(settings.surreal_namespace, settings.surreal_database)
            print(f"✅ Namespace/Database sélectionnés: {settings.surreal_namespace}/{settings.surreal_database}")
        except Exception as e:
            print(f"⚠️  Erreur lors de la sélection: {e}")
            print("   Tentative d'authentification root avant use()...")

            # Essayer signin en premier
            try:
                db.signin({
                    "user": settings.surreal_username,
                    "pass": settings.surreal_password
                })
                print("✅ Authentification root réussie (avant use)")

                # Puis use
                db.use(settings.surreal_namespace, settings.surreal_database)
                print(f"✅ Namespace/Database sélectionnés après signin")
            except Exception as e2:
                print(f"❌ Échec authentification: {e2}")
                raise

        # Test 3: Écriture dans namespace "notary"
        print("\n" + "="*80)
        print("TEST 3: Écriture dans namespace 'notary'")
        print("="*80)

        try:
            print(f"   Namespace actuel: '{settings.surreal_namespace}'")

            # Tester écriture
            test_record = db.create("test_auth", {
                "message": "Test diagnostic",
                "timestamp": "2025-11-20T12:00:00Z"
            })
            print(f"✅ Écriture dans namespace '{settings.surreal_namespace}' réussie")
            print(f"   Record créé: {test_record}")

            # Nettoyer
            db.delete("test_auth")
            print(f"✅ Nettoyage effectué")

        except Exception as e:
            print(f"❌ Erreur namespace '{settings.surreal_namespace}': {e}")

        # Test 4: Namespace "agno" (utilisé par Agno)
        print("\n" + "="*80)
        print("TEST 4: Accès namespace 'agno' (utilisé par Agno)")
        print("="*80)

        try:
            db.use("agno", settings.surreal_database)
            print("✅ Namespace 'agno' accessible")

            # Tester écriture
            test_record = db.create("test_auth", {
                "message": "Test diagnostic Agno",
                "timestamp": "2025-11-20T12:00:00Z"
            })
            print("✅ Écriture dans namespace 'agno' réussie")
            print(f"   Record créé: {test_record}")

            # Nettoyer
            db.delete("test_auth")
            print("✅ Nettoyage effectué")

        except Exception as e:
            print(f"❌ Erreur namespace 'agno': {e}")
            print("\n💡 SOLUTION POSSIBLE:")
            print("   Le namespace 'agno' n'existe peut-être pas ou n'a pas les bonnes permissions.")
            print("   Essayons de le créer...")

            # Tenter de créer le namespace
            try:
                # Se reconnecter en root
                db.signin({
                    "user": settings.surreal_username,
                    "pass": settings.surreal_password
                })

                # Définir le namespace (même s'il existe déjà)
                db.query("DEFINE NAMESPACE agno;")
                print("✅ Namespace 'agno' défini")

                # Définir la database
                db.use("agno", settings.surreal_database)
                db.query(f"DEFINE DATABASE {settings.surreal_database};")
                print(f"✅ Database '{settings.surreal_database}' définie dans namespace 'agno'")

                # Re-tester l'écriture
                test_record = db.create("test_auth", {
                    "message": "Test après création namespace",
                    "timestamp": "2025-11-20T12:00:00Z"
                })
                print("✅ Écriture dans namespace 'agno' réussie après création!")
                print(f"   Record créé: {test_record}")

                # Nettoyer
                db.delete("test_auth")
                print("✅ Nettoyage effectué")

            except Exception as e2:
                print(f"❌ Impossible de créer namespace 'agno': {e2}")

        # Test 5: Test avec Agno SurrealDb
        print("\n" + "="*80)
        print("TEST 5: Test avec agno.db.surrealdb.SurrealDb")
        print("="*80)

        try:
            from agno.db.surrealdb import SurrealDb

            agno_db = SurrealDb(
                None,  # session
                settings.surreal_url,
                {
                    "user": settings.surreal_username,
                    "pass": settings.surreal_password
                },
                "agno",
                settings.surreal_database
            )

            print("✅ Instance Agno SurrealDb créée")
            print(f"   Namespace: agno")
            print(f"   Database: {settings.surreal_database}")

            # Tenter d'accéder au client sous-jacent
            if hasattr(agno_db, 'client'):
                print("✅ Client SurrealDB accessible via agno_db.client")

                # Tester écriture
                try:
                    test_record = agno_db.client.create("test_agno_write", {
                        "message": "Test écriture via Agno",
                        "timestamp": "2025-11-20T12:00:00Z"
                    })
                    print("✅ Écriture via Agno SurrealDb réussie!")
                    print(f"   Record créé: {test_record}")

                    # Nettoyer
                    agno_db.client.delete("test_agno_write")
                    print("✅ Nettoyage effectué")

                except Exception as e:
                    print(f"❌ Erreur écriture via Agno: {e}")
                    print(f"   Type erreur: {type(e).__name__}")
                    print(f"   Détails: {str(e)}")
            else:
                print("⚠️  Attribut 'client' non trouvé sur agno_db")
                print(f"   Attributs disponibles: {dir(agno_db)}")

        except Exception as e:
            print(f"❌ Erreur test Agno SurrealDb: {e}")
            import traceback
            print(traceback.format_exc())

        # Résumé
        print("\n" + "="*80)
        print("RÉSUMÉ DU DIAGNOSTIC")
        print("="*80)
        print()
        print("Si vous voyez des ❌ au-dessus, voici les solutions possibles:")
        print()
        print("1. Namespace 'agno' n'existe pas:")
        print("   Solution: Exécutez les commandes suivantes dans un terminal:")
        print(f"""
   curl -X POST {settings.surreal_url.replace('ws://', 'http://').replace('/rpc', '/sql')} \\
     -H "Accept: application/json" \\
     -H "NS: agno" \\
     -H "DB: {settings.surreal_database}" \\
     -u "{settings.surreal_username}:{settings.surreal_password}" \\
     -d "DEFINE NAMESPACE agno; DEFINE DATABASE {settings.surreal_database};"
        """)
        print()
        print("2. Problème de permissions:")
        print("   Vérifiez que l'utilisateur root a les permissions complètes")
        print()
        print("3. Problème de connexion Agno:")
        print("   Vérifiez la version d'Agno et SurrealDB:")
        print("   - uv pip list | grep agno")
        print("   - uv pip list | grep surrealdb")
        print()

        # Fermer la connexion (si la méthode existe)
        try:
            if hasattr(db, 'close'):
                db.close()
        except Exception:
            pass  # Ignore si la méthode n'existe pas

    except Exception as e:
        print(f"\n❌ ERREUR FATALE: {e}")
        import traceback
        print(traceback.format_exc())


if __name__ == "__main__":
    test_surreal_connection()
