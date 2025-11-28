"""
Provider Ollama pour l'inférence locale cross-platform.

Ollama est une alternative simple à MLX qui fonctionne sur:
- macOS (Apple Silicon et Intel)
- Linux
- Windows

Avantages:
- Installation très simple (un seul binaire)
- Gère automatiquement le téléchargement des modèles
- API REST simple et rapide
- Large sélection de modèles (Llama, Mistral, Phi, etc.)
"""

import logging
from typing import Any, Optional
import json

from services.llm_provider import LLMProvider, LLMMessage, LLMResponse

logger = logging.getLogger(__name__)


class OllamaProvider(LLMProvider):
    """
    Provider pour Ollama (inférence locale cross-platform).

    Ollama doit être installé et en cours d'exécution sur la machine.
    Téléchargez-le depuis: https://ollama.ai
    """

    def __init__(
        self,
        model_name: str = "mistral",
        base_url: str = "http://localhost:11434",
        **kwargs
    ):
        """
        Initialise le provider Ollama.

        Args:
            model_name: Nom du modèle Ollama (ex: "mistral", "llama3", "phi3")
            base_url: URL de l'API Ollama (défaut: http://localhost:11434)
            **kwargs: Configuration additionnelle
        """
        super().__init__(model_name, **kwargs)

        self.base_url = base_url.rstrip("/")
        self.default_max_tokens = kwargs.get("max_tokens", 2000)
        self.default_temperature = kwargs.get("temperature", 0.7)

        logger.info(f"OllamaProvider initialisé avec modèle: {model_name}")

    def generate(
        self,
        messages: list[LLMMessage],
        max_tokens: int = 2000,
        temperature: float = 0.7,
        **kwargs
    ) -> LLMResponse:
        """
        Génère une réponse avec Ollama.

        Args:
            messages: Liste de messages de la conversation
            max_tokens: Nombre maximum de tokens à générer
            temperature: Température (0.0 = déterministe, 1.0 = créatif)
            **kwargs: Paramètres additionnels Ollama (top_k, top_p, etc.)

        Returns:
            LLMResponse avec la réponse générée
        """
        logger.debug(
            f"Génération avec Ollama (max_tokens={max_tokens}, temp={temperature})"
        )

        try:
            import requests

            # Convertir nos messages au format Ollama
            ollama_messages = [
                {"role": msg.role, "content": msg.content}
                for msg in messages
            ]

            # Préparer la requête
            payload = {
                "model": self.model_name,
                "messages": ollama_messages,
                "stream": False,  # Désactiver le streaming pour l'instant
                "options": {
                    "temperature": temperature,
                    "num_predict": max_tokens,  # max_tokens dans Ollama
                }
            }

            # Ajouter les paramètres optionnels
            if "top_k" in kwargs:
                payload["options"]["top_k"] = kwargs["top_k"]
            if "top_p" in kwargs:
                payload["options"]["top_p"] = kwargs["top_p"]
            if "repeat_penalty" in kwargs:
                payload["options"]["repeat_penalty"] = kwargs["repeat_penalty"]

            # Appel à l'API Ollama
            response = requests.post(
                f"{self.base_url}/api/chat",
                json=payload,
                timeout=120  # 2 minutes timeout
            )

            response.raise_for_status()

            # Parser la réponse
            result = response.json()

            # Extraire le texte de la réponse
            content = result.get("message", {}).get("content", "")

            # Calculer les tokens utilisés (si disponible)
            eval_count = result.get("eval_count", 0)
            prompt_eval_count = result.get("prompt_eval_count", 0)
            total_tokens = eval_count + prompt_eval_count

            return LLMResponse(
                content=content,
                model=result.get("model", self.model_name),
                tokens_used=total_tokens if total_tokens > 0 else None,
                finish_reason=result.get("done_reason", "stop"),
                metadata={
                    "provider": "ollama",
                    "eval_count": eval_count,
                    "prompt_eval_count": prompt_eval_count,
                    "eval_duration_ms": result.get("eval_duration", 0) / 1_000_000,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                }
            )

        except ImportError:
            raise RuntimeError(
                "Le package 'requests' n'est pas installé. "
                "Installez-le avec: uv add requests"
            )
        except Exception as e:
            logger.error(f"❌ Erreur lors de la génération avec Ollama: {e}")

            # Message d'aide si Ollama n'est pas démarré
            if "Connection" in str(e) or "refused" in str(e).lower():
                raise RuntimeError(
                    f"Impossible de se connecter à Ollama sur {self.base_url}. "
                    f"Vérifiez qu'Ollama est démarré avec: ollama serve"
                )

            raise RuntimeError(f"Erreur de génération Ollama: {e}")

    def is_available(self) -> bool:
        """
        Vérifie si Ollama est disponible et en cours d'exécution.

        Returns:
            True si Ollama répond sur l'URL configurée
        """
        try:
            import requests

            # Ping l'API Ollama
            response = requests.get(
                f"{self.base_url}/api/tags",
                timeout=5
            )

            return response.status_code == 200

        except ImportError:
            logger.warning(
                "Le package 'requests' n'est pas installé. "
                "Installez-le avec: uv add requests"
            )
            return False
        except Exception as e:
            logger.warning(f"Ollama non disponible sur {self.base_url}: {e}")
            return False

    def get_info(self) -> dict[str, Any]:
        """
        Retourne les informations sur ce provider.

        Returns:
            Dictionnaire avec les informations
        """
        available = self.is_available()

        info = {
            "name": "Ollama Provider",
            "model": self.model_name,
            "available": available,
            "base_url": self.base_url,
            "platform": "Ollama (Local, cross-platform)",
            "config": {
                "max_tokens": self.default_max_tokens,
                "temperature": self.default_temperature,
                **self.config
            }
        }

        # Si disponible, récupérer la liste des modèles installés
        if available:
            try:
                import requests
                response = requests.get(f"{self.base_url}/api/tags", timeout=5)
                if response.status_code == 200:
                    models = response.json().get("models", [])
                    info["installed_models"] = [m.get("name") for m in models]
            except:
                pass

        return info

    def list_models(self) -> list[dict]:
        """
        Liste les modèles Ollama installés sur la machine.

        Returns:
            Liste de dictionnaires avec les informations sur les modèles
        """
        try:
            import requests

            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            response.raise_for_status()

            models = response.json().get("models", [])

            return [
                {
                    "name": model.get("name"),
                    "size": model.get("size"),
                    "modified": model.get("modified_at"),
                }
                for model in models
            ]

        except Exception as e:
            logger.error(f"Erreur lors de la récupération des modèles: {e}")
            return []

    def pull_model(self, model_name: Optional[str] = None) -> bool:
        """
        Télécharge un modèle Ollama.

        Args:
            model_name: Nom du modèle à télécharger (ou self.model_name si None)

        Returns:
            True si le téléchargement a réussi
        """
        model = model_name or self.model_name

        try:
            import requests

            logger.info(f"Téléchargement du modèle Ollama: {model}")

            # Appel à l'API de pull
            response = requests.post(
                f"{self.base_url}/api/pull",
                json={"name": model},
                stream=True,
                timeout=300  # 5 minutes timeout
            )

            response.raise_for_status()

            # Afficher la progression (si stream)
            for line in response.iter_lines():
                if line:
                    data = json.loads(line)
                    status = data.get("status", "")
                    if status:
                        logger.info(f"  {status}")

            logger.info(f"✓ Modèle {model} téléchargé avec succès")
            return True

        except Exception as e:
            logger.error(f"❌ Erreur lors du téléchargement du modèle: {e}")
            return False


