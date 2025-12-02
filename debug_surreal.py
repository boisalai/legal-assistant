#!/usr/bin/env python3
"""Script pour déboguer les enregistrements SurrealDB."""

import asyncio
from pathlib import Path
from surrealdb import AsyncSurreal

async def main():
    db = AsyncSurreal("ws://localhost:8002/rpc")
    await db.signin({"username": "root", "password": "root"})

    # Lister tous les namespaces et databases
    print("=== Namespaces et Databases ===")
    try:
        info_result = await db.query("INFO FOR ROOT")
        print(f"Info ROOT: {info_result}\n")
    except Exception as e:
        print(f"Erreur lors de la récupération des infos ROOT: {e}\n")

    # Utiliser le bon namespace/database (celui du backend)
    await db.use("legal", "legal_db")
    print(f"Utilisation de: namespace='legal', database='legal_db'\n")

    # Récupérer TOUS les documents (avec leur ID brut)
    print("=== Tous les documents ===")
    all_docs_result = await db.query("SELECT *, meta::id(id) AS raw_id FROM document")

    if all_docs_result and len(all_docs_result) > 0:
        items = all_docs_result[0].get("result", all_docs_result) if isinstance(all_docs_result[0], dict) else all_docs_result
        print(f"Nombre total de documents: {len(items)}")

        malformed_ids = []

        for i, doc in enumerate(items):
            doc_id = doc.get('id')
            raw_id = doc.get('raw_id')
            judgment_id = doc.get('judgment_id')
            nom_fichier = doc.get('nom_fichier')
            file_path = doc.get('file_path')

            print(f"\n--- Document {i+1} ---")
            print(f"ID: {doc_id}")
            print(f"Raw ID: {raw_id}")
            print(f"Judgment ID: {judgment_id}")
            print(f"Nom fichier: {nom_fichier}")
            print(f"Chemin: {file_path}")

            # Vérifier si l'ID est malformé (double préfixe)
            doc_id_str = str(doc_id)
            if doc_id_str.startswith("document:document:") or doc_id_str.count(":") > 1:
                print(f"⚠️  ID MALFORMÉ détecté!")
                malformed_ids.append((doc_id_str, nom_fichier))

            # Vérifier si le fichier existe
            if file_path:
                exists = Path(file_path).exists()
                print(f"Fichier existe: {exists}")
                if not exists:
                    print(f"⚠️  Fichier physique manquant!")

        # Nettoyer les IDs malformés
        if malformed_ids:
            print(f"\n\n{'='*60}")
            print(f"⚠️  {len(malformed_ids)} document(s) avec ID malformé(s) trouvé(s):")
            for doc_id, filename in malformed_ids:
                print(f"  - {doc_id} ({filename})")

            print(f"\nCes enregistrements doivent être supprimés manuellement.")
            response = input("\nVoulez-vous les supprimer maintenant? (o/n): ")

            if response.lower() == "o":
                for doc_id, filename in malformed_ids:
                    try:
                        # Utiliser une requête DELETE au lieu de db.delete()
                        # car db.delete() ne peut pas gérer les IDs malformés
                        result = await db.query(f"DELETE {doc_id}")
                        print(f"✓ Supprimé: {filename} ({doc_id})")
                    except Exception as e:
                        print(f"✗ Erreur lors de la suppression de {filename}: {e}")
                        # Essayer avec une approche différente
                        try:
                            # Extraire juste l'ID sans le préfixe
                            clean_id = doc_id.split(":")[-1]
                            result = await db.query(
                                "DELETE document WHERE meta::id(id) = $id",
                                {"id": clean_id}
                            )
                            print(f"✓ Supprimé avec méthode alternative: {filename}")
                        except Exception as e2:
                            print(f"✗ Échec complet: {e2}")

                print(f"\n✓ Nettoyage terminé")
    else:
        print("Aucun document trouvé dans la base de données")

    await db.close()

if __name__ == "__main__":
    asyncio.run(main())
