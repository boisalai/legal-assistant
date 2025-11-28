# Configuration Ollama pour Tests Locaux

> Guide pour installer et tester le workflow avec Ollama
> Date: 2025-11-19

## 📖 Vue d'ensemble

Ollama permet d'exécuter des modèles LLM localement sans API externe.

**Avantages:**
- ✅ Gratuit et illimité
- ✅ Fonctionne offline
- ✅ Pas besoin de clé API
- ✅ Parfait pour tests CI/CD
- ✅ Supporte plusieurs modèles (Mistral, Llama2, Phi, etc.)

**Utilisations dans le projet:**
- Tests automatisés (CI/CD)
- Développement local sans coûts
- Validation rapide des workflows
- Alternative à Claude API pour prototypage

---

## 🚀 Installation

### macOS

```bash
# Via Homebrew
brew install ollama

# Ou télécharger depuis le site
# https://ollama.com/download
```

### Linux

```bash
# Script officiel
curl -fsSL https://ollama.com/install.sh | sh

# Ou installation manuelle
curl -L https://github.com/ollama/ollama/releases/latest/download/ollama-linux-amd64 -o /usr/local/bin/ollama
chmod +x /usr/local/bin/ollama
```

### Windows

Télécharger depuis: https://ollama.com/download

---

## 🔧 Configuration

### 1. Démarrer Ollama

```bash
# Lancer le serveur (écoute sur localhost:11434)
ollama serve

# Laisser tourner en arrière-plan
# Le serveur doit rester actif pendant les tests
```

### 2. Télécharger un modèle

```bash
# Mistral (recommandé - ~4GB)
ollama pull mistral

# Llama2 (alternative - ~4GB)
ollama pull llama2

# Phi-3 (plus léger - ~2GB)
ollama pull phi

# Vérifier les modèles installés
ollama list
```

### 3. Tester le modèle

```bash
# Test interactif
ollama run mistral "Bonjour, comment ça va?"

# Devrait répondre en français
```

---

## 🧪 Tests avec le Workflow Notary

### Prérequis

1. **SurrealDB lancé:**
   ```bash
   cd /path/to/notary
   docker-compose up -d surrealdb
   ```

2. **Ollama lancé:**
   ```bash
   ollama serve
   # Dans un terminal séparé
   ```

3. **Modèle téléchargé:**
   ```bash
   ollama pull mistral
   ```

### Lancer le test

```bash
cd backend

# Test avec Mistral (défaut)
uv run python test_workflow_ollama.py

# Test avec un autre modèle
MODEL=ollama:llama2 uv run python test_workflow_ollama.py
MODEL=ollama:phi uv run python test_workflow_ollama.py

# Pour comparaison avec Claude
export ANTHROPIC_API_KEY=your_key
MODEL=anthropic:claude-sonnet-4-5-20250929 uv run python test_workflow_ollama.py
```

### Sortie attendue

```
🧪 TEST WORKFLOW AGNO + OLLAMA
======================================================================
🧪 Test du workflow avec modèle: ollama:mistral
📊 SurrealDB URL: ws://localhost:8000
✅ AgnoDBService initialized
✅ Workflow created with automatic persistence
📄 3 fichier(s) PDF à analyser
🚀 Lancement du workflow...

[... logs d'exécution ...]

✅ Workflow terminé en 45.23s
======================================================================
📊 RÉSULTATS DU WORKFLOW
======================================================================
✅ Succès!
📋 Score de confiance: 78.00%
⚠️  Requiert validation: True

📝 Checklist générée:
   - Items: 12
   - Points d'attention: 3
   - Documents manquants: 2

🔍 Vérification de la persistance dans SurrealDB...
✅ 1 workflow run(s) trouvé(s)
   Run #1:
      - ID: workflow_runs:abc123
      - Created: 2025-11-19T10:30:00Z
      - Status: completed

======================================================================
✅ TEST RÉUSSI
======================================================================
```

---

## 📊 Modèles Recommandés

