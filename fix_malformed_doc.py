#!/usr/bin/env python3
"""Script pour supprimer le document avec ID malformé."""

import asyncio
from surrealdb import AsyncSurreal

async def main():
    db = AsyncSurreal("ws://localhost:8002/rpc")
    await db.signin({"username": "root", "password": "root"})
    await db.use("legal", "legal_db")

    malformed_id = "document:document:bbb01c49-8f30-4b1f-9115-022600a7b3af"

    print(f"Tentative de suppression de: {malformed_id}")

    # Méthode 1: DELETE avec l'ID complet
    try:
        result = await db.query(f"DELETE `{malformed_id}`")
        print(f"✓ Méthode 1 réussie: {result}")
    except Exception as e:
        print(f"✗ Méthode 1 échouée: {e}")

        # Méthode 2: DELETE avec filtre sur le nom de fichier
        try:
            result = await db.query(
                "DELETE document WHERE nom_fichier = $filename",
                {"filename": "DRT1151_M1_Notes de cours.md"}
            )
            print(f"✓ Méthode 2 réussie: {result}")
        except Exception as e2:
            print(f"✗ Méthode 2 échouée: {e2}")

            # Méthode 3: Suppression avec l'ID brut
            try:
                raw_id = "document:bbb01c49-8f30-4b1f-9115-022600a7b3af"
                result = await db.query(
                    f"DELETE document WHERE string::contains(meta::id(id), $raw_id)",
                    {"raw_id": "bbb01c49-8f30-4b1f-9115-022600a7b3af"}
                )
                print(f"✓ Méthode 3 réussie: {result}")
            except Exception as e3:
                print(f"✗ Méthode 3 échouée: {e3}")

    # Vérifier que le document a bien été supprimé
    check = await db.query("SELECT * FROM document WHERE nom_fichier = 'DRT1151_M1_Notes de cours.md'")
    if check and len(check) > 0:
        items = check[0].get("result", [])
        if items:
            print(f"\n⚠️  Le document existe toujours en base!")
        else:
            print(f"\n✓ Document supprimé avec succès!")
    else:
        print(f"\n✓ Document supprimé avec succès!")

    await db.close()

if __name__ == "__main__":
    asyncio.run(main())
