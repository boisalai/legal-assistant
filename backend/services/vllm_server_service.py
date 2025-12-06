"""
Service pour gérer le serveur vLLM automatiquement.

Ce service démarre et arrête le serveur vLLM en fonction du modèle sélectionné,
permettant de charger n'importe quel modèle HuggingFace localement.
"""

import asyncio
import logging
import subprocess
import time
from typing import Optional

logger = logging.getLogger(__name__)


class VLLMServerService:
    """
    Gère le lifecycle du serveur vLLM.

    Features:
    - Démarre automatiquement le serveur vLLM avec le modèle demandé
    - Arrête proprement le serveur en cours
    - Switch entre modèles (arrête l'ancien, démarre le nouveau)
    - Vérifie la santé du serveur
    - Support MPS (Apple Silicon) et CUDA (NVIDIA)
    """

    def __init__(self, port: int = 8001, host: str = "localhost"):  # Port 8001 pour éviter conflit avec FastAPI (8000)
        self.port = port
        self.host = host
        self.process: Optional[subprocess.Popen] = None
        self.current_model: Optional[str] = None
        self._startup_timeout = 60  # vLLM prend plus de temps à démarrer

    def is_running(self) -> bool:
        """Vérifie si le serveur vLLM est en cours d'exécution."""
        if self.process is None:
            return False

        # Vérifier si le processus est toujours vivant
        poll = self.process.poll()
        return poll is None

    async def health_check(self) -> bool:
        """
        Vérifie la santé du serveur vLLM via un appel HTTP.

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

    def _detect_device(self) -> str:
        """
        Détecte automatiquement le meilleur device disponible.

        Returns:
            "cuda" si NVIDIA GPU disponible, "cpu" sinon
        """
        try:
            import torch
            if torch.cuda.is_available():
                return "cuda"
        except ImportError:
            pass

        # vLLM ne supporte pas MPS officiellement
        # Sur Apple Silicon, on utilise CPU (lent) ou MLX (recommandé)
        return "cpu"

    async def start(self, model_id: str, max_wait: int = 60, device: Optional[str] = None) -> bool:
        """
        Démarre le serveur vLLM avec le modèle spécifié.

        Args:
            model_id: ID du modèle HuggingFace (ex: "Qwen/Qwen2.5-3B-Instruct")
            max_wait: Temps max d'attente pour le démarrage (secondes)
            device: Device à utiliser ("cuda" ou "cpu", auto-détecté si None)

        Returns:
            True si le serveur a démarré avec succès, False sinon
        """
        # Si le modèle demandé est déjà en cours, ne rien faire
        if self.is_running() and self.current_model == model_id:
            logger.info(f"✅ Serveur vLLM déjà en cours avec {model_id}")
            return True

        # Si un autre modèle tourne, l'arrêter d'abord
        if self.is_running():
            logger.info(f"🔄 Changement de modèle: {self.current_model} → {model_id}")
            await self.stop()

        # Détecter le device si non spécifié
        if device is None:
            device = self._detect_device()

        logger.info(f"🚀 Démarrage serveur vLLM avec {model_id}...")
        logger.info(f"   Port: {self.port}")
        logger.info(f"   Device: {device}")
        logger.info(f"   ⚠️  Premier démarrage: téléchargement du modèle (~6-14 GB)")

        try:
            # Construire la commande vLLM
            # Note: vLLM 0.6+ détecte automatiquement le device (CUDA/CPU)
            # L'argument --device n'est plus supporté
            cmd = [
                "vllm", "serve",
                model_id,
                "--port", str(self.port),
                "--host", self.host,
                "--max-model-len", "2048",  # Limite pour CPU (moins de mémoire que GPU)
            ]

            # Démarrer le serveur vLLM en subprocess
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            self.current_model = model_id

            # Attendre que le serveur soit prêt
            logger.info(f"⏳ Attente du démarrage du serveur (max {max_wait}s)...")
            start_time = time.time()

            while time.time() - start_time < max_wait:
                if await self.health_check():
                    elapsed = time.time() - start_time
                    logger.info(f"✅ Serveur vLLM démarré avec succès en {elapsed:.1f}s")
                    logger.info(f"   URL: http://{self.host}:{self.port}/v1")
                    return True

                # Vérifier si le processus a crashé
                if not self.is_running():
                    logger.error("❌ Le processus vLLM s'est arrêté de manière inattendue")
                    if self.process and self.process.stderr:
                        stderr = self.process.stderr.read()
                        logger.error(f"Erreur: {stderr}")
                    return False

                await asyncio.sleep(2)  # vLLM prend plus de temps

            # Timeout atteint
            logger.error(f"❌ Timeout: Le serveur vLLM n'a pas démarré en {max_wait}s")
            await self.stop()
            return False

        except FileNotFoundError:
            logger.error("❌ vLLM n'est pas installé. Installez avec: pip install vllm")
            return False
        except Exception as e:
            logger.error(f"❌ Erreur lors du démarrage du serveur vLLM: {e}")
            return False

    async def stop(self) -> None:
        """Arrête proprement le serveur vLLM."""
        if not self.is_running():
            logger.debug("Serveur vLLM déjà arrêté")
            return

        logger.info(f"🛑 Arrêt du serveur vLLM (modèle: {self.current_model})...")

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
                    logger.warning("Force kill du serveur vLLM...")
                    self.process.kill()

                self.process = None
                self.current_model = None
                logger.info("✅ Serveur vLLM arrêté")
        except Exception as e:
            logger.error(f"Erreur lors de l'arrêt du serveur vLLM: {e}")

    async def restart(self, model_id: str, device: Optional[str] = None) -> bool:
        """
        Redémarre le serveur vLLM avec un nouveau modèle.

        Args:
            model_id: ID du nouveau modèle
            device: Device à utiliser (auto-détecté si None)

        Returns:
            True si le redémarrage a réussi
        """
        await self.stop()
        return await self.start(model_id, device=device)

    def get_status(self) -> dict:
        """
        Retourne le statut actuel du serveur vLLM.

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

