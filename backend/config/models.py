"""
Configuration des modèles LLM pour Notary Assistant.

Ce fichier centralise la configuration de tous les modèles supportés:
- Ollama: Modèles locaux open-source
- Claude: API Anthropic (production)
- MLX: Modèles Apple Silicon via OpenAI-compatible API

Modèles recommandés pour MacBook Pro M1 Pro 16 Go (testés 2025-11-20):
- Ollama: qwen2.5:7b (80% confiance), llama3.2 (70%, ultra-rapide)
- MLX: Phi-3-mini, Llama-3.2, Mistral-7B (quantized)

⚠️ phi3 ne supporte pas les tools (function calling) - À ÉVITER
"""

from typing import Literal

# ========================================
# Modèles Ollama recommandés pour M1 Pro 16 Go
# ========================================

OllamaModel = Literal[
    "mistral",          # 7B params, excellent qualité/performance (4 GB RAM)
    "llama3.2",         # 3B params, très rapide (2 GB RAM)
    "phi3",             # 3.8B params, excellent pour extraction (2.3 GB RAM)
    "qwen2.5:7b",       # 7B params, excellent multilingual (4.7 GB RAM)
    "gemma2:9b",        # 9B params, très bon raisonnement (5.5 GB RAM)
    "llama3.1:8b",      # 8B params, très bon général (4.7 GB RAM)
]

OLLAMA_MODELS_INFO = {
    "qwen2.5:7b": {
        "name": "Qwen 2.5 7B",
        "params": "7B",
        "ram": "4.7 GB",
        "speed": "Medium",  # 83.64s testé
        "quality": "Excellent",
        "best_for": "Production locale - Meilleur score (80% confiance)",
        "recommended": True,
        "test_score": "80%",
        "test_duration": "83.64s",
    },
    "llama3.2": {
        "name": "Llama 3.2",
        "params": "3B",
        "ram": "2 GB",
        "speed": "Very Fast",  # 38.44s testé - LE PLUS RAPIDE
        "quality": "Good",
        "best_for": "Développement - Meilleur rapport qualité/vitesse (70% confiance)",
        "recommended": True,
        "test_score": "70%",
        "test_duration": "38.44s",
    },
    "mistral": {
        "name": "Mistral 7B",
        "params": "7B",
        "ram": "4 GB",
        "speed": "Fast",  # 58.01s testé
        "quality": "Low",  # Score 25% seulement
        "best_for": "Tests généraux uniquement (score confiance faible)",
        "recommended": False,  # Score trop faible (25%)
        "test_score": "25%",
        "test_duration": "58.01s",
    },
    "llama3.1:8b": {
        "name": "Llama 3.1 8B",
        "params": "8B",
        "ram": "4.7 GB",
        "speed": "Medium",  # 79.39s testé
        "quality": "Low",  # Score 33% + tool calling errors
        "best_for": "À éviter (score faible + erreurs tool calling)",
        "recommended": False,  # Score faible (33%) + tool errors
        "test_score": "33%",
        "test_duration": "79.39s",
        "issues": "Tool calling errors (auto-corrigé)",
    },
    "phi3": {
        "name": "Phi-3",
        "params": "3.8B",
        "ram": "2.3 GB",
        "speed": "N/A",
        "quality": "N/A",
        "best_for": "⚠️ NE FONCTIONNE PAS - Ne supporte pas les tools",
        "recommended": False,
        "test_score": "N/A",
        "test_duration": "0.41s",
        "issues": "❌ ERREUR: 'phi3:latest does not support tools' - Function calling non supporté",
    },
    "gemma2:9b": {
        "name": "Gemma 2 9B",
        "params": "9B",
        "ram": "5.5 GB",
        "speed": "Medium",
        "quality": "Unknown",  # Non testé
        "best_for": "Raisonnement, vérification (NON TESTÉ)",
        "recommended": False,  # Plus lourd, non testé
    },
}

# Modèle Ollama par défaut (meilleur score testé: 80%)
DEFAULT_OLLAMA_MODEL: OllamaModel = "qwen2.5:7b"

# Modèle Ollama pour développement (plus rapide)
DEFAULT_DEV_OLLAMA_MODEL: OllamaModel = "llama3.2"


# ========================================
# Modèles Claude API
# ========================================

ClaudeModel = Literal[
    "claude-sonnet-4-5-20250929",      # Sonnet 4.5 (latest) - Meilleur équilibre
    "claude-sonnet-4-20250514",         # Sonnet 4.0
    "claude-opus-4-20250514",           # Opus 4.0 - Qualité maximale
    "claude-3-5-sonnet-20241022",       # Sonnet 3.5 (legacy)
]

