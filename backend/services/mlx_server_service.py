"""
Service pour gérer le serveur MLX-LM automatiquement.

Ce service démarre et arrête le serveur MLX en fonction du modèle sélectionné,
permettant de switcher entre modèles sans intervention manuelle.
"""

import asyncio
import logging
import subprocess
import time
from typing import Optional

logger = logging.getLogger(__name__)


class MLXServerService:
    """
    Gère le lifecycle du serveur MLX-LM.

    Features:
    - Démarre automatiquement le serveur MLX avec le modèle demandé
    - Arrête proprement le serveur en cours
    - Switch entre modèles (arrête l'ancien, démarre le nouveau)
    - Vérifie la santé du serveur
    """

    def __init__(self, port: int = 8080, host: str = "localhost"):
        self.port = port
        self.host = host
        self.process: Optional[subprocess.Popen] = None
        self.current_model: Optional[str] = None
        self._startup_timeout = 120  # secondes (augmenté pour téléchargement initial)

    def is_running(self) -> bool:
        """Vérifie si le serveur MLX est en cours d'exécution."""
        if self.process is None:
            return False

        # Vérifier si le processus est toujours vivant
        poll = self.process.poll()
        return poll is None

    async def health_check(self) -> bool:
        """
        Vérifie la santé du serveur MLX via un appel HTTP.

        Returns:
            True si le serveur répond, False sinon
        """
        try:
            import httpx
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"http://{self.host}:{self.port}/v1/models")
                return response.status_code == 200
        except Exception as e:
            logger.debug(f"Health check failed: {e}")
            return False

    async def start(self, model_id: str, max_wait: Optional[int] = None) -> bool:
        """
        Démarre le serveur MLX avec le modèle spécifié.

        Args:
            model_id: ID du modèle MLX (ex: "mlx-community/Qwen2.5-3B-Instruct-4bit")
            max_wait: Temps max d'attente pour le démarrage (secondes). Si None, utilise self._startup_timeout

        Returns:
            True si le serveur a démarré avec succès, False sinon
        """
        # Utiliser le timeout configuré si max_wait n'est pas spécifié
        if max_wait is None:
            max_wait = self._startup_timeout
        # Si le modèle demandé est déjà en cours, ne rien faire
        if self.is_running() and self.current_model == model_id:
            logger.info(f"✅ Serveur MLX déjà en cours avec {model_id}")
            return True

        # Si un autre modèle tourne, l'arrêter d'abord
        if self.is_running():
            logger.info(f"🔄 Changement de modèle: {self.current_model} → {model_id}")
            await self.stop()

        logger.info(f"🚀 Démarrage serveur MLX avec {model_id}...")
        logger.info(f"   Port: {self.port}")
        logger.info(f"   ⚠️  Si premier démarrage: téléchargement du modèle (~2-4 GB)")
        logger.info(f"   ⏱️  Cela peut prendre 1-2 minutes selon votre connexion...")

        try:
            # Démarrer le serveur MLX en subprocess
            # Note: Utiliser "mlx_lm.server" directement (pas "python -m mlx_lm.server" qui est déprécié)
            self.process = subprocess.Popen(
                [
                    "mlx_lm.server",
                    "--model", model_id,
                    "--port", str(self.port),
                    "--host", self.host,
                ],
                stdout=subprocess.DEVNULL,  # Ignorer stdout pour éviter buffer overflow
                stderr=subprocess.PIPE,      # Capturer stderr pour les erreurs
                text=True,
            )

            self.current_model = model_id

            # Attendre que le serveur soit prêt
            logger.info(f"⏳ Attente du démarrage du serveur (max {max_wait}s)...")
            start_time = time.time()

            while time.time() - start_time < max_wait:
                if await self.health_check():
                    elapsed = time.time() - start_time
                    logger.info(f"✅ Serveur MLX démarré avec succès en {elapsed:.1f}s")
                    logger.info(f"   URL: http://{self.host}:{self.port}/v1")
                    return True

                # Vérifier si le processus a crashé
                if not self.is_running():
                    logger.error("❌ Le processus MLX s'est arrêté de manière inattendue")
                    if self.process and self.process.stderr:
                        stderr = self.process.stderr.read()
                        logger.error(f"Erreur: {stderr}")
                    return False

                await asyncio.sleep(1)

            # Timeout atteint
            logger.error(f"❌ Timeout: Le serveur MLX n'a pas démarré en {max_wait}s")
            logger.error(f"   Vérifiez votre connexion Internet si c'est le premier démarrage")
            logger.error(f"   Le modèle doit télécharger ~2-4 GB depuis HuggingFace")
            await self.stop()
            return False

        except FileNotFoundError:
            logger.error("❌ mlx-lm n'est pas installé. Installez avec: uv sync")
            return False
        except Exception as e:
            logger.error(f"❌ Erreur lors du démarrage du serveur MLX: {e}")
            return False

    async def stop(self) -> None:
        """Arrête proprement le serveur MLX."""
        if not self.is_running():
            logger.debug("Serveur MLX déjà arrêté")
            return

        logger.info(f"🛑 Arrêt du serveur MLX (modèle: {self.current_model})...")

        try:
            # Essayer d'abord SIGTERM (arrêt propre)
            if self.process:
                self.process.terminate()

                # Attendre max 5 secondes
                for _ in range(5):
                    if self.process.poll() is not None:
                        break
                    await asyncio.sleep(1)

                # Si toujours vivant, SIGKILL
                if self.process.poll() is None:
                    logger.warning("Force kill du serveur MLX...")
                    self.process.kill()

                self.process = None
                self.current_model = None
                logger.info("✅ Serveur MLX arrêté")
        except Exception as e:
            logger.error(f"Erreur lors de l'arrêt du serveur MLX: {e}")

    async def restart(self, model_id: str) -> bool:
        """
        Redémarre le serveur MLX avec un nouveau modèle.

        Args:
            model_id: ID du nouveau modèle

        Returns:
            True si le redémarrage a réussi
        """
        await self.stop()
        return await self.start(model_id)

    def get_status(self) -> dict:
        """
        Retourne le statut actuel du serveur MLX.

        Returns:
            Dict avec: running, model, port, host
        """
        return {
            "running": self.is_running(),
            "model": self.current_model,
            "port": self.port,
            "host": self.host,
            "url": f"http://{self.host}:{self.port}/v1" if self.is_running() else None,
        }


