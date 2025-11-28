#!/usr/bin/env python3
"""
Script de test SurrealDB - Vérifie la connexion et les opérations de base

Usage:
    cd backend
    uv run python test_surrealdb.py

Prérequis:
    - SurrealDB doit être démarré: docker-compose up -d surrealdb
"""

import asyncio
import sys
import time
from pathlib import Path

# Ajouter le répertoire backend au path pour les imports
sys.path.insert(0, str(Path(__file__).parent))

from services.surreal_service import get_db_connection
from config.settings import settings


def print_test(test_name: str):
    """Afficher le nom du test en cours."""
    print(f"\n{'='*60}")
    print(f"TEST: {test_name}")
    print(f"{'='*60}")


async def test_connection():
    """Test 1: Connexion à SurrealDB."""
    print_test("Connexion à SurrealDB")

    try:
        async with get_db_connection(
            url=settings.surreal_url,
            namespace=settings.surreal_namespace,
            database=settings.surreal_database
        ) as db:
            print(f"✅ Connexion réussie à {settings.surreal_url}")
            print(f"   Namespace: {settings.surreal_namespace}")
            print(f"   Database: {settings.surreal_database}")
            return True

    except Exception as e:
        print(f"❌ Échec de la connexion: {e}")
        return False


async def test_create_user():
    """Test 2: Créer un utilisateur."""
    print_test("Création d'un utilisateur")

    async with get_db_connection() as db:
        try:
            # Créer un utilisateur de test
            user_data = {
                "email": "test@notaire.qc.ca",
                "nom": "Tremblay",
                "prenom": "François",
                "role": "notaire",
                "actif": True
            }

            print(f"Création de l'utilisateur: {user_data}")
            result = await db.create("user", user_data, record_id="test_notaire")

            print(f"✅ Utilisateur créé: {result}")
            return True

        except Exception as e:
            print(f"❌ Échec de la création: {e}")
            return False


async def test_select_user():
    """Test 3: Récupérer un utilisateur."""
    print_test("Récupération d'un utilisateur")

    async with get_db_connection() as db:
        try:
            # Récupérer l'utilisateur créé
            result = await db.select("user:test_notaire")
            print(f"✅ Utilisateur récupéré: {result}")

            # Vérifier les données
            if result and len(result) > 0:
                user = result[0]
                assert user.get("email") == "test@notaire.qc.ca"
                assert user.get("nom") == "Tremblay"
                print("✅ Données vérifiées correctement")

            return True

        except Exception as e:
            print(f"❌ Échec de la récupération: {e}")
            return False


async def test_query():
    """Test 4: Requête SurrealQL."""
    print_test("Requête SurrealQL")

    async with get_db_connection() as db:
        try:
            # Requête avec paramètre
            query = "SELECT * FROM user WHERE email = $email"
            params = {"email": "test@notaire.qc.ca"}

            print(f"Requête: {query}")
            print(f"Paramètres: {params}")

            result = await db.query(query, params)
            print(f"✅ Résultat: {result}")

            return True

        except Exception as e:
            print(f"❌ Échec de la requête: {e}")
            return False


async def test_update_user():
    """Test 5: Mettre à jour un utilisateur."""
    print_test("Mise à jour d'un utilisateur")

    async with get_db_connection() as db:
        try:
            # Mise à jour partielle avec merge
            update_data = {"actif": False}

            print(f"Mise à jour: {update_data}")
            result = await db.merge("user:test_notaire", update_data)
            print(f"✅ Utilisateur mis à jour: {result}")

            # Vérifier la mise à jour
            user = await db.select("user:test_notaire")
            if user and len(user) > 0:
                assert user[0].get("actif") is False
                print("✅ Mise à jour vérifiée")

            return True

        except Exception as e:
            print(f"❌ Échec de la mise à jour: {e}")
            return False


async def test_create_dossier():
    """Test 6: Créer un dossier."""
    print_test("Création d'un dossier")

    async with get_db_connection() as db:
        try:
            # Import RecordID pour la conversion
            from surrealdb import RecordID

            dossier_data = {
                "nom_dossier": "Vente Dupont-Tremblay",
                "type_transaction": "vente",
                "statut": "nouveau",
                "user_id": RecordID("user", "test_notaire")  # Utiliser RecordID au lieu de string
            }

            print(f"Création du dossier: {dossier_data}")
            result = await db.create("dossier", dossier_data, record_id="test_dossier")
            print(f"✅ Dossier créé: {result}")

            return True

        except Exception as e:
            print(f"❌ Échec de la création: {e}")
            return False


