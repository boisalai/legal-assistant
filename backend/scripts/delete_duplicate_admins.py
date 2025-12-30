#!/usr/bin/env python3
"""Supprimer les comptes admin@legal.com en double."""

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.surreal_service import init_surreal_service, get_surreal_service
from config.settings import settings


async def delete_duplicates():
    """Supprimer les comptes admin@legal.com."""

    print("🔧 Initialisation SurrealDB...")
    init_surreal_service(
        url=settings.surreal_url,
        namespace=settings.surreal_namespace,
        database=settings.surreal_database
    )

    db_service = get_surreal_service()
    await db_service.connect()

    print("🔍 Recherche des comptes admin@legal.com...")

    # Trouver tous les admin@legal.com
    result = await db_service.db.query("SELECT * FROM user WHERE email = 'admin@legal.com'")

    if result and len(result) > 0:
        admin_accounts = result

        if admin_accounts and len(admin_accounts) > 0:
            print(f"✅ {len(admin_accounts)} compte(s) admin@legal.com trouvé(s)\n")

            for account in admin_accounts:
                user_id = account.get('id')
                created_at = account.get('created_at')
                print(f"  🗑️  Suppression de {user_id}")
                print(f"     Créé le: {created_at}")

                # Supprimer le compte
                delete_query = f"DELETE {user_id}"
                await db_service.db.query(delete_query)
                print(f"     ✅ Supprimé\n")

            print(f"✅ {len(admin_accounts)} compte(s) supprimé(s)")
        else:
            print("❌ Aucun compte admin@legal.com trouvé")
    else:
        print("❌ Aucun compte admin@legal.com trouvé")


if __name__ == "__main__":
    asyncio.run(delete_duplicates())
