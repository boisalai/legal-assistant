# Sprint 1 - Résultats Tests Modèles Ollama

**Date:** 2025-11-20
**Environnement:** MacBook Pro M1 Pro 16 GB RAM
**Ollama Version:** Latest (23 modèles installés)
**Tests:** 5 modèles Ollama recommandés

---

## 🎯 Résultats Globaux

| Modèle | Succès | Durée | Score Confiance | Checklist | Notes |
|--------|--------|-------|----------------|-----------|-------|
| **ollama:mistral** | ✅ | 58.01s | 25% | 8 items | Succès mais score faible |
| **ollama:llama3.2** | ✅ | 38.44s | 70% | 8 items | **Meilleur rapport qualité/vitesse** ⭐ |
| **ollama:phi3** | ❌ | 0.41s | N/A | N/A | **Ne supporte pas les tools** |
| **ollama:qwen2.5:7b** | ✅ | 83.64s | 80% | 9 items | **Meilleur score confiance** ⭐ |
| **ollama:llama3.1:8b** | ✅ | 79.39s | 33% | 8 items | Tool calling error (auto-corrigé) |

**Taux de succès:** 4/5 (80%)

---

## ⭐ Recommandations Mises à Jour

### 🥇 Meilleur choix: **qwen2.5:7b**
- ✅ **Score:** 80% de confiance (le plus élevé)
- ✅ **Durée:** 83.64s (acceptable)
- ✅ **Qualité:** 9 items de checklist générés
- ✅ **Robustesse:** Aucune erreur de tool calling
- 💰 **RAM:** 4.7 GB
- 🎯 **Usage:** Production locale, documents complexes

### 🥈 Deuxième choix: **llama3.2**
- ✅ **Score:** 70% de confiance (bon)
- ✅ **Durée:** 38.44s (le plus rapide!)
- ✅ **Qualité:** 8 items de checklist
- ✅ **Robustesse:** Aucune erreur
- 💰 **RAM:** 2 GB (très léger)
- 🎯 **Usage:** Développement, tests rapides, prototypage

### 🥉 Troisième choix: **mistral**
- ⚠️ **Score:** 25% de confiance (faible)
- ✅ **Durée:** 58.01s (moyen)
- ✅ **Qualité:** 8 items de checklist
- ✅ **Robustesse:** Aucune erreur
- 💰 **RAM:** 4 GB
- 🎯 **Usage:** Tests généraux (mais score faible)

### ❌ **À ÉVITER:** phi3
- ❌ **Erreur:** `registry.ollama.ai/library/phi3:latest does not support tools`
- ❌ **Cause:** Phi3 ne supporte pas le function calling (tools)
- 💡 **Solution:** Retirer phi3 des recommandations

### ⚠️ **Usage limité:** llama3.1:8b
- ⚠️ **Score:** 33% de confiance (faible)
- ⚠️ **Erreur tool calling:** Paramètres incorrects (auto-corrigé après retry)
- ✅ **Durée:** 79.39s
- 💰 **RAM:** 4.7 GB
- 🎯 **Usage:** Éviter pour production, peut servir pour tests

---

## 🔍 Analyse Détaillée

### Test 1: ollama:mistral
**Durée:** 58.01s | **Score:** 25% | **Résultat:** ✅ SUCCÈS

**Workflow:**
1. ✅ Extraction des données (12.2s)
2. ✅ Classification de la transaction (8.6s)
3. ✅ Vérification de cohérence (12.9s)
4. ✅ Génération de la checklist (24.3s)

**Checklist générée:** 8 items

**Problèmes:**
- ⚠️ Score de confiance très faible (25%) malgré l'exécution complète
- ⚠️ Qualité de l'analyse probablement limitée

**Recommandation:** Utiliser pour tests généraux uniquement, pas pour production.

---

### Test 2: ollama:llama3.2
**Durée:** 38.44s | **Score:** 70% | **Résultat:** ✅ SUCCÈS ⭐

**Workflow:**
1. ✅ Extraction des données (13.0s)
2. ✅ Classification de la transaction (3.3s)
3. ✅ Vérification de cohérence (7.5s)
4. ✅ Génération de la checklist (13.8s)

**Checklist générée:** 8 items

**Points forts:**
- ✅ **Vitesse:** Le plus rapide de tous (38.44s)
- ✅ **Score:** 70% (bon niveau de confiance)
- ✅ **Légèreté:** Seulement 2 GB RAM
- ✅ **Robustesse:** Aucune erreur

