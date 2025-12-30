#!/usr/bin/env python3
"""
Script pour créer un utilisateur admin dans SurrealDB.
Usage: python scripts/create_admin.py
"""

import asyncio
import sys
import os

# Ajouter le répertoire parent au path pour les imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.surreal_service import init_surreal_service, get_surreal_service
from config.settings import settings
import hashlib
import uuid


async def create_admin_user():
    """Créer un utilisateur admin par défaut."""

    # Configuration de l'admin par défaut
    admin_email = "admin@legal.com"
    admin_password = "admin123"  # À changer après première connexion!
    admin_name = "Administrateur"
    admin_prenom = "Super"

    print("🔧 Initialisation du service SurrealDB...")
    init_surreal_service(
        url=settings.surreal_url,
        namespace=settings.surreal_namespace,
        database=settings.surreal_database
    )

    print("🔧 Connexion à SurrealDB...")
    db_service = get_surreal_service()
    await db_service.connect()

    print(f"🔍 Vérification si l'utilisateur {admin_email} existe déjà...")

    # Vérifier si l'utilisateur existe
    query = f"SELECT * FROM user WHERE email = '{admin_email}'"
    result = await db_service.db.query(query)

    existing_user = None
    if result and len(result) > 0:
        first_result = result[0]
        if isinstance(first_result, dict) and "result" in first_result:
            users = first_result["result"]
            if users and len(users) > 0:
                existing_user = users[0]

    if existing_user:
        print(f"✅ L'utilisateur {admin_email} existe déjà")
        print(f"   ID: {existing_user.get('id')}")
        print(f"   Rôle: {existing_user.get('role')}")

        # Mettre à jour le rôle en admin si ce n'est pas déjà le cas
        if existing_user.get('role') != 'admin':
            print(f"🔄 Mise à jour du rôle en 'admin'...")
            user_id = existing_user['id']
            update_query = f"UPDATE {user_id} SET role = 'admin'"
            await db_service.db.query(update_query)
            print(f"✅ Rôle mis à jour!")
    else:
        print(f"➕ Création d'un nouvel utilisateur admin...")

        # Générer un ID unique
        user_id = f"user:{uuid.uuid4().hex[:16]}"

        # Hasher le mot de passe (SHA-256 simple pour le moment)
        password_hash = hashlib.sha256(admin_password.encode()).hexdigest()

        # Créer l'utilisateur
        create_query = f"""
        CREATE {user_id} CONTENT {{
            email: '{admin_email}',
            nom: '{admin_name}',
            prenom: '{admin_prenom}',
            password_hash: '{password_hash}',
            role: 'admin',
            actif: true,
            created_at: time::now(),
            updated_at: time::now()
        }}
        """

        await db_service.db.query(create_query)
        print(f"✅ Utilisateur admin créé avec succès!")

    print("\n" + "="*60)
    print("📧 Email:     admin@legal.com")
    print("🔑 Password:  admin123")
    print("⚠️  IMPORTANT: Changez ce mot de passe après première connexion!")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(create_admin_user())
