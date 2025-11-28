"""
Test de diagnostic pour le problème de persistance SurrealDB.

Ce script teste si les données persistent correctement entre les connexions.
"""

import asyncio
import logging
from services.surreal_service import SurrealDBService
from config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_persistence_issue():
    """
    Test pour reproduire le bug de persistance.

    Scénario:
    1. Connexion 1: Créer un dossier
    2. Déconnecter
    3. Connexion 2: Essayer de lire le dossier
    """
    print("\n" + "="*70)
    print("TEST 1: Connexions séparées (comme dans l'API actuelle)")
    print("="*70)

    # Connexion 1: Créer un dossier
    db1 = SurrealDBService(
        url=settings.surreal_url,
        namespace=settings.surreal_namespace,
        database=settings.surreal_database,
    )
    await db1.connect()

    dossier_id = "test_persistence_001"
    dossier_data = {
        "nom_dossier": "Test Persistence",
        "user_id": "user:test",
        "statut": "nouveau",
    }

    print(f"\n1️⃣  Création du dossier avec connexion 1...")
    created = await db1.create("dossier", dossier_data, record_id=dossier_id)
    print(f"   ✅ Dossier créé: dossier:{dossier_id}")
    print(f"   Created result: {created}")

    # Vérifier qu'on peut le lire avec la MÊME connexion
    print(f"\n2️⃣  Lecture avec la MÊME connexion (avant disconnect)...")
    result_same = await db1.select(f"dossier:{dossier_id}")
    print(f"   Result: {result_same}")

    if result_same:
        print(f"   ✅ Trouvé avec la même connexion")
    else:
        print(f"   ❌ PAS TROUVÉ avec la même connexion (TRÈS MAUVAIS!)")

    print(f"\n3️⃣  Déconnexion de la connexion 1...")
    await db1.disconnect()
    print(f"   ✅ Déconnecté")

    # Petit délai pour simuler le temps entre requêtes
    print(f"\n4️⃣  Attente de 100ms (simuler temps entre requêtes)...")
    await asyncio.sleep(0.1)

    # Connexion 2: Essayer de lire
    print(f"\n5️⃣  Nouvelle connexion (connexion 2)...")
    db2 = SurrealDBService(
        url=settings.surreal_url,
        namespace=settings.surreal_namespace,
        database=settings.surreal_database,
    )
    await db2.connect()
    print(f"   ✅ Connecté")

    print(f"\n6️⃣  Lecture du dossier avec connexion 2...")
    result_new = await db2.select(f"dossier:{dossier_id}")
    print(f"   Result: {result_new}")

    if result_new and len(result_new) > 0:
        print(f"   ✅ TROUVÉ avec nouvelle connexion (PERSISTANCE OK!)")
    else:
        print(f"   ❌ PAS TROUVÉ avec nouvelle connexion (BUG CONFIRMÉ!)")

    # Cleanup
    print(f"\n7️⃣  Nettoyage...")
    await db2.query(f"DELETE dossier:{dossier_id}")
    await db2.disconnect()

    print("\n" + "="*70)
    print("TEST 2: Même connexion (pour comparaison)")
    print("="*70)

    # Test avec la MÊME connexion (pas de disconnect)
    db3 = SurrealDBService(
        url=settings.surreal_url,
        namespace=settings.surreal_namespace,
        database=settings.surreal_database,
    )
    await db3.connect()

    dossier_id_2 = "test_persistence_002"

    print(f"\n1️⃣  Création avec connexion 3...")
    created2 = await db3.create("dossier", dossier_data, record_id=dossier_id_2)
    print(f"   ✅ Créé: {created2}")

    print(f"\n2️⃣  Lecture avec la MÊME connexion (sans disconnect)...")
    result2 = await db3.select(f"dossier:{dossier_id_2}")
    print(f"   Result: {result2}")

    if result2 and len(result2) > 0:
        print(f"   ✅ Trouvé (normal)")
    else:
        print(f"   ❌ Pas trouvé (bizarre!)")

    # Cleanup
    await db3.query(f"DELETE dossier:{dossier_id_2}")
    await db3.disconnect()

    print("\n" + "="*70)
    print("TEST 3: Avec délai avant disconnect")
    print("="*70)

    # Test avec délai avant disconnect
    db4 = SurrealDBService(
        url=settings.surreal_url,
        namespace=settings.surreal_namespace,
        database=settings.surreal_database,
    )
    await db4.connect()

    dossier_id_3 = "test_persistence_003"

    print(f"\n1️⃣  Création avec connexion 4...")
    created3 = await db4.create("dossier", dossier_data, record_id=dossier_id_3)
    print(f"   ✅ Créé: {created3}")

    print(f"\n2️⃣  Attente de 500ms avant disconnect...")
    await asyncio.sleep(0.5)

    print(f"\n3️⃣  Déconnexion...")
    await db4.disconnect()

    print(f"\n4️⃣  Nouvelle connexion pour lire...")
    db5 = SurrealDBService(
        url=settings.surreal_url,
        namespace=settings.surreal_namespace,
        database=settings.surreal_database,
    )
    await db5.connect()

    result3 = await db5.select(f"dossier:{dossier_id_3}")
    print(f"   Result: {result3}")

    if result3 and len(result3) > 0:
        print(f"   ✅ TROUVÉ (le délai aide!)")
    else:
        print(f"   ❌ PAS TROUVÉ (même avec délai)")

    # Cleanup
    await db5.query(f"DELETE dossier:{dossier_id_3}")
    await db5.disconnect()

    print("\n" + "="*70)
    print("CONCLUSIONS")
    print("="*70)
    print("")
    print("Si les tests montrent:")
    print("  - Test 1: ❌ Pas trouvé → Bug de disconnect immédiat")
    print("  - Test 2: ✅ Trouvé → Même connexion fonctionne")
    print("  - Test 3: ✅ Trouvé → Le délai résout le problème")
    print("")
    print("Alors la solution est:")
    print("  1. Utiliser un pool de connexions (réutiliser les connexions)")
    print("  2. OU ajouter await asyncio.sleep(0.1) avant disconnect")
    print("  3. OU ne pas disconnect immédiatement (FastAPI gère le cleanup)")
    print("")


if __name__ == "__main__":
    asyncio.run(test_persistence_issue())