# ========================================
# Modèles Ollama recommandés
# ========================================

OLLAMA_MODELS = {
    "mistral": {
        "name": "mistral",
        "description": "Mistral 7B - Excellent rapport qualité/performance",
        "size": "~4GB",
        "languages": "Multilingue",
        "command": "ollama pull mistral"
    },
    "llama3": {
        "name": "llama3",
        "description": "Llama 3 8B - Très performant de Meta",
        "size": "~5GB",
        "languages": "Multilingue",
        "command": "ollama pull llama3"
    },
    "phi3": {
        "name": "phi3",
        "description": "Phi-3 de Microsoft - Petit et rapide",
        "size": "~2GB",
        "languages": "Multilingue",
        "command": "ollama pull phi3"
    },
    "gemma": {
        "name": "gemma:7b",
        "description": "Gemma 7B de Google - Excellent sur les instructions",
        "size": "~5GB",
        "languages": "Multilingue",
        "command": "ollama pull gemma:7b"
    },
    "codellama": {
        "name": "codellama",
        "description": "Code Llama - Spécialisé pour le code",
        "size": "~4GB",
        "languages": "Code + Texte",
        "command": "ollama pull codellama"
    },
    "llama3-70b": {
        "name": "llama3:70b",
        "description": "Llama 3 70B - Le plus puissant (nécessite beaucoup de RAM)",
        "size": "~40GB",
        "languages": "Multilingue",
        "command": "ollama pull llama3:70b"
    }
}


def get_ollama_model(preference: str = "balanced") -> str:
    """
    Retourne un modèle Ollama recommandé selon la préférence.

    Args:
        preference: "fast" (rapide), "balanced" (équilibré), "quality" (qualité)

    Returns:
        Nom du modèle Ollama
    """
    if preference == "fast":
        return OLLAMA_MODELS["phi3"]["name"]
    elif preference == "quality":
        return OLLAMA_MODELS["llama3"]["name"]
    else:  # balanced
        return OLLAMA_MODELS["mistral"]["name"]
