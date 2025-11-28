"""
Service principal pour la gestion des LLMs.

Ce service:
- Choisit le bon provider selon la configuration
- Fournit une interface unifiée pour tous les workflows
- Gère le cache et l'optimisation
"""

import logging
from typing import Optional

from config import settings
from services.llm_provider import LLMProvider, LLMMessage, LLMResponse
from services.mlx_provider import MLXProvider, get_recommended_model

logger = logging.getLogger(__name__)


class LLMService:
    """
    Service principal pour l'inférence LLM.

    Ce service choisit automatiquement le bon provider selon
    la configuration et fournit une interface simple pour les workflows.
    """

    def __init__(self):
        """
        Initialise le service LLM.

        Le provider est choisi selon settings.llm_provider.
        """
        self.provider: Optional[LLMProvider] = None
        self._initialize_provider()

    def _initialize_provider(self):
        """
        Initialise le provider selon la configuration.
        """
        provider_type = settings.llm_provider.lower()

        logger.info(f"Initialisation du provider LLM: {provider_type}")

        if provider_type == "mlx":
            self._init_mlx_provider()
        elif provider_type == "anthropic":
            self._init_anthropic_provider()
        elif provider_type == "huggingface":
            self._init_huggingface_provider()
        elif provider_type == "ollama":
            self._init_ollama_provider()
        else:
            raise ValueError(
                f"Provider LLM inconnu: {provider_type}. "
                f"Valeurs acceptées: mlx, anthropic, huggingface, ollama"
            )

    def _init_mlx_provider(self):
        """Initialise le provider MLX."""
        try:
            # Vérifier que MLX est disponible
            from services.mlx_provider import MLXProvider

            # Utiliser le modèle configuré ou le modèle par défaut
            model_name = settings.mlx_model_path or get_recommended_model("balanced")

            self.provider = MLXProvider(model_name=model_name)

            if not self.provider.is_available():
                raise RuntimeError(
                    "MLX n'est pas disponible sur ce système. "
                    "MLX nécessite macOS avec Apple Silicon (M1/M2/M3)"
                )

            logger.info(f"✓ Provider MLX initialisé avec: {model_name}")

        except Exception as e:
            logger.error(f"❌ Erreur lors de l'initialisation de MLX: {e}")
            raise

    def _init_anthropic_provider(self):
        """Initialise le provider Anthropic."""
        try:
            from services.anthropic_provider import AnthropicProvider, get_claude_model

            # Utiliser le modèle configuré ou le modèle par défaut
            model_name = settings.anthropic_model or get_claude_model("balanced")
            api_key = settings.anthropic_api_key

            self.provider = AnthropicProvider(
                model_name=model_name,
                api_key=api_key
            )

            if not self.provider.is_available():
                raise RuntimeError(
                    "Anthropic n'est pas disponible. "
                    "Vérifiez que ANTHROPIC_API_KEY est définie dans .env"
                )

            logger.info(f"✓ Provider Anthropic initialisé avec: {model_name}")

        except Exception as e:
            logger.error(f"❌ Erreur lors de l'initialisation d'Anthropic: {e}")
            raise

    def _init_huggingface_provider(self):
        """Initialise le provider Hugging Face."""
        try:
            from services.huggingface_provider import HuggingFaceProvider, get_hf_model

            # Utiliser le modèle configuré ou le modèle par défaut
            model_name = settings.hf_model_name or get_hf_model("balanced")
            device = settings.hf_device

            # Configuration pour la quantization
            load_in_8bit = settings.hf_load_in_8bit
            load_in_4bit = settings.hf_load_in_4bit

            self.provider = HuggingFaceProvider(
                model_name=model_name,
                device=device,
                load_in_8bit=load_in_8bit,
                load_in_4bit=load_in_4bit,
            )

            if not self.provider.is_available():
                raise RuntimeError(
                    "Hugging Face n'est pas disponible. "
                    "Installez transformers et torch avec: uv add transformers torch"
                )

            logger.info(f"✓ Provider Hugging Face initialisé avec: {model_name}")

        except Exception as e:
            logger.error(f"❌ Erreur lors de l'initialisation de Hugging Face: {e}")
            raise

    def _init_ollama_provider(self):
        """Initialise le provider Ollama."""
        try:
            from services.ollama_provider import OllamaProvider, get_ollama_model

            # Utiliser le modèle configuré ou le modèle par défaut
            model_name = settings.ollama_model or get_ollama_model("balanced")
            base_url = settings.ollama_base_url

            self.provider = OllamaProvider(
                model_name=model_name,
                base_url=base_url
            )

            if not self.provider.is_available():
                raise RuntimeError(
                    "Ollama n'est pas disponible. "
                    "Installez Ollama depuis https://ollama.ai et démarrez-le avec: ollama serve"
                )

            logger.info(f"✓ Provider Ollama initialisé avec: {model_name}")

        except Exception as e:
            logger.error(f"❌ Erreur lors de l'initialisation d'Ollama: {e}")
            raise

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 2000,
        temperature: float = 0.7,
        **kwargs
    ) -> str:
        """
        Génère une réponse simple à partir d'un prompt.

        Args:
            prompt: Le prompt utilisateur
            system_prompt: Instructions système optionnelles
            max_tokens: Nombre maximum de tokens
            temperature: Température de génération
            **kwargs: Paramètres additionnels

        Returns:
            Texte généré
        """
        messages = []

        # Ajouter le message système si fourni
        if system_prompt:
            messages.append(LLMMessage(role="system", content=system_prompt))

        # Ajouter le prompt utilisateur
        messages.append(LLMMessage(role="user", content=prompt))

        # Générer
        response = self.provider.generate(
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
            **kwargs
        )

        return response.content

    def generate_with_messages(
        self,
        messages: list[LLMMessage],
        max_tokens: int = 2000,
        temperature: float = 0.7,
        **kwargs
    ) -> LLMResponse:
        """
        Génère une réponse à partir d'une conversation complète.

        Args:
            messages: Liste de messages (system, user, assistant)
            max_tokens: Nombre maximum de tokens
            temperature: Température
            **kwargs: Paramètres additionnels

        Returns:
            LLMResponse complète
        """
        return self.provider.generate(
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
            **kwargs
        )

    def get_provider_info(self) -> dict:
        """
        Retourne les informations sur le provider actuel.

        Returns:
            Dictionnaire avec les informations
        """
        if self.provider:
            return self.provider.get_info()
        return {"error": "Aucun provider initialisé"}

    def is_ready(self) -> bool:
        """
        Vérifie si le service est prêt à générer.

        Returns:
            True si le service est opérationnel
        """
        return (
            self.provider is not None
            and self.provider.is_available()
        )

    # ========================================
    # Helpers pour créer des messages
    # ========================================

    @staticmethod
    def create_system_message(content: str) -> LLMMessage:
        """Helper pour créer un message système."""
        return LLMMessage(role="system", content=content)

    @staticmethod
    def create_user_message(content: str) -> LLMMessage:
        """Helper pour créer un message utilisateur."""
        return LLMMessage(role="user", content=content)

    @staticmethod
    def create_assistant_message(content: str) -> LLMMessage:
        """Helper pour créer un message assistant."""
        return LLMMessage(role="assistant", content=content)


