# Guide des Modèles Locaux - MLX et vLLM

Ce guide explique comment utiliser les modèles HuggingFace localement avec **auto-démarrage automatique** des serveurs.

## 🎯 Vue d'ensemble

L'application supporte 3 méthodes pour charger des modèles HuggingFace localement :

| Provider | Modèles | Device | Auto-démarrage | Recommandé pour |
|----------|---------|--------|----------------|-----------------|
| **MLX** | Convertis MLX uniquement | Apple Silicon (MPS) | ✅ Oui | Mac M1/M2/M3 |
| **vLLM** | **N'IMPORTE QUEL** modèle HF | CUDA / CPU | ✅ Oui | NVIDIA GPU |
| **Ollama** | Modèles Ollama | CPU / GPU | ⚠️ Manuel | Tous |

## 🍎 MLX (Apple Silicon) - **RECOMMANDÉ pour Mac**

### Installation

```bash
# Déjà installé avec uv sync
uv sync
```

### Modèles disponibles

```python
# 5 modèles préconfigurés (tous en 4-bit quantization)
"mlx:mlx-community/Qwen2.5-3B-Instruct-4bit"        # ⭐ Recommandé - Français excellent (~2 GB)
"mlx:mlx-community/Llama-3.2-3B-Instruct-4bit"      # Ultra-rapide (~1.5 GB)
"mlx:mlx-community/Mistral-7B-Instruct-v0.3-4bit"   # Meilleure qualité (~4 GB)
"mlx:mlx-community/Phi-3-mini-4k-instruct-4bit"     # Legacy (~2 GB)
"mlx:mlx-community/Qwen2.5-7B-Instruct-4bit"        # Plus puissant (~4.5 GB)
```

### Utilisation

**🎉 AUTO-DÉMARRAGE AUTOMATIQUE !**

1. **Dans l'interface** : Sélectionne un modèle MLX dans Settings
2. **Pose une question** : Le serveur MLX démarre automatiquement
3. **C'est tout !** Pas besoin de commandes manuelles

**Logs au démarrage :**

```
🚀 Modèle MLX détecté: mlx:mlx-community/Qwen2.5-3B-Instruct-4bit
⏳ Démarrage automatique du serveur MLX...
🚀 Démarrage serveur MLX avec mlx-community/Qwen2.5-3B-Instruct-4bit...
   Port: 8080
   ⚠️  Premier démarrage: téléchargement du modèle (~2-4 GB)
⏳ Attente du démarrage du serveur (max 30s)...
✅ Serveur MLX démarré avec succès en 12.3s
   URL: http://localhost:8080/v1
✅ Serveur MLX prêt
```

**Au premier lancement :**
- Le modèle sera téléchargé depuis HuggingFace Hub (~2-4 GB selon le modèle)
- Temps de téléchargement : ~5-10 min selon votre connexion
- Les fois suivantes : démarrage instantané (modèle en cache)

### Performance

**Sur MacBook Pro M1 Pro 16 GB :**
- Qwen 2.5 3B : ~50 tokens/sec
- Llama 3.2 3B : ~60 tokens/sec (le plus rapide)
- Mistral 7B : ~35 tokens/sec (meilleure qualité)

## 🎮 vLLM (NVIDIA GPU) - **RECOMMANDÉ pour CUDA**

### Installation

```bash
# Sur système avec CUDA
pip install vllm

# Sur Apple Silicon (mode CPU - lent, MLX recommandé)
pip install vllm
```

### Modèles disponibles

**✨ N'IMPORTE QUEL modèle HuggingFace !**

```python
# Modèles préconfigurés (exemples)
"vllm:Qwen/Qwen2.5-3B-Instruct"          # ⭐ Recommandé - Français excellent (~6 GB)
"vllm:meta-llama/Llama-3.2-3B-Instruct"  # Ultra-rapide (~6 GB)
"vllm:Qwen/Qwen2.5-7B-Instruct"          # Plus puissant (~14 GB)
"vllm:mistralai/Mistral-7B-Instruct-v0.3"# Meilleure qualité (~14 GB)

# Mais vous pouvez utiliser N'IMPORTE QUEL modèle HuggingFace !
"vllm:votre/modele-prefere"
```

