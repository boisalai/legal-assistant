#!/usr/bin/env python3
"""Liste tous les utilisateurs dans SurrealDB."""

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.surreal_service import init_surreal_service, get_surreal_service
from config.settings import settings


async def list_users():
    """Lister tous les utilisateurs."""

    print("🔧 Initialisation SurrealDB...")
    init_surreal_service(
        url=settings.surreal_url,
        namespace=settings.surreal_namespace,
        database=settings.surreal_database
    )

    db_service = get_surreal_service()
    await db_service.connect()

    print("📋 Récupération des utilisateurs...\n")

    result = await db_service.db.query("SELECT * FROM user")

    print(f"DEBUG: Result type: {type(result)}")
    print(f"DEBUG: Result length: {len(result) if result else 0}")
    print(f"DEBUG: Result content: {result}")

    if result and len(result) > 0:
        first_result = result[0]
        print(f"DEBUG: First result type: {type(first_result)}")
        print(f"DEBUG: First result: {first_result}")

        if isinstance(first_result, dict) and "result" in first_result:
            users = first_result["result"]

            if users:
                print(f"\n✅ {len(users)} utilisateur(s) trouvé(s):\n")
                for user in users:
                    print(f"  ID: {user.get('id')}")
                    print(f"  ID repr: {repr(user.get('id'))}")
                    print(f"  Email: {user.get('email')}")
                    print(f"  Nom: {user.get('prenom')} {user.get('nom')}")
                    print(f"  Rôle: {user.get('role')}")
                    print(f"  Actif: {user.get('actif')}")
                    print(f"  Type ID: {type(user.get('id'))}")
                    print(f"  Full user: {user}")
                    print("  " + "="*50)
            else:
                print("❌ Aucun utilisateur trouvé (users list vide)")
        else:
            print(f"❌ Format inattendu: {first_result}")
    else:
        print("❌ Requête échouée ou result vide")


if __name__ == "__main__":
    asyncio.run(list_users())
