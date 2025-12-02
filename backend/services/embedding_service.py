"""
Service d'embeddings vectoriels pour la recherche semantique.

Supporte:
- Ollama embeddings (nomic-embed-text, mxbai-embed-large, etc.)
- OpenAI embeddings (text-embedding-3-small, text-embedding-ada-002)
- SentenceTransformers local (all-MiniLM-L6-v2, etc.)

Les embeddings sont stockes dans SurrealDB pour la recherche vectorielle.
"""

import logging
import asyncio
from typing import Optional
from dataclasses import dataclass, field

import httpx

logger = logging.getLogger(__name__)

# Verifier si sentence-transformers est disponible
SENTENCE_TRANSFORMERS_AVAILABLE = False
try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    logger.info("sentence-transformers non installe, utilisation d'Ollama pour embeddings")


@dataclass
class EmbeddingResult:
    """Resultat de generation d'embedding."""
    success: bool
    embedding: list[float] = field(default_factory=list)
    model: str = ""
    dimensions: int = 0
    error: Optional[str] = None


@dataclass
class ChunkResult:
    """Resultat du chunking de texte."""
    chunks: list[str] = field(default_factory=list)
    total_tokens: int = 0


class EmbeddingService:
    """
    Service de generation d'embeddings vectoriels.

    Providers supportes:
    - ollama: Utilise Ollama local (nomic-embed-text recommande)
    - openai: Utilise l'API OpenAI
    - local: Utilise SentenceTransformers local
    """

    # Modeles d'embedding recommandes
    # Pour le francais et l'anglais, privilegier les modeles multilingues
    MODELS = {
        "ollama": {
            # Modeles multilingues recommandes pour FR/EN
            "nomic-embed-text": {"dimensions": 768, "description": "Multilingue, bon pour texte legal FR/EN", "multilingual": True},
            "mxbai-embed-large": {"dimensions": 1024, "description": "Haute qualite, multilingue", "multilingual": True},
            "snowflake-arctic-embed": {"dimensions": 1024, "description": "Multilingue, performant", "multilingual": True},
            "bge-m3": {"dimensions": 1024, "description": "Multilingue (100+ langues), recommande FR/EN", "multilingual": True},
        },
        "openai": {
            "text-embedding-3-small": {"dimensions": 1536, "description": "Multilingue, bon rapport qualite/prix", "multilingual": True},
            "text-embedding-3-large": {"dimensions": 3072, "description": "Multilingue, meilleure qualite", "multilingual": True},
            "text-embedding-ada-002": {"dimensions": 1536, "description": "Multilingue, modele legacy", "multilingual": True},
        },
        "local": {
            # Modeles SentenceTransformers multilingues (RECOMMANDÉ)
            "BAAI/bge-m3": {"dimensions": 1024, "description": "Multilingue (100+ langues), SOTA, recommandé pour juridique FR/EN", "multilingual": True},
            "paraphrase-multilingual-MiniLM-L12-v2": {"dimensions": 384, "description": "Multilingue (50+ langues), rapide", "multilingual": True},
            "paraphrase-multilingual-mpnet-base-v2": {"dimensions": 768, "description": "Multilingue, meilleure qualite", "multilingual": True},
            "distiluse-base-multilingual-cased-v2": {"dimensions": 512, "description": "Multilingue, bon equilibre", "multilingual": True},
            # Modeles anglais seulement (pour reference)
            "all-MiniLM-L6-v2": {"dimensions": 384, "description": "Anglais seulement, rapide", "multilingual": False},
            "all-mpnet-base-v2": {"dimensions": 768, "description": "Anglais seulement, bonne qualite", "multilingual": False},
        }
    }

    # Modele par defaut multilingue
    DEFAULT_MODEL = {
        "ollama": "bge-m3",  # Excellent pour FR/EN, 100+ langues
        "openai": "text-embedding-3-small",
        "local": "BAAI/bge-m3"  # BGE-M3 via HuggingFace - SOTA multilingue
    }

    def __init__(
        self,
        provider: str = "ollama",
        model: str = "nomic-embed-text",
        ollama_url: str = "http://localhost:11434",
        openai_api_key: Optional[str] = None
    ):
        """
        Initialise le service d'embeddings.

        Args:
            provider: Provider a utiliser (ollama, openai, local)
            model: Modele d'embedding
            ollama_url: URL du serveur Ollama
            openai_api_key: Cle API OpenAI (si provider=openai)
        """
        self.provider = provider
        self.model = model
        self.ollama_url = ollama_url
        self.openai_api_key = openai_api_key
        self._local_model = None

        # Determiner les dimensions
        provider_models = self.MODELS.get(provider, {})
        model_info = provider_models.get(model, {})
        self.dimensions = model_info.get("dimensions", 768)

    def _load_local_model(self):
        """Charge le modele SentenceTransformers local avec support MPS/CUDA/CPU."""
        if not SENTENCE_TRANSFORMERS_AVAILABLE:
            return None

        if self._local_model is None:
            try:
                import torch

                # Detecter le meilleur device disponible
                if torch.backends.mps.is_available():
                    device = "mps"
                    logger.info("MPS (Metal Performance Shaders) detecte - utilisation du GPU Apple Silicon")
                elif torch.cuda.is_available():
                    device = "cuda"
                    logger.info("CUDA detecte - utilisation du GPU NVIDIA")
                else:
                    device = "cpu"
                    logger.info("Utilisation du CPU (pas de GPU detecte)")

                logger.info(f"Chargement du modele local: {self.model} sur {device}")
                self._local_model = SentenceTransformer(self.model, device=device)
                logger.info(f"Modele {self.model} charge sur {device}")
            except Exception as e:
                logger.error(f"Erreur chargement modele local: {e}")
                return None

        return self._local_model

    async def generate_embedding(self, text: str) -> EmbeddingResult:
        """
        Genere un embedding pour un texte.

        Args:
            text: Texte a encoder

        Returns:
            EmbeddingResult avec le vecteur d'embedding
        """
        if not text or not text.strip():
            return EmbeddingResult(
                success=False,
                error="Texte vide"
            )

        if self.provider == "ollama":
            return await self._generate_ollama(text)
        elif self.provider == "openai":
            return await self._generate_openai(text)
        elif self.provider == "local":
            return await self._generate_local(text)
        else:
            return EmbeddingResult(
                success=False,
                error=f"Provider non supporte: {self.provider}"
            )

    async def _generate_ollama(self, text: str) -> EmbeddingResult:
        """Genere un embedding via Ollama."""
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.ollama_url}/api/embeddings",
                    json={
                        "model": self.model,
                        "prompt": text
                    }
                )

                if response.status_code != 200:
                    return EmbeddingResult(
                        success=False,
                        error=f"Ollama error: {response.status_code} - {response.text}"
                    )

                data = response.json()
                embedding = data.get("embedding", [])

                return EmbeddingResult(
                    success=True,
                    embedding=embedding,
                    model=f"ollama:{self.model}",
                    dimensions=len(embedding)
                )

        except httpx.ConnectError:
            return EmbeddingResult(
                success=False,
                error="Impossible de se connecter a Ollama. Verifiez qu'il est demarre."
            )
        except Exception as e:
            return EmbeddingResult(
                success=False,
                error=str(e)
            )

    async def _generate_openai(self, text: str) -> EmbeddingResult:
        """Genere un embedding via OpenAI API."""
        if not self.openai_api_key:
            return EmbeddingResult(
                success=False,
                error="Cle API OpenAI non configuree"
            )

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    "https://api.openai.com/v1/embeddings",
                    headers={
                        "Authorization": f"Bearer {self.openai_api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": self.model,
                        "input": text
                    }
                )

                if response.status_code != 200:
                    return EmbeddingResult(
                        success=False,
                        error=f"OpenAI error: {response.status_code}"
                    )

                data = response.json()
                embedding = data["data"][0]["embedding"]

                return EmbeddingResult(
                    success=True,
                    embedding=embedding,
                    model=f"openai:{self.model}",
                    dimensions=len(embedding)
                )

        except Exception as e:
            return EmbeddingResult(
                success=False,
                error=str(e)
            )

    async def _generate_local(self, text: str) -> EmbeddingResult:
        """Genere un embedding via SentenceTransformers local."""
        if not SENTENCE_TRANSFORMERS_AVAILABLE:
            return EmbeddingResult(
                success=False,
                error="sentence-transformers non installe"
            )

        model = self._load_local_model()
        if model is None:
            return EmbeddingResult(
                success=False,
                error="Impossible de charger le modele local"
            )

        try:
            loop = asyncio.get_event_loop()
            embedding = await loop.run_in_executor(
                None,
                lambda: model.encode(text).tolist()
            )

            return EmbeddingResult(
                success=True,
                embedding=embedding,
                model=f"local:{self.model}",
                dimensions=len(embedding)
            )

        except Exception as e:
            return EmbeddingResult(
                success=False,
                error=str(e)
            )

    async def generate_embeddings_batch(self, texts: list[str]) -> list[EmbeddingResult]:
        """
        Genere des embeddings pour plusieurs textes.

        Args:
            texts: Liste de textes a encoder

        Returns:
            Liste de EmbeddingResult
        """
        results = []
        for text in texts:
            result = await self.generate_embedding(text)
            results.append(result)
        return results

    def chunk_text(
        self,
        text: str,
        chunk_size: int = 500,
        overlap: int = 50
    ) -> ChunkResult:
        """
        Decoupe un texte en chunks pour l'embedding.

        Args:
            text: Texte a decouper
            chunk_size: Taille approximative des chunks en mots
            overlap: Nombre de mots de chevauchement entre chunks

        Returns:
            ChunkResult avec les chunks
        """
        if not text:
            return ChunkResult()

        words = text.split()
        chunks = []
        start = 0

        while start < len(words):
            end = min(start + chunk_size, len(words))
            chunk = " ".join(words[start:end])
            chunks.append(chunk)

            # Avancer avec chevauchement
            start = end - overlap if end < len(words) else len(words)

        return ChunkResult(
            chunks=chunks,
            total_tokens=len(words)
        )

    @staticmethod
    def is_ollama_available() -> bool:
        """Verifie si Ollama est disponible."""
        try:
            import httpx
            response = httpx.get("http://localhost:11434/api/tags", timeout=5.0)
            return response.status_code == 200
        except Exception:
            return False


# Singleton pour le service
_embedding_service: Optional[EmbeddingService] = None


def get_embedding_service(
    provider: str = "ollama",
    model: Optional[str] = None
) -> EmbeddingService:
    """
    Obtient l'instance singleton du service d'embeddings.

    Par defaut, utilise un modele multilingue (FR/EN) pour chaque provider.
    """
    global _embedding_service
    if _embedding_service is None:
        # Utiliser le modele multilingue par defaut si non specifie
        if model is None:
            model = EmbeddingService.DEFAULT_MODEL.get(provider, "nomic-embed-text")
        _embedding_service = EmbeddingService(provider=provider, model=model)
    return _embedding_service
