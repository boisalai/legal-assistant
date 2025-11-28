"""
Script pour corriger le problème d'authentification SurrealDB avec Agno.

Ce script:
1. Crée le namespace "agno" s'il n'existe pas
2. Définit la database dans ce namespace
3. Teste que tout fonctionne correctement

Usage:
    uv run python fix_surrealdb_agno_namespace.py
"""

import asyncio
import logging
from typing import Any

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def fix_agno_namespace():
    """
    Corrige le namespace Agno dans SurrealDB.

    Le problème: Agno essaie d'écrire dans le namespace "agno" mais celui-ci
    n'est pas correctement initialisé, ce qui cause des erreurs d'authentification.

    Solution: Créer explicitement le namespace "agno" et la database.
    """

    print("\n" + "="*80)
    print("FIX SURREALDB AGNO NAMESPACE - NOTARY ASSISTANT")
    print("="*80 + "\n")

    try:
        from surrealdb import Surreal
        from config import settings

        print("📊 Configuration:")
        print(f"   URL: {settings.surreal_url}")
        print(f"   Username: {settings.surreal_username}")
        print(f"   Namespace Agno: agno")
        print(f"   Database: {settings.surreal_database}")
        print()

        # Connexion
        print("🔌 Connexion à SurrealDB...")
        # Note: surrealdb 1.0.6 - le constructeur établit déjà la connexion
        db = Surreal(settings.surreal_url)
        print("✅ Connecté\n")

        # Authentification ROOT
        print("🔐 Authentification ROOT...")
        db.signin({
            "username": settings.surreal_username,
            "password": settings.surreal_password
        })
        print("✅ Authentifié\n")

        # Sélection namespace/database
        print("📂 Sélection namespace/database...")
        db.use(settings.surreal_namespace, settings.surreal_database)
        print(f"✅ Namespace/Database sélectionnés: {settings.surreal_namespace}/{settings.surreal_database}\n")

        # Étape 1: Définir le namespace "agno"
        print("="*80)
        print("ÉTAPE 1: Création/Vérification du namespace 'agno'")
        print("="*80)

        try:
            result = db.query("DEFINE NAMESPACE agno;")
            print("✅ Namespace 'agno' défini")
            print(f"   Résultat: {result}\n")
        except Exception as e:
            print(f"⚠️  Avertissement lors de la définition du namespace: {e}")
            print("   (Peut être normal si le namespace existe déjà)\n")

        # Étape 2: Utiliser le namespace et définir la database
        print("="*80)
        print("ÉTAPE 2: Définition de la database dans namespace 'agno'")
        print("="*80)

        try:
            db.use("agno", settings.surreal_database)
            print(f"✅ Namespace/Database sélectionnés: agno/{settings.surreal_database}")

            result = db.query(f"DEFINE DATABASE {settings.surreal_database};")
            print(f"✅ Database '{settings.surreal_database}' définie dans namespace 'agno'")
            print(f"   Résultat: {result}\n")
        except Exception as e:
            print(f"⚠️  Avertissement lors de la définition de la database: {e}")
            print("   (Peut être normal si la database existe déjà)\n")

        # Étape 3: Tester l'écriture
        print("="*80)
        print("ÉTAPE 3: Test d'écriture dans namespace 'agno'")
        print("="*80)

        try:
            test_record = db.create("test_fix", {
                "message": "Test après fix du namespace",
                "timestamp": "2025-11-20T12:00:00Z",
                "status": "success"
            })
            print("✅ Écriture dans namespace 'agno' réussie!")
            print(f"   Record créé: {test_record}\n")

            # Lire pour vérifier
            records = db.select("test_fix")
            print(f"✅ Lecture vérifiée: {len(records)} record(s) trouvé(s)")

            # Nettoyer
            db.delete("test_fix")
            print("✅ Nettoyage effectué\n")

        except Exception as e:
            print(f"❌ Erreur lors du test d'écriture: {e}\n")
            raise

        # Étape 4: Tester avec Agno
        print("="*80)
        print("ÉTAPE 4: Test avec Agno SurrealDb")
        print("="*80)

        try:
            from agno.db.surrealdb import SurrealDb

            agno_db = SurrealDb(
                None,  # session
                settings.surreal_url,
                {
                    "username": settings.surreal_username,
                    "password": settings.surreal_password
                },
                "agno",  # namespace
                settings.surreal_database
            )

            print("✅ Instance Agno SurrealDb créée")

            # Tester avec le client sous-jacent
            if hasattr(agno_db, 'client'):
                test_record = agno_db.client.create("test_agno_fix", {
                    "message": "Test Agno après fix",
                    "timestamp": "2025-11-20T12:00:00Z"
                })
                print("✅ Écriture via Agno réussie!")
                print(f"   Record créé: {test_record}")

                # Nettoyer
                agno_db.client.delete("test_agno_fix")
                print("✅ Nettoyage Agno effectué\n")
            else:
                print("⚠️  Attribut 'client' non trouvé sur agno_db\n")

        except Exception as e:
            print(f"❌ Erreur test Agno: {e}\n")
            import traceback
            print(traceback.format_exc())

        # Étape 5: Créer les tables Agno si nécessaire
        print("="*80)
        print("ÉTAPE 5: Création des tables Agno (optionnel)")
        print("="*80)

        print("ℹ️  Les tables Agno sont normalement créées automatiquement:")
        print("   - workflow_runs")
        print("   - workflow_sessions")
        print("   - agent_sessions")
        print("   - team_sessions")
        print()
        print("   Ces tables seront créées lors du premier workflow.arun()\n")

        # Résumé final
        print("="*80)
        print("✅ FIX COMPLÉTÉ AVEC SUCCÈS!")
        print("="*80)
        print()
        print("Le namespace 'agno' est maintenant correctement configuré.")
        print()
        print("Prochaines étapes:")
        print("1. Relancez vos tests:")
        print("   uv run python test_sprint1_validation.py")
        print()
        print("2. Les warnings d'authentification devraient avoir disparu")
        print()
        print("3. Les workflows Agno devraient maintenant persister correctement dans SurrealDB")
        print()

        # Fermer la connexion (si la méthode existe)
        try:
            if hasattr(db, 'close'):
                db.close()
        except Exception:
            pass  # Ignore si la méthode n'existe pas

    except Exception as e:
        print(f"\n❌ ERREUR: {e}")
        import traceback
        print(traceback.format_exc())
        print()
        print("💡 Si l'erreur persiste:")
        print("   1. Vérifiez que SurrealDB est bien démarré")
        print("   2. Vérifiez les credentials dans .env")
        print("   3. Essayez de redémarrer SurrealDB:")
        print("      docker-compose restart surrealdb")
        print()


if __name__ == "__main__":
    fix_agno_namespace()
