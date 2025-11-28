# Option 2: Intégration des Prompts Améliorés

**Date:** 2025-11-20
**Objectif:** Améliorer la qualité d'extraction de 38% vers 70-90%
**Statut:** ✅ Prompts intégrés dans le code

---

## Résumé

Les prompts améliorés documentés dans `PROMPTS_AMELIORES.md` ont été intégrés dans le workflow principal `backend/workflows/analyse_dossier.py`.

### Changements Effectués

| Agent | Lignes Modifiées | Améliorations Clés |
|-------|------------------|-------------------|
| **Extracteur** | 226-302 | Contexte juridique québécois, exemples concrets, priorités |
| **Classificateur** | 307-389 | Types de transactions détaillés, documents attendus par type |
| **Vérificateur** | 391-465 | Calculs de taxe de bienvenue, seuils d'alerte, vérifications critiques |
| **Générateur** | 467-594 | Checklist actionnable, délais typiques, priorisation claire |

---

## Améliorations par Agent

### 1. Agent Extracteur (ExtracteurDocuments)

**Avant (Générique):**
```
Tu es un expert en lecture et analyse de documents notariaux du Québec.
Tu extrais les informations structurées avec précision et rigueur.
```

**Après (Spécifique):**
- ✅ **Contexte juridique québécois** explicite (Code civil, terminologie)
- ✅ **4 catégories d'extraction** détaillées (parties, immeubles, finances, dates)
- ✅ **Exemples concrets** pour chaque type de données
- ✅ **Instructions précises** (format ISO dates, devise CAD, etc.)
- ✅ **Priorités** définies (CRITIQUE, HAUTE, MOYENNE)

**Impact Attendu:**
- Extraction de **7/7 montants** au lieu de 2-3
- Extraction de **6/6 dates** au lieu de 1-2
- Noms complets avec rôles (vendeur/acheteur)
- Adresses structurées avec code postal

---

### 2. Agent Classificateur (ClassificateurTransactions)

**Avant (Générique):**
```
Identifie le type de transaction et les documents associés.
```

**Après (Spécifique):**
- ✅ **6 types de transactions** reconnus avec indices (vente, hypothèque, donation, etc.)
- ✅ **Documents attendus** par type de transaction (REQUIS vs RECOMMANDÉ)
- ✅ **Exemples concrets** de classification avec justification
- ✅ **Terminologie juridique** québécoise spécifique

**Impact Attendu:**
- Classification précise du type de transaction
- Liste complète des **documents manquants** identifiés
- Score de confiance de classification > 0.9

---

### 3. Agent Vérificateur (VerificateurCoherence)

**Avant (Générique):**
```
Vérifie la cohérence mathématique et temporelle.
```

**Après (Spécifique):**
- ✅ **Formules de calcul** de la taxe de bienvenue (3 paliers)
- ✅ **5 types de vérifications** critiques (montants, dates, parties, propriété, complétude)
- ✅ **Seuils d'alerte** définis (ROUGE < 0.5, ORANGE 0.5-0.7, VERT > 0.7)
- ✅ **Checklist complétude** pour vente résidentielle (8 documents)
- ✅ **Exemple concret** d'alerte avec calcul

**Impact Attendu:**
- Détection des écarts de taxe de bienvenue (ex: 2 425 $)
- Vérification temporelle des dates (logique signature → acte → occupation)
- Alertes précises et actionnables
- Score de vérification basé sur 4 critères pondérés

---

### 4. Agent Générateur (GenerateurChecklist)

**Avant (Générique):**
```
Génère des checklists claires et actionnables.
```

**Après (Spécifique):**
- ✅ **4 niveaux de priorité** (CRITIQUE, HAUTE, MOYENNE, BASSE)
- ✅ **4 catégories d'items** (documents, vérifications, calculs, coordination)
- ✅ **Délais typiques** pour chaque type de document (1-2 semaines, 3-5 jours, etc.)
- ✅ **Points d'attention** basés sur vérifications (écarts, dates serrées, etc.)
- ✅ **Exemple complet** de checklist avec 3 items priorisés
- ✅ **Commentaires finaux** avec recommandation générale

