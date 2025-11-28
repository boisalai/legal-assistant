# Guide Configuration Claude API

**Date:** 2025-11-20
**Objectif:** Configurer Claude API pour améliorer l'extraction de PDF

---

## Pourquoi Claude API?

- ✅ **Meilleure qualité** d'extraction pour documents juridiques
- ✅ **Excellent français** (Anthropic a un focus multilingue)
- ✅ **Function calling** de très haute qualité
- ✅ **Comprend le contexte** juridique/notarial
- 💰 Coût: **$3/$15 par million de tokens** (input/output)

**Estimation de coût pour votre usage:**
- 1 dossier notarial (~10 pages PDF) ≈ 5000 tokens ≈ **$0.015** (1.5¢)
- 100 dossiers/mois ≈ **$1.50/mois**
- Très abordable pour la qualité obtenue

---

## Étape 1: Obtenir une clé API

### 1.1 Créer un compte Anthropic

1. Allez sur: https://console.anthropic.com/
2. Cliquez sur **"Sign Up"**
3. Utilisez votre email professionnel
4. Vérifiez votre email

### 1.2 Ajouter un moyen de paiement

1. Dans la console: https://console.anthropic.com/settings/billing
2. Cliquez sur **"Add Payment Method"**
3. Entrez votre carte de crédit
4. **Configurez un budget** (recommandé: $10/mois pour débuter)

### 1.3 Générer une clé API

1. Allez sur: https://console.anthropic.com/settings/keys
2. Cliquez sur **"Create Key"**
3. Nommez votre clé: `notary-assistant-dev`
4. **Copiez la clé** (elle commence par `sk-ant-`)
5. ⚠️ **Sauvegardez-la** - Elle ne sera plus affichée!

---

## Étape 2: Configurer la clé localement

### 2.1 Option A: Variable d'environnement (Recommandé)

**macOS/Linux:**
```bash
# Ajouter à votre ~/.zshrc ou ~/.bashrc
export ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# Recharger le shell
source ~/.zshrc
```

**Vérifier:**
```bash
echo $ANTHROPIC_API_KEY
# Devrait afficher: sk-ant-xxxxx...
```

### 2.2 Option B: Fichier .env (Développement)

```bash
cd /home/user/notary/backend

# Copier l'exemple si pas déjà fait
cp .env.example .env

# Éditer .env
nano .env
```

Modifier la ligne:
```bash
ANTHROPIC_API_KEY=sk-ant-votre-clé-ici
```

⚠️ **Important:** Le fichier `.env` est dans `.gitignore` - Ne jamais le commiter!

---

## Étape 3: Tester la configuration

### Test 1: Vérification de la clé

```bash
cd /home/user/notary/backend

# Test simple
uv run python -c "
import os
from anthropic import Anthropic

client = Anthropic(api_key=os.environ.get('ANTHROPIC_API_KEY'))
message = client.messages.create(
    model='claude-sonnet-4-5-20250929',
    max_tokens=100,
    messages=[{'role': 'user', 'content': 'Bonjour! Réponds en français.'}]
)
print('✅ Claude API fonctionne!')
print(f'Réponse: {message.content[0].text}')
"
```

**Résultat attendu:**
```
✅ Claude API fonctionne!
Réponse: Bonjour ! Comment puis-je vous aider aujourd'hui ?
```

### Test 2: Avec le model factory

```bash
cd /home/user/notary/backend

uv run python -c "
from services.model_factory import create_model

model = create_model('anthropic:claude-sonnet-4-5-20250929')
print(f'✅ Modèle créé: {model}')
"
```

### Test 3: Workflow complet

```bash
cd /home/user/notary/backend

MODEL=anthropic:claude-sonnet-4-5-20250929 uv run python test_sprint1_validation.py
```

**Résultat attendu:**
- ✅ Workflow s'exécute
- ✅ Score de confiance > 70% (vs 25% avec qwen2.5:7b)
- ✅ Extraction plus précise

---

## Étape 4: Comparer les performances

### Script de comparaison

```bash
cd /home/user/notary/backend

# Test avec Qwen 2.5 (baseline)
echo "=== TEST QWEN 2.5 7B ==="
MODEL=ollama:qwen2.5:7b uv run python test_sprint1_validation.py > results_qwen.txt

# Test avec Claude Sonnet 4.5
echo "=== TEST CLAUDE SONNET 4.5 ==="
MODEL=anthropic:claude-sonnet-4-5-20250929 uv run python test_sprint1_validation.py > results_claude.txt

# Comparer les résultats
echo "=== COMPARAISON ==="
grep "Score de confiance" results_qwen.txt
grep "Score de confiance" results_claude.txt
```

---

## Dépannage

### Erreur: "API key not found"

**Vérifier:**
```bash
echo $ANTHROPIC_API_KEY
cat backend/.env | grep ANTHROPIC_API_KEY
```

**Solution:**
```bash
export ANTHROPIC_API_KEY=sk-ant-xxxxx
```

### Erreur: "Authentication failed"

**Cause:** Clé API invalide ou expirée

**Solution:**
1. Vérifier que la clé est correcte (commence par `sk-ant-`)
2. Régénérer une nouvelle clé sur https://console.anthropic.com/settings/keys

### Erreur: "Rate limit exceeded"

**Cause:** Trop de requêtes trop rapidement

**Solution:**
- Attendre quelques secondes
- Configurer un délai entre requêtes dans le code
- Augmenter votre limite sur la console Anthropic

### Erreur: "Insufficient credits"

**Cause:** Budget épuisé ou carte expirée

**Solution:**
1. Vérifier sur https://console.anthropic.com/settings/billing
2. Ajouter des crédits ou augmenter le budget

---

## Surveillance des coûts

### Dashboard Anthropic

1. Allez sur: https://console.anthropic.com/settings/usage
2. Consultez:
   - Utilisation du jour
   - Utilisation du mois
   - Coût par modèle

### Bonnes pratiques

1. **Commencez avec un petit budget** ($10/mois)
2. **Surveillez l'utilisation** les premiers jours
3. **Utilisez Claude uniquement en production**, Ollama pour dev
4. **Configurez des alertes** de budget sur la console

---

## Modèles disponibles

| Modèle | Contexte | Input | Output | Usage recommandé |
|--------|----------|-------|--------|------------------|
| **claude-sonnet-4-5-20250929** | 200K | $3/M | $15/M | ⭐ Production (recommandé) |
| claude-opus-4-20250514 | 200K | $15/M | $75/M | Analyse complexe uniquement |
| claude-sonnet-4-20250514 | 200K | $3/M | $15/M | Alternative Sonnet 4.5 |

**Recommandation:** Utilisez `claude-sonnet-4-5-20250929` - Meilleur rapport qualité/prix.

---

## Prochaines étapes

Une fois Claude API configuré:

1. ✅ Créer un PDF de test réaliste (vente immobilière)
2. ✅ Améliorer les prompts des agents
3. ✅ Tester extraction avec Claude vs Ollama
4. ✅ Comparer scores et qualité

---

**Créé:** 2025-11-20
**Pour:** Option 2 - Améliorer extraction PDF
**Référence:** https://docs.anthropic.com/claude/reference/getting-started-with-the-api