### Utilisation

**🎉 AUTO-DÉMARRAGE AUTOMATIQUE !**

1. **Dans l'interface** : Sélectionne un modèle vLLM dans Settings
2. **Pose une question** : Le serveur vLLM démarre automatiquement
3. **C'est tout !** Pas besoin de commandes manuelles

**Logs au démarrage :**

```
🚀 Modèle vLLM détecté: vllm:Qwen/Qwen2.5-3B-Instruct
⏳ Démarrage automatique du serveur vLLM...
🚀 Démarrage serveur vLLM avec Qwen/Qwen2.5-3B-Instruct...
   Port: 8001
   Device: cuda
   ⚠️  Premier démarrage: téléchargement du modèle (~6-14 GB)
⏳ Attente du démarrage du serveur (max 60s)...
✅ Serveur vLLM démarré avec succès en 45.2s
   URL: http://localhost:8001/v1
✅ Serveur vLLM prêt
```

**Au premier lancement :**
- Le modèle sera téléchargé depuis HuggingFace Hub (~6-14 GB selon le modèle)
- Temps de téléchargement : ~10-20 min selon votre connexion
- vLLM prend plus de temps à démarrer que MLX (~30-60s)
- Les fois suivantes : modèle en cache

### Performance

**Sur NVIDIA GPU (exemple RTX 3090) :**
- Modèles 3B : ~80-100 tokens/sec
- Modèles 7B : ~40-60 tokens/sec

**⚠️ Sur Apple Silicon (CPU mode - pas recommandé) :**
- Modèles 3B : ~5-10 tokens/sec (très lent)
- **Utilisez MLX à la place !**

## 🔄 Gestion automatique des serveurs

### Switch entre modèles

**Le manager gère automatiquement les transitions :**

1. **MLX → MLX (même modèle)** : Réutilise le serveur existant
2. **MLX → MLX (modèle différent)** : Redémarre avec le nouveau modèle
3. **MLX → vLLM** : Arrête MLX, démarre vLLM
4. **vLLM → MLX** : Arrête vLLM, démarre MLX
5. **MLX/vLLM → Ollama/Claude** : Arrête le serveur local (économise RAM)

**Logs lors du switch :**

```
🔄 Changement de modèle: mlx-community/Qwen2.5-3B-Instruct-4bit → mlx-community/Mistral-7B-Instruct-v0.3-4bit
🛑 Arrêt du serveur MLX...
✅ Serveur MLX arrêté
🚀 Démarrage serveur MLX avec mlx-community/Mistral-7B-Instruct-v0.3-4bit...
```

### Arrêt automatique au shutdown

Tous les serveurs sont arrêtés proprement lors de l'arrêt de l'application :

```
Legal Assistant API - Shutting down...
🛑 Arrêt de tous les serveurs de modèles...
🛑 Arrêt du serveur MLX (modèle: mlx-community/Qwen2.5-3B-Instruct-4bit)...
✅ Serveur MLX arrêté
✅ Tous les serveurs arrêtés
All model servers stopped
```

## 📊 API de gestion des serveurs

### Vérifier le statut

```bash
curl http://localhost:8000/api/model-servers/status
```

**Réponse :**

```json
{
  "mlx": {
    "running": true,
    "model": "mlx-community/Qwen2.5-3B-Instruct-4bit",
    "port": 8080,
    "host": "localhost",
    "url": "http://localhost:8080/v1"
  },
  "vllm": {
    "running": false,
    "model": null,
    "port": 8001,
    "host": "localhost",
    "url": null
  }
}
```

### Arrêter tous les serveurs manuellement

```bash
curl -X POST http://localhost:8000/api/model-servers/stop-all
```

**Utilité :** Libérer la RAM sans redémarrer l'application.

## ⚙️ Configuration

### Ports par défaut

- **MLX** : `http://localhost:8080/v1`
- **vLLM** : `http://localhost:8001/v1`
- **Backend FastAPI** : `http://localhost:8000` (API REST)

### Variables d'environnement (optionnel)

