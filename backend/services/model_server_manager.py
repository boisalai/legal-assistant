"""
Manager centralisé pour orchestrer les serveurs de modèles locaux.

Ce service gère automatiquement le démarrage/arrêt des serveurs MLX et vLLM
selon le modèle sélectionné par l'utilisateur.
"""

import logging
from typing import Optional

from services.mlx_server_service import ensure_mlx_server, get_mlx_server_service
from services.vllm_server_service import ensure_vllm_server, get_vllm_server_service

logger = logging.getLogger(__name__)


class ModelServerManager:
    """
    Orchestre les serveurs de modèles locaux (MLX et vLLM).

    Features:
    - Détecte automatiquement quel serveur démarrer selon le model_id
    - Arrête les serveurs inutilisés pour économiser les ressources
    - Gère les transitions entre modèles différents
    """

    def __init__(self):
        pass

    def _detect_provider(self, model_id: str) -> str:
        """
        Détecte le provider du modèle à partir de son ID.

        Args:
            model_id: ID complet (ex: "mlx:model" ou "vllm:model")

        Returns:
            "mlx", "vllm", "ollama", "anthropic", ou "unknown"
        """
        if ":" not in model_id:
            return "unknown"

        provider = model_id.split(":", 1)[0].lower()
        return provider

    async def ensure_server_ready(self, model_id: str) -> bool:
        """
        S'assure que le bon serveur est démarré pour le modèle donné.

        Cette fonction:
        1. Détecte le provider du modèle (MLX ou vLLM)
        2. Démarre le serveur approprié si nécessaire
        3. Arrête les autres serveurs pour économiser les ressources

        Args:
            model_id: ID complet du modèle (ex: "mlx:..." ou "vllm:...")

        Returns:
            True si le serveur est prêt, False sinon
        """
        provider = self._detect_provider(model_id)

        # Modèles qui ne nécessitent pas de serveur local
        if provider in ["ollama", "anthropic", "openai"]:
            logger.debug(f"Modèle {model_id} ne nécessite pas de serveur local")
            return True

        # Compatibilité: huggingface: est déprécié, redirigé vers vLLM
        if provider == "huggingface":
            logger.warning(f"⚠️  Provider 'huggingface:' déprécié - Traitement comme vLLM")
            provider = "vllm"

        # MLX
        if provider == "mlx":
            logger.info(f"📦 Préparation du serveur MLX pour {model_id}...")

            # Arrêter vLLM s'il tourne
            vllm_service = get_vllm_server_service()
            if vllm_service.is_running():
                logger.info("🛑 Arrêt du serveur vLLM (non nécessaire)")
                await vllm_service.stop()

            # Démarrer MLX
            success = await ensure_mlx_server(model_id)
            if success:
                logger.info(f"✅ Serveur MLX prêt pour {model_id}")
            else:
                logger.error(f"❌ Échec du démarrage du serveur MLX pour {model_id}")
            return success

        # vLLM
        elif provider == "vllm":
            logger.info(f"📦 Préparation du serveur vLLM pour {model_id}...")

            # Arrêter MLX s'il tourne
            mlx_service = get_mlx_server_service()
            if mlx_service.is_running():
                logger.info("🛑 Arrêt du serveur MLX (non nécessaire)")
                await mlx_service.stop()

            # Démarrer vLLM
            success = await ensure_vllm_server(model_id)
            if success:
                logger.info(f"✅ Serveur vLLM prêt pour {model_id}")
            else:
                logger.error(f"❌ Échec du démarrage du serveur vLLM pour {model_id}")
            return success

        # Provider inconnu
        else:
            logger.warning(f"⚠️  Provider inconnu pour {model_id}: {provider}")
            return False

    async def stop_all_servers(self) -> None:
        """
        Arrête tous les serveurs de modèles en cours.

        Utile au shutdown de l'application.
        """
        logger.info("🛑 Arrêt de tous les serveurs de modèles...")

        mlx_service = get_mlx_server_service()
        vllm_service = get_vllm_server_service()

        if mlx_service.is_running():
            await mlx_service.stop()

        if vllm_service.is_running():
            await vllm_service.stop()

        logger.info("✅ Tous les serveurs arrêtés")

    def get_status(self) -> dict:
        """
        Retourne le statut de tous les serveurs.

        Returns:
            Dict avec le statut de MLX et vLLM
        """
        mlx_service = get_mlx_server_service()
        vllm_service = get_vllm_server_service()

        return {
            "mlx": mlx_service.get_status(),
            "vllm": vllm_service.get_status(),
        }


# ============================================================================
# Singleton instance
# ============================================================================

_manager: Optional[ModelServerManager] = None


def get_model_server_manager() -> ModelServerManager:
    """Retourne l'instance singleton du manager."""
    global _manager
    if _manager is None:
        _manager = ModelServerManager()
    return _manager


async def ensure_model_server(model_id: str) -> bool:
    """
    Helper pour s'assurer que le bon serveur tourne pour un modèle.

    Args:
        model_id: ID complet du modèle (ex: "mlx:..." ou "vllm:...")

    Returns:
        True si le serveur est prêt

    Examples:
        >>> await ensure_model_server("mlx:mlx-community/Qwen2.5-3B-Instruct-4bit")
        True
        >>> await ensure_model_server("vllm:Qwen/Qwen2.5-3B-Instruct")
        True
        >>> await ensure_model_server("ollama:mistral")
        True  # Pas besoin de serveur, retourne True immédiatement
    """
    manager = get_model_server_manager()
    return await manager.ensure_server_ready(model_id)


async def shutdown_all_model_servers():
    """Arrête tous les serveurs au shutdown de l'application."""
    manager = get_model_server_manager()
    await manager.stop_all_servers()