**Recommandation:** **EXCELLENT pour développement et prototypage.** Bon compromis qualité/vitesse.

---

### Test 3: ollama:phi3
**Durée:** 0.41s | **Score:** N/A | **Résultat:** ❌ ÉCHEC

**Erreur critique:**
```
HTTP/1.1 400 Bad Request
registry.ollama.ai/library/phi3:latest does not support tools
```

**Cause:** Phi3 ne supporte pas le function calling (feature requise par Agno pour appeler les tools).

**Impact:** Workflow impossible à exécuter.

**Recommandation:** **RETIRER phi3 de la liste des modèles recommandés.**

---

### Test 4: ollama:qwen2.5:7b
**Durée:** 83.64s | **Score:** 80% | **Résultat:** ✅ SUCCÈS ⭐⭐

**Workflow:**
1. ✅ Extraction des données (12.3s)
2. ✅ Classification de la transaction (8.3s)
3. ✅ Vérification de cohérence (9.7s)
4. ✅ Génération de la checklist (52.2s)

**Checklist générée:** 9 items (le plus!)

**Points forts:**
- ✅ **Score:** 80% (le meilleur!)
- ✅ **Qualité:** 9 items de checklist (vs 8 pour les autres)
- ✅ **Robustesse:** Aucune erreur
- ✅ **Multilingual:** Excellent pour documents complexes

**Point faible:**
- ⚠️ Durée un peu longue (83.64s), surtout pour la génération de checklist (52s)

**Recommandation:** **MEILLEUR CHOIX pour production locale.** Qualité maximale avec Ollama.

---

### Test 5: ollama:llama3.1:8b
**Durée:** 79.39s | **Score:** 33% | **Résultat:** ✅ SUCCÈS (avec erreur)

**Workflow:**
1. ⚠️ Extraction des données (31.1s - avec erreur tool calling)
2. ✅ Classification de la transaction (6.2s)
3. ✅ Vérification de cohérence (13.4s)
4. ✅ Génération de la checklist (27.6s)

**Checklist générée:** 8 items

**Problèmes:**
- ⚠️ **Erreur tool calling:** Le modèle a essayé d'appeler `extraire_texte_pdf` avec de mauvais paramètres:
  ```
  Missing required argument: chemin_pdf
  Unexpected keyword argument: documents
  ```
  Le workflow a auto-retry et réussi au 2e essai.

- ⚠️ **Score:** 33% seulement (très faible)

**Recommandation:** **À ÉVITER pour production.** Trop d'erreurs et score faible malgré la taille (8B).

---

## ⚠️ Problèmes Identifiés

### 1. Warnings SurrealDB Authentication (Non-bloquant)

**Erreur observée (sur tous les tests):**
```
WARNING Error getting session from db: {'code': -32000, 'message': 'There was a problem with the database: There was a problem with authentication'}
WARNING Error upserting session into db: {'code': -32000, 'message': 'There was a problem with authentication'}
```

**Impact:**
- ❌ Persistance Agno dans SurrealDB échoue
- ✅ Workflow s'exécute quand même normalement
- ✅ Résultats disponibles (score, checklist, etc.)

**Cause probable:**
- Namespace/credentials différents entre AgnoDBService et ce que Agno attend
- AgnoDBService utilise: `namespace=agno, database=notary_db`
- Peut-être que Agno tente d'écrire dans un namespace différent?

**À investiguer:**
- Vérifier les credentials SurrealDB dans la configuration Agno
- Vérifier que le namespace `agno` a les bonnes permissions
- Consulter la documentation Agno pour la persistance SurrealDB

**Priorité:** Moyenne (workflow fonctionne, mais historique non sauvegardé)

### 2. Phi3 ne supporte pas les tools

**Problème:** Le modèle `phi3:latest` ne supporte pas le function calling.

**Solution:** Retirer de la liste des modèles recommandés.

**Action:** Mise à jour de `backend/config/models.py` pour supprimer phi3.

### 3. Variabilité des scores de confiance

**Observation:**
- qwen2.5:7b → 80%
- llama3.2 → 70%
- llama3.1:8b → 33%
- mistral → 25%

**Question:** Pourquoi une telle variabilité?

**Hypothèses:**
1. Les modèles génèrent des réponses de qualité variable
2. Le calcul du score de confiance dans le workflow peut être trop strict
3. Certains modèles sont meilleurs pour comprendre les instructions en français