```bash
# Ports personnalisés (non implémenté actuellement)
MLX_SERVER_PORT=8080
VLLM_SERVER_PORT=8001
```

## 🆚 Comparaison MLX vs vLLM

| Critère | MLX | vLLM |
|---------|-----|------|
| **Compatibilité** | Modèles convertis MLX | **Tous les modèles HF** |
| **Device** | Apple Silicon (MPS) | CUDA / CPU |
| **Vitesse** | ⚡⚡⚡ Très rapide | ⚡⚡ Rapide (CUDA) / ⚡ Lent (CPU) |
| **RAM** | ✅ Réduite (4-bit) | ❌ Plus élevée (full precision) |
| **Démarrage** | ✅ Rapide (~10-20s) | ⚠️ Lent (~30-60s) |
| **Installation** | ✅ Inclus (uv sync) | ⚠️ Manuelle (pip install vllm) |
| **Modèles** | ~100 modèles convertis | **Tous les modèles HF** |

## 💡 Recommandations

### Pour Apple Silicon (M1/M2/M3)

✅ **Utilisez MLX**
- Plus rapide
- Moins de RAM
- Quantization 4-bit
- Installation simple

### Pour NVIDIA GPU

✅ **Utilisez vLLM**
- Support de tous les modèles HF
- Optimisations CUDA avancées
- Pas de conversion nécessaire

### Pour CPU uniquement

✅ **Utilisez Ollama**
- Meilleure compatibilité CPU
- vLLM/MLX sont trop lents sur CPU

## 🐛 Dépannage

### Erreur : "vLLM n'est pas installé"

```bash
pip install vllm
```

### Erreur : "mlx-lm n'est pas installé"

```bash
uv sync
```

### Le serveur ne démarre pas

1. Vérifiez les logs pour l'erreur exacte
2. Vérifiez que le port n'est pas déjà utilisé :
   ```bash
   lsof -i :8080  # MLX
   lsof -i :8001  # vLLM
   ```
3. Essayez d'arrêter tous les serveurs :
   ```bash
   curl -X POST http://localhost:8000/api/model-servers/stop-all
   ```

### Timeout au démarrage

**Causes possibles :**
- Premier téléchargement du modèle (peut prendre 10-20 min)
- Connexion Internet lente
- RAM insuffisante

**Solutions :**
- Attendre le téléchargement complet
- Choisir un modèle plus petit (3B au lieu de 7B)
- Vérifier les logs pour voir la progression

## 📝 Exemples d'utilisation

### Exemple 1 : Utiliser MLX sur Mac

1. Sélectionne `mlx:mlx-community/Qwen2.5-3B-Instruct-4bit` dans Settings
2. Pose ta question dans le chat
3. Le serveur démarre automatiquement (première fois : ~10s + téléchargement)
4. Les fois suivantes : démarrage instantané

### Exemple 2 : Tester plusieurs modèles MLX

1. Essaye d'abord Qwen 2.5 3B (français excellent)
2. Si trop lent, passe à Llama 3.2 3B (plus rapide)
3. Si besoin de qualité, passe à Mistral 7B (meilleur raisonnement)
4. Le serveur redémarre automatiquement à chaque changement

### Exemple 3 : Utiliser vLLM avec un modèle custom

1. Trouve un modèle HuggingFace (ex: `unsloth/Llama-3.2-1B-Instruct`)
2. Ajoute-le dans `backend/config/models.py` :
   ```python
   "unsloth/Llama-3.2-1B-Instruct": {
       "name": "Llama 3.2 1B Instruct",
       "params": "1B",
       "ram": "~2 GB",
       ...
   }
   ```
3. Redémarre le backend
4. Sélectionne `vllm:unsloth/Llama-3.2-1B-Instruct`
5. Le serveur télécharge et démarre automatiquement

## 🎓 Conclusion

**L'auto-démarrage automatique rend l'utilisation de modèles locaux aussi simple que les API cloud !**

- ✅ Pas besoin de lancer manuellement les serveurs
- ✅ Switch entre modèles en un clic
- ✅ Gestion automatique de la RAM
- ✅ Toujours via Agno (jamais de LLM direct)

**Profitez-en !** 🚀
