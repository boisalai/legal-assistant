"""
Script pour tester et corriger le problème de permissions SurrealDB.

Le problème: IAM error: Not enough permissions to perform this action
La cause: SurrealDB nécessite une authentification root explicite

Solution: Se connecter en tant que root SYSTEM avant toute opération
"""

from surrealdb import Surreal
from config import settings

print("\n" + "="*80)
print("TEST PERMISSIONS SURREALDB")
print("="*80 + "\n")

try:
    # Connexion
    print("1. Connexion à SurrealDB...")
    db = Surreal(settings.surreal_url)
    print("✅ Connecté\n")

    # Authentification ROOT au niveau SYSTEM (pas namespace)
    print("2. Authentification ROOT au niveau SYSTEM...")
    try:
        # Méthode 1: Signin direct sans namespace
        db.signin({
            "user": "root",
            "pass": "root"
        })
        print("✅ Authentifié en tant que root SYSTEM\n")
    except Exception as e:
        print(f"❌ Échec méthode 1: {e}\n")

        # Méthode 2: Query direct
        print("Tentative méthode 2: Query direct...")
        try:
            result = db.query("INFO FOR ROOT;")
            print(f"✅ Query ROOT: {result}\n")
        except Exception as e2:
            print(f"❌ Échec méthode 2: {e2}\n")

    # Test 3: Sélection namespace après authentification
    print("3. Sélection namespace après authentification...")
    db.use("notary", "notary_db")
    print("✅ Namespace sélectionné: notary/notary_db\n")

    # Test 4: Écriture
    print("4. Test d'écriture...")
    try:
        record = db.create("test_permissions", {
            "message": "Test après authentification root",
            "timestamp": "2025-11-20"
        })
        print("✅ Écriture réussie!")
        print(f"   Record créé: {record}\n")

        # Nettoyer
        db.delete("test_permissions")
        print("✅ Nettoyage effectué\n")

    except Exception as e:
        print(f"❌ Erreur écriture: {e}\n")

        # Solution: DEFINE ROOT USER
        print("\n" + "="*80)
        print("SOLUTION: Définir l'utilisateur ROOT explicitement")
        print("="*80 + "\n")

        print("Le problème est que SurrealDB avec --user root --pass root")
        print("ne crée pas automatiquement les permissions nécessaires.")
        print()
        print("SOLUTION 1: Redémarrer SurrealDB sans authentification (DEV ONLY)")
        print("-" * 80)
        print("Modifiez docker-compose.yml:")
        print()
        print("  command: >")
        print("    start")
        print("    --log trace")
        print("    --allow-all          # ← AJOUTER CECI (dev seulement!)")
        print("    file:/data/notary.db")
        print()
        print("Puis:")
        print("  docker-compose restart surrealdb")
        print()
        print()
        print("SOLUTION 2: Utiliser memory:// pour les tests (recommandé)")
        print("-" * 80)
        print("  command: >")
        print("    start")
        print("    --log trace")
        print("    memory://")
        print()
        print()
        print("SOLUTION 3: Activer --auth avec configuration IAM")
        print("-" * 80)
        print("Plus complexe, nécessite configuration des rôles et permissions")
        print()

except Exception as e:
    print(f"\n❌ ERREUR: {e}")
    import traceback
    print(traceback.format_exc())

print("\n" + "="*80)
print("RECOMMANDATION")
print("="*80 + "\n")
print("Pour le développement, utilisez --allow-all dans docker-compose.yml")
print("Cela désactive l'authentification et permet toutes les opérations.")
print()
print("⚠️  ATTENTION: Ne JAMAIS utiliser --allow-all en production!")
print()
