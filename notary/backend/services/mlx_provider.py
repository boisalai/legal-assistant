"""
Provider MLX pour l'inférence locale sur Apple Silicon.

MLX est optimisé pour les puces M1/M2/M3 d'Apple et utilise
Metal Performance Shaders pour accélérer les calculs.
"""

import logging
from typing import Any, Optional

from services.llm_provider import LLMProvider, LLMMessage, LLMResponse

logger = logging.getLogger(__name__)


class MLXProvider(LLMProvider):
    """
    Provider pour l'inférence locale avec MLX.

    Utilise mlx-lm pour charger et exécuter des modèles quantifiés
    optimisés pour Apple Silicon.
    """

    def __init__(
        self,
        model_name: str = "mlx-community/Phi-3-mini-4k-instruct-4bit",
        **kwargs
    ):
        """
        Initialise le provider MLX.

        Args:
            model_name: Nom du modèle Hugging Face compatible MLX
                       (doit être dans mlx-community ou converti)
            **kwargs: Configuration additionnelle
        """
        super().__init__(model_name, **kwargs)

        self.model = None
        self.tokenizer = None
        self._model_loaded = False

        # Configuration par défaut
        self.default_max_tokens = kwargs.get("max_tokens", 2000)
        self.default_temperature = kwargs.get("temperature", 0.7)

        logger.info(f"MLXProvider initialisé avec modèle: {model_name}")

    def _load_model(self):
        """
        Charge le modèle MLX en mémoire.

        Cette opération peut prendre quelques secondes la première fois
        car le modèle doit être téléchargé et compilé.
        """
        if self._model_loaded:
            return

        try:
            logger.info(f"Chargement du modèle MLX: {self.model_name}")

            # Import ici pour éviter de charger MLX si non utilisé
            from mlx_lm import load, generate

            # Charger le modèle et le tokenizer
            self.model, self.tokenizer = load(self.model_name)

            self._model_loaded = True
            logger.info("✓ Modèle MLX chargé avec succès")

        except Exception as e:
            logger.error(f"❌ Erreur lors du chargement du modèle MLX: {e}")
            raise RuntimeError(f"Impossible de charger le modèle MLX: {e}")

    def generate(
        self,
        messages: list[LLMMessage],
        max_tokens: int = 2000,
        temperature: float = 0.7,
        **kwargs
    ) -> LLMResponse:
        """
        Génère une réponse avec MLX.

        Args:
            messages: Liste de messages de la conversation
            max_tokens: Nombre maximum de tokens à générer
            temperature: Température (0.0 = déterministe, 1.0 = créatif)
            **kwargs: Paramètres additionnels pour MLX

        Returns:
            LLMResponse avec la réponse générée
        """
        # Charger le modèle si nécessaire
        if not self._model_loaded:
            self._load_model()

        # Formater les messages en un prompt
        prompt = self._format_prompt_for_model(messages)

        logger.debug(f"Génération avec MLX (max_tokens={max_tokens}, temp={temperature})")

        try:
            from mlx_lm import generate

            # Générer avec MLX
            # Note: mlx-lm ne supporte pas tous les paramètres standard
            # On utilise seulement max_tokens pour l'instant
            response_text = generate(
                model=self.model,
                tokenizer=self.tokenizer,
                prompt=prompt,
                max_tokens=max_tokens,
                verbose=False,  # Pas de logging verbeux
            )

            # Nettoyer la réponse (enlever le prompt si présent)
            if response_text.startswith(prompt):
                response_text = response_text[len(prompt):].strip()

            return LLMResponse(
                content=response_text,
                model=self.model_name,
                tokens_used=None,  # MLX ne retourne pas le compte de tokens facilement
                finish_reason="stop",
                metadata={
                    "provider": "mlx",
                    "temperature": temperature,
                    "max_tokens": max_tokens
                }
            )

        except Exception as e:
            logger.error(f"❌ Erreur lors de la génération MLX: {e}")
            raise RuntimeError(f"Erreur de génération MLX: {e}")

    def _format_prompt_for_model(self, messages: list[LLMMessage]) -> str:
        """
        Formate les messages selon le format attendu par le modèle.

        Différents modèles utilisent différents formats:
        - Mistral/Hermes: <|im_start|>role\ncontent<|im_end|>
        - Llama: [INST] user [/INST]
        - etc.

        Pour Nous-Hermes-2-Mistral, on utilise le format ChatML.
        """
        formatted_parts = []

        for msg in messages:
            if msg.role == "system":
                formatted_parts.append(
                    f"<|im_start|>system\n{msg.content}<|im_end|>"
                )
            elif msg.role == "user":
                formatted_parts.append(
                    f"<|im_start|>user\n{msg.content}<|im_end|>"
                )
            elif msg.role == "assistant":
                formatted_parts.append(
                    f"<|im_start|>assistant\n{msg.content}<|im_end|>"
                )

        # Ajouter le début de la réponse de l'assistant
        formatted_parts.append("<|im_start|>assistant\n")

        return "\n".join(formatted_parts)

    def is_available(self) -> bool:
        """
        Vérifie si MLX est disponible sur ce système.

        Returns:
            True si MLX peut être utilisé (Mac avec Apple Silicon)
        """
        try:
            import platform
            import mlx.core as mx

            # Vérifier qu'on est sur macOS avec Apple Silicon
            is_mac = platform.system() == "Darwin"
            is_arm = platform.machine() == "arm64"

            if not (is_mac and is_arm):
                logger.warning(
                    "MLX n'est disponible que sur macOS avec Apple Silicon (M1/M2/M3)"
                )
                return False

            # Vérifier que MLX fonctionne
            _ = mx.array([1, 2, 3])

            return True

        except ImportError:
            logger.error("MLX n'est pas installé")
            return False
        except Exception as e:
            logger.error(f"MLX n'est pas disponible: {e}")
            return False

    def get_info(self) -> dict[str, Any]:
        """
        Retourne les informations sur ce provider.

        Returns:
            Dictionnaire avec les informations
        """
        return {
            "name": "MLX Provider",
            "model": self.model_name,
            "available": self.is_available(),
            "loaded": self._model_loaded,
            "platform": "Apple Silicon (M1/M2/M3)",
            "config": {
                "max_tokens": self.default_max_tokens,
                "temperature": self.default_temperature,
                **self.config
            }
        }

    def unload_model(self):
        """
        Décharge le modèle de la mémoire.

        Utile pour libérer la RAM si le modèle n'est plus utilisé.
        """
        if self._model_loaded:
            logger.info("Déchargement du modèle MLX...")
            self.model = None
            self.tokenizer = None
            self._model_loaded = False

            # Forcer le garbage collector
            import gc
            gc.collect()

            logger.info("✓ Modèle déchargé")


