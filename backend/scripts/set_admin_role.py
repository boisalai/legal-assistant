#!/usr/bin/env python3
"""Définir le rôle admin pour un utilisateur existant."""

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.surreal_service import init_surreal_service, get_surreal_service
from config.settings import settings


async def set_admin_role(email: str):
    """Définir le rôle admin pour un utilisateur."""

    print("🔧 Initialisation SurrealDB...")
    init_surreal_service(
        url=settings.surreal_url,
        namespace=settings.surreal_namespace,
        database=settings.surreal_database
    )

    db_service = get_surreal_service()
    await db_service.connect()

    print(f"🔍 Recherche de l'utilisateur {email}...")

    # Trouver l'utilisateur
    query = f"SELECT * FROM user WHERE email = '{email}'"
    result = await db_service.db.query(query)

    if result and len(result) > 0:
        users = result
        if users and len(users) > 0:
            user = users[0]
            user_id = user.get('id')
            current_role = user.get('role')

            print(f"✅ Utilisateur trouvé!")
            print(f"   ID: {user_id}")
            print(f"   Rôle actuel: {current_role}")

            if current_role == 'admin':
                print(f"✅ L'utilisateur est déjà admin!")
            else:
                print(f"🔄 Mise à jour du rôle en 'admin'...")

                # Mettre à jour le rôle
                update_query = "UPDATE user SET role = 'admin' WHERE email = $email"
                await db_service.db.query(update_query, {"email": email})

                print(f"✅ Rôle mis à jour : {current_role} → admin")
        else:
            print(f"❌ Utilisateur {email} non trouvé")
    else:
        print(f"❌ Utilisateur {email} non trouvé")


if __name__ == "__main__":
    email = sys.argv[1] if len(sys.argv) > 1 else "ay.boisvert@gmail.com"
    asyncio.run(set_admin_role(email))