| Modèle | Taille | Vitesse | Qualité | Usage |
|--------|--------|---------|---------|-------|
| **mistral** | ~4GB | ⚡⚡⚡ | ⭐⭐⭐⭐ | Production locale, français |
| **llama2** | ~4GB | ⚡⚡⚡ | ⭐⭐⭐ | Alternative stable |
| **phi** | ~2GB | ⚡⚡⚡⚡ | ⭐⭐⭐ | Tests rapides, CI/CD |
| **codellama** | ~4GB | ⚡⚡⚡ | ⭐⭐⭐⭐ | Code, développement |

### Sélectionner un modèle

Critères:
1. **Français requis:** Mistral ou Llama2
2. **Vitesse maximale:** Phi
3. **Meilleure qualité:** Mistral
4. **Espace limité:** Phi

---

## 🔍 Vérification de la Persistance

### Requête manuelle SurrealDB

```bash
# Voir tous les workflow runs
curl -X POST http://localhost:8001/sql \
  -H "Accept: application/json" \
  -H "NS: agno" \
  -H "DB: notary_db" \
  -u "root:root" \
  -d "SELECT * FROM workflow_runs ORDER BY created_at DESC LIMIT 5;"

# Workflow runs pour un dossier spécifique
curl -X POST http://localhost:8001/sql \
  -H "Accept: application/json" \
  -H "NS: agno" \
  -H "DB: notary_db" \
  -u "root:root" \
  -d "SELECT * FROM workflow_runs WHERE metadata.dossier_id = 'dossier:test_ollama_20251119';"
```

### Via Python

```python
from services.agno_db_service import get_agno_db_service

# Récupérer l'historique
service = get_agno_db_service()
history = await service.get_workflow_history(
    dossier_id="dossier:test_ollama_20251119",
    limit=10
)

for run in history:
    print(f"Run: {run['id']}, Status: {run.get('status')}")
```

---

## 🐛 Troubleshooting

### Erreur: "connection refused"

**Problème:** Ollama n'est pas lancé
**Solution:**
```bash
# Vérifier si Ollama tourne
curl http://localhost:11434/api/version

# Si erreur, lancer:
ollama serve
```

### Erreur: "model not found"

**Problème:** Modèle pas téléchargé
**Solution:**
```bash
# Télécharger le modèle
ollama pull mistral

# Vérifier
ollama list
```

### Workflow très lent

**Cause possible:** CPU seulement (pas de GPU)
**Solutions:**
1. Utiliser un modèle plus petit (phi au lieu de mistral)
2. Réduire le nombre de PDFs à analyser
3. Utiliser Claude API pour production

### Réponses incohérentes

**Cause:** Modèle trop petit ou mal adapté
**Solutions:**
1. Utiliser Mistral (meilleur français)
2. Ajuster les prompts dans le workflow
3. Utiliser Claude API pour qualité maximale

---

## 📈 Comparaison des Providers

| Provider | Coût | Vitesse | Qualité | Offline | Usage |
|----------|------|---------|---------|---------|-------|
| **Ollama** | Gratuit | Moyen | Bon | ✅ | Dev, tests |
| **Claude API** | Payant | Rapide | Excellent | ❌ | Production |
| **MLX (Mac)** | Gratuit | Très rapide | Bon | ✅ | Dev Mac |

### Stratégie Recommandée

1. **Développement:** Ollama (gratuit, illimité)
2. **Tests CI/CD:** Ollama (automatisable)
3. **Production:** Claude API (qualité maximale)
4. **Mac local:** MLX (ultra-rapide sur M1/M2)

---

## 🔗 Ressources

- Site officiel: https://ollama.com
- Documentation: https://github.com/ollama/ollama
- Modèles disponibles: https://ollama.com/library
- Agno + Ollama: https://docs.agno.com/concepts/models/ollama

---

**Maintenu par:** Claude Code
**Dernière mise à jour:** 2025-11-19
**Sprint:** 1 (Foundation)