**Impact Attendu:**
- **10-15 items** de checklist au lieu de 3-5
- Items actionnables avec responsables et délais
- Points d'attention clairs (⚠️ CRITIQUE, ❗ IMPORTANT, ℹ️ INFO)
- Score de confiance basé sur 3 critères pondérés (complétude 40%, cohérence 30%, drapeaux rouges 30%)

---

## Résultats Attendus

### Métriques Cibles

| Métrique | Avant (Prompts génériques) | Objectif (Prompts spécifiques) |
|----------|----------------------------|--------------------------------|
| **Score de confiance global** | 38% (Claude) / 20% (Qwen) | **70-90%** |
| **Montants extraits** | 2-3 sur 7 | **7 sur 7** (100%) |
| **Dates extraites** | 1-2 sur 6 | **6 sur 6** (100%) |
| **Noms extraits** | Partiels | **Complets avec rôles** |
| **Adresses structurées** | Brutes | **Formatées avec code postal** |
| **Documents identifiés** | Génériques | **Spécifiques + manquants** |
| **Checklist générée** | 3-5 items | **10-15 items actionnables** |
| **Points d'attention** | Vagues | **Précis avec calculs** |
| **Délai avant signature** | Non estimé | **Estimé avec justification** |

### Comparaison Claude vs Qwen (Attendu)

Avec les prompts améliorés:

| Modèle | Score Confiance | Checklist Items | Temps | Coût |
|--------|-----------------|-----------------|-------|------|
| **Claude Sonnet 4.5** | **75-90%** | **15-20** | ~110s | ~$0.015/doc |
| **Qwen 2.5 7B** | **50-65%** | **8-12** | ~70s | Gratuit (local) |
| **Amélioration** | +97-137% | +116-233% | - | - |

**Recommandation:**
- **Production:** Claude Sonnet 4.5 (qualité maximale, coût acceptable)
- **Développement:** Qwen 2.5 7B (gratuit, rapide, qualité acceptable)

---

## Tests de Validation

### 1. Test avec PDF Réaliste

```bash
cd /home/user/notary/backend

# Générer le PDF de test (si pas déjà fait)
uv run python generate_realistic_pdf.py

# Test avec Claude Sonnet 4.5
MODEL=anthropic:claude-sonnet-4-5-20250929 uv run python test_sprint1_validation.py

# Test avec Qwen 2.5 7B (comparaison)
MODEL=ollama:qwen2.5:7b uv run python test_sprint1_validation.py
```

### 2. Vérifications à Effectuer

Après exécution, vérifier dans les résultats:

**✅ Extraction (Agent 1):**
- [ ] Prix de vente: 485 000 $ détecté
- [ ] Acompte: 25 000 $ détecté
- [ ] Mise de fonds: 72 500 $ détecté
- [ ] Hypothèque: 387 500 $ détecté
- [ ] Taxe de bienvenue: 7 425 $ détecté
- [ ] Taxes municipales: 4 850 $ détecté
- [ ] Taxes scolaires: 1 245 $ détecté
- [ ] 6 dates extraites (signature, conditions, acte, occupation, etc.)
- [ ] Parties: Vendeur (Jean-Pierre Tremblay), Acheteur (François Bélanger)
- [ ] Adresse: 456 rue Champlain, Québec (Québec) G1K 4H2

**✅ Classification (Agent 2):**
- [ ] Type transaction: "vente"
- [ ] Type propriété: "residentielle"
- [ ] Documents identifiés: "promesse_achat_vente.pdf"
- [ ] Documents manquants listés (certificat localisation, titre propriété, etc.)

**✅ Vérification (Agent 3):**
- [ ] Vérification cohérence montants (485 000 = 25 000 + 72 500 + 387 500)
- [ ] Calcul taxe bienvenue (7 425 $ = 300 + 2 400 + 4 725)
- [ ] Vérification dates (ordre logique)
- [ ] Score vérification > 0.7
- [ ] Alertes pertinentes si écarts

**✅ Checklist (Agent 4):**
- [ ] Au moins 10 items générés
- [ ] Priorités assignées (critique/haute/moyenne/basse)
- [ ] Documents à obtenir listés
- [ ] Prochaines étapes avec délais
- [ ] Score confiance **> 70%** (objectif principal!)
- [ ] Commentaires finaux avec recommandation