async def test_graph_relations():
    """Test 7: Relations graphe."""
    print_test("Relations graphe")

    async with get_db_connection() as db:
        try:
            # Créer des entités
            print("Création des entités...")

            personne_vendeur = await db.create("personne", {
                "nom": "Dupont",
                "prenom": "Jean",
                "type": "vendeur"
            }, record_id="jean_dupont")
            print(f"✅ Vendeur créé: {personne_vendeur}")

            personne_acheteur = await db.create("personne", {
                "nom": "Tremblay",
                "prenom": "Marie",
                "type": "acheteur"
            }, record_id="marie_tremblay")
            print(f"✅ Acheteur créé: {personne_acheteur}")

            propriete = await db.create("propriete", {
                "adresse": "123 Rue St-Denis, Montréal",
                "type": "maison",
                "prix": 450000
            }, record_id="maison123")
            print(f"✅ Propriété créée: {propriete}")

            # Créer des relations
            print("\nCréation des relations...")

            await db.relate(
                "personne:jean_dupont",
                "vend",
                "propriete:maison123",
                {
                    "prix": 450000,
                    "date_offre": "2025-10-15",
                    "dossier": "dossier:test_dossier"
                }
            )
            print("✅ Relation 'vend' créée")

            await db.relate(
                "personne:marie_tremblay",
                "achete",
                "propriete:maison123",
                {
                    "prix": 450000,
                    "date_acceptation": "2025-10-20",
                    "dossier": "dossier:test_dossier"
                }
            )
            print("✅ Relation 'achete' créée")

            # Query graphe
            print("\nRequête graphe...")
            query = "SELECT * FROM personne:jean_dupont->vend->propriete"
            result = await db.query(query)
            print(f"✅ Propriétés vendues par Jean: {result}")

            return True

        except Exception as e:
            print(f"❌ Échec des relations: {e}")
            import traceback
            traceback.print_exc()
            return False


async def test_workflow_execution():
    """Test 8: Stocker l'exécution d'un workflow (schemaless)."""
    print_test("Stockage d'exécution de workflow (SCHEMALESS)")

    async with get_db_connection() as db:
        try:
            # Simuler un workflow en cours
            workflow_data = {
                "workflow_name": "analyse_dossier",
                "dossier": "dossier:test_dossier",
                "status": "running",
                "current_step": "extraction",
                "progress": 0.35,
                "context": {
                    "documents_to_process": 5,
                    "documents_processed": 2,
                    "errors": []
                }
            }

            print(f"Création du workflow: {workflow_data}")
            result = await db.create(
                "workflow_execution",
                workflow_data,
                record_id="test_workflow"
            )
            print(f"✅ Workflow créé: {result}")

            # Mise à jour de la progression
            await asyncio.sleep(0.5)
            update = {
                "progress": 0.65,
                "current_step": "classification",
                "context": {
                    "documents_to_process": 5,
                    "documents_processed": 4,
                    "errors": []
                }
            }

            print(f"\nMise à jour du workflow: {update}")
            result = await db.merge("workflow_execution:test_workflow", update)
            print(f"✅ Workflow mis à jour: {result}")

            return True

        except Exception as e:
            print(f"❌ Échec du workflow: {e}")
            return False


async def test_cleanup():
    """Test 9: Nettoyage des données de test."""
    print_test("Nettoyage des données de test")

    async with get_db_connection() as db:
        try:
            # Supprimer les données de test
            tables_to_clean = [
                "workflow_execution:test_workflow",
                "personne:jean_dupont",
                "personne:marie_tremblay",
                "propriete:maison123",
                "dossier:test_dossier",
                "user:test_notaire"
            ]

            for table in tables_to_clean:
                try:
                    await db.delete(table)
                    print(f"✅ Supprimé: {table}")
                except Exception as e:
                    print(f"⚠️  Impossible de supprimer {table}: {e}")

            return True

        except Exception as e:
            print(f"❌ Échec du nettoyage: {e}")
            return False


async def main():
    """Exécuter tous les tests."""
    print("\n" + "="*60)
    print("TESTS SURREALDB - NOTARY ASSISTANT")
    print("="*60)
    print(f"\nConfiguration:")
    print(f"  URL: {settings.surreal_url}")
    print(f"  Namespace: {settings.surreal_namespace}")
    print(f"  Database: {settings.surreal_database}")

    # Liste des tests
    tests = [
        ("Connexion", test_connection),
        ("Création utilisateur", test_create_user),
        ("Récupération utilisateur", test_select_user),
        ("Requête SurrealQL", test_query),
        ("Mise à jour utilisateur", test_update_user),
        ("Création dossier", test_create_dossier),
        ("Relations graphe", test_graph_relations),
        ("Workflow execution", test_workflow_execution),
        ("Nettoyage", test_cleanup),
    ]

    # Exécuter les tests
    results = []
    start_time = time.time()

    for name, test_func in tests:
        try:
            success = await test_func()
            results.append((name, success))
        except Exception as e:
            print(f"❌ Erreur inattendue dans {name}: {e}")
            results.append((name, False))

        # Petite pause entre les tests
        await asyncio.sleep(0.2)

    # Résumé
    duration = time.time() - start_time

    print("\n" + "="*60)
    print("RÉSUMÉ DES TESTS")
    print("="*60)

    passed = sum(1 for _, success in results if success)
    total = len(results)

    for name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"  {status} - {name}")

    print(f"\n{'='*60}")
    print(f"Résultat: {passed}/{total} tests réussis")
    print(f"Durée: {duration:.2f}s")
    print(f"{'='*60}\n")

    # Code de sortie
    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⚠️  Tests interrompus par l'utilisateur")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Erreur fatale: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
