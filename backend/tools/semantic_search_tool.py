"""
Semantic search tool for the Agno agent.

This tool allows the AI agent to perform semantic (vector similarity) search
through documents in a case using natural language queries.
"""

import logging
from typing import Optional

from agno.tools import tool

from services.document_indexing_service import get_document_indexing_service
from services.surreal_service import get_surreal_service

logger = logging.getLogger(__name__)


@tool(name="semantic_search")
async def semantic_search(
    case_id: str,
    query: str,
    top_k: int = 5
) -> str:
    """
    Recherche sémantique dans les documents d'un dossier.

    ⚠️ OUTIL PRINCIPAL: Utilisez cet outil pour TOUTE question de l'utilisateur.
    Cet outil utilise l'IA pour comprendre le sens de la question et trouve les passages pertinents dans les documents.

    **RÈGLE ABSOLUE**: TOUJOURS utiliser cet outil en premier pour répondre aux questions, qu'elles soient générales ou spécifiques.

    Exemples de questions à traiter avec cet outil:
    - "Qu'est-ce que le notariat ?" → Cherche dans les documents si le sujet est abordé
    - "Quel est le prix mentionné dans ce contrat ?" → Cherche les informations de prix
    - "Explique-moi les obligations du vendeur" → Cherche les passages sur les obligations
    - "Résume ce document" → Cherche les points clés dans le document
    - "Comment fonctionne X ?" → Cherche les explications sur X dans les documents

    Si la recherche ne trouve rien de pertinent, vous DEVEZ informer l'utilisateur que l'information
    n'est pas disponible dans les documents du dossier.

    DIFFÉRENCE avec search_documents:
    - search_documents: Recherche de mots-clés exacts (ex: "signature")
    - semantic_search: Comprend le sens de la question (ex: "quelles sont les obligations du vendeur ?")

    Args:
        case_id: L'identifiant du dossier (ex: "1f9fc70e" ou "judgment:1f9fc70e")
        query: La question de l'utilisateur (ex: "qu'est-ce que le notariat ?")
        top_k: Nombre de passages pertinents à retourner (défaut: 5)

    Returns:
        Les passages les plus pertinents avec leur score de pertinence
    """
    try:
        logger.info(f"[semantic_search] START - case_id={case_id}, query={query[:50]}...")

        # Obtenir le service d'indexation
        indexing_service = get_document_indexing_service()
        logger.info(f"[semantic_search] Got indexing service: {indexing_service}")

        # Normaliser case_id
        case_id = case_id
        if not case_id.startswith("case:"):
            case_id = f"judgment:{case_id}"

        logger.info(f"[semantic_search] Normalized case_id: {case_id}")

        # Vérifier si des documents sont indexés
        logger.info(f"[semantic_search] Getting index stats for {case_id}...")
        stats = await indexing_service.get_index_stats(case_id=case_id)
        logger.info(f"[semantic_search] Stats: {stats}")

        if stats.get("total_chunks", 0) == 0:
            return """Les documents de ce dossier ne sont pas encore indexés pour la recherche sémantique.

Pour utiliser la recherche sémantique:
1. Les documents avec du texte extrait sont automatiquement indexés lors de l'upload
2. Vous pouvez utiliser l'outil `index_document_tool` pour indexer manuellement un document

En attendant, je ne peux pas répondre à votre question car je n'ai pas accès au contenu des documents."""

        # Effectuer la recherche sémantique
        logger.info(f"[semantic_search] Searching with query='{query}', top_k={top_k}...")
        results = await indexing_service.search_similar(
            query_text=query,
            case_id=case_id,
            top_k=top_k,
            min_similarity=0.5  # Score minimum de similarité
        )
        logger.info(f"[semantic_search] Found {len(results)} results")

        if not results:
            return f"""Je n'ai pas trouvé d'information pertinente sur "{query}" dans les documents du dossier.

Cela peut signifier que:
- Les documents ne contiennent pas d'informations sur ce sujet
- Le score de similarité est trop faible (< 50%)

Vous pouvez:
- Reformuler votre question de manière différente
- Vérifier si les documents du dossier traitent bien de ce sujet"""

        # Récupérer les informations des documents sources
        logger.info(f"[semantic_search] Getting surreal service...")
        surreal_service = get_surreal_service()
        logger.info(f"[semantic_search] Surreal service DB connected: {surreal_service.db is not None}")

        if not surreal_service.db:
            logger.info(f"[semantic_search] Connecting to SurrealDB...")
            await surreal_service.connect()

        # Construire une map document_id -> nom_fichier
        doc_ids = list(set([r["document_id"] for r in results]))
        logger.info(f"[semantic_search] Fetching names for {len(doc_ids)} unique documents...")
        doc_names = {}

        for doc_id in doc_ids:
            # Use type::thing() to properly handle UUIDs with dashes
            doc_result = await surreal_service.query(
                "SELECT nom_fichier FROM type::thing($table, $id)",
                {"table": "document", "id": doc_id.replace("document:", "")}
            )
            if doc_result and len(doc_result) > 0:
                first_item = doc_result[0]
                if isinstance(first_item, dict):
                    if "result" in first_item and first_item["result"]:
                        doc_names[doc_id] = first_item["result"][0].get("nom_fichier", doc_id)
                    else:
                        doc_names[doc_id] = first_item.get("nom_fichier", doc_id)
                else:
                    doc_names[doc_id] = doc_id

        # Formater la réponse
        response = f'J\'ai trouvé **{len(results)} passages pertinents** pour la question: "{query}"\n\n'

        for idx, result in enumerate(results, 1):
            doc_id = result["document_id"]
            doc_name = doc_names.get(doc_id, "Document inconnu")
            chunk_text = result["chunk_text"]
            similarity = result["similarity_score"]

            # Convertir le score en pourcentage
            similarity_pct = int(similarity * 100)

            response += f"### Résultat {idx}: {doc_name} (Pertinence: {similarity_pct}%)\n"
            response += f"{chunk_text}\n\n"
            response += "---\n\n"

        # Ajouter une note explicative
        response += f"""*Note: La recherche sémantique utilise l'intelligence artificielle pour comprendre le sens de votre question.*
*Les passages sont classés par ordre de pertinence (similarité vectorielle).*
*Modèle utilisé: {stats.get('embedding_model', 'inconnu')}*"""

        return response.strip()

    except Exception as e:
        logger.error(f"Semantic search error: {e}", exc_info=True)
        return f"Erreur lors de la recherche sémantique: {str(e)}"


