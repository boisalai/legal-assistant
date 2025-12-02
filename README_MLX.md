# 🍎 Legal Assistant + MLX (Apple Silicon)

Utilisation de modèles Hugging Face locaux optimisés pour MacBook M1/M2/M3.

**⚡ NOUVEAU : Auto-démarrage automatique !**
Le backend démarre automatiquement le serveur MLX quand vous sélectionnez un modèle MLX. Plus besoin de lancer le serveur manuellement !

## Démarrage rapide (2 minutes)

### 1. Installation

```bash
# Depuis le dossier backend (MLX-LM est installé par défaut)
cd backend
uv sync
```

### 2. Démarrer Legal Assistant

```bash
# Terminal 1: SurrealDB
surreal start --user root --pass root --bind 0.0.0.0:8002 file:data/surreal.db

# Terminal 2: Backend
cd backend
uv run python main.py

# Terminal 3: Frontend
cd frontend
npm run dev -- -p 3001
```

### 3. Sélectionner le modèle MLX

1. Ouvrir http://localhost:3001
2. Ouvrir un dossier
3. Cliquer sur **"Paramètres LLM"** dans le chat
4. Sélectionner `🍎 Qwen 2.5 3B (MLX) - Recommandé Apple Silicon`
5. Envoyer un message

**⚡ Le serveur MLX démarre automatiquement !**
- Au premier message, le modèle est téléchargé (~2 GB, 1-2 min)
- Un message de statut s'affiche : "🍎 Démarrage du serveur MLX..."
- Puis : "✅ Serveur MLX prêt"
- Les messages suivants utilisent le serveur déjà démarré (instantané)

---

## Modèles disponibles

| Modèle | RAM | Vitesse (M1) | Qualité | Meilleur pour |
|--------|-----|--------------|---------|---------------|
| **Qwen 2.5 3B** ⭐ | ~2 GB | ~50 tok/s | Excellent | Français, léger |
| **Llama 3.2 3B** | ~1.5 GB | ~60 tok/s | Très bon | Ultra-rapide |
| **Mistral 7B** | ~4 GB | ~35 tok/s | Excellent | Qualité max |

---

## Pourquoi MLX ?

**Avantages vs Ollama :**
- ✅ 2x plus rapide sur Apple Silicon
- ✅ RAM réduite (~2 GB vs ~4-5 GB)
- ✅ Support complet de function calling
- ✅ Optimisé Metal (GPU M1/M2/M3)

**Avantages vs Claude :**
- ✅ 100% gratuit
- ✅ 100% local (privacy)
- ✅ Pas de coût API
- ✅ Fonctionne hors ligne

---

## Documentation complète

📖 **Guide détaillé :** `backend/MLX_GUIDE.md`

**Inclut :**
- Installation pas à pas
- Résolution de problèmes
- Comparaison de performances
- Exemples de code Python
- Configuration avancée

---

## Liens utiles

- **MLX-LM Documentation:** https://github.com/ml-explore/mlx-examples/tree/main/llms
- **Hugging Face MLX Community:** https://huggingface.co/mlx-community
- **Agno Framework:** https://docs.agno.com
- **Article Medium:** [Running Local HF Models with MLX-LM](https://medium.com/@levchevajoana/running-local-hugging-face-models-with-mlx-lm-and-the-agno-agentic-framework-de134259d34d)

---

## Dépannage rapide

**Erreur "Connection refused"**
```bash
# Vérifier si le serveur tourne
lsof -i :8080

# Démarrer le serveur
mlx_lm.server --model mlx-community/Qwen2.5-3B-Instruct-4bit --port 8080
```

**Serveur crash "Killed: 9"**
```bash
# Utiliser un modèle plus léger
mlx_lm.server --model mlx-community/Llama-3.2-3B-Instruct-4bit --port 8080
```

**Plus d'aide :** Voir `backend/MLX_GUIDE.md`

---

**Bon usage de Legal Assistant avec MLX ! 🚀**
