# Correction des Warnings SurrealDB Authentication

Ce répertoire contient des scripts pour diagnostiquer et corriger les warnings d'authentification SurrealDB avec Agno.

---

## 🐛 Problème

Lors des tests, vous voyez ces warnings:
```
WARNING Error getting session from db: {'code': -32000, 'message': 'There was a problem with authentication'}
```

**Cause:** Le namespace `agno` n'est pas initialisé dans SurrealDB.

**Impact:**
- ❌ L'historique des workflows n'est pas sauvegardé
- ✅ Les workflows s'exécutent quand même

---

## 🛠️ Solution Rapide (2 minutes)

### Étape 1: Diagnostic
```bash
cd backend
uv run python diagnose_surrealdb_auth.py
```

Ce script va tester la connexion et identifier le problème.

### Étape 2: Fix Automatique
```bash
uv run python fix_surrealdb_agno_namespace.py
```

Ce script va:
1. Créer le namespace `agno`
2. Définir la database
3. Tester que tout fonctionne

### Étape 3: Vérification
```bash
# Relancer les tests
MODEL=ollama:qwen2.5:7b uv run python test_sprint1_validation.py

# Les warnings devraient avoir disparu!
```

---

## 📁 Scripts Disponibles

### `diagnose_surrealdb_auth.py`
**Rôle:** Diagnostique complet de la connexion SurrealDB

**Tests effectués:**
- ✅ Connexion WebSocket
- ✅ Authentification root
- ✅ Accès namespace `notary`
- ✅ Accès namespace `agno`
- ✅ Test d'écriture dans chaque namespace
- ✅ Test avec Agno SurrealDb

**Usage:**
```bash
uv run python diagnose_surrealdb_auth.py
```

**Résultat attendu:**
```
TEST 1: Connexion SurrealDB de base
✅ Connexion WebSocket établie

TEST 2: Authentification root
✅ Authentification root réussie

TEST 3: Accès namespace 'notary'
✅ Namespace 'notary' accessible
✅ Écriture dans namespace 'notary' réussie

TEST 4: Accès namespace 'agno'
❌ Erreur namespace 'agno': ... (AVANT FIX)
✅ Namespace 'agno' accessible (APRÈS FIX)

TEST 5: Test avec agno.db.surrealdb.SurrealDb
✅ Instance Agno SurrealDb créée
✅ Écriture via Agno SurrealDb réussie!
```

---

### `fix_surrealdb_agno_namespace.py`
**Rôle:** Corrige automatiquement le namespace Agno

**Actions effectuées:**
1. Connexion à SurrealDB en tant que root
2. Création du namespace `agno` (DEFINE NAMESPACE)
3. Sélection du namespace/database
4. Définition de la database (DEFINE DATABASE)
5. Test d'écriture pour validation
6. Test avec Agno SurrealDb

**Usage:**
```bash
uv run python fix_surrealdb_agno_namespace.py
```

**Résultat attendu:**
```
ÉTAPE 1: Création/Vérification du namespace 'agno'
✅ Namespace 'agno' défini

ÉTAPE 2: Définition de la database
✅ Database 'notary_db' définie dans namespace 'agno'

ÉTAPE 3: Test d'écriture
✅ Écriture dans namespace 'agno' réussie!

ÉTAPE 4: Test avec Agno SurrealDb
✅ Instance Agno SurrealDb créée
✅ Écriture via Agno réussie!

✅ FIX COMPLÉTÉ AVEC SUCCÈS!
```

---

## 🔍 Vérification Post-Fix

### 1. Vérifier que les warnings ont disparu
```bash
MODEL=ollama:qwen2.5:7b uv run python test_sprint1_validation.py

# Avant fix:
# WARNING Error getting session from db...  ❌

# Après fix:
# (pas de warning)  ✅
```

### 2. Vérifier la persistance des workflows
```bash
# Interroger SurrealDB pour voir les workflows sauvegardés
curl -X POST http://localhost:8001/sql \
  -H "Accept: application/json" \
  -H "NS: agno" \
  -H "DB: notary_db" \
  -u "root:root" \
  -d "SELECT * FROM workflow_runs ORDER BY created_at DESC LIMIT 5;"
```

**Résultat attendu:**
```json
[
  {
    "id": "workflow_runs:abc123",
    "workflow_name": "AnalyseDossierNotarial",
    "created_at": "2025-11-20T12:00:00Z",
    "status": "completed",
    "metadata": {
      "dossier_id": "...",
      "model": "ollama:qwen2.5:7b"
    },
    ...
  },
  ...
]
```

### 3. Vérifier les tables Agno
```bash
curl -X POST http://localhost:8001/sql \
  -H "NS: agno" \
  -H "DB: notary_db" \
  -u "root:root" \
  -d "INFO FOR DB;"
```

**Tables attendues:**
- `workflow_runs` ✅
- `workflow_sessions` ✅
- `agent_sessions` ✅
- `team_sessions` ✅

---

## ❓ FAQ

### Q: Pourquoi deux namespaces (`notary` et `agno`)?

**R:** Architecture hybride:
- **Namespace `notary`:** Tables métier (dossier, document, user, checklist)
- **Namespace `agno`:** Tables Agno créées automatiquement (workflow_runs, agent_sessions)

Cette séparation est conforme aux exemples officiels Agno.

### Q: Le fix doit-il être refait après redémarrage?

**R:** Non! Une fois le namespace créé, il persiste dans SurrealDB.

Mais si vous supprimez complètement SurrealDB (rm -rf data/surrealdb), vous devrez:
1. Re-lancer `init_schema.py` (pour les tables métier)
2. Re-lancer `fix_surrealdb_agno_namespace.py` (pour le namespace Agno)

### Q: Puis-je utiliser un seul namespace pour tout?

**R:** Oui, mais ce n'est pas recommandé:
- ❌ Agno et tables métier mélangées
- ❌ Moins clair architecturalement
- ✅ Le pattern actuel sépare proprement les responsabilités

### Q: Les workflows continuent de fonctionner sans fix?

**R:** Oui! L'impact est uniquement sur la persistance:
- ✅ Workflow s'exécute normalement
- ✅ Résultats disponibles (score, checklist)
- ❌ Pas d'historique sauvegardé
- ❌ Pas de traçabilité des agents

---

## 📚 Documentation Complète

Pour plus de détails, voir:
- **`docs/SURREALDB_AGNO_AUTH_ISSUE.md`** - Documentation technique complète
- **`CLAUDE.md`** - Historique du projet et sessions

---

## 🚀 Prochaines Étapes

Une fois le fix appliqué:

1. **Relancer tous les tests:**
   ```bash
   TEST_ALL_OLLAMA=1 uv run python test_sprint1_validation.py
   ```

2. **Créer Pull Request** pour merger Sprint 1

3. **Sprint 2:** Dashboard avec historique des workflows depuis `workflow_runs`

---

**Créé:** 2025-11-20
**Par:** Claude Code
**Context:** Sprint 1 - Investigation warnings SurrealDB