---

## Analyse des Résultats

### Grille d'Évaluation

| Critère | Poids | Score Attendu | Notes |
|---------|-------|---------------|-------|
| **Montants extraits** | 20% | 100% (7/7) | Tous les montants du PDF |
| **Dates extraites** | 15% | 100% (6/6) | Toutes les dates clés |
| **Parties identifiées** | 15% | 100% | Vendeur + Acheteur + Courtier |
| **Adresse structurée** | 10% | 100% | Avec code postal |
| **Classification** | 10% | 100% | Vente résidentielle |
| **Documents manquants** | 10% | 100% | Liste complète |
| **Checklist actionnable** | 10% | 100% | 10-15 items |
| **Calcul taxe bienvenue** | 5% | 100% | 7 425 $ exact |
| **Prochaines étapes** | 5% | 100% | Avec délais |

**SCORE GLOBAL CIBLE:** **≥ 70%**

---

## Troubleshooting

### Score < 70% après intégration prompts

**Causes possibles:**
1. Modèle LLM pas assez puissant (Qwen 2.5 7B limité)
2. PDF mal formaté ou illisible
3. Temps d'exécution trop court (timeout)
4. Erreurs dans les tools d'extraction

**Solutions:**
```bash
# 1. Utiliser Claude au lieu de Qwen
MODEL=anthropic:claude-sonnet-4-5-20250929 uv run python test_sprint1_validation.py

# 2. Vérifier que le PDF est généré correctement
ls -lh /home/user/notary/backend/test_data/promesse_achat_vente_realiste.pdf

# 3. Augmenter le timeout (si nécessaire)
# Modifier test_sprint1_validation.py ligne ~200

# 4. Vérifier les tools
uv run python -c "from workflows.tools import *; print('OK')"
```

### Erreur "Could not resolve authentication method"

**Cause:** `ANTHROPIC_API_KEY` non configurée ou non chargée.

**Solution:**
```bash
# Vérifier que la clé est dans .env
cat backend/.env | grep ANTHROPIC_API_KEY

# Vérifier qu'elle est chargée
cd backend
uv run python -c "from config.settings import settings; print(settings.anthropic_api_key[:10])"
```

### Warnings SurrealDB authentification

**Cause:** Namespace 'agno' non initialisé.

**Solution:**
```bash
cd backend
uv run python fix_surrealdb_agno_namespace.py
```

---

## Prochaines Étapes

### Après validation (Score ≥ 70%)

1. **Commit et push:**
   ```bash
   git add backend/workflows/analyse_dossier.py OPTION2_PROMPTS_INTEGRATION.md
   git commit -m "feat(option2): Intégrer prompts améliorés - Objectif 70-90% confiance"
   git push
   ```

2. **Créer PR:**
   - Titre: `feat(option2): Améliorer extraction avec prompts spécifiques québécois`
   - Description: Intégration des prompts améliorés pour passer de 38% à 70-90% de confiance

3. **Tests avec PDFs réels:**
   - Tester avec vrais dossiers notariaux (si disponibles)
   - Valider sur plusieurs types de transactions
   - Affiner les prompts si nécessaire

4. **Option suivante:**
   - **Sprint 2:** Frontend + Dashboard historique
   - **Ou:** Optimisation continue extraction (si < 70%)

### Si Score < 70%

1. Analyser les logs du workflow (quelles étapes échouent?)
2. Identifier les données manquantes ou mal extraites
3. Ajuster les prompts en conséquence
4. Re-tester
5. Itérer jusqu'à atteindre 70%

---

## Références

- **Guide Claude API:** `GUIDE_CLAUDE_API.md`
- **Prompts documentés:** `PROMPTS_AMELIORES.md`
- **PDF de test:** `backend/generate_realistic_pdf.py`
- **Script de test:** `backend/test_sprint1_validation.py`
- **Workflow principal:** `backend/workflows/analyse_dossier.py`

---

**Créé:** 2025-11-20
**Pour:** Option 2 - Améliorer qualité extraction
**Statut:** ✅ Prêt pour tests de validation
**Objectif:** Score confiance **≥ 70%**
