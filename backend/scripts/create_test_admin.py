"""
Script pour créer un utilisateur admin de test.
"""

import asyncio
import sys
import hashlib
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.surreal_service import get_db_connection


def hash_password(password: str) -> str:
    """Hash le mot de passe avec SHA-256."""
    return hashlib.sha256(password.encode()).hexdigest()


async def create_test_admin():
    """Crée un utilisateur admin de test."""
    async with get_db_connection(
        url="ws://localhost:8002/rpc",
        namespace="legal_assistant",
        database="legal_assistant"
    ) as db:
        # Check if admin exists
        existing = await db.query(
            "SELECT * FROM user WHERE email = $email",
            {"email": "admin@test.com"}
        )

        if existing and len(existing) > 0:
            print("✅ Admin test existe déjà: admin@test.com")
            # Update password
            await db.query(
                "UPDATE user SET password_hash = $hash WHERE email = $email",
                {
                    "email": "admin@test.com",
                    "hash": hash_password("admin123")
                }
            )
            print("✅ Mot de passe mis à jour: admin123")
        else:
            # Create new admin
            await db.create("user", {
                "email": "admin@test.com",
                "nom": "Admin",
                "prenom": "Test",
                "role": "admin",
                "actif": True,
                "password_hash": hash_password("admin123")
            })
            print("✅ Nouvel admin créé: admin@test.com / admin123")


if __name__ == "__main__":
    asyncio.run(create_test_admin())
