"""
Configuration centralisée de l'application.

Ce fichier charge et valide toutes les variables d'environnement
en utilisant Pydantic Settings pour une gestion type-safe.
"""

from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Configuration de l'application.

    Les valeurs sont automatiquement chargées depuis:
    1. Variables d'environnement
    2. Fichier .env
    3. Valeurs par défaut définies ici
    """

    # ===== Configuration API =====
    api_host: str = Field(default="0.0.0.0", description="Host de l'API")
    api_port: int = Field(default=8000, description="Port de l'API")
    api_reload: bool = Field(default=True, description="Auto-reload en développement")
    debug: bool = Field(default=True, description="Mode debug")

    # ===== Sécurité =====
    secret_key: str = Field(
        default="dev-secret-key-change-in-production",
        description="Clé secrète pour JWT"
    )
    algorithm: str = Field(default="HS256", description="Algorithme de chiffrement JWT")
    access_token_expire_minutes: int = Field(
        default=30,
        description="Durée de validité du token (minutes)"
    )

    # ===== Base de données SurrealDB =====
    surreal_url: str = Field(
        default="ws://localhost:8001/rpc",
        description="URL de connexion SurrealDB (WebSocket)"
    )
    surreal_namespace: str = Field(
        default="notary",
        description="Namespace SurrealDB"
    )
    surreal_database: str = Field(
        default="notary_db",
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
        description="Répertoire pour les fichiers uploadés"
    )
    max_upload_size_mb: int = Field(
        default=50,
        description="Taille maximale des uploads (MB)"
    )

    # ===== Configuration LLM =====
    llm_provider: Literal["mlx", "huggingface", "anthropic", "ollama"] = Field(
        default="mlx",
        description="Fournisseur de LLM"
    )

    # MLX (Apple Silicon - Local)
    mlx_model_path: str = Field(
        default="mlx-community/Phi-3-mini-4k-instruct-4bit",
        description="Modèle MLX à utiliser"
    )

    # Hugging Face (Transformers - Local)
    hf_model_name: str = Field(
        default="mistralai/Mistral-7B-Instruct-v0.2",
        description="Modèle Hugging Face"
    )
    hf_device: str = Field(
        default="auto",
        description="Device pour HF (auto, mps, cuda, cpu)"
    )
    hf_load_in_8bit: bool = Field(
        default=False,
        description="Charger le modèle HF en 8-bit (économise RAM)"
    )
    hf_load_in_4bit: bool = Field(
        default=False,
        description="Charger le modèle HF en 4-bit (économise encore plus RAM)"
    )

    # Anthropic (Claude API - Cloud)
    anthropic_api_key: str = Field(
        default="",
        description="Clé API Anthropic"
    )
    anthropic_model: str = Field(
        default="claude-3-5-sonnet-20241022",
        description="Modèle Claude à utiliser"
    )

    # Ollama (Local - Cross-platform)
    ollama_base_url: str = Field(
        default="http://localhost:11434",
        description="URL de l'API Ollama"
    )
    ollama_model: str = Field(
        default="mistral",
        description="Modèle Ollama à utiliser"
    )

    # ===== Agno =====
    agno_log_level: str = Field(default="INFO", description="Niveau de log Agno")
    agno_storage_path: Path = Field(
        default=Path("./data/agno_state"),
        description="Stockage de l'état Agno"
    )

    # Configuration de Pydantic Settings
    model_config = SettingsConfigDict(
        # Chercher .env dans le répertoire parent de config/
        env_file=str(Path(__file__).parent.parent / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    def __init__(self, **kwargs):
        """Initialise et crée les répertoires nécessaires."""
        super().__init__(**kwargs)

        # Créer les répertoires s'ils n'existent pas
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.agno_storage_path.mkdir(parents=True, exist_ok=True)


# Instance globale de configuration
settings = Settings()