CLAUDE_MODELS_INFO = {
    "claude-sonnet-4-5-20250929": {
        "name": "Claude Sonnet 4.5",
        "speed": "Fast",
        "quality": "Excellent",
        "cost": "$3 / $15 per 1M tokens",
        "context": "200K tokens",
        "best_for": "Production - Excellent équilibre qualité/coût",
        "recommended": True,
    },
    "claude-opus-4-20250514": {
        "name": "Claude Opus 4.0",
        "speed": "Medium",
        "quality": "Best",
        "cost": "$15 / $75 per 1M tokens",
        "context": "200K tokens",
        "best_for": "Analyse complexe, qualité maximale",
        "recommended": False,  # Plus cher
    },
    "claude-sonnet-4-20250514": {
        "name": "Claude Sonnet 4.0",
        "speed": "Fast",
        "quality": "Excellent",
        "cost": "$3 / $15 per 1M tokens",
        "context": "200K tokens",
        "best_for": "Usage général production",
        "recommended": True,
    },
}

# Modèle Claude par défaut
DEFAULT_CLAUDE_MODEL: ClaudeModel = "claude-sonnet-4-5-20250929"


# ========================================
# Modèles MLX (via OpenAI-compatible API)
# ========================================

MLXModel = Literal[
    # Modèles recommandés pour M1 Pro 16 GB (3 modèles principaux)
    "mlx-community/Qwen2.5-3B-Instruct-4bit",        # Léger, excellent français
    "mlx-community/Llama-3.2-3B-Instruct-4bit",      # Rapide, général
    "mlx-community/Mistral-7B-Instruct-v0.3-4bit",   # Qualité maximale
    # Modèles additionnels (legacy)
    "mlx-community/Phi-3-mini-4k-instruct-4bit",
    "mlx-community/Qwen2.5-7B-Instruct-4bit",
]

MLX_MODELS_INFO = {
    # ========================================
    # 🎯 TOP 3 MODÈLES RECOMMANDÉS POUR M1 PRO 16 GB
    # ========================================
    "mlx-community/Qwen2.5-3B-Instruct-4bit": {
        "name": "Qwen 2.5 3B (4-bit)",
        "params": "3B",
        "quantization": "4-bit",
        "ram": "~2 GB",
        "speed": "~50 tokens/sec (M1)",
        "quality": "Excellent",
        "best_for": "Français excellent, léger, rapide",
        "recommended": True,
        "recommended_rank": 1,  # Meilleur choix
        "tools_support": True,
    },
    "mlx-community/Llama-3.2-3B-Instruct-4bit": {
        "name": "Llama 3.2 3B (4-bit)",
        "params": "3B",
        "quantization": "4-bit",
        "ram": "~1.5 GB",
        "speed": "~60 tokens/sec (M1)",
        "quality": "Very Good",
        "best_for": "Ultra-rapide, usage général",
        "recommended": True,
        "recommended_rank": 2,  # Deuxième choix
        "tools_support": True,
    },
    "mlx-community/Mistral-7B-Instruct-v0.3-4bit": {
        "name": "Mistral 7B v0.3 (4-bit)",
        "params": "7B",
        "quantization": "4-bit",
        "ram": "~4 GB",
        "speed": "~35 tokens/sec (M1)",
        "quality": "Excellent",
        "best_for": "Qualité maximale, tâches complexes",
        "recommended": True,
        "recommended_rank": 3,  # Troisième choix
        "tools_support": True,
    },
    # ========================================
    # Modèles additionnels (legacy)
    # ========================================
    "mlx-community/Phi-3-mini-4k-instruct-4bit": {
        "name": "Phi-3 Mini 4K (4-bit)",
        "params": "3.8B",
        "quantization": "4-bit",
        "ram": "~2 GB",
        "speed": "~40 tokens/sec (M1)",
        "quality": "Very Good",
        "best_for": "Tests rapides, extraction",
        "recommended": False,  # Non dans le top 3
        "tools_support": False,  # ⚠️ Problème tool calling (voir Ollama phi3)
    },
    "mlx-community/Qwen2.5-7B-Instruct-4bit": {
        "name": "Qwen 2.5 7B (4-bit)",
        "params": "7B",
        "quantization": "4-bit",
        "ram": "~4.5 GB",
        "speed": "~30 tokens/sec (M1)",
        "quality": "Excellent",
        "best_for": "Documents complexes, multilingual",
        "recommended": False,  # Non dans le top 3 (plus lourd)
        "tools_support": True,
    },
}

# Modèle MLX par défaut (meilleur choix pour M1 Pro 16 GB)
DEFAULT_MLX_MODEL: MLXModel = "mlx-community/Qwen2.5-3B-Instruct-4bit"

# Configuration MLX server
DEFAULT_MLX_SERVER_URL = "http://localhost:8080/v1"  # URL OpenAI-compatible


# ========================================
# Modèles vLLM - SUPPRIMÉS
# ========================================
# vLLM est lent sur Apple Silicon (CPU uniquement, ~5-10 tok/s)
# Utiliser MLX à la place (GPU Metal, ~50-60 tok/s)
# Le code vLLM est conservé pour usage manuel si nécessaire


# ========================================
# Helpers
# ========================================

