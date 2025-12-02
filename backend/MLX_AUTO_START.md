# Auto-démarrage du serveur MLX

Le backend démarre automatiquement le serveur MLX-LM quand vous sélectionnez un modèle MLX dans l'interface.

## Comment ça fonctionne

### 1. Sélection d'un modèle MLX dans le chat

Quand vous sélectionnez un modèle MLX dans "Paramètres LLM" :
- Exemple : `🍎 Qwen 2.5 3B (MLX) - Recommandé Apple Silicon`

### 2. Auto-détection et démarrage

Le backend détecte automatiquement que c'est un modèle MLX (prefix `mlx:`) et :

1. **Vérifie si le serveur tourne déjà**
   - Si le bon modèle tourne → utilise le serveur existant
   - Si un autre modèle tourne → arrête l'ancien, démarre le nouveau
   - Si aucun serveur ne tourne → démarre le serveur

2. **Démarre le serveur MLX** (si nécessaire)
   ```bash
   python3 -m mlx_lm.server --model <model_id> --port 8080
   ```

3. **Attend que le serveur soit prêt**
   - Health check toutes les secondes
   - Timeout: 30 secondes max
   - Au premier lancement: téléchargement du modèle (~2-4 GB)

4. **Affiche un message de statut dans le chat**
   ```
   🍎 Démarrage du serveur MLX...
   ✅ Serveur MLX prêt
   ```

## Architecture technique

### Service `MLXServerService`

**Fichier :** `backend/services/mlx_server_service.py`

**Responsabilités :**
- Gère le lifecycle du subprocess `mlx_lm.server`
- Switch automatique entre modèles
- Health checks via appels HTTP
- Cleanup au shutdown de l'application

**Méthodes principales :**
```python
service = get_mlx_server_service()

# Démarrer avec un modèle
await service.start("mlx-community/Qwen2.5-3B-Instruct-4bit")

# Vérifier le statut
status = service.get_status()  # {'running': True, 'model': '...', ...}

# Arrêter
await service.stop()

# Helper pour auto-start/switch
await ensure_mlx_server("mlx:mlx-community/Qwen2.5-3B-Instruct-4bit")
```

### Intégration dans le chat

**Fichier :** `backend/routes/chat.py`

**Logique :**
```python
async def _handle_regular_chat_stream(request: ChatRequest):
    # Auto-start MLX server if needed
    if request.model_id.startswith("mlx:"):
        await ensure_mlx_server(request.model_id)

    # Create the model
    model = create_model(request.model_id)
    ...
```

### Endpoints API

**Fichier :** `backend/routes/settings.py`

```bash
# Vérifier le statut
GET /api/settings/mlx/status
→ {"running": true, "model": "mlx-community/Qwen2.5-3B-Instruct-4bit", ...}

# Démarrer manuellement
POST /api/settings/mlx/start
Body: {"model_id": "mlx:mlx-community/Qwen2.5-3B-Instruct-4bit"}

# Arrêter
POST /api/settings/mlx/stop
```

## Workflow utilisateur

### Scénario 1 : Premier usage d'un modèle MLX

1. **Utilisateur** : Sélectionne "🍎 Qwen 2.5 3B (MLX)" dans Paramètres LLM
2. **Utilisateur** : Envoie un message : "Bonjour"
3. **Backend** :
   - Détecte `mlx:mlx-community/Qwen2.5-3B-Instruct-4bit`
   - Affiche : "🍎 Démarrage du serveur MLX..."
   - Télécharge le modèle (~2 GB, 1-2 min)
   - Démarre le serveur MLX
   - Attend que le serveur soit prêt
   - Affiche : "✅ Serveur MLX prêt"
4. **Backend** : Répond au message avec le modèle MLX

**⏱️ Durée totale (premier usage) :** ~1-3 minutes (téléchargement + démarrage)

### Scénario 2 : Réutilisation du même modèle

1. **Utilisateur** : Envoie un autre message
2. **Backend** :
   - Détecte que le serveur MLX avec Qwen 2.5 3B tourne déjà
   - Utilise directement le serveur existant
   - Répond immédiatement

**⏱️ Durée totale :** Instantané (pas de démarrage)

### Scénario 3 : Switch entre modèles MLX

