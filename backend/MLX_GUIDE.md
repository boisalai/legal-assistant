# Guide d'utilisation des modèles MLX avec Legal Assistant

Ce guide explique comment utiliser les modèles Hugging Face localement via MLX-LM avec votre Legal Assistant sur MacBook Pro M1 Pro 16 Go.

## Table des matières

1. [Prérequis](#prérequis)
2. [Installation](#installation)
3. [Modèles recommandés](#modèles-recommandés)
4. [Démarrage rapide](#démarrage-rapide)
5. [Configuration de l'assistant](#configuration-de-lassistant)
6. [Résolution de problèmes](#résolution-de-problèmes)

---

## Prérequis

- **MacBook Pro M1/M2/M3** (Apple Silicon uniquement)
- **16 Go RAM minimum** (recommandé)
- **Python 3.10+** installé
- **mlx-lm** installé (voir installation ci-dessous)

**Note:** MLX est optimisé exclusivement pour les puces Apple Silicon. Si vous utilisez un Mac Intel, préférez Ollama.

---

## Installation

### 1. Installer MLX-LM

```bash
# Depuis le dossier backend (MLX-LM est installé par défaut)
uv sync

# Ou avec pip (si vous n'utilisez pas uv)
pip install mlx-lm
```

### 2. Vérifier l'installation

```bash
python3 -c "import mlx_lm; print('✅ MLX-LM installé avec succès')"
```

---

## Modèles recommandés

Legal Assistant supporte 3 modèles MLX optimisés pour votre M1 Pro 16 Go :

| Modèle | Taille | RAM | Vitesse | Qualité | Meilleur pour |
|--------|--------|-----|---------|---------|---------------|
| **Qwen 2.5 3B (4-bit)** ⭐ | 3B | ~2 GB | ~50 tok/s | Excellent | Français excellent, léger, rapide |
| **Llama 3.2 3B (4-bit)** | 3B | ~1.5 GB | ~60 tok/s | Très bon | Ultra-rapide, usage général |
| **Mistral 7B v0.3 (4-bit)** | 7B | ~4 GB | ~35 tok/s | Excellent | Qualité maximale, tâches complexes |

⭐ **Recommandé:** Qwen 2.5 3B est le meilleur choix pour :
- Excellent en français (langue principale de Legal Assistant)
- Léger et rapide sur M1 Pro
- Support complet du function calling (outils)

---

## Démarrage rapide

### 1. Lancer le serveur MLX

Le serveur MLX expose une API compatible OpenAI sur le port 8080 :

```bash
# Démarrer avec Qwen 2.5 3B (recommandé)
mlx_lm.server --model mlx-community/Qwen2.5-3B-Instruct-4bit --port 8080

# Ou avec Llama 3.2 3B (plus rapide)
mlx_lm.server --model mlx-community/Llama-3.2-3B-Instruct-4bit --port 8080

# Ou avec Mistral 7B (meilleure qualité)
mlx_lm.server --model mlx-community/Mistral-7B-Instruct-v0.3-4bit --port 8080
```

**Au premier lancement**, le modèle sera téléchargé automatiquement depuis Hugging Face (~2-4 GB selon le modèle).

### 2. Vérifier que le serveur fonctionne

```bash
# Test simple
curl http://localhost:8080/v1/models

# Devrait retourner : {"data": [...], "object": "list"}
```

### 3. Démarrer Legal Assistant

```bash
# Terminal 1: SurrealDB (base de données)
surreal start --user root --pass root --bind 0.0.0.0:8002 file:data/surreal.db

# Terminal 2: Backend (API)
cd backend
uv run python main.py

# Terminal 3: Frontend (UI)
cd frontend
npm run dev -- -p 3001
```

---

## Configuration de l'assistant

### Via l'interface web (Settings)

1. Ouvrir http://localhost:3001
2. Aller dans **Settings** (paramètres)
3. Section **Modèle IA**
4. Sélectionner un modèle MLX dans le menu déroulant :
   - `mlx:mlx-community/Qwen2.5-3B-Instruct-4bit` ⭐
   - `mlx:mlx-community/Llama-3.2-3B-Instruct-4bit`
   - `mlx:mlx-community/Mistral-7B-Instruct-v0.3-4bit`
5. Cliquer sur **Sauvegarder les paramètres**

**Note:** Les modèles MLX ont une icône 🍎 (Apple Silicon) dans le menu.

### Via code Python (pour développeurs)

```python
from services.model_factory import create_model
from agno.agent import Agent

# Créer un modèle MLX
model = create_model("mlx:mlx-community/Qwen2.5-3B-Instruct-4bit")

# Utiliser dans un agent
agent = Agent(
    name="Legal Assistant",
    model=model,
    instructions="Tu es un assistant juridique expert.",
)

# Tester
agent.print_response("Résume l'article 1 du Code civil.")
```

---

## Résolution de problèmes

### Erreur: "Connection refused" ou "API not available"

**Cause:** Le serveur MLX n'est pas démarré.

**Solution:**
```bash
# Vérifier si le serveur tourne
lsof -i :8080

# Démarrer le serveur MLX
mlx_lm.server --model mlx-community/Qwen2.5-3B-Instruct-4bit --port 8080
```

---

### Erreur: "Model not found" ou téléchargement qui échoue

**Cause:** Problème de connexion à Hugging Face ou modèle mal nommé.

**Solution:**
```bash
# Télécharger manuellement le modèle
python3 -c "from huggingface_hub import snapshot_download; snapshot_download('mlx-community/Qwen2.5-3B-Instruct-4bit')"

# Puis relancer le serveur
mlx_lm.server --model mlx-community/Qwen2.5-3B-Instruct-4bit --port 8080
```

---

### Performances lentes (< 10 tokens/sec)

**Causes possibles:**
1. **RAM insuffisante** : Mistral 7B nécessite ~4 GB RAM libre. Fermez les applications.
2. **Swap actif** : macOS utilise le swap disque (beaucoup plus lent).
3. **Modèle trop lourd** : Passez à Qwen 2.5 3B ou Llama 3.2 3B.

**Solution:**
```bash
# Utiliser un modèle plus léger
mlx_lm.server --model mlx-community/Llama-3.2-3B-Instruct-4bit --port 8080

# Ou fermer les applications gourmandes (Chrome, etc.)
```

---

### Le serveur MLX crash avec "Killed: 9"

**Cause:** Mémoire insuffisante. macOS tue le processus.

**Solution:** Utilisez un modèle plus léger ou libérez de la RAM.

```bash
# Modèle le plus léger (1.5 GB)
mlx_lm.server --model mlx-community/Llama-3.2-3B-Instruct-4bit --port 8080
```

---

## Avantages de MLX vs Ollama

| Critère | MLX | Ollama |
|---------|-----|--------|
| **Optimisation Apple Silicon** | ✅ Natif | ⚠️ Émulation |
| **Performance (M1)** | ~50-60 tok/s | ~30-40 tok/s |
| **Mémoire requise** | 1.5-4 GB | 2-5 GB |
| **Installation** | pip install | Application séparée |
| **Format modèles** | HuggingFace (4-bit) | GGUF (quantized) |
| **API** | OpenAI-compatible | OpenAI-compatible |
| **Support GPU** | Metal (MPS) | Metal (MPS) |

**Verdict:** MLX est plus rapide et mieux optimisé pour Apple Silicon, mais Ollama est plus simple à installer.

---

## Comparaison avec Claude et Ollama

| Critère | MLX (Local) | Ollama (Local) | Claude (API) |
|---------|-------------|----------------|--------------|
| **Coût** | Gratuit | Gratuit | $3-15 / 1M tokens |
| **Vitesse** | ~50 tok/s | ~30 tok/s | ~70 tok/s (réseau) |
| **Qualité** | Très bon | Très bon | Excellent |
| **Privacy** | 100% local | 100% local | Envoi à Anthropic |
| **Function calling** | ✅ Oui | ✅ Oui | ✅ Oui (meilleur) |
| **Français** | Excellent (Qwen) | Bon | Excellent |
| **RAG / Recherche sémantique** | ⚠️ Moyen | ⚠️ Moyen | ✅ Excellent |

**Recommandation selon le cas d'usage:**
- **Questions sur les documents (RAG)** → Claude Sonnet 4.5 (meilleure compréhension)
- **Conversations simples** → MLX Qwen 2.5 3B (rapide, gratuit)
- **Développement/tests** → MLX Llama 3.2 3B (ultra-rapide)

---

## Références

- **MLX-LM Documentation:** https://github.com/ml-explore/mlx-examples/tree/main/llms
- **Hugging Face MLX Community:** https://huggingface.co/mlx-community
- **Agno Framework:** https://docs.agno.com
- **Guide Article (Medium):** [Running Local HF Models with MLX-LM and Agno](https://medium.com/@levchevajoana/running-local-hugging-face-models-with-mlx-lm-and-the-agno-agentic-framework-de134259d34d)

---

## Support

Pour toute question ou problème :
1. Vérifier cette documentation
2. Consulter les logs du serveur MLX (`mlx_lm.server --model ... --port 8080`)
3. Consulter les logs du backend (`backend/main.py`)
4. Ouvrir une issue sur GitHub

---

**Bon usage de Legal Assistant avec MLX ! 🚀**