@tool(name="index_document")
async def index_document_tool(
    case_id: str,
    document_name: str
) -> str:
    """
    Indexe un document pour la recherche sémantique.

    Cet outil permet d'indexer manuellement un document si l'indexation automatique
    n'a pas fonctionné ou si vous voulez forcer la réindexation.

    Args:
        case_id: L'identifiant du dossier
        document_name: Nom du fichier à indexer

    Returns:
        Résultat de l'indexation
    """
    try:
        # Normaliser case_id
        case_id = case_id
        if not case_id.startswith("case:"):
            case_id = f"judgment:{case_id}"

        # Récupérer le document
        surreal_service = get_surreal_service()
        if not surreal_service.db:
            await surreal_service.connect()

        doc_result = await surreal_service.query(
            "SELECT * FROM document WHERE case_id = $case_id AND nom_fichier = $nom_fichier",
            {"case_id": case_id, "nom_fichier": document_name}
        )

        documents = []
        if doc_result and len(doc_result) > 0:
            first_item = doc_result[0]
            if isinstance(first_item, dict) and "result" in first_item:
                documents = first_item["result"] if isinstance(first_item["result"], list) else []
            elif isinstance(first_item, list):
                documents = first_item
            elif isinstance(first_item, dict):
                documents = doc_result

        if not documents:
            return f"Document '{document_name}' non trouvé dans le dossier {case_id}."

        document = documents[0]
        doc_id = document.get("id")
        texte_extrait = document.get("texte_extrait", "")

        if not texte_extrait:
            return f"Le document '{document_name}' n'a pas de texte extrait. L'indexation nécessite du contenu textuel."

        # Indexer le document
        indexing_service = get_document_indexing_service()
        result = await indexing_service.index_document(
            document_id=doc_id,
            case_id=case_id,
            text_content=texte_extrait,
            force_reindex=True  # Forcer la réindexation
        )

        if result["success"]:
            chunks_created = result.get("chunks_created", 0)
            embedding_model = result.get("embedding_model", "inconnu")
            return f"✅ Document '{document_name}' indexé avec succès!\n\n- {chunks_created} segments créés\n- Modèle: {embedding_model}\n\nLe document est maintenant disponible pour la recherche sémantique."
        else:
            error = result.get("error", "Erreur inconnue")
            return f"❌ Échec de l'indexation: {error}"

    except Exception as e:
        logger.error(f"Index document error: {e}", exc_info=True)
        return f"Erreur lors de l'indexation du document: {str(e)}"


@tool(name="get_index_stats")
async def get_index_stats(case_id: str) -> str:
    """
    Affiche les statistiques de l'index de recherche sémantique pour un dossier.

    Args:
        case_id: L'identifiant du dossier

    Returns:
        Statistiques de l'index
    """
    try:
        # Normaliser case_id
        case_id = case_id
        if not case_id.startswith("case:"):
            case_id = f"judgment:{case_id}"

        indexing_service = get_document_indexing_service()
        stats = await indexing_service.get_index_stats(case_id=case_id)

        if "error" in stats:
            return f"Erreur lors de la récupération des statistiques: {stats['error']}"

        total_chunks = stats.get("total_chunks", 0)
        embedding_model = stats.get("embedding_model", "inconnu")
        embedding_dimensions = stats.get("embedding_dimensions", 0)

        if total_chunks == 0:
            return f"""**Index de recherche sémantique pour le dossier {case_id}:**

📊 **Statut:** Aucun document indexé

Pour indexer des documents:
1. Les documents avec du texte extrait sont automatiquement indexés lors de l'upload
2. Utilisez l'outil `index_document` pour indexer manuellement un document spécifique"""

        return f"""**Index de recherche sémantique pour le dossier {case_id}:**

📊 **Statistiques:**
- Segments indexés: {total_chunks}
- Modèle d'embeddings: {embedding_model}
- Dimensions: {embedding_dimensions}

✅ La recherche sémantique est disponible pour ce dossier!
Utilisez `semantic_search` pour poser des questions en langage naturel."""

    except Exception as e:
        logger.error(f"Get index stats error: {e}", exc_info=True)
        return f"Erreur lors de la récupération des statistiques: {str(e)}"
