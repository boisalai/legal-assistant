"""
Test en live des rubriques CAIJ avec une vraie recherche
"""

import asyncio
import sys
sys.path.insert(0, '/Users/alain/Workspace/GitHub/legal-assistant/backend')

from services.caij_search_service import CAIJSearchService
from models.caij_models import CAIJSearchRequest


async def test_live_rubriques():
    """Tester avec une vraie recherche CAIJ."""
    print("=" * 80)
    print("TEST DES RUBRIQUES CAIJ - RECHERCHE LIVE")
    print("=" * 80)
    print()

    async with CAIJSearchService(headless=True) as service:
        await service.authenticate()
        print("✅ Authentification réussie\n")

        # Recherche avec un terme générique pour avoir des résultats variés
        request = CAIJSearchRequest(query="contrat", max_results=15)
        response = await service.search(request)

        print(f"📚 Résultats pour '{request.query}' ({len(response.results)} résultats)")
        print(f"⏱️  Recherche effectuée en {response.execution_time_seconds}s\n")
        print("=" * 80)

        # Grouper par rubrique
        rubriques_count = {}
        results_by_rubrique = {}

        for result in response.results:
            rubrique = result.rubrique or "Non classé"

            if rubrique not in rubriques_count:
                rubriques_count[rubrique] = 0
                results_by_rubrique[rubrique] = []

            rubriques_count[rubrique] += 1
            results_by_rubrique[rubrique].append(result)

        # Afficher statistiques
        print("\n📊 DISTRIBUTION PAR RUBRIQUE:")
        print("-" * 80)
        for rubrique, count in sorted(rubriques_count.items(), key=lambda x: x[1], reverse=True):
            print(f"  {rubrique:40s} {count:2d} résultats")

        # Afficher détails par rubrique
        print("\n\n📖 DÉTAILS PAR RUBRIQUE:")
        print("=" * 80)

        for rubrique in sorted(results_by_rubrique.keys()):
            results = results_by_rubrique[rubrique]

            print(f"\n[{rubrique}] - {len(results)} résultat(s)")
            print("-" * 80)

            for i, result in enumerate(results, 1):
                print(f"\n  [{i}] {result.title[:70]}")
                print(f"      Type: {result.document_type}")
                print(f"      Source: {result.source[:50]}")
                print(f"      Date: {result.date}")
                print(f"      URL: {result.url[:70]}...")

        print("\n" + "=" * 80)
        print("✅ Test terminé!")
        print("=" * 80)


if __name__ == "__main__":
    asyncio.run(test_live_rubriques())
