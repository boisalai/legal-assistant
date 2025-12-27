#!/usr/bin/env python3
"""
Script d'urgence pour nettoyer les null bytes dans la base de données.

Problème: Un ou plusieurs documents contiennent des null bytes (\x00) dans
leur champ texte_extrait, ce qui empêche SurrealDB de sérialiser les requêtes.

Solution: Parcourir tous les documents et nettoyer les null bytes.
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.surreal_service import SurrealDBService


async def fix_null_bytes():
    """Fix all documents with null bytes in texte_extrait."""

    # Create and connect to surreal service
    surreal_service = SurrealDBService(
        url="ws://localhost:8002/rpc",
        namespace="legal_assistant",
        database="legal_assistant"
    )
    await surreal_service.connect()

    print("🔍 Searching for documents with null bytes...")

    # Try using select_all to get all document IDs
    try:
        all_docs = await surreal_service.select_all("document")
        print(f"📄 Found {len(all_docs)} documents total")

        # Extract IDs
        document_ids = [doc["id"] for doc in all_docs if "id" in doc]
    except Exception as e:
        print(f"❌ Failed to get documents with select_all: {e}")
        print("⚠️  The database might be corrupted with null bytes.")
        print("   Trying alternative approach...")

        # Alternative: Try to query the database schema to find document table records
        try:
            # Use INFO FOR TABLE to get count without pulling data
            result = await surreal_service.db.query("INFO FOR TABLE document")
            print(f"DEBUG: INFO result = {result}")
        except Exception as e2:
            print(f"❌ Alternative approach also failed: {e2}")
            return

        # If we can't get documents, we're stuck
        return

    fixed_count = 0
    error_count = 0

    # Process each document individually
    for doc_id in document_ids:
        try:
            # Try to get the document
            result = await surreal_service.query(
                "SELECT * FROM $doc_id",
                {"doc_id": doc_id}
            )

            if not result or not result[0]["result"]:
                continue

            doc = result[0]["result"][0]
            texte_extrait = doc.get("texte_extrait")

            if texte_extrait and "\x00" in texte_extrait:
                # Clean null bytes
                cleaned_text = texte_extrait.replace("\x00", "")

                # Update document
                await surreal_service.query(
                    "UPDATE $doc_id SET texte_extrait = $text",
                    {"doc_id": doc_id, "text": cleaned_text}
                )

                print(f"✅ Fixed {doc_id}: Removed {texte_extrait.count(chr(0))} null bytes")
                fixed_count += 1

        except Exception as e:
            # Document probably contains null bytes
            print(f"⚠️  Error processing {doc_id}: {e}")

            # Try to fix by setting texte_extrait to None
            try:
                await surreal_service.query(
                    "UPDATE $doc_id SET texte_extrait = NONE",
                    {"doc_id": doc_id}
                )
                print(f"✅ Fixed {doc_id}: Cleared texte_extrait field")
                fixed_count += 1
            except Exception as e2:
                print(f"❌ Failed to fix {doc_id}: {e2}")
                error_count += 1

    print(f"\n📊 Summary:")
    print(f"   ✅ Fixed: {fixed_count} documents")
    print(f"   ❌ Errors: {error_count} documents")
    print(f"   📄 Total: {len(document_ids)} documents")

    # Fermer la connexion pour flush les changements
    await surreal_service.disconnect()


if __name__ == "__main__":
    print("🚑 Emergency fix: Cleaning null bytes from database")
    print("=" * 60)
    asyncio.run(fix_null_bytes())
    print("=" * 60)
    print("✅ Done! Try reloading your documents now.")
