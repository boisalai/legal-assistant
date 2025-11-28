#!/usr/bin/env python3
"""
Initialize demo users in SurrealDB.

Run this script after the database is started to create demo users:
    cd backend
    uv run python init_demo_users.py
"""

import asyncio
import hashlib
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def hash_password(password: str) -> str:
    """Hash a password using SHA256."""
    return hashlib.sha256(password.encode()).hexdigest()


async def init_demo_users():
    """Initialize demo users in SurrealDB."""
    from services.surreal_service import get_db_connection

    demo_users = [
        {
            "id": "demo_notaire",
            "email": "notaire@test.com",
            "nom": "Jean Tremblay",
            "prenom": "",
            "password_hash": hash_password("notaire123"),
            "role": "notaire",
            "actif": True,
        },
        {
            "id": "admin",
            "email": "admin@test.com",
            "nom": "Admin User",
            "prenom": "",
            "password_hash": hash_password("admin1234"),
            "role": "admin",
            "actif": True,
        },
    ]

    async with get_db_connection() as db:
        for user in demo_users:
            user_id = user.pop("id")
            try:
                # Check if user already exists
                result = await db.query(
                    "SELECT * FROM user WHERE email = $email",
                    {"email": user["email"]}
                )

                if result and len(result) > 0 and len(result[0].get("result", [])) > 0:
                    logger.info(f"User {user['email']} already exists, skipping...")
                    continue

                # Create user
                await db.create("user", user, record_id=user_id)
                logger.info(f"Created user: {user['email']} (role: {user['role']})")

            except Exception as e:
                logger.error(f"Failed to create user {user['email']}: {e}")

    logger.info("Demo users initialization complete!")
    logger.info("")
    logger.info("Demo credentials:")
    logger.info("  Notaire: notaire@test.com / notaire123")
    logger.info("  Admin:   admin@test.com / admin1234")


if __name__ == "__main__":
    asyncio.run(init_demo_users())
