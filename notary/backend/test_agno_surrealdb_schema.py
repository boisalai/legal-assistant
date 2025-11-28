#!/usr/bin/env python3
"""
Test script pour analyser le schéma SurrealDB créé automatiquement par Agno.

Basé sur les exemples officiels:
- https://github.com/agno-agi/agno/blob/main/cookbook/db/surrealdb/surrealdb_for_workflow.py
- https://github.com/agno-agi/agno/blob/main/cookbook/db/surrealdb/surrealdb_for_agent.py

Ce script:
1. Crée une connexion SurrealDB avec les credentials standard
2. Initialise un Workflow simple avec db=
3. Exécute le workflow pour forcer Agno à créer ses tables
4. Inspecte les tables créées via l'API SurrealDB
"""

import asyncio
import json
from pathlib import Path

# Configuration SurrealDB (pattern officiel Agno)
SURREALDB_URL = "ws://localhost:8000"
SURREALDB_NAMESPACE = "agno"
SURREALDB_DATABASE = "test_schema"
SURREALDB_CREDS = {"user": "root", "pass": "root"}


async def test_agno_schema():
    """Test la création automatique de schéma par Agno."""

    print("=" * 70)
    print("TEST: Analyse du schéma SurrealDB créé par Agno")
    print("=" * 70)
    print()

    # Import Agno
    try:
        from agno import Workflow, Agent
        from agno.db.surrealdb import SurrealDb
        print("✅ Imports Agno réussis")
    except ImportError as e:
        print(f"❌ Erreur import Agno: {e}")
        print("💡 Installer avec: uv add agno[surrealdb]")
        return

    # 1. Créer connexion SurrealDB (pattern officiel)
    print("\n1️⃣  Création connexion SurrealDB...")
    print(f"   URL: {SURREALDB_URL}")
    print(f"   Namespace: {SURREALDB_NAMESPACE}")
    print(f"   Database: {SURREALDB_DATABASE}")

    try:
        db = SurrealDb(
            None,
            SURREALDB_URL,
            SURREALDB_CREDS,
            SURREALDB_NAMESPACE,
            SURREALDB_DATABASE
        )
        print("✅ Connexion SurrealDB créée")
    except Exception as e:
        print(f"❌ Erreur connexion SurrealDB: {e}")
        print("💡 Vérifier que SurrealDB tourne sur ws://localhost:8000")
        return

    # 2. Créer un Workflow simple avec db=
    print("\n2️⃣  Création Workflow avec persistance...")

    try:
        # Agent simple pour le test
        test_agent = Agent(
            name="TestAgent",
            model="openai:gpt-4o-mini",
            instructions="Tu es un agent de test. Réponds simplement 'Test OK'.",
        )

        # Workflow avec db= (Agno va créer ses tables automatiquement)
        workflow = Workflow(
            name="test_schema_workflow",
            db=db,  # ✅ Pattern officiel Agno
            agents=[test_agent],
        )
        print("✅ Workflow créé avec db=")

    except Exception as e:
        print(f"❌ Erreur création Workflow: {e}")
        return

    # 3. Exécuter le workflow (force la création des tables)
    print("\n3️⃣  Exécution Workflow (création tables)...")

    try:
        # Exécution simple
        result = workflow.run("Test de création de schéma")
        print("✅ Workflow exécuté")
        print(f"   Résultat: {result[:100] if isinstance(result, str) else result}...")

    except Exception as e:
        print(f"⚠️  Erreur exécution (normal si pas d'API key): {e}")
        print("   Les tables devraient quand même être créées")

    # 4. Inspecter les tables créées
    print("\n4️⃣  Inspection des tables SurrealDB...")

    try:
        import httpx

        # API SurrealDB pour lister les tables
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://localhost:8001/sql",
                headers={
                    "Accept": "application/json",
                    "NS": SURREALDB_NAMESPACE,
                    "DB": SURREALDB_DATABASE,
                },
                auth=("root", "root"),
                content="INFO FOR DB;"
            )

            if response.status_code == 200:
                data = response.json()
                print("✅ Tables créées par Agno:")

                # Parser la réponse
                if data and len(data) > 0:
                    info = data[0].get("result", {})

                    # Tables
                    tables = info.get("tb", {})
                    if tables:
                        print("\n📊 Tables:")
                        for table_name in tables.keys():
                            print(f"   - {table_name}")

                    # Indexes
                    indexes = info.get("ix", {})
                    if indexes:
                        print("\n🔍 Indexes:")
                        for idx_name in indexes.keys():
                            print(f"   - {idx_name}")

                    # Sauvegarder le schéma complet
                    output_file = Path("docs/agno-surrealdb-schema.json")
                    output_file.parent.mkdir(parents=True, exist_ok=True)

                    with open(output_file, "w") as f:
                        json.dump(data, f, indent=2)

                    print(f"\n💾 Schéma complet sauvegardé: {output_file}")

                else:
                    print("⚠️  Pas de résultat dans la réponse")

            else:
                print(f"❌ Erreur HTTP {response.status_code}: {response.text}")

    except Exception as e:
        print(f"❌ Erreur inspection: {e}")

    # 5. Requêter une table Agno
    print("\n5️⃣  Requête table workflow_runs...")

    try:
        import httpx

        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://localhost:8001/sql",
                headers={
                    "Accept": "application/json",
                    "NS": SURREALDB_NAMESPACE,
                    "DB": SURREALDB_DATABASE,
                },
                auth=("root", "root"),
                content="SELECT * FROM workflow_runs LIMIT 5;"
            )

            if response.status_code == 200:
                data = response.json()
                if data and len(data) > 0 and data[0].get("result"):
                    runs = data[0]["result"]
                    print(f"✅ Trouvé {len(runs)} workflow runs")

                    for i, run in enumerate(runs, 1):
                        print(f"\n   Run #{i}:")
                        print(f"   - ID: {run.get('id')}")
                        print(f"   - Name: {run.get('workflow_name')}")
                        print(f"   - Status: {run.get('status')}")
                        print(f"   - Created: {run.get('created_at')}")
                else:
                    print("⚠️  Aucun workflow run trouvé")

    except Exception as e:
        print(f"❌ Erreur requête: {e}")

    print("\n" + "=" * 70)
    print("✨ Test terminé!")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(test_agno_schema())