# ========================================
# Instance globale du service
# ========================================

# Cette instance sera importée partout où on a besoin du LLM
llm_service: Optional[LLMService] = None


def get_llm_service() -> LLMService:
    """
    Retourne l'instance globale du LLM service.

    Cette fonction crée le service la première fois qu'elle est appelée
    (lazy initialization) pour éviter de charger le modèle au démarrage.

    Returns:
        Instance de LLMService
    """
    global llm_service

    if llm_service is None:
        logger.info("Initialisation du LLM Service...")
        llm_service = LLMService()

    return llm_service


def test_llm_service():
    """
    Fonction de test pour vérifier que le LLM fonctionne.

    Returns:
        True si le test passe, False sinon
    """
    try:
        logger.info("🧪 Test du LLM Service...")

        service = get_llm_service()

        # Vérifier que le service est prêt
        if not service.is_ready():
            logger.error("❌ Service LLM pas prêt")
            return False

        # Test simple
        prompt = "Réponds en un mot: Quelle est la capitale de la France?"

        response = service.generate(
            prompt=prompt,
            max_tokens=50,
            temperature=0.1  # Déterministe
        )

        logger.info(f"Question: {prompt}")
        logger.info(f"Réponse: {response}")

        # Vérifier qu'on a une réponse
        if response and len(response) > 0:
            logger.info("✓ Test réussi!")
            return True
        else:
            logger.error("❌ Réponse vide")
            return False

    except Exception as e:
        logger.error(f"❌ Erreur lors du test: {e}")
        return False
