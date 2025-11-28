#!/usr/bin/env python3
"""
Script de migration directe pour corriger les statuts des dossiers.
Utilise la même connexion SurrealDB que le backend.
"""
import asyncio
from surrealdb import AsyncSurreal
from config.settings import settings

async def migrate_statuts():
    """Migre tous les anciens statuts vers les nouveaux."""
    print("🔍 Connexion à SurrealDB...")

    # Connexion avec les mêmes paramètres que le backend
    db = AsyncSurreal(settings.surreal_url)

    # AsyncSurreal se connecte automatiquement, pas besoin d'appeler connect()
    await db.signin({"username": settings.surreal_username, "password": settings.surreal_password})
    await db.use(settings.surreal_namespace, settings.surreal_database)

    print("✅ Connecté à SurrealDB")
    print(f"   URL: {settings.surreal_url}")
    print(f"   Namespace: {settings.surreal_namespace}")
    print(f"   Database: {settings.surreal_database}")
    print()

    # Vérifier les statuts actuels
    print("📊 Statuts actuels:")
    result = await db.query("SELECT statut, count() as total FROM dossier GROUP BY statut;")
    if result and len(result) > 0:
        for item in result[0]:
            print(f"   - {item.get('statut')}: {item.get('total')} dossier(s)")
    print()

    # Migrations
    migrations = [
        ("complete", "termine"),
        ("erreur", "en_erreur"),
        ("valide", "termine"),
        ("analyse_complete", "termine"),
    ]

    total_updated = 0

    for old_status, new_status in migrations:
        print(f"🔄 Migration: '{old_status}' → '{new_status}'")

        # Exécuter la migration 3 fois pour être sûr
        for attempt in range(3):
            query = f"UPDATE dossier SET statut = '{new_status}' WHERE statut = '{old_status}';"
            result = await db.query(query)

            # Compter combien ont été mis à jour
            if result and len(result) > 0 and isinstance(result[0], list):
                count = len(result[0])
                if count > 0:
                    print(f"   Tentative {attempt + 1}: ✅ {count} dossier(s) mis à jour")
                    total_updated += count

        print()

    # Vérification finale
    print("📊 Statuts après migration:")
    result = await db.query("SELECT statut, count() as total FROM dossier GROUP BY statut;")
    if result and len(result) > 0:
        for item in result[0]:
            print(f"   - {item.get('statut')}: {item.get('total')} dossier(s)")
    print()

    # Lister les statuts invalides restants
    print("🔍 Vérification des statuts invalides:")
    invalid_query = """
    SELECT id, nom_dossier, statut
    FROM dossier
    WHERE statut NOT IN ['nouveau', 'en_analyse', 'termine', 'en_erreur', 'archive'];
    """
    result = await db.query(invalid_query)

    if result and len(result) > 0 and result[0]:
        print(f"   ⚠️  {len(result[0])} dossier(s) avec statut invalide:")
        for item in result[0]:
            print(f"      - {item.get('id')}: {item.get('nom_dossier')} (statut: {item.get('statut')})")
    else:
        print("   ✅ Aucun statut invalide trouvé!")

    print()
    print(f"✅ Migration terminée! {total_updated} dossier(s) mis à jour au total.")

    # Pas besoin de fermer explicitement avec AsyncSurreal

if __name__ == "__main__":
    asyncio.run(migrate_statuts())