# ========================================
# Modèles MLX recommandés
# ========================================

RECOMMENDED_MLX_MODELS = {
    "hermes-7b-4bit": {
        "name": "mlx-community/Nous-Hermes-2-Mistral-7B-DPO-4bit",
        "description": "Modèle polyvalent 7B, quantifié 4-bit (~4GB RAM)",
        "size": "~4GB",
        "quality": "Excellent",
        "speed": "Rapide"
    },
    "mistral-7b-4bit": {
        "name": "mlx-community/Mistral-7B-Instruct-v0.2-4bit",
        "description": "Mistral 7B officiel, quantifié 4-bit",
        "size": "~4GB",
        "quality": "Très bon",
        "speed": "Rapide"
    },
    "phi-3-mini": {
        "name": "mlx-community/Phi-3-mini-4k-instruct-4bit",
        "description": "Petit modèle Microsoft, très rapide",
        "size": "~2GB",
        "quality": "Bon",
        "speed": "Très rapide"
    },
    "llama-3-8b": {
        "name": "mlx-community/Meta-Llama-3-8B-Instruct-4bit",
        "description": "Llama 3 de Meta, très performant",
        "size": "~5GB",
        "quality": "Excellent",
        "speed": "Rapide"
    }
}


def get_recommended_model(preference: str = "balanced") -> str:
    """
    Retourne un modèle recommandé selon la préférence.

    Args:
        preference: "fast" (rapide), "balanced" (équilibré), "quality" (qualité)

    Returns:
        Nom du modèle recommandé
    """
    if preference == "fast":
        return RECOMMENDED_MLX_MODELS["phi-3-mini"]["name"]
    elif preference == "quality":
        return RECOMMENDED_MLX_MODELS["llama-3-8b"]["name"]
    else:  # balanced
        return RECOMMENDED_MLX_MODELS["hermes-7b-4bit"]["name"]
