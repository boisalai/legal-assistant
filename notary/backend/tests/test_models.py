#!/usr/bin/env python3
"""Script pour tester les modèles Pydantic."""

from models.user import UserBase, UserCreate, User
from models.dossier import DossierBase, DossierCreate, Dossier
from datetime import datetime

print("=== Test 1: Créer un utilisateur valide ===")
try:
    user = UserBase(
        email="john@example.com",
        nom="Doe",
        prenom="John",
        role="notaire"
    )
    print(f"✓ Utilisateur créé: {user.email}")
    print(f"  Nom complet: {user.prenom} {user.nom}")
    print(f"  JSON: {user.model_dump_json()}")
except Exception as e:
    print(f"✗ Erreur: {e}")

print("\n=== Test 2: Email invalide (devrait échouer) ===")
try:
    user = UserBase(
        email="pas-un-email",  # Invalide!
        nom="Doe",
        prenom="John",
        role="notaire"
    )
    print(f"✓ Utilisateur créé: {user.email}")
except Exception as e:
    print(f"✓ Erreur capturée (normal): {type(e).__name__}")

print("\n=== Test 3: Rôle invalide (devrait échouer) ===")
try:
    user = UserBase(
        email="john@example.com",
        nom="Doe",
        prenom="John",
        role="super-admin"  # Invalide! Doit être notaire/assistant/admin
    )
    print(f"✓ Utilisateur créé")
except Exception as e:
    print(f"✓ Erreur capturée (normal): {type(e).__name__}")

print("\n=== Test 4: Créer un dossier ===")
try:
    dossier = DossierCreate(
        nom_dossier="Vente Dupont-Tremblay",
        type_transaction="vente",
        user_id="user:abc123"
    )
    print(f"✓ Dossier créé: {dossier.nom_dossier}")
    print(f"  Type: {dossier.type_transaction}")
    print(f"  User ID: {dossier.user_id}")
except Exception as e:
    print(f"✗ Erreur: {e}")

print("\n=== Test 5: Sérialisation JSON ===")
dossier_dict = dossier.model_dump()
print(f"Dict Python: {dossier_dict}")
dossier_json = dossier.model_dump_json(indent=2)
print(f"JSON:\n{dossier_json}")