"""
Script de migration pour mettre à jour les statuts des dossiers.

Convertit les anciens statuts vers les nouveaux statuts uniformisés:
- complete → termine
- erreur → en_erreur
- valide → termine
- analyse_complete → termine

Usage:
    uv run python migrate_statuts.py
"""

import asyncio
from surrealdb import Surreal
from config.settings import settings


async def migrate_statuts():
    """Migrer les statuts des dossiers existants."""

    # Connexion à SurrealDB
    async with Surreal(settings.surreal_url) as db:
        await db.signin({
            "username": settings.surreal_username,
            "password": settings.surreal_password,
        })
        await db.use(settings.surreal_namespace, settings.surreal_database)

        print("🔍 Vérification des dossiers avec anciens statuts...")

        # Mapping des anciens statuts vers les nouveaux
        migrations = [
            ("complete", "termine"),
            ("erreur", "en_erreur"),
            ("valide", "termine"),
            ("analyse_complete", "termine"),
        ]

        total_updated = 0

        for old_status, new_status in migrations:
            # Trouver les dossiers avec l'ancien statut
            query = f"SELECT id FROM dossier WHERE statut = '{old_status}'"
            result = await db.query(query)

            if result and len(result) > 0 and len(result[0]) > 0:
                dossiers = result[0]
                count = len(dossiers)

                if count > 0:
                    print(f"\n📝 Migration: '{old_status}' → '{new_status}' ({count} dossier(s))")

                    # Mettre à jour chaque dossier
                    for dossier in dossiers:
                        dossier_id = dossier['id']
                        update_query = f"UPDATE {dossier_id} SET statut = '{new_status}'"
                        await db.query(update_query)
                        print(f"  ✅ Mis à jour: {dossier_id}")
                        total_updated += 1
                else:
                    print(f"\n✓ Aucun dossier avec statut '{old_status}'")
            else:
                print(f"\n✓ Aucun dossier avec statut '{old_status}'")

        print(f"\n✨ Migration terminée! {total_updated} dossier(s) mis à jour.")

        # Vérification finale
        print("\n📊 Statuts actuels des dossiers:")
        query = "SELECT statut, count() as total FROM dossier GROUP BY statut"
        result = await db.query(query)

        if result and len(result) > 0 and len(result[0]) > 0:
            for row in result[0]:
                statut = row.get('statut', 'N/A')
                total = row.get('total', 0)
                print(f"  - {statut}: {total}")

    print("\n✅ Migration terminée avec succès!")


if __name__ == "__main__":
    asyncio.run(migrate_statuts())
