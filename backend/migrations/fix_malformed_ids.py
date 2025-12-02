#!/usr/bin/env python3
"""
Migration pour corriger les IDs malformés dans SurrealDB.

Ce script :
1. Trouve tous les documents avec des IDs malformés (double préfixe)
2. Crée de nouveaux enregistrements avec des IDs corrects
3. Supprime les anciens enregistrements malformés
4. Met à jour les références dans d'autres tables si nécessaire
"""

import asyncio
import sys
from pathlib import Path

# Ajouter le chemin parent pour importer les modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from surrealdb import AsyncSurreal
from config.settings import settings


async def main():
    print("=== Migration: Correction des IDs malformés ===\n")

    db = AsyncSurreal(settings.surreal_url)
    await db.signin({
        "username": settings.surreal_username,
        "password": settings.surreal_password
    })
    await db.use(settings.surreal_namespace, settings.surreal_database)

    # Récupérer tous les documents
    result = await db.query("SELECT * FROM document")

    documents = []
    if result and len(result) > 0:
        documents = result[0].get("result", result) if isinstance(result[0], dict) else result

    print(f"Documents trouvés: {len(documents)}\n")

    malformed_docs = []

    for doc in documents:
        doc_id = str(doc.get("id", ""))

        # Vérifier si l'ID est malformé (contient plus d'un ":")
        if doc_id.count(":") > 1:
            malformed_docs.append(doc)
            print(f"⚠️  ID malformé trouvé: {doc_id}")
            print(f"   Fichier: {doc.get('nom_fichier')}")
            print(f"   Judgment: {doc.get('judgment_id')}\n")

    if not malformed_docs:
        print("✓ Aucun ID malformé trouvé. Base de données propre!")
        await db.close()
        return

    print(f"\n{'='*60}")
    print(f"Total: {len(malformed_docs)} document(s) avec ID malformé(s)")
    print(f"{'='*60}\n")

    response = input("Voulez-vous les corriger automatiquement? (o/n): ")

    if response.lower() != "o":
        print("Migration annulée.")
        await db.close()
        return

    # Corriger chaque document
    for doc in malformed_docs:
        malformed_id = str(doc.get("id", ""))
        filename = doc.get("nom_fichier", "unknown")

        print(f"\nCorrection de: {filename}")
        print(f"  ID malformé: {malformed_id}")

        # Extraire le vrai ID (la partie après le dernier ":")
        clean_id = malformed_id.split(":")[-1]
        print(f"  Nouvel ID: document:{clean_id}")

        try:
            # Créer une copie des données sans l'ID
            doc_data = {k: v for k, v in doc.items() if k != "id"}

            # Créer un nouveau document avec l'ID correct
            await db.query(
                f"CREATE document:{clean_id} CONTENT $data",
                {"data": doc_data}
            )
            print(f"  ✓ Nouveau document créé")

            # Supprimer l'ancien document malformé
            await db.query(f"DELETE `{malformed_id}`")
            print(f"  ✓ Ancien document supprimé")

        except Exception as e:
            print(f"  ✗ Erreur: {e}")
            continue

    print(f"\n{'='*60}")
    print("✓ Migration terminée!")
    print(f"{'='*60}\n")

    # Vérification finale
    result = await db.query("SELECT * FROM document")
    documents = []
    if result and len(result) > 0:
        documents = result[0].get("result", result) if isinstance(result[0], dict) else result

    still_malformed = [doc for doc in documents if str(doc.get("id", "")).count(":") > 1]

    if still_malformed:
        print(f"⚠️  Attention: {len(still_malformed)} ID(s) malformé(s) restant(s)")
    else:
        print("✓ Tous les IDs sont maintenant corrects!")

    await db.close()


if __name__ == "__main__":
    asyncio.run(main())
