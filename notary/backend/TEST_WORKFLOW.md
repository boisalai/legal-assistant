# 🧪 Test End-to-End du Workflow Agno

Guide complet pour tester le workflow d'analyse de dossiers notariaux avec Agno, SurrealDB et Claude Anthropic.

---

## 📋 Prérequis

### 1. SurrealDB actif

Démarrez SurrealDB en local:

```bash
# Option 1: Docker (recommandé)
docker compose up -d surrealdb

# Option 2: Binaire SurrealDB
surreal start --user root --pass root --bind 0.0.0.0:8001
```

Vérifiez que SurrealDB fonctionne:
```bash
curl http://localhost:8001/health
# Devrait retourner: OK
```

### 2. Configuration de la clé API Anthropic

Ajoutez votre clé API dans le fichier `.env`:

```bash
# backend/.env
ANTHROPIC_API_KEY=sk-ant-api03-...votre-clé...
```

**Important:** Ne committez JAMAIS votre clé API!

### 3. Initialisation du schéma SurrealDB

```bash
cd backend
uv run python init_schema.py
```

Cela créera:
- 6 tables (user, dossier, document, checklist, agent_execution, audit_log)
- Relations graphe (possede, contient)
- Utilisateur de test: `user:test_notaire`

---

## 🚀 Lancer le Test

### Test complet end-to-end

```bash
cd backend
uv run python test_workflow_e2e.py
```

**Ce script va:**