1. **Utilisateur** : Change de "Qwen 2.5 3B" → "Llama 3.2 3B" dans Paramètres LLM
2. **Utilisateur** : Envoie un message
3. **Backend** :
   - Détecte un changement de modèle MLX
   - Affiche : "🍎 Démarrage du serveur MLX..."
   - Arrête le serveur Qwen 2.5 3B
   - Démarre le serveur Llama 3.2 3B
   - Affiche : "✅ Serveur MLX prêt"
4. **Backend** : Répond avec le nouveau modèle

**⏱️ Durée totale :** ~10-30 secondes (si modèle déjà téléchargé)

### Scénario 4 : Switch MLX → Ollama

1. **Utilisateur** : Change de "MLX Qwen 2.5 3B" → "Ollama Qwen 2.5 7B"
2. **Utilisateur** : Envoie un message
3. **Backend** :
   - Détecte que le modèle n'est pas MLX
   - Laisse le serveur MLX tourner en arrière-plan
   - Utilise Ollama directement

**Note :** Le serveur MLX reste actif jusqu'au shutdown du backend.

## Gestion des erreurs

### Erreur : mlx-lm non installé

```
❌ Échec du démarrage du serveur MLX. Vérifiez que mlx-lm est installé (uv sync).
```

**Solution :**
```bash
cd backend
uv sync  # mlx-lm est installé par défaut
```

### Erreur : Port 8080 déjà utilisé

Le serveur MLX ne peut pas démarrer si le port 8080 est occupé.

**Solution :**
```bash
# Trouver le processus
lsof -i :8080

# Tuer le processus
kill -9 <PID>
```

### Erreur : Modèle introuvable sur HuggingFace

Le téléchargement échoue si le modèle n'existe pas.

**Solution :**
- Vérifier l'orthographe du modèle
- Vérifier la connexion Internet
- Utiliser un autre modèle MLX

## Optimisations

### Cache des modèles

Les modèles téléchargés sont cachés dans `~/.cache/huggingface/hub/`.

**Avantages :**
- Pas de re-téléchargement après le premier usage
- Switch rapide entre modèles déjà téléchargés

**Nettoyage du cache :**
```bash
rm -rf ~/.cache/huggingface/hub/models--mlx-community*
```

### Health checks

Le service vérifie la santé du serveur toutes les secondes pendant le démarrage.

**Endpoint vérifié :**
```bash
GET http://localhost:8080/v1/models
```

**Timeout :** 30 secondes max

## Shutdown propre

Au shutdown du backend (`Ctrl+C`), le serveur MLX est arrêté automatiquement.

**Logs :**
```
Legal Assistant API - Shutting down...
MLX server stopped
SurrealDB disconnected
Goodbye!
```

## Troubleshooting

### Le serveur ne démarre pas

**1. Vérifier les logs du backend**
```bash
cd backend
uv run python main.py
# Observer les logs lors de la sélection d'un modèle MLX
```

**2. Tester manuellement le démarrage**
```bash
python3 -m mlx_lm.server --model mlx-community/Qwen2.5-3B-Instruct-4bit --port 8080
```

**3. Vérifier l'installation de mlx-lm**
```bash
python3 -c "import mlx_lm; print(mlx_lm.__version__)"
```

### Le serveur démarre mais ne répond pas

**Vérifier le health check :**
```bash
curl http://localhost:8080/v1/models
```

**Résultat attendu :**
```json
{"data": [...], "object": "list"}
```

## Comparaison : Auto vs Manuel

| Critère | Auto-start | Manuel |
|---------|------------|--------|
| **Setup utilisateur** | Aucun | Terminal séparé |
| **Switch modèles** | Automatique | Redémarrer manuellement |
| **Gestion processus** | Backend | Utilisateur |
| **Cleanup** | Automatique | Manuel (Ctrl+C) |
| **Premier démarrage** | ~1-3 min | ~1-3 min |
| **Complexité** | Simple | Technique |

**Verdict :** L'auto-start simplifie grandement l'expérience utilisateur.

## Références

- **Service source :** `backend/services/mlx_server_service.py`
- **Intégration chat :** `backend/routes/chat.py:590-612`
- **Endpoints API :** `backend/routes/settings.py:165-238`
- **Guide utilisateur :** `backend/MLX_GUIDE.md`
