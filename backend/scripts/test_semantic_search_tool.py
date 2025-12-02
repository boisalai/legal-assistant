#!/usr/bin/env python3
"""Script to test the semantic_search tool directly."""

import sys
import asyncio
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

sys.path.insert(0, "/Users/alain/Workspace/GitHub/legal-assistant/backend")

from services.surreal_service import init_surreal_service
from tools.semantic_search_tool import semantic_search


async def main():
    # Initialize SurrealDB
    init_surreal_service(
        url="http://localhost:8002",
        namespace="legal",
        database="legal_db",
        username="root",
        password="root"
    )

    print("=" * 80)
    print("Testing semantic_search tool")
    print("=" * 80)

    # Test the tool (using entrypoint because it's an Agno Function)
    result = await semantic_search.entrypoint(
        case_id="c9d207fc",
        query="Qu'est-ce que le droit?",
        top_k=3
    )

    print("\nResult:")
    print(result)


if __name__ == "__main__":
    asyncio.run(main())
