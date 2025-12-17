"""
Service d'indexation des documents pour la recherche sémantique.

Ce service gère:
- Le chunking intelligent des documents
- La génération d'embeddings vectoriels
- Le stockage des embeddings dans SurrealDB
- La recherche par similarité vectorielle
"""

import logging
import asyncio
from typing import Optional, List
from datetime import datetime

from services.embedding_service import get_embedding_service, EmbeddingResult
from services.surreal_service import get_surreal_service

logger = logging.getLogger(__name__)


class DocumentIndexingService:
    """
    Service d'indexation des documents avec embeddings vectoriels.

    Utilise un modèle d'embeddings multilingue (FR/EN) pour supporter
    les documents juridiques en français et en anglais.
    """

    def __init__(
        self,
        embedding_provider: str = "local",
        embedding_model: str = "BAAI/bge-m3",
        chunk_size: int = 400,
        chunk_overlap: int = 50
    ):
        """
        Initialise le service d'indexation.

        Args:
            embedding_provider: Provider d'embeddings (local, ollama, openai)
            embedding_model: Modèle d'embeddings (BAAI/bge-m3 recommandé pour FR/EN)
            chunk_size: Taille des chunks en mots (réduit à 400 pour plus de robustesse)
            chunk_overlap: Chevauchement entre chunks en mots
        """
        self.embedding_service = get_embedding_service(
            provider=embedding_provider,
            model=embedding_model
        )
        self.surreal_service = get_surreal_service()
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    async def index_document(
        self,
        document_id: str,
        case_id: str,
        text_content: str,
        force_reindex: bool = False
    ) -> dict:
        """
        Indexe un document en générant ses embeddings.

        Args:
            document_id: ID du document (ex: "document:abc123")
            case_id: ID du cours (ex: "course:xyz")
            text_content: Contenu textuel à indexer
            force_reindex: Si True, supprime les embeddings existants avant de réindexer

        Returns:
            Dict avec success, chunks_created, et error (si applicable)
        """
        try:
            # Normaliser les IDs
            if not document_id.startswith("document:"):
                document_id = f"document:{document_id}"
            if not case_id.startswith("case:"):
                case_id = f"case:{case_id}"

            logger.info(f"Indexing document {document_id} with {len(text_content)} chars")

            # Vérifier si déjà indexé
            if not force_reindex:
                existing = await self._get_document_embeddings(document_id)
                if existing:
                    logger.info(f"Document {document_id} already indexed with {len(existing)} chunks")
                    return {
                        "success": True,
                        "already_indexed": True,
                        "chunks_count": len(existing)
                    }
            else:
                # Supprimer les embeddings existants
                await self._delete_document_embeddings(document_id)

            # Découper le texte en chunks
            chunk_result = self.embedding_service.chunk_text(
                text_content,
                chunk_size=self.chunk_size,
                overlap=self.chunk_overlap
            )

            if not chunk_result.chunks:
                return {
                    "success": False,
                    "error": "Aucun chunk généré à partir du texte"
                }

            logger.info(f"Generated {len(chunk_result.chunks)} chunks")

            # Générer les embeddings pour chaque chunk
            chunks_created = 0
            max_retries = 3
            retry_delay = 2.0  # seconds

            for idx, chunk_text in enumerate(chunk_result.chunks):
                # Retry loop for each chunk
                retry_count = 0
                embedding_success = False

                while retry_count < max_retries and not embedding_success:
                    try:
                        embedding_result = await self.embedding_service.generate_embedding(chunk_text)

                        if not embedding_result.success:
                            logger.warning(f"Failed to generate embedding for chunk {idx} (attempt {retry_count + 1}/{max_retries}): {embedding_result.error}")
                            retry_count += 1
                            if retry_count < max_retries:
                                await asyncio.sleep(retry_delay)
                            continue

                        # Stocker l'embedding dans SurrealDB
                        await self._store_embedding(
                            document_id=document_id,
                            case_id=case_id,
                            chunk_index=idx,
                            chunk_text=chunk_text,
                            embedding=embedding_result.embedding,
                            embedding_model=embedding_result.model,
                            embedding_dimensions=embedding_result.dimensions
                        )

                        chunks_created += 1
                        embedding_success = True

                    except Exception as e:
                        logger.warning(f"Exception generating embedding for chunk {idx} (attempt {retry_count + 1}/{max_retries}): {e}")
                        retry_count += 1
                        if retry_count < max_retries:
                            await asyncio.sleep(retry_delay)

                if not embedding_success:
                    logger.error(f"Failed to generate embedding for chunk {idx} after {max_retries} attempts - skipping")

            logger.info(f"Indexed document {document_id}: {chunks_created} chunks created")

            return {
                "success": True,
                "chunks_created": chunks_created,
                "total_chunks": len(chunk_result.chunks),
                "embedding_model": self.embedding_service.model
            }

        except Exception as e:
            logger.error(f"Error indexing document {document_id}: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }

    async def _store_embedding(
        self,
        document_id: str,
        case_id: str,
        chunk_index: int,
        chunk_text: str,
        embedding: List[float],
        embedding_model: str,
        embedding_dimensions: int
    ):
        """Stocke un embedding dans SurrealDB."""
        if not self.surreal_service.db:
            await self.surreal_service.connect()

        word_count = len(chunk_text.split())

        # Utiliser le format datetime SurrealDB: d"ISO8601"
        # Format: d"2025-01-15T12:00:00.000Z"
        now = datetime.utcnow()
        surreal_datetime = now.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"

        # Utiliser une requête SQL avec des paramètres
        query = """
        CREATE document_embedding CONTENT {{
            document_id: $document_id,
            case_id: $case_id,
            chunk_index: $chunk_index,
            chunk_text: $chunk_text,
            embedding: $embedding,
            embedding_model: $embedding_model,
            embedding_dimensions: $embedding_dimensions,
            word_count: $word_count,
            created_at: $created_at
        }}
        """

        params = {
            "document_id": document_id,
            "case_id": case_id,
            "chunk_index": chunk_index,
            "chunk_text": chunk_text,
            "embedding": embedding,
            "embedding_model": embedding_model,
            "embedding_dimensions": embedding_dimensions,
            "word_count": word_count,
            "created_at": surreal_datetime
        }

        result = await self.surreal_service.query(query, params)
        logger.info(f"Stored embedding: {len(embedding)} dimensions")

    async def _get_document_embeddings(self, document_id: str) -> List[dict]:
        """Récupère les embeddings existants d'un document."""
        if not self.surreal_service.db:
            await self.surreal_service.connect()

        result = await self.surreal_service.query(
            "SELECT * FROM document_embedding WHERE document_id = $document_id ORDER BY chunk_index",
            {"document_id": document_id}
        )

        if result and len(result) > 0:
            first_item = result[0]
            if isinstance(first_item, dict) and "result" in first_item:
                return first_item["result"] if isinstance(first_item["result"], list) else []
            elif isinstance(first_item, list):
                return first_item
            elif isinstance(first_item, dict) and ("id" in first_item or "chunk_text" in first_item):
                return result

        return []

    async def _delete_document_embeddings(self, document_id: str):
        """Supprime tous les embeddings d'un document."""
        if not self.surreal_service.db:
            await self.surreal_service.connect()

        await self.surreal_service.query(
            "DELETE document_embedding WHERE document_id = $document_id",
            {"document_id": document_id}
        )

    async def search_similar(
        self,
        query_text: str,
        case_id: Optional[str] = None,
        top_k: int = 5,
        min_similarity: float = 0.5
    ) -> List[dict]:
        """
        Recherche les chunks les plus similaires à une requête.

        Utilise l'opérateur vectoriel natif de SurrealDB <|k,COSINE|> pour
        une recherche optimisée par similarité cosinus.

        Args:
            query_text: Texte de la requête
            case_id: Optionnel, limiter la recherche à un cours
            top_k: Nombre maximum de résultats
            min_similarity: Score de similarité minimum (0-1)

        Returns:
            Liste de résultats avec document_id, chunk_text, similarity_score
        """
        try:
            # Générer l'embedding de la requête
            query_embedding_result = await self.embedding_service.generate_embedding(query_text)

            if not query_embedding_result.success:
                logger.error(f"Failed to generate query embedding: {query_embedding_result.error}")
                return []

            query_embedding = query_embedding_result.embedding

            # Normaliser case_id si fourni
            if case_id and not case_id.startswith("case:"):
                case_id = f"case:{case_id}"

            # Utiliser l'opérateur vectoriel natif de SurrealDB
            if not self.surreal_service.db:
                await self.surreal_service.connect()

            # Construire la requête avec calcul de similarité manuelle
            # Note: L'opérateur <|k,COSINE|> nécessite un index MTREE qui n'est pas encore configuré
            # Pour l'instant, on utilise vector::similarity::cosine() et on filtre manuellement
            if case_id:
                query = """
                SELECT *, vector::similarity::cosine(embedding, $query_embedding) AS similarity_score
                FROM document_embedding
                WHERE case_id = $case_id
                ORDER BY similarity_score DESC
                """
                params = {
                    "case_id": case_id,
                    "query_embedding": query_embedding
                }
            else:
                query = """
                SELECT *, vector::similarity::cosine(embedding, $query_embedding) AS similarity_score
                FROM document_embedding
                ORDER BY similarity_score DESC
                """
                params = {
                    "query_embedding": query_embedding
                }

            result = await self.surreal_service.query(query, params)

            embeddings = []
            if result and len(result) > 0:
                first_item = result[0]
                if isinstance(first_item, dict) and "result" in first_item:
                    embeddings = first_item["result"] if isinstance(first_item["result"], list) else []
                elif isinstance(first_item, list):
                    embeddings = first_item
                elif isinstance(first_item, dict):
                    embeddings = result

            if not embeddings:
                return []

            # Filtrer par similarité minimum et formater les résultats
            similarities = []
            for emb_record in embeddings:
                similarity = emb_record.get("similarity_score", 0)

                if similarity >= min_similarity:
                    similarities.append({
                        "document_id": emb_record.get("document_id"),
                        "case_id": emb_record.get("case_id"),
                        "chunk_index": emb_record.get("chunk_index"),
                        "chunk_text": emb_record.get("chunk_text"),
                        "similarity_score": similarity,
                        "word_count": emb_record.get("word_count", 0)
                    })

            return similarities

        except Exception as e:
            logger.error(f"Error in semantic search: {e}", exc_info=True)
            return []

    @staticmethod
    def _cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
        """Calcule la similarité cosinus entre deux vecteurs."""
        if len(vec1) != len(vec2):
            return 0.0

        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = sum(a * a for a in vec1) ** 0.5
        norm2 = sum(b * b for b in vec2) ** 0.5

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return dot_product / (norm1 * norm2)

    async def delete_document_index(self, document_id: str) -> bool:
        """
        Supprime l'index d'un document.

        Args:
            document_id: ID du document

        Returns:
            True si succès, False sinon
        """
        try:
            if not document_id.startswith("document:"):
                document_id = f"document:{document_id}"

            await self._delete_document_embeddings(document_id)
            logger.info(f"Deleted embeddings for document {document_id}")
            return True

        except Exception as e:
            logger.error(f"Error deleting document index: {e}", exc_info=True)
            return False

    async def get_index_stats(self, case_id: Optional[str] = None) -> dict:
        """
        Obtient des statistiques sur l'index.

        Args:
            case_id: Optionnel, filtrer par cours

        Returns:
            Dict avec total_chunks, total_documents, embedding_model
        """
        try:
            if not self.surreal_service.db:
                await self.surreal_service.connect()

            if case_id:
                if not case_id.startswith("case:"):
                    case_id = f"case:{case_id}"
                query = "SELECT count() AS total, math::max(document_id) AS docs FROM document_embedding WHERE case_id = $case_id GROUP ALL"
                params = {"case_id": case_id}
            else:
                query = "SELECT count() AS total, count(DISTINCT document_id) AS docs FROM document_embedding GROUP ALL"
                params = {}

            result = await self.surreal_service.query(query, params)

            if result and len(result) > 0:
                stats = result[0]
                if isinstance(stats, dict) and "result" in stats:
                    stats = stats["result"][0] if stats["result"] else {}
                elif isinstance(stats, list):
                    stats = stats[0] if stats else {}

                return {
                    "total_chunks": stats.get("total", 0),
                    "embedding_model": self.embedding_service.model,
                    "embedding_dimensions": self.embedding_service.dimensions
                }

            return {
                "total_chunks": 0,
                "embedding_model": self.embedding_service.model,
                "embedding_dimensions": self.embedding_service.dimensions
            }

        except Exception as e:
            logger.error(f"Error getting index stats: {e}", exc_info=True)
            return {
                "error": str(e)
            }


# Singleton
_indexing_service: Optional[DocumentIndexingService] = None


def get_document_indexing_service(
    embedding_provider: str = "local",
    embedding_model: str = "BAAI/bge-m3"
) -> DocumentIndexingService:
    """
    Obtient l'instance singleton du service d'indexation.

    Par défaut utilise BAAI/bge-m3 via sentence-transformers (multilingue FR/EN, 100+ langues).
    Utilise MPS sur Apple Silicon pour accélération GPU.
    """
    global _indexing_service
    if _indexing_service is None:
        _indexing_service = DocumentIndexingService(
            embedding_provider=embedding_provider,
            embedding_model=embedding_model
        )
    return _indexing_service
