#!/usr/bin/env python3
"""
Script d'initialisation du schéma SurrealDB

Usage:
    cd backend
    uv run python init_schema.py

Prérequis:
    - SurrealDB doit être démarré: docker-compose up -d surrealdb
"""

import asyncio
import sys
from pathlib import Path

# Ajouter le répertoire backend au path
sys.path.insert(0, str(Path(__file__).parent))

from services.surreal_service import get_db_connection
from config.settings import settings


async def init_schema():
    """Initialiser le schéma SurrealDB."""
    print("🔧 Initialisation du schéma SurrealDB...")
    print(f"   URL: {settings.surreal_url}")
    print(f"   Namespace: {settings.surreal_namespace}")
    print(f"   Database: {settings.surreal_database}\n")

    # Lire le fichier schema.surql
    schema_file = Path(__file__).parent / "data" / "surreal" / "schema.surql"

    if not schema_file.exists():
        print(f"❌ Fichier schema.surql introuvable: {schema_file}")
        return False

    print(f"📖 Lecture du schéma: {schema_file}")
    schema_sql = schema_file.read_text(encoding="utf-8")

    # Diviser en commandes individuelles (séparées par des lignes vides ou --)
    commands = []
    current_command = []

    for line in schema_sql.split("\n"):
        stripped = line.strip()

        # Ignorer les commentaires et lignes vides
        if not stripped or stripped.startswith("--"):
            if current_command:
                # Ligne vide ou commentaire après une commande = fin de commande
                commands.append("\n".join(current_command))
                current_command = []
            continue

        current_command.append(line)

    # Ajouter la dernière commande si elle existe
    if current_command:
        commands.append("\n".join(current_command))

    print(f"✅ {len(commands)} commandes trouvées\n")

    # Se connecter à SurrealDB
    async with get_db_connection() as db:
        print("✅ Connecté à SurrealDB\n")

        # Exécuter chaque commande
        success_count = 0
        error_count = 0

        for i, command in enumerate(commands, 1):
            # Nettoyer la commande
            cmd = command.strip()
            if not cmd:
                continue

            # Afficher un résumé de la commande
            cmd_preview = cmd[:80].replace("\n", " ")
            print(f"[{i}/{len(commands)}] {cmd_preview}...")

            try:
                result = await db.query(cmd)
                success_count += 1
                print(f"    ✅ OK")

                # Afficher le résultat si pertinent
                if result and len(result) > 0:
                    print(f"    → Résultat: {result}")

            except Exception as e:
                error_count += 1
                print(f"    ❌ Erreur: {e}")

        print(f"\n{'='*60}")
        print(f"📊 Résumé:")
        print(f"   ✅ Succès: {success_count}")
        print(f"   ❌ Erreurs: {error_count}")
        print(f"{'='*60}\n")

        # Vérifier que les tables sont créées
        print("🔍 Vérification des tables créées...")
        try:
            result = await db.query("INFO FOR DB;")
            print(f"✅ Tables créées: {result}")
        except Exception as e:
            print(f"❌ Impossible de vérifier les tables: {e}")

        return error_count == 0


if __name__ == "__main__":
    success = asyncio.run(init_schema())
    sys.exit(0 if success else 1)
