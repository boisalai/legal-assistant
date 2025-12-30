#!/usr/bin/env python3
"""Debug l'API /api/auth/me pour voir la réponse exacte."""

import requests
import json

# Login
print("🔐 Test de connexion...")
login_response = requests.post(
    "http://localhost:8000/api/auth/login",
    data={
        "username": "ay.boisvert@gmail.com",
        "password": "Curio2024!"
    }
)

if login_response.status_code != 200:
    print(f"❌ Login échoué: {login_response.status_code}")
    print(f"   {login_response.text}")
    exit(1)

data = login_response.json()
token = data["access_token"]
print(f"✅ Login réussi!")

# Tester /api/auth/me
print(f"\n🔍 Test de /api/auth/me...")
me_response = requests.get(
    "http://localhost:8000/api/auth/me",
    headers={"Authorization": f"Bearer {token}"}
)

print(f"Status code: {me_response.status_code}")
print(f"\n📄 Réponse complète:")
print(json.dumps(me_response.json(), indent=2, ensure_ascii=False))

if me_response.status_code == 200:
    user = me_response.json()
    print(f"\n🔑 Champs reçus:")
    for key, value in user.items():
        print(f"   {key}: {value} (type: {type(value).__name__})")

    role = user.get('role')
    print(f"\n🎭 Rôle détecté: '{role}'")
    print(f"   Est admin? {role == 'admin'}")
