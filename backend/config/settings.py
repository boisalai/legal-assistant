"""
Configuration centralisee de l'application Legal Assistant.

Ce fichier charge et valide toutes les variables d'environnement
en utilisant Pydantic Settings pour une gestion type-safe.
"""

from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Load .env file into os.environ for SDK clients that check os.environ directly
# (e.g., Anthropic SDK used by Agno)
_env_path = Path(__file__).parent.parent / ".env"
load_dotenv(_env_path)


class Settings(BaseSettings):
    """
    Configuration de l'application.

    Les valeurs sont automatiquement chargees depuis:
    1. Variables d'environnement
    2. Fichier .env
    3. Valeurs par defaut definies ici
    """

    # ===== Configuration API =====
    api_host: str = Field(default="0.0.0.0", description="Host de l'API")
    api_port: int = Field(default=8000, description="Port de l'API")
    api_reload: bool = Field(default=True, description="Auto-reload en developpement")
    debug: bool = Field(default=True, description="Mode debug")

    # ===== Securite =====
    secret_key: str = Field(
        default="dev-secret-key-change-in-production",
        description="Cle secrete pour JWT"
    )
    algorithm: str = Field(default="HS256", description="Algorithme de chiffrement JWT")
    access_token_expire_minutes: int = Field(
        default=30,
        description="Duree de validite du token (minutes)"
    )

    # ===== Base de donnees SurrealDB =====
    surreal_url: str = Field(
        default="ws://localhost:8002/rpc",
        description="URL de connexion SurrealDB (WebSocket)"
    )
    surreal_namespace: str = Field(
        default="legal",
        description="Namespace SurrealDB"
    )
    surreal_database: str = Field(
        default="legal_db",
        description="Database SurrealDB"
    )
    surreal_username: str = Field(
        default="root",
        description="Utilisateur SurrealDB"
    )
    surreal_password: str = Field(
        default="root",
        description="Mot de passe SurrealDB"
    )

    # ===== Stockage de fichiers =====
    upload_dir: Path = Field(
        default=Path("./data/uploads"),
        description="Repertoire pour les fichiers uploades"
    )
    max_upload_size_mb: int = Field(
        default=50,
        description="Taille maximale des uploads (MB)"
    )

    # ===== Configuration LLM =====
    llm_provider: Literal["mlx", "huggingface", "anthropic", "ollama"] = Field(
        default="ollama",
        description="Fournisseur de LLM"
    )

    # Model ID unifie (format: provider:model)
    model_id: str = Field(
        default="ollama:qwen2.5:7b",
        description="ID du modele au format provider:model"
    )

    # MLX (Apple Silicon - Local)
    mlx_model_path: str = Field(
        default="mlx-community/Phi-3-mini-4k-instruct-4bit",
        description="Modele MLX a utiliser"
    )

    # Hugging Face (Transformers - Local)
    hf_model_name: str = Field(
        default="mistralai/Mistral-7B-Instruct-v0.2",
        description="Modele Hugging Face"
    )
    hf_device: str = Field(
        default="auto",
        description="Device pour HF (auto, mps, cuda, cpu)"
    )

    # Anthropic (Claude API - Cloud)
    anthropic_api_key: str = Field(
        default="",
        description="Cle API Anthropic"
    )
    anthropic_model: str = Field(
        default="claude-sonnet-4-5-20250929",
        description="Modele Claude a utiliser"
    )

    # Google (Gemini API - Cloud)
    google_api_key: str = Field(
        default="",
        description="Clé API Google Gemini"
    )
    google_model: str = Field(
        default="gemini-1.5-pro",
        description="Modèle Google à utiliser"
    )

    # Ollama (Local - Cross-platform)
    ollama_base_url: str = Field(
        default="http://localhost:11434",
        description="URL de l'API Ollama"
    )
    ollama_model: str = Field(
        default="qwen2.5:7b",
        description="Modele Ollama a utiliser"
    )

    # ===== Embeddings pour recherche sémantique =====
    embedding_provider: Literal["local", "openai"] = Field(
        default="local",
        description="Provider d'embeddings (local: gratuit, openai: payant)"
    )
    embedding_model: str = Field(
        default="BAAI/bge-m3",
        description="Modèle d'embedding à utiliser"
    )
    openai_api_key: str = Field(
        default="",
        description="Clé API OpenAI pour embeddings (si provider=openai)"
    )

    # ===== Agno =====
    agno_log_level: str = Field(default="INFO", description="Niveau de log Agno")
    agno_storage_path: Path = Field(
        default=Path("./data/agno_state"),
        description="Stockage de l'etat Agno"
    )

    # ===== Synchronisation automatique des répertoires liés =====
    auto_sync_interval: int = Field(
        default=300,
        description="Intervalle de synchronisation automatique des répertoires liés (secondes)"
    )
    auto_sync_enabled: bool = Field(
        default=True,
        description="Activer la synchronisation automatique des répertoires liés"
    )

    # Configuration de Pydantic Settings
    model_config = SettingsConfigDict(
        env_file=str(Path(__file__).parent.parent / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    def __init__(self, **kwargs):
        """Initialise et cree les repertoires necessaires."""
        super().__init__(**kwargs)

        # Creer les repertoires s'ils n'existent pas
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.agno_storage_path.mkdir(parents=True, exist_ok=True)


# Instance globale de configuration
settings = Settings()
