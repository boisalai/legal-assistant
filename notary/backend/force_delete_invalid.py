#!/usr/bin/env python3
"""
Script pour forcer la suppression des dossiers avec statuts invalides.
"""
import asyncio
from surrealdb import AsyncSurreal

async def delete_invalid():
    """Supprime les dossiers avec statuts invalides."""
    print("🔍 Connexion à SurrealDB...")

    db = AsyncSurreal("ws://localhost:8001/rpc")
    await db.signin({"username": "root", "password": "root"})
    await db.use("notary", "notary_db")

    print("✅ Connecté\n")

    # Afficher les dossiers avant
    print("📊 Dossiers avec statuts invalides :")
    result = await db.query("""
        SELECT id, nom_dossier, statut
        FROM dossier
        WHERE statut NOT IN ['nouveau', 'en_analyse', 'termine', 'en_erreur', 'archive'];
    """)

    if result and result[0]:
        count = 0
        for item in result[0]:
            # item peut être un dict ou un objet avec des attributs
            if isinstance(item, dict):
                print(f"   - {item.get('id')}: {item.get('nom_dossier')} ({item.get('statut')})")
            else:
                print(f"   - {item}")
            count += 1
        print(f"\n⚠️  {count} dossier(s) seront supprimés\n")
    else:
        print("   ✅ Aucun dossier invalide trouvé!")
        return

    # Supprimer
    print("🗑️  Suppression en cours...")
    delete_result = await db.query("""
        DELETE dossier
        WHERE statut NOT IN ['nouveau', 'en_analyse', 'termine', 'en_erreur', 'archive'];
    """)

    print("✅ Suppression effectuée\n")

    # Vérifier
    print("🔍 Vérification finale :")
    check = await db.query("""
        SELECT count() as total FROM dossier
        WHERE statut NOT IN ['nouveau', 'en_analyse', 'termine', 'en_erreur', 'archive']
        GROUP ALL;
    """)

    remaining = 0
    if check and check[0]:
        # Le résultat devrait contenir le count
        remaining = len(check[0]) if isinstance(check[0], list) else 0

    if remaining > 0:
        print(f"   ⚠️  Il reste {remaining} dossier(s) invalide(s)")
    else:
        print("   ✅ Plus aucun dossier invalide!")

    print("\n🎉 Terminé! Rafraîchissez votre page web.")

if __name__ == "__main__":
    asyncio.run(delete_invalid())
