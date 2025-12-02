#!/usr/bin/env python3
"""Script to test document indexing."""

import sys
import asyncio
sys.path.insert(0, "/Users/alain/Workspace/GitHub/legal-assistant/backend")

from services.document_indexing_service import get_document_indexing_service
from services.surreal_service import get_surreal_service


async def main():
    # Initialize and connect to SurrealDB
    from services.surreal_service import init_surreal_service
    init_surreal_service(
        url="http://localhost:8002",
        namespace="legal",
        database="legal_db",
        username="root",
        password="root"
    )
    surreal = get_surreal_service()
    await surreal.connect()

    # Get the indexing service
    indexing_service = get_document_indexing_service()

    # Document info
    document_id = "document:637d6a2c-5de1-4080-ab05-39e247eaffdb"
    judgment_id = "judgment:c9d207fc"

    # Read the document text
    text_path = "/Users/alain/Workspace/GitHub/legal-assistant/backend/data/uploads/c9d207fc/DRT1151_M1_Notes de cours.md"
    with open(text_path, "r", encoding="utf-8") as f:
        text_content = f.read()

    print(f"Document size: {len(text_content)} characters")
    print(f"Indexing document: {document_id}")

    # Index the document
    result = await indexing_service.index_document(
        document_id=document_id,
        judgment_id=judgment_id,
        text_content=text_content,
        force_reindex=True
    )

    print(f"\nIndexing result:")
    print(f"  Success: {result['success']}")
    if result['success']:
        print(f"  Chunks created: {result['chunks_created']}")
        print(f"  Model: {result['embedding_model']}")
        print(f"  Dimensions: {result.get('embedding_dimensions', 'N/A')}")
    else:
        print(f"  Error: {result.get('error')}")

    # Test search
    if result['success']:
        print(f"\nTesting semantic search...")
        search_results = await indexing_service.search_similar(
            query_text="Qu'est-ce que le droit?",
            judgment_id=judgment_id,
            top_k=3,
            min_similarity=0.5
        )

        print(f"  Found {len(search_results)} results")
        for idx, res in enumerate(search_results, 1):
            print(f"\n  Result {idx}:")
            print(f"    Similarity: {res['similarity_score']:.2%}")
            print(f"    Text: {res['chunk_text'][:100]}...")


if __name__ == "__main__":
    asyncio.run(main())
