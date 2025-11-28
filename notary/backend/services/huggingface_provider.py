"""
Provider Hugging Face pour l'inférence locale avec transformers.

Utilise la bibliothèque transformers pour charger et exécuter
n'importe quel modèle open-source de Hugging Face.

Supporte les accélérateurs:
- MPS (Apple Silicon M1/M2/M3)
- CUDA (NVIDIA)
- CPU (fallback)
"""

import logging
from typing import Any, Optional

from services.llm_provider import LLMProvider, LLMMessage, LLMResponse

logger = logging.getLogger(__name__)


class HuggingFaceProvider(LLMProvider):
    """
    Provider pour l'inférence locale avec Hugging Face Transformers.

    Utilise la bibliothèque transformers pour charger et exécuter
    des modèles open-source localement.
    """

    def __init__(
        self,
        model_name: str = "mistralai/Mistral-7B-Instruct-v0.2",
        device: str = "auto",
        **kwargs
    ):
        """
        Initialise le provider Hugging Face.

        Args:
            model_name: Nom du modèle Hugging Face (ex: "mistralai/Mistral-7B-Instruct-v0.2")
            device: Device à utiliser ("auto", "mps", "cuda", "cpu")
            **kwargs: Configuration additionnelle
                - load_in_8bit: Charger en 8-bit pour économiser la RAM (bool)
                - load_in_4bit: Charger en 4-bit pour économiser encore plus (bool)
                - trust_remote_code: Autoriser l'exécution de code distant (bool)
        """
        super().__init__(model_name, **kwargs)

        self.device = device
        self.model = None
        self.tokenizer = None
        self._model_loaded = False

        # Configuration par défaut
        self.load_in_8bit = kwargs.get("load_in_8bit", False)
        self.load_in_4bit = kwargs.get("load_in_4bit", False)
        self.trust_remote_code = kwargs.get("trust_remote_code", False)
        self.default_max_tokens = kwargs.get("max_tokens", 2000)
        self.default_temperature = kwargs.get("temperature", 0.7)

        logger.info(f"HuggingFaceProvider initialisé avec modèle: {model_name}")

    def _detect_device(self) -> str:
        """
        Détecte automatiquement le meilleur device disponible.

        Returns:
            Device à utiliser: "mps", "cuda", ou "cpu"
        """
        try:
            import torch
            import platform

            if self.device != "auto":
                return self.device

            # Vérifier CUDA (NVIDIA)
            if torch.cuda.is_available():
                logger.info("✓ CUDA détecté (NVIDIA GPU)")
                return "cuda"

            # Vérifier MPS (Apple Silicon)
            if platform.system() == "Darwin" and platform.machine() == "arm64":
                if torch.backends.mps.is_available():
                    logger.info("✓ MPS détecté (Apple Silicon)")
                    return "mps"

            # Fallback sur CPU
            logger.info("Utilisation du CPU (pas de GPU détecté)")
            return "cpu"

        except Exception as e:
            logger.warning(f"Erreur lors de la détection du device: {e}. Utilisation du CPU.")
            return "cpu"

    def _load_model(self):
        """
        Charge le modèle et le tokenizer Hugging Face.

        Cette opération peut prendre du temps car le modèle
        doit être téléchargé (si pas en cache) et chargé en mémoire.
        """
        if self._model_loaded:
            return

        try:
            logger.info(f"Chargement du modèle Hugging Face: {self.model_name}")

            from transformers import AutoTokenizer, AutoModelForCausalLM
            import torch

            # Détecter le device
            device = self._detect_device()

            # Préparer les arguments de chargement
            model_kwargs = {
                "trust_remote_code": self.trust_remote_code,
            }

            # Quantization (pour économiser la RAM)
            if self.load_in_8bit:
                model_kwargs["load_in_8bit"] = True
                model_kwargs["device_map"] = "auto"
                logger.info("Chargement en 8-bit activé")
            elif self.load_in_4bit:
                model_kwargs["load_in_4bit"] = True
                model_kwargs["device_map"] = "auto"
                logger.info("Chargement en 4-bit activé")
            else:
                model_kwargs["torch_dtype"] = torch.float16 if device != "cpu" else torch.float32

            # Charger le tokenizer
            self.tokenizer = AutoTokenizer.from_pretrained(
                self.model_name,
                trust_remote_code=self.trust_remote_code
            )

            # Charger le modèle
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_name,
                **model_kwargs
            )

            # Déplacer sur le device si pas de quantization
            if not (self.load_in_8bit or self.load_in_4bit):
                self.model = self.model.to(device)

            self.model.eval()  # Mode évaluation (pas d'entraînement)

            self._model_loaded = True
            self.device = device

            logger.info(f"✓ Modèle chargé avec succès sur {device}")

        except Exception as e:
            logger.error(f"❌ Erreur lors du chargement du modèle HF: {e}")
            raise RuntimeError(f"Impossible de charger le modèle Hugging Face: {e}")

    def generate(
        self,
        messages: list[LLMMessage],
        max_tokens: int = 2000,
        temperature: float = 0.7,
        **kwargs
    ) -> LLMResponse:
        """
        Génère une réponse avec Hugging Face Transformers.

        Args:
            messages: Liste de messages de la conversation
            max_tokens: Nombre maximum de tokens à générer
            temperature: Température (0.0 = déterministe, 1.0 = créatif)
            **kwargs: Paramètres additionnels (top_p, top_k, repetition_penalty, etc.)

        Returns:
            LLMResponse avec la réponse générée
        """
        # Charger le modèle si nécessaire
        if not self._model_loaded:
            self._load_model()

        # Formater le prompt
        prompt = self._format_prompt(messages)

        logger.debug(f"Génération avec HF (max_tokens={max_tokens}, temp={temperature})")

        try:
            import torch

            # Tokenizer le prompt
            inputs = self.tokenizer(prompt, return_tensors="pt").to(self.device)

            # Préparer les paramètres de génération
            gen_kwargs = {
                "max_new_tokens": max_tokens,
                "temperature": temperature,
                "do_sample": temperature > 0,  # Sampling si température > 0
                "pad_token_id": self.tokenizer.eos_token_id,
            }

            # Ajouter les paramètres optionnels
            if "top_p" in kwargs:
                gen_kwargs["top_p"] = kwargs["top_p"]
            if "top_k" in kwargs:
                gen_kwargs["top_k"] = kwargs["top_k"]
            if "repetition_penalty" in kwargs:
                gen_kwargs["repetition_penalty"] = kwargs["repetition_penalty"]

            # Générer
            with torch.no_grad():
                outputs = self.model.generate(
                    inputs.input_ids,
                    **gen_kwargs
                )

            # Décoder la réponse
            generated_text = self.tokenizer.decode(
                outputs[0],
                skip_special_tokens=True
            )

            # Nettoyer (enlever le prompt)
            if generated_text.startswith(prompt):
                response_text = generated_text[len(prompt):].strip()
            else:
                response_text = generated_text.strip()

            # Calculer le nombre de tokens (approximatif)
            tokens_used = len(outputs[0])

            return LLMResponse(
                content=response_text,
                model=self.model_name,
                tokens_used=tokens_used,
                finish_reason="stop",
                metadata={
                    "provider": "huggingface",
                    "device": self.device,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                }
            )

        except Exception as e:
            logger.error(f"❌ Erreur lors de la génération HF: {e}")
            raise RuntimeError(f"Erreur de génération Hugging Face: {e}")

    def _format_prompt(self, messages: list[LLMMessage]) -> str:
        """
        Formate les messages en un prompt texte.

        Utilise le template du tokenizer si disponible,
        sinon utilise un format générique.
        """
        # Vérifier si le tokenizer a un chat template
        if hasattr(self.tokenizer, "chat_template") and self.tokenizer.chat_template:
            # Convertir nos messages au format attendu par le tokenizer
            chat_messages = [
                {"role": msg.role, "content": msg.content}
                for msg in messages
            ]
            return self.tokenizer.apply_chat_template(
                chat_messages,
                tokenize=False,
                add_generation_prompt=True
            )

        # Sinon, utiliser un format générique (ChatML)
        formatted_parts = []

        for msg in messages:
            if msg.role == "system":
                formatted_parts.append(f"<|im_start|>system\n{msg.content}<|im_end|>")
            elif msg.role == "user":
                formatted_parts.append(f"<|im_start|>user\n{msg.content}<|im_end|>")
            elif msg.role == "assistant":
                formatted_parts.append(f"<|im_start|>assistant\n{msg.content}<|im_end|>")

        formatted_parts.append("<|im_start|>assistant\n")

        return "\n".join(formatted_parts)

    def is_available(self) -> bool:
        """
        Vérifie si Hugging Face Transformers est disponible.

        Returns:
            True si transformers et torch sont installés
        """
        try:
            import transformers
            import torch

            return True

        except ImportError:
            logger.warning(
                "Les packages 'transformers' et 'torch' ne sont pas installés. "
                "Installez-les avec: uv add transformers torch"
            )
            return False
        except Exception as e:
            logger.error(f"Hugging Face non disponible: {e}")
            return False

    def get_info(self) -> dict[str, Any]:
        """
        Retourne les informations sur ce provider.

        Returns:
            Dictionnaire avec les informations
        """
        device = self._detect_device() if not self._model_loaded else self.device

        return {
            "name": "Hugging Face Provider",
            "model": self.model_name,
            "available": self.is_available(),
            "loaded": self._model_loaded,
            "device": device,
            "platform": "Hugging Face Transformers (Local)",
            "config": {
                "max_tokens": self.default_max_tokens,
                "temperature": self.default_temperature,
                "load_in_8bit": self.load_in_8bit,
                "load_in_4bit": self.load_in_4bit,
                **self.config
            }
        }

    def unload_model(self):
        """
        Décharge le modèle de la mémoire.

        Utile pour libérer la RAM/VRAM.
        """
        if self._model_loaded:
            logger.info("Déchargement du modèle Hugging Face...")
            self.model = None
            self.tokenizer = None
            self._model_loaded = False

            # Libérer la mémoire GPU si disponible
            try:
                import torch
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                elif torch.backends.mps.is_available():
                    torch.mps.empty_cache()
            except:
                pass

            # Forcer le garbage collector
            import gc
            gc.collect()

            logger.info("✓ Modèle déchargé")