# ============================================================================
# Singleton instance
# ============================================================================

_mlx_service: Optional[MLXServerService] = None


def get_mlx_server_service() -> MLXServerService:
    """Retourne l'instance singleton du service MLX."""
    global _mlx_service
    if _mlx_service is None:
        _mlx_service = MLXServerService()
    return _mlx_service


async def ensure_mlx_server(model_id: str) -> bool:
    """
    Helper pour s'assurer que le serveur MLX tourne avec le bon modèle.

    Args:
        model_id: ID complet du modèle (ex: "mlx:mlx-community/Qwen2.5-3B-Instruct-4bit")

    Returns:
        True si le serveur est prêt

    Examples:
        >>> await ensure_mlx_server("mlx:mlx-community/Qwen2.5-3B-Instruct-4bit")
        True
    """
    # Extraire le model_id sans le prefix "mlx:"
    if model_id.startswith("mlx:"):
        model_id = model_id.replace("mlx:", "")

    service = get_mlx_server_service()

    # Si le bon modèle tourne déjà, retourner immédiatement
    if service.is_running() and service.current_model == model_id:
        return True

    # Sinon, démarrer le serveur avec le modèle
    return await service.start(model_id)


# ============================================================================
# Cleanup au shutdown
# ============================================================================

async def shutdown_mlx_server():
    """Arrête le serveur MLX au shutdown de l'application."""
    service = get_mlx_server_service()
    await service.stop()