**À investiguer:**
- Analyser les checklists générées pour comparer la qualité réelle
- Vérifier le code de calcul du score de confiance dans le workflow
- Tester avec des PDFs plus réalistes (documents notariaux réels)

---

## 📊 Comparaison Performances

### Vitesse (du plus rapide au plus lent)
1. 🥇 **llama3.2:** 38.44s (2 GB RAM)
2. 🥈 **mistral:** 58.01s (4 GB RAM)
3. 🥉 **llama3.1:8b:** 79.39s (4.7 GB RAM)
4. 4️⃣ **qwen2.5:7b:** 83.64s (4.7 GB RAM)

### Qualité (score de confiance)
1. 🥇 **qwen2.5:7b:** 80%
2. 🥈 **llama3.2:** 70%
3. 🥉 **llama3.1:8b:** 33%
4. 4️⃣ **mistral:** 25%

### Rapport Qualité/Vitesse
1. 🥇 **llama3.2:** 70% en 38.44s (1.82% par seconde)
2. 🥈 **qwen2.5:7b:** 80% en 83.64s (0.96% par seconde)
3. 🥉 **mistral:** 25% en 58.01s (0.43% par seconde)
4. 4️⃣ **llama3.1:8b:** 33% en 79.39s (0.42% par seconde)

---

## 🎯 Recommandations Finales

### Pour Développement/Tests
**Choix:** `ollama:llama3.2`
- Ultra-rapide (38s)
- Léger (2 GB RAM)
- Score acceptable (70%)
- Parfait pour itérations rapides

### Pour Production Locale
**Choix:** `ollama:qwen2.5:7b`
- Meilleur score (80%)
- Qualité maximale avec Ollama
- Acceptable en vitesse (84s)
- 9 items de checklist vs 8

### Pour Production Cloud
**Choix:** `anthropic:claude-sonnet-4-5-20250929`
- Qualité maximale attendue (non testé)
- Coût raisonnable ($3/$15 par 1M tokens)
- Robustesse prouvée

### Stratégie Hybride Recommandée
1. **Développement:** llama3.2 (gratuit, rapide)
2. **Pre-production:** qwen2.5:7b (gratuit, qualité)
3. **Production (cas complexes):** Claude Sonnet 4.5 (payant, excellence)

---

## 📋 Actions Requises

### Haute Priorité
1. ✅ **Retirer phi3 de la liste des modèles recommandés**
   - Fichier: `backend/config/models.py`
   - Raison: Ne supporte pas les tools

2. ⚠️ **Investiguer problème authentification SurrealDB**
   - Impact: Persistance Agno échoue
   - Workflow fonctionne, mais pas d'historique sauvegardé
   - Vérifier credentials et namespace

### Moyenne Priorité
3. 📊 **Analyser la variabilité des scores de confiance**
   - Comparer les checklists générées
   - Vérifier le code de calcul du score
   - Tester avec PDFs réels

4. 📝 **Mettre à jour la documentation**
   - `CLAUDE.md`: Ajouter résultats tests
   - `SPRINT1_VALIDATION_RESULTS.md`: Corriger recommandations
   - `backend/config/models.py`: Supprimer phi3, ajuster infos

### Basse Priorité
5. 🧪 **Tester avec documents réels**
   - PDFs de vrais dossiers notariaux
   - Comparer résultats entre modèles
   - Valider qualité extraction

6. 🔧 **Optimiser les prompts**
   - Améliorer les instructions pour les agents
   - Tester si cela améliore les scores de confiance
   - Documenter les meilleures pratiques

---

## 📈 Métriques Tests

| Métrique | Valeur |
|----------|--------|
| Modèles testés | 5 |
| Succès | 4 (80%) |
| Échecs | 1 (20%) |
| Durée totale | ~340s (5min 40s) |
| Durée moyenne (succès) | 64.87s |
| Score moyen (succès) | 52% |
| Score médian (succès) | 51.5% |
| Meilleur score | 80% (qwen2.5:7b) |
| Plus rapide | 38.44s (llama3.2) |

---

## 🔗 Références

- **Script de test:** `backend/test_sprint1_validation.py`
- **Configuration modèles:** `backend/config/models.py`
- **Factory pattern:** `backend/services/model_factory.py`
- **Workflow:** `backend/workflows/analyse_dossier.py`

---

**Rapport généré:** 2025-11-20
**Par:** Claude Code
**Sprint:** Sprint 1 - Validation Multi-Modèles
**Statut:** ✅ Tests complétés, recommandations mises à jour