# ========================================
# Modèles Hugging Face recommandés
# ========================================

RECOMMENDED_HF_MODELS = {
    "mistral-7b": {
        "name": "mistralai/Mistral-7B-Instruct-v0.2",
        "description": "Mistral 7B officiel - Excellent rapport qualité/performance",
        "size": "~14GB (fp16)",
        "languages": "Multilingue (excellent français)",
        "quantization": "8-bit recommandé"
    },
    "llama-3-8b": {
        "name": "meta-llama/Meta-Llama-3-8B-Instruct",
        "description": "Llama 3 de Meta - Très performant",
        "size": "~16GB (fp16)",
        "languages": "Multilingue",
        "quantization": "8-bit recommandé"
    },
    "phi-3": {
        "name": "microsoft/Phi-3-mini-4k-instruct",
        "description": "Petit modèle Microsoft - Rapide et efficace",
        "size": "~7GB (fp16)",
        "languages": "Multilingue",
        "quantization": "Non nécessaire (déjà petit)"
    },
    "gemma-7b": {
        "name": "google/gemma-7b-it",
        "description": "Gemma de Google - Très bon sur les instructions",
        "size": "~14GB (fp16)",
        "languages": "Multilingue",
        "quantization": "8-bit recommandé"
    },
    "zephyr-7b": {
        "name": "HuggingFaceH4/zephyr-7b-beta",
        "description": "Zephyr - Fine-tuné pour suivre des instructions",
        "size": "~14GB (fp16)",
        "languages": "Multilingue",
        "quantization": "8-bit recommandé"
    }
}


def get_hf_model(preference: str = "balanced") -> str:
    """
    Retourne un modèle Hugging Face recommandé selon la préférence.

    Args:
        preference: "fast" (rapide), "balanced" (équilibré), "quality" (qualité)

    Returns:
        Nom du modèle Hugging Face
    """
    if preference == "fast":
        return RECOMMENDED_HF_MODELS["phi-3"]["name"]
    elif preference == "quality":
        return RECOMMENDED_HF_MODELS["llama-3-8b"]["name"]
    else:  # balanced
        return RECOMMENDED_HF_MODELS["mistral-7b"]["name"]