_vllm_service: Optional[VLLMServerService] = None


def get_vllm_server_service() -> VLLMServerService:
    """Retourne l'instance singleton du service vLLM."""
    global _vllm_service
    if _vllm_service is None:
        _vllm_service = VLLMServerService()
    return _vllm_service


async def ensure_vllm_server(model_id: str, device: Optional[str] = None) -> bool:
    """
    Helper pour s'assurer que le serveur vLLM tourne avec le bon modèle.

    Args:
        model_id: ID complet du modèle (ex: "vllm:Qwen/..." ou "huggingface:Qwen/...")
        device: Device à utiliser (auto-détecté si None)

    Returns:
        True si le serveur est prêt

    Examples:
        >>> await ensure_vllm_server("vllm:Qwen/Qwen2.5-3B-Instruct")
        True
        >>> await ensure_vllm_server("huggingface:Qwen/Qwen2.5-3B-Instruct")  # Compatibilité
        True
    """
    # Extraire le model_id sans le prefix "vllm:" ou "huggingface:"
    if model_id.startswith("vllm:"):
        model_id = model_id.replace("vllm:", "")
    elif model_id.startswith("huggingface:"):
        model_id = model_id.replace("huggingface:", "")

    service = get_vllm_server_service()

    # Si le bon modèle tourne déjà, retourner immédiatement
    if service.is_running() and service.current_model == model_id:
        return True

    # Sinon, démarrer le serveur avec le modèle
    return await service.start(model_id, device=device)


# ============================================================================
# Cleanup au shutdown
# ============================================================================

async def shutdown_vllm_server():
    """Arrête le serveur vLLM au shutdown de l'application."""
    service = get_vllm_server_service()
    await service.stop()
