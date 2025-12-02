#!/usr/bin/env python3
"""Script pour vérifier l'état des documents dérivés."""

import asyncio
import sys
from pathlib import Path

# Ajouter le dossier backend au PYTHONPATH
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from services.surreal_service import SurrealDBService

db = SurrealDBService()

async def check_derived_docs():
    """Vérifier l'état des documents dans la base."""

    # Récupérer tous les documents du dossier c9d207fc
    query = """
        SELECT id, nom, type_fichier, source_document_id, is_derived, derivation_type
        FROM document
        WHERE judgment_id = 'c9d207fc'
        ORDER BY created_at DESC
    """

    docs = await db.query(query)

    print("\n=== Documents dans le dossier c9d207fc ===\n")
    for doc in docs:
        print(f"ID: {doc['id']}")
        print(f"  Nom: {doc['nom']}")
        print(f"  Type: {doc['type_fichier']}")
        print(f"  Source: {doc.get('source_document_id', 'None')}")
        print(f"  Is Derived: {doc.get('is_derived', 'None')}")
        print(f"  Derivation Type: {doc.get('derivation_type', 'None')}")
        print()

    # Tester spécifiquement la requête pour a2ee226c
    query_derived = """
        SELECT * FROM document
        WHERE source_document_id = 'a2ee226c'
    """

    derived = await db.query(query_derived)

    print("\n=== Fichiers dérivés de a2ee226c ===\n")
    if derived:
        for doc in derived:
            print(f"ID: {doc['id']}")
            print(f"  Nom: {doc['nom']}")
            print(f"  Type: {doc.get('derivation_type', 'None')}")
            print()
    else:
        print("Aucun fichier dérivé trouvé!\n")

if __name__ == "__main__":
    asyncio.run(check_derived_docs())