1. ✅ Vérifier que ANTHROPIC_API_KEY est configurée
2. 📄 Générer un PDF de test réaliste (promesse d'achat-vente)
3. 📁 Créer un dossier notarial dans SurrealDB
4. 📤 Uploader le document PDF
5. 🤖 Exécuter le workflow Agno avec 4 agents:
   - **Agent Extracteur** - Extrait les données du PDF
   - **Agent Classificateur** - Identifie le type de transaction
   - **Agent Vérificateur** - Vérifie la cohérence
   - **Agent Générateur** - Crée la checklist finale
6. 📊 Afficher les résultats détaillés
7. 🧹 Nettoyer (supprimer le dossier de test)

**Durée estimée:** 1-2 minutes

---

## 📊 Résultats Attendus

### Sortie attendue

```
================================================================================
TEST END-TO-END: Workflow Agno + SurrealDB + Claude Anthropic
================================================================================

✅ ANTHROPIC_API_KEY trouvée

📄 Étape 1: Génération d'un PDF de test...
   ✅ PDF généré (12456 bytes)

📁 Étape 2: Création d'un dossier notarial...
   ✅ Dossier créé: dossier:abc123
      Nom: Test E2E - Vente Tremblay/Gagnon
      Type: vente

📤 Étape 3: Upload du document PDF...
   ✅ Document uploadé: document:def456
      Fichier: promesse_achat_vente_tremblay_gagnon.pdf
      Taille: 12456 bytes
      Hash: 7f8a9b2c3d4e5f6a...

📋 Fichiers à analyser: 1
   - data/uploads/dossier_abc123/def456_promesse_achat_vente_tremblay_gagnon.pdf

🤖 Étape 4: Exécution du workflow Agno (4 agents)...
   Ceci peut prendre 1-2 minutes...

======================================================================
WORKFLOW: Analyse de dossier notarial
Dossier: Test E2E - Vente Tremblay/Gagnon
Documents: 1 PDF(s)
======================================================================

📄 Étape 1: Extraction des données des documents...
✓ Extraction complétée

🏷️  Étape 2: Classification de la transaction...
✓ Classification complétée

✅ Étape 3: Vérification de cohérence...
✓ Vérification complétée

📋 Étape 4: Génération de la checklist...
✓ Checklist générée

======================================================================
✨ ANALYSE COMPLÉTÉE
Score de confiance: 87.50%
Validation humaine requise: NON
======================================================================

================================================================================
✨ RÉSULTATS DE L'ANALYSE
================================================================================

✅ Analyse réussie!

🏷️  CLASSIFICATION:
   Type transaction: vente
   Type propriété: residentielle

✅ VÉRIFICATION:
   Score: 92.00%
   Alertes: 0

📋 CHECKLIST:
   Score de confiance: 87.50%
   Validation requise: NON
   Items à vérifier: 8
      1. [HAUTE] Obtenir le certificat de localisation
      2. [HAUTE] Vérifier l'approbation de financement (échéance: 2025-01-30)
      3. [MOYENNE] Confirmer réparation fissure sous-sol
      4. [MOYENNE] Vérifier certificat de conformité ville
      5. [BASSE] Inventaire électroménagers inclus

   ⚠️  Points d'attention:
      - Date limite financement: 2025-01-30
      - Réparation sous-sol à compléter avant transfert
      - Vérifier taxe de bienvenue calculée

   📄 Documents à obtenir:
      - Certificat de localisation (vendeur)
      - Certificat de conformité (ville)
      - Approbation hypothèque (acheteur)

Étapes complétées: extraction, classification, verification, checklist

🧹 Étape 5: Nettoyage...
   ✅ Dossier supprimé

================================================================================
✅ TEST TERMINÉ
================================================================================
```

---

## 🔍 Vérification dans SurrealDB

### Pendant l'exécution

Vous pouvez monitorer les données en temps réel dans SurrealDB:

```bash
# Voir tous les dossiers
curl -X POST http://localhost:8001/sql \
  -H "Accept: application/json" \
  -H "NS: notary" \
  -H "DB: notary_db" \
  -u "root:root" \
  -d "SELECT * FROM dossier;"

# Voir les sessions de workflow Agno
curl -X POST http://localhost:8001/sql \
  -H "Accept: application/json" \
  -H "NS: notary" \
  -H "DB: notary_db" \
  -u "root:root" \
  -d "SELECT * FROM agno_session;"
```

### Avec Surrealist (GUI)

1. Téléchargez [Surrealist](https://surrealdb.com/surrealist)
2. Connectez-vous:
   - Endpoint: `http://localhost:8001`
   - Namespace: `notary`
   - Database: `notary_db`
   - Username: `root`
   - Password: `root`
3. Explorez les tables visuellement

---

## 🐛 Dépannage

### Erreur: "ANTHROPIC_API_KEY non configurée"

**Solution:**
```bash
# Ajoutez dans backend/.env
ANTHROPIC_API_KEY=sk-ant-api03-...votre-clé...

# Relancez le test
uv run python test_workflow_e2e.py
```

### Erreur: "Connection refused" (SurrealDB)

**Solution:**
```bash
# Vérifiez que SurrealDB est actif
docker compose ps surrealdb
# OU
ps aux | grep surreal

# Si non actif, démarrez-le
docker compose up -d surrealdb
```

### Erreur: "Table does not exist"

**Solution:**
```bash
# Réinitialisez le schéma
uv run python init_schema.py
```

### Erreur: "Rate limit exceeded" (Anthropic)

**Solution:**
- Attendez quelques secondes
- Vérifiez votre quota sur https://console.anthropic.com
- Claude Sonnet 4.5 est utilisé (modèle rapide et économique)

### Agents trop lents

**Solution:**
Vous pouvez passer à un modèle plus petit en modifiant `workflows/analyse_dossier.py`:

```python
# Remplacer
model=Claude(id="claude-sonnet-4-5-20250929"),

# Par (plus rapide mais moins précis)
model=Claude(id="claude-haiku-20241022"),
```

---

## 📁 Structure des Fichiers

```
backend/
├── test_workflow_e2e.py       # Script de test E2E
├── workflows/
│   └── analyse_dossier.py     # Workflow Agno (4 agents)
├── data/
│   ├── uploads/               # PDFs uploadés
│   └── surrealdb/             # Données SurrealDB
└── .env                       # Configuration (ANTHROPIC_API_KEY)
```

---

## 🎯 Prochaines Étapes

Une fois que le test E2E fonctionne:

1. **Tester avec de vrais PDFs** de votre cabinet
2. **Ajuster les prompts** des agents selon vos besoins
3. **Configurer l'API FastAPI** pour l'intégration frontend
4. **Créer le frontend Next.js** avec upload drag & drop
5. **Déployer en production** (AWS/Azure/GCP)

---

## 📚 Ressources

- [Documentation Agno](https://docs.agno.com)
- [SurrealDB Docs](https://surrealdb.com/docs)
- [Claude API Docs](https://docs.anthropic.com)
- [ReportLab Guide](https://www.reportlab.com/docs/reportlab-userguide.pdf)

---

**Bon test! 🚀**