def get_recommended_ollama_models() -> list[str]:
    """Retourne la liste des modèles Ollama recommandés pour M1 Pro 16 Go."""
    return [
        model for model, info in OLLAMA_MODELS_INFO.items()
        if info.get("recommended", False)
    ]


def get_all_ollama_models() -> list[str]:
    """Retourne tous les modèles Ollama supportés."""
    return list(OLLAMA_MODELS_INFO.keys())


def get_recommended_claude_models() -> list[str]:
    """Retourne la liste des modèles Claude recommandés."""
    return [
        model for model, info in CLAUDE_MODELS_INFO.items()
        if info.get("recommended", False)
    ]


def get_recommended_mlx_models() -> list[str]:
    """Retourne la liste des modèles MLX recommandés pour M1 Pro 16 Go."""
    return [
        model for model, info in MLX_MODELS_INFO.items()
        if info.get("recommended", False)
    ]


def get_recommended_vllm_models() -> list[str]:
    """Retourne la liste des modèles vLLM recommandés."""
    return [
        model for model, info in VLLM_MODELS_INFO.items()
        if info.get("recommended", False)
    ]


def get_all_models_for_api() -> dict:
    """
    Retourne tous les modèles formatés pour l'API frontend.
    Structure utilisée par le composant AdvancedSettings.
    """
    return {
        "ollama": {
            "name": "Ollama",
            "description": "Modèles locaux open-source",
            "icon": "server",
            "requires_api_key": False,
            "default": DEFAULT_OLLAMA_MODEL,
            "models": [
                {
                    "id": f"ollama:{model}",
                    "name": info["name"],
                    "params": info.get("params", ""),
                    "ram": info.get("ram", ""),
                    "speed": info.get("speed", ""),
                    "quality": info.get("quality", ""),
                    "best_for": info.get("best_for", ""),
                    "recommended": info.get("recommended", False),
                    "test_score": info.get("test_score"),
                    "issues": info.get("issues"),
                }
                for model, info in OLLAMA_MODELS_INFO.items()
            ],
        },
        "anthropic": {
            "name": "Claude (Anthropic)",
            "description": "API Claude - Production",
            "icon": "cloud",
            "requires_api_key": True,
            "default": f"anthropic:{DEFAULT_CLAUDE_MODEL}",
            "models": [
                {
                    "id": f"anthropic:{model}",
                    "name": info["name"],
                    "speed": info.get("speed", ""),
                    "quality": info.get("quality", ""),
                    "cost": info.get("cost", ""),
                    "context": info.get("context", ""),
                    "best_for": info.get("best_for", ""),
                    "recommended": info.get("recommended", False),
                }
                for model, info in CLAUDE_MODELS_INFO.items()
            ],
        },
        "mlx": {
            "name": "MLX (Apple Silicon)",
            "description": "Modèles HF convertis pour Mac M1/M2/M3",
            "icon": "cpu",
            "requires_api_key": False,
            "requires_mlx_server": True,
            "server_url": DEFAULT_MLX_SERVER_URL,
            "default": f"mlx:{DEFAULT_MLX_MODEL}",
            "models": [
                {
                    "id": f"mlx:{model}",
                    "name": info["name"],
                    "params": info.get("params", ""),
                    "quantization": info.get("quantization", ""),
                    "ram": info.get("ram", ""),
                    "speed": info.get("speed", ""),
                    "quality": info.get("quality", ""),
                    "best_for": info.get("best_for", ""),
                    "recommended": info.get("recommended", False),
                }
                for model, info in MLX_MODELS_INFO.items()
            ],
        },
    }


def print_models_info():
    """Affiche les informations sur tous les modèles supportés."""
    print("=" * 80)
    print("MODÈLES SUPPORTÉS - NOTARY ASSISTANT")
    print("=" * 80)

    print("\n📦 OLLAMA (Local Open-Source)")
    print("-" * 80)
    for model, info in OLLAMA_MODELS_INFO.items():
        recommended = "⭐" if info.get("recommended") else "  "
        print(f"{recommended} {model:20} | {info['name']:25} | {info['ram']:8} | {info['quality']:12} | {info['best_for']}")

    print("\n☁️  CLAUDE API (Anthropic)")
    print("-" * 80)
    for model, info in CLAUDE_MODELS_INFO.items():
        recommended = "⭐" if info.get("recommended") else "  "
        # Truncate model name for display
        model_short = model[:35] + "..." if len(model) > 35 else model
        print(f"{recommended} {model_short:38} | {info['cost']:25} | {info['quality']:12} | {info['best_for']}")

    print("\n🍎 MLX (Apple Silicon)")
    print("-" * 80)
    for model, info in MLX_MODELS_INFO.items():
        recommended = "⭐" if info.get("recommended") else "  "
        model_short = model.split("/")[1] if "/" in model else model
        print(f"{recommended} {model_short:45} | {info['ram']:8} | {info['speed']:25} | {info['best_for']}")

    print("\n⭐ = Recommandé pour MacBook Pro M1 Pro 16 Go")
    print("=" * 80)


if __name__ == "__main__":
    print_models_info()
