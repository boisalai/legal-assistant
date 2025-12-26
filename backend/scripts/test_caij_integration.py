"""
Test d'intégration CAIJ - Sans pytest

Script simple pour valider le service CAIJ complet.
"""

import asyncio
import sys
sys.path.insert(0, '/Users/alain/Workspace/GitHub/legal-assistant/backend')

from services.caij_search_service import CAIJSearchService
from models.caij_models import CAIJSearchRequest
from tools.caij_search_tool import search_caij_jurisprudence


async def test_service_search():
    """Test du service de recherche."""
    print("\n🧪 Test: Service de recherche CAIJ")
    print("-" * 80)

    async with CAIJSearchService(headless=False) as service:
        # Auth
        await service.authenticate()
        print("✅ Authentification réussie")

        # Recherche
        request = CAIJSearchRequest(query="mariage", max_results=5)
        response = await service.search(request)

        print(f"✅ Recherche réussie: {len(response.results)} résultats en {response.execution_time_seconds}s")

        # Afficher résultats
        for i, result in enumerate(response.results[:3], 1):
            print(f"\n[{i}] {result.title}")
            print(f"    Type: {result.document_type}")
            print(f"    Source: {result.source}")
            print(f"    Date: {result.date}")
            print(f"    URL: {result.url}")


async def test_tool():
    """Test du tool Agno."""
    print("\n\n🧪 Test: Tool Agno search_caij_jurisprudence")
    print("-" * 80)

    result = await search_caij_jurisprudence("responsabilité civile", max_results=3)

    print(result)
    print("\n✅ Tool Agno fonctionnel")


async def main():
    """Exécuter les tests."""
    print("=" * 80)
    print("TESTS D'INTÉGRATION CAIJ")
    print("=" * 80)

    try:
        await test_service_search()
        await test_tool()

        print("\n" + "=" * 80)
        print("✅ TOUS LES TESTS PASSÉS")
        print("=" * 80)

    except Exception as e:
        print(f"\n❌ ERREUR: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
