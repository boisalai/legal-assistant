"""
Tests d'intégration pour le service CAIJ

Tests complets du workflow :
1. Initialisation du service
2. Authentification
3. Recherche
4. Extraction de résultats
5. Rate limiting
"""

import asyncio
import pytest
from services.caij_search_service import CAIJSearchService
from models.caij_models import CAIJSearchRequest
from tools.caij_search_tool import search_caij_jurisprudence


@pytest.mark.asyncio
async def test_caij_service_initialization():
    """Test d'initialisation du service CAIJ."""
    async with CAIJSearchService(headless=True) as service:
        assert service.browser is not None
        assert service.page is not None
        print("✅ Service initialisé correctement")


@pytest.mark.asyncio
async def test_caij_authentication():
    """Test d'authentification CAIJ."""
    async with CAIJSearchService(headless=True) as service:
        await service.authenticate()
        assert service.authenticated is True
        print("✅ Authentification réussie")


@pytest.mark.asyncio
async def test_caij_search_basic():
    """Test de recherche basique."""
    async with CAIJSearchService(headless=True) as service:
        await service.authenticate()

        request = CAIJSearchRequest(query="mariage", max_results=5)
        response = await service.search(request)

        assert response is not None
        assert response.query == "mariage"
        assert len(response.results) > 0
        assert len(response.results) <= 5
        assert response.execution_time_seconds is not None

        # Vérifier qu'au moins un résultat a toutes les données
        first_result = response.results[0]
        assert first_result.title != "N/A"
        assert first_result.url != "N/A"
        assert first_result.document_type != "N/A"

        print(f"✅ Recherche réussie: {len(response.results)} résultats en {response.execution_time_seconds}s")


@pytest.mark.asyncio
async def test_caij_multiple_searches():
    """Test de recherches multiples (rate limiting)."""
    async with CAIJSearchService(headless=True) as service:
        await service.authenticate()

        queries = ["mariage", "responsabilité civile", "bail commercial"]

        for query in queries:
            request = CAIJSearchRequest(query=query, max_results=3)
            response = await service.search(request)

            assert response is not None
            assert len(response.results) > 0

            print(f"✅ Recherche '{query}': {len(response.results)} résultats")


@pytest.mark.asyncio
async def test_caij_tool_integration():
    """Test d'intégration du tool Agno."""
    result = await search_caij_jurisprudence("contrat de travail", max_results=3)

    assert result is not None
    assert isinstance(result, str)
    assert "contrat de travail" in result.lower()
    assert "Type:" in result
    assert "URL:" in result

    print(f"✅ Tool Agno fonctionnel")
    print(f"\n{result}")


@pytest.mark.asyncio
async def test_caij_invalid_query():
    """Test avec requête invalide."""
    result = await search_caij_jurisprudence("", max_results=5)

    assert "Erreur" in result
    print("✅ Gestion d'erreur fonctionnelle")


async def main():
    """Exécuter tous les tests manuellement."""
    print("=" * 80)
    print("TESTS D'INTÉGRATION CAIJ")
    print("=" * 80)
    print()

    tests = [
        ("Initialisation du service", test_caij_service_initialization),
        ("Authentification", test_caij_authentication),
        ("Recherche basique", test_caij_search_basic),
        ("Recherches multiples", test_caij_multiple_searches),
        ("Tool Agno", test_caij_tool_integration),
        ("Gestion d'erreur", test_caij_invalid_query),
    ]

    results = []

    for test_name, test_func in tests:
        print(f"\n🧪 Test: {test_name}")
        print("-" * 80)

        try:
            await test_func()
            results.append((test_name, "✅ PASS"))
        except Exception as e:
            results.append((test_name, f"❌ FAIL: {e}"))
            print(f"❌ ÉCHEC: {e}")

        print()

    # Résumé
    print("=" * 80)
    print("RÉSUMÉ DES TESTS")
    print("=" * 80)

    for test_name, status in results:
        print(f"{status:60s} {test_name}")

    passed = sum(1 for _, status in results if "PASS" in status)
    total = len(results)

    print()
    print(f"Résultats: {passed}/{total} tests passés ({passed/total*100:.1f}%)")


if __name__ == "__main__":
    asyncio.run(main())
