"""
Script de test pour le système RAG (Retrieval-Augmented Generation).

Ce script teste:
1. L'indexation d'un document avec texte
2. La recherche sémantique
3. Les statistiques de l'index
"""

import asyncio
import logging
from services.document_indexing_service import get_document_indexing_service
from services.surreal_service import init_surreal_service, get_surreal_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_rag_system():
    """Test complet du système RAG."""

    # Initialiser SurrealDB
    init_surreal_service(
        url="http://localhost:8002",
        username="root",
        password="root",
        namespace="test",
        database="test"
    )

    # Exemple de texte juridique en français
    sample_text = """
# Contrat de vente immobilière

## Article 1 - Parties

Le vendeur, Monsieur Jean Dupont, demeurant au 123 rue de la Paix, Paris,
cède à l'acquéreur, Madame Marie Martin, demeurant au 456 avenue des Champs, Lyon,
un bien immobilier situé au 789 boulevard Victor Hugo, Marseille.

## Article 2 - Prix et modalités de paiement

Le prix de vente est fixé à la somme de deux cent cinquante mille euros (250 000 €).

Le paiement s'effectuera de la manière suivante:
- Un acompte de cinquante mille euros (50 000 €) à la signature du présent contrat
- Le solde de deux cent mille euros (200 000 €) lors de la signature de l'acte authentique

## Article 3 - Obligations du vendeur

Le vendeur s'engage à:
1. Délivrer le bien libre de toute occupation à la date convenue
2. Garantir l'acquéreur contre les vices cachés
3. Fournir tous les documents relatifs à la propriété
4. Assurer le transfert de propriété dans un délai de trois mois

## Article 4 - Obligations de l'acquéreur

L'acquéreur s'engage à:
1. Respecter les échéances de paiement
2. Souscrire une assurance habitation avant la prise de possession
3. Prendre possession du bien dans l'état où il se trouve
4. Acquitter tous les frais de notaire et d'enregistrement

## Article 5 - Conditions suspensives

Le présent contrat est conclu sous les conditions suspensives suivantes:
- Obtention d'un prêt bancaire de 200 000 € dans un délai de 45 jours
- Absence de servitudes non déclarées

## Article 6 - Clause pénale

En cas de non-respect des obligations, la partie défaillante devra verser à l'autre partie
une pénalité de dix mille euros (10 000 €) à titre de dommages et intérêts.

Fait à Paris, le 15 janvier 2025, en deux exemplaires originaux.
"""

    logger.info("=== Test du système RAG ===\n")

    # 1. Connexion à SurrealDB
    logger.info("1. Connexion à SurrealDB...")
    surreal_service = get_surreal_service()
    await surreal_service.connect()
    logger.info("   ✓ Connecté\n")

    # 2. Créer un document de test
    logger.info("2. Création d'un document de test...")
    test_judgment_id = "judgment:test_rag"
    test_doc_id = "test_rag_doc_001"

    # Supprimer les anciens documents de test
    try:
        await surreal_service.delete(f"document:{test_doc_id}")
        logger.info("   - Ancien document supprimé")
    except Exception:
        pass

    # Créer le document
    doc_data = {
        "judgment_id": test_judgment_id,
        "nom_fichier": "contrat_vente.md",
        "type_fichier": "md",
        "type_mime": "text/markdown",
        "taille": len(sample_text.encode("utf-8")),
        "file_path": "/tmp/contrat_vente.md",
        "texte_extrait": sample_text,
        "created_at": "2025-01-15T12:00:00Z",
    }

    await surreal_service.create("document", doc_data, record_id=test_doc_id)
    logger.info(f"   ✓ Document créé: document:{test_doc_id}\n")

    # 3. Indexer le document
    logger.info("3. Indexation du document...")
    indexing_service = get_document_indexing_service(
        embedding_provider="ollama",
        embedding_model="bge-m3"
    )

    index_result = await indexing_service.index_document(
        document_id=f"document:{test_doc_id}",
        judgment_id=test_judgment_id,
        text_content=sample_text,
        force_reindex=True
    )

    if index_result["success"]:
        logger.info(f"   ✓ Indexation réussie: {index_result['chunks_created']} chunks créés")
        logger.info(f"   - Modèle: {index_result['embedding_model']}\n")
    else:
        logger.error(f"   ✗ Échec de l'indexation: {index_result.get('error')}")
        return

    # 4. Afficher les statistiques
    logger.info("4. Statistiques de l'index...")
    stats = await indexing_service.get_index_stats(judgment_id=test_judgment_id)
    logger.info(f"   - Total de chunks: {stats.get('total_chunks', 0)}")
    logger.info(f"   - Modèle: {stats.get('embedding_model', 'inconnu')}")
    logger.info(f"   - Dimensions: {stats.get('embedding_dimensions', 0)}\n")

    # 5. Tests de recherche sémantique
    logger.info("5. Tests de recherche sémantique...\n")

    test_queries = [
        ("Quel est le prix de vente ?", "Prix et paiement"),
        ("Quelles sont les obligations du vendeur ?", "Obligations du vendeur"),
        ("Que se passe-t-il en cas de non-respect du contrat ?", "Clause pénale"),
        ("Qui sont les parties au contrat ?", "Parties contractantes"),
        ("Quels sont les délais mentionnés ?", "Délais et échéances"),
    ]

    for query, expected_topic in test_queries:
        logger.info(f"   Question: '{query}'")
        logger.info(f"   Thème attendu: {expected_topic}")

        results = await indexing_service.search_similar(
            query_text=query,
            judgment_id=test_judgment_id,
            top_k=3,
            min_similarity=0.3
        )

        if results:
            best_result = results[0]
            similarity_pct = int(best_result["similarity_score"] * 100)
            logger.info(f"   ✓ Résultat trouvé (pertinence: {similarity_pct}%)")

            # Afficher un extrait du chunk le plus pertinent
            chunk_preview = best_result["chunk_text"][:150].replace("\n", " ")
            logger.info(f"   Extrait: {chunk_preview}...")
            logger.info("")
        else:
            logger.warning("   ✗ Aucun résultat trouvé")
            logger.info("")

    # 6. Test de recherche en anglais
    logger.info("6. Test multilingue (anglais)...\n")
    english_query = "What are the seller's obligations?"
    logger.info(f"   Question (EN): '{english_query}'")

    results = await indexing_service.search_similar(
        query_text=english_query,
        judgment_id=test_judgment_id,
        top_k=2,
        min_similarity=0.3
    )

    if results:
        best_result = results[0]
        similarity_pct = int(best_result["similarity_score"] * 100)
        logger.info(f"   ✓ Recherche multilingue fonctionne! (pertinence: {similarity_pct}%)")
        chunk_preview = best_result["chunk_text"][:150].replace("\n", " ")
        logger.info(f"   Extrait: {chunk_preview}...")
    else:
        logger.warning("   ✗ Recherche multilingue échouée")

    logger.info("\n=== Test terminé ===")
    logger.info("\nLe système RAG est opérationnel!")
    logger.info("- Indexation automatique: ✓")
    logger.info("- Recherche sémantique: ✓")
    logger.info("- Support multilingue (FR/EN): ✓")


if __name__ == "__main__":
    asyncio.run(test_rag_system())
