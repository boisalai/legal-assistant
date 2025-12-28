"""
Tool Agno pour recherche de jurisprudence sur CAIJ

Permet aux agents conversationnels d'accéder à la jurisprudence québécoise.
"""

from agno.tools import tool
from typing import Optional
import asyncio

from services.caij_search_service import CAIJSearchService
from models.caij_models import CAIJSearchRequest


# Instance globale du service (réutilisation de session)
_caij_service: Optional[CAIJSearchService] = None


async def get_caij_service() -> CAIJSearchService:
    """Obtenir ou créer l'instance du service CAIJ."""
    global _caij_service

    if _caij_service is None:
        _caij_service = CAIJSearchService(headless=True)
        await _caij_service.initialize()
        await _caij_service.authenticate()

    return _caij_service


async def _search_caij_implementation(query: str, max_results: int = 10) -> str:
    """
    Internal implementation for CAIJ search (used by both tool and tests).

    Args:
        query: Search terms
        max_results: Maximum number of results (1-20)

    Returns:
        Formatted search results
    """
    try:
        # Valider paramètres
        if not query or len(query.strip()) < 2:
            return "❌ Erreur: La requête doit contenir au moins 2 caractères."

        if max_results < 1 or max_results > 20:
            max_results = min(max(max_results, 1), 20)

        # Obtenir le service
        service = await get_caij_service()

        # Effectuer la recherche
        request = CAIJSearchRequest(query=query.strip(), max_results=max_results)
        response = await service.search(request)

        # Formater les résultats pour l'agent
        if not response.results:
            return f"Aucun résultat trouvé pour '{query}' sur CAIJ."

        output = [
            f"📚 Résultats CAIJ pour '{query}' ({response.total_found} résultats):\n"
        ]

        for i, result in enumerate(response.results, 1):
            output.append(f"\n[{i}] {result.title}")
            output.append(f"    Rubrique: {result.rubrique}")
            output.append(f"    Type: {result.document_type}")
            output.append(f"    Source: {result.source}")
            output.append(f"    Date: {result.date}")
            output.append(f"    URL: {result.url}")

            # Extrait (limité pour lisibilité)
            excerpt = result.excerpt[:200] + "..." if len(result.excerpt) > 200 else result.excerpt
            output.append(f"    Résumé: {excerpt}")

        output.append(f"\n⏱️  Recherche effectuée en {response.execution_time_seconds}s")

        return "\n".join(output)

    except Exception as e:
        return f"❌ Erreur lors de la recherche CAIJ: {str(e)}"


@tool
async def search_caij_jurisprudence(
    query: str,
    max_results: int = 10
) -> str:
    """
    Rechercher de la jurisprudence québécoise sur CAIJ.

    Utilise le Centre d'accès à l'information juridique du Québec (CAIJ) pour
    rechercher des jugements, doctrine, lois annotées et autres ressources juridiques.

    Args:
        query: Termes de recherche (ex: "responsabilité civile", "mariage", "bail commercial")
        max_results: Nombre maximum de résultats à retourner (1-20, défaut: 10)

    Returns:
        Résultats formatés avec titre, type, source, date, URL et extrait pour chaque document trouvé.

    Examples:
        >>> await search_caij_jurisprudence("nullité de mariage")
        >>> await search_caij_jurisprudence("contrat de travail", max_results=5)
    """
    return await _search_caij_implementation(query, max_results)


@tool
async def get_caij_document_url(title: str) -> str:
    """
    Obtenir l'URL complète d'un document CAIJ à partir de son titre.

    Utile lorsque l'agent veut fournir un lien direct vers un jugement ou une ressource.

    Args:
        title: Titre du document (doit correspondre à un résultat de recherche récent)

    Returns:
        URL complète du document sur CAIJ ou message d'erreur.

    Examples:
        >>> await get_caij_document_url("Mariage")
    """
    try:
        # Cette fonction nécessiterait de stocker les derniers résultats
        # Pour l'instant, on suggère de faire une nouvelle recherche
        return (
            f"Pour obtenir l'URL du document '{title}', veuillez d'abord effectuer "
            f"une recherche avec search_caij_jurisprudence('{title}')."
        )

    except Exception as e:
        return f"❌ Erreur: {str(e)}"


# Fonction de nettoyage pour fermer le service à la fin
async def cleanup_caij_service():
    """Fermer le service CAIJ (à appeler au shutdown)."""
    global _caij_service

    if _caij_service is not None:
        await _caij_service.close()
        _caij_service = None
