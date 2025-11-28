#!/usr/bin/env python3
"""
Debug script for authentication issues.

Run this script to diagnose login problems:
    cd backend
    uv run python debug_auth.py
"""

import asyncio
import hashlib
from services.surreal_service import get_db_connection


def hash_password(password: str) -> str:
    """Hash a password using SHA256."""
    return hashlib.sha256(password.encode()).hexdigest()


async def debug_auth():
    print("=" * 60)
    print("DEBUG AUTHENTIFICATION")
    print("=" * 60)

    async with get_db_connection() as db:
        # 1. List all users
        print("\n1. UTILISATEURS DANS LA BASE DE DONNÉES")
        print("-" * 40)
        result = await db.query("SELECT * FROM user")
        print(f"Résultat brut de la requête: {result}")

        users = []
        if result and len(result) > 0:
            # SurrealDB returns results in different formats
            if isinstance(result[0], dict) and "result" in result[0]:
                users = result[0].get("result", [])
            elif isinstance(result[0], list):
                users = result[0]
            elif isinstance(result, list):
                users = result

        if not users:
            print("❌ AUCUN UTILISATEUR TROUVÉ!")
            print("   Veuillez exécuter: uv run python init_demo_users.py")
            return

        print(f"✅ {len(users)} utilisateur(s) trouvé(s):")
        for u in users:
            print(f"   - Email: {u.get('email')}")
            print(f"     Role: {u.get('role')}")
            print(f"     Actif: {u.get('actif')}")
            print(f"     Hash: {u.get('password_hash', 'N/A')[:30]}...")
            print()

        # 2. Test query with email filter
        print("\n2. TEST REQUÊTE PAR EMAIL")
        print("-" * 40)

        test_email = "notaire@test.com"
        result2 = await db.query(
            "SELECT * FROM user WHERE email = $email AND actif = true",
            {"email": test_email}
        )
        print(f"Requête: SELECT * FROM user WHERE email = '{test_email}' AND actif = true")
        print(f"Résultat: {result2}")

        # Parse result
        found_user = None
        if result2 and len(result2) > 0:
            if isinstance(result2[0], dict) and "result" in result2[0]:
                res = result2[0].get("result", [])
                if res:
                    found_user = res[0]
            elif isinstance(result2[0], dict):
                found_user = result2[0]

        if found_user:
            print(f"✅ Utilisateur trouvé: {found_user.get('email')}")
        else:
            print(f"❌ Utilisateur '{test_email}' NON TROUVÉ avec la requête filtrée!")
            print("   Cela peut être dû à:")
            print("   - Le champ 'actif' n'est pas défini ou est false")
            print("   - Le format de la requête n'est pas correct")

        # 3. Verify password hash
        print("\n3. VÉRIFICATION DU HASH")
        print("-" * 40)

        passwords_to_test = [
            ("notaire123", "notaire@test.com"),
            ("admin1234", "admin@test.com"),
        ]

        for password, email in passwords_to_test:
            computed_hash = hash_password(password)
            print(f"\nMot de passe: '{password}' pour {email}")
            print(f"Hash calculé: {computed_hash}")

            # Find user and compare
            for u in users:
                if u.get("email") == email:
                    stored_hash = u.get("password_hash", "")
                    print(f"Hash stocké:  {stored_hash}")
                    if computed_hash == stored_hash:
                        print("✅ Les hashes correspondent!")
                    else:
                        print("❌ LES HASHES NE CORRESPONDENT PAS!")
                    break

        # 4. Test with simple query (without filter)
        print("\n4. TEST REQUÊTE SIMPLE (SANS FILTRE actif)")
        print("-" * 40)

        result3 = await db.query(
            "SELECT * FROM user WHERE email = $email",
            {"email": test_email}
        )
        print(f"Requête: SELECT * FROM user WHERE email = '{test_email}'")
        print(f"Résultat: {result3}")

        # 5. Check if 'actif' field exists and its value
        print("\n5. VÉRIFICATION DU CHAMP 'actif'")
        print("-" * 40)

        for u in users:
            actif_value = u.get("actif")
            print(f"{u.get('email')}: actif = {actif_value} (type: {type(actif_value).__name__})")

    print("\n" + "=" * 60)
    print("FIN DU DEBUG")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(debug_auth())
