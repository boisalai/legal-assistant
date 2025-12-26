# Roadmap de développement 2025

> Créé le 2025-12-26
> Plan d'action sur 2 semaines

---

## 🔴 **Phase 1 : Finaliser le travail en cours** (Immédiat - 1h15)

### 1.1 Committer les changements en attente (~1h)
Il y a beaucoup de modifications non commitées qui semblent complètes :

**Fichiers à committer ensemble :**
- `backend/migrations/004_add_pinned_field.surql` - Migration pour épingler les cours
- `backend/models/course.py` - Suppression de `course_name` dupliqué
- `backend/models/document_models.py` - `serialization_alias` pour compatibilité API
- `frontend/src/app/settings/page.tsx` - Paramètres LLM avancés
- `frontend/src/components/layout/model-selector.tsx` - Améliorations sélecteur
- Logos SVG (`meta.svg`, `mistral.svg`, `qwen.svg`)

**Actions :**
- Exécuter la migration 004 sur SurrealDB
- Tester les paramètres LLM avancés dans Settings
- Commit avec message descriptif des améliorations UX

### 1.2 Nettoyer les fichiers temporaires (~15 min)
**À ajouter au .gitignore :**
```
backend/logs*.txt
backend/screenshot_*.png
backend/caij_*.png
backend/scripts/caij_*.png
backend/test_chat_debug.py
backend/scripts/test_app_ui.py
```

---

## 🟡 **Phase 2 : Dette technique critique** (1-2 jours)

### 2.1 Refactoring DocumentResponse - **URGENT** ⚠️
**Problème** : Duplication dans `routes/documents.py` (lignes 61-78)
- Cette duplication a déjà causé des bugs (session 2025-12-08)
- Risque de désynchronisation entre les modèles

**Solution** :
```python
# routes/documents.py
from models.document_models import DocumentResponse, DocumentListResponse

# Supprimer la redéfinition locale
```

### 2.2 Simplification de `routes/documents.py` (~4-6h)
**Problème** : Fichier trop long (~2100 lignes)

**Refactoring proposé** :
```
backend/services/
├── document_service.py         # CRUD documents, upload, gestion fichiers
├── linked_directory_service.py # Logique répertoires liés (existe partiellement)
└── docusaurus_service.py       # Import Docusaurus
```

**Bénéfices** :
- Code plus maintenable
- Tests unitaires plus faciles
- Séparation des responsabilités

---

## 🟢 **Phase 3 : Qualité et stabilité** (2-3 jours)

### 3.1 Tests d'intégration complets (~6-8h)
**Priorité** : Couvrir les endpoints critiques

```python
backend/tests/integration/
├── test_courses_api.py        # CRUD complet
├── test_documents_api.py      # Upload, liaison, suppression
├── test_chat_api.py           # Streaming SSE avec RAG
├── test_tutor_api.py          # Outils pédagogiques
├── test_caij_search.py        # Recherche CAIJ
└── test_rag_pipeline.py       # Indexation et recherche
```

### 3.2 Benchmarking et optimisation RAG (~3-4h)
**Objectif** : Trouver les meilleurs paramètres

**Expériences à mener** :
```python
# Matrice de tests
params_grid = {
    'top_k': [5, 7, 10, 15],
    'min_similarity': [0.3, 0.4, 0.5, 0.6],
    'chunk_size': [300, 400, 500],
    'chunk_overlap': [30, 50, 70]
}

# Métriques à mesurer :
- Précision des réponses
- Rappel (% de documents pertinents trouvés)
- Temps de réponse
- Pertinence utilisateur (feedback)
```

**Documenter dans** : `ARCHITECTURE.md` ou nouveau `docs/RAG_BENCHMARKS.md`

---

## 🔵 **Phase 4 : Fonctionnalités UX** (3-5 jours)

### 4.1 Progression en temps réel (~4h)
**Objectif** : Feedback visuel pour opérations longues

```typescript
// WebSocket ou SSE pour :
- Transcription audio (progression %)
- Indexation de répertoires liés
- Import Docusaurus
- Génération de quiz/résumés
```

**UI** :
- Progress bars avec shadcn/ui `<Progress>`
- Toast notifications pour complétion
- État de chargement dans les DataTables

### 4.2 Recherche avancée dans documents (~3h)
**Actuellement** : Filtres basiques (nom, type)

**Améliorations** :
```typescript
// Nouveaux filtres :
- Date de création (range picker)
- Taille de fichier
- Source (upload, linked, docusaurus)
- Indexation status
- Recherche full-text dans le nom

// UI : Collapsible filter panel
```

### 4.3 Auto-transcription YouTube (~2h)
**Actuellement** : Checkbox `auto_transcribe` backend seulement

**À faire** :
- Ajouter checkbox dans `youtube-download-modal.tsx`
- Progression en temps réel de la transcription
- Notification à la fin

---

## 🟣 **Phase 5 : Fonctionnalités avancées** (1-2 semaines)

### 5.1 Système d'authentification (~6-8h)
**Composants** :
```typescript
- Page login/signup
- JWT tokens avec refresh
- Middleware de protection routes
- Multi-utilisateurs dans SurrealDB
- Migration pour table users
```

### 5.2 Export et partage (~4-6h)
**Fonctionnalités** :
```typescript
- Export cours en PDF (avec résumés/cartes mentales)
- Export conversations en Markdown
- Partage de résumés par lien
- Export quizzes en format imprimable
```

### 5.3 OCR avancé avec Docling (~4h)
**Objectif** : Améliorer extraction de PDF scannés

```python
# Exploiter Docling (déjà installé)
- OCR pour PDF scannés
- Extraction tableaux structurés
- Extraction d'images et diagrammes
- Benchmark vs extraction actuelle
```

### 5.4 Extraction d'entités juridiques (~8-12h)
**Utiliser NLP pour extraire** :
```python
entities = {
    "parties": ["demandeur", "défendeur"],
    "dates": ["jugement", "événements"],
    "juridictions": ["tribunaux"],
    "references": ["articles", "lois"]
}

# Enrichir l'indexation RAG
# Créer filtres de recherche
```

---

## 🎯 **Plan d'action recommandé : 2 semaines**

### Semaine 1 : Stabilisation
1. ✅ **Jour 1 : Finaliser et committer** (Phase 1)
2. ✅ **Jours 2-3 : Dette technique** (Phase 2)
3. ✅ **Jours 4-5 : Tests et RAG** (Phase 3)

### Semaine 2 : Amélioration UX
4. ✅ **Jours 6-8 : UX Features** (Phase 4.1, 4.2, 4.3)
5. ✅ **Jours 9-10 : Feature avancée** (Choisir entre 5.1, 5.2, 5.3, 5.4)

---

## 📊 **Quick Wins pour impact immédiat**

Si besoin de résultats visibles rapidement :

1. **Progression temps réel** (4h) → Beaucoup d'impact UX
2. **Commit changements en cours** (1h) → Nettoyer le repo
3. **Auto-transcription YouTube UI** (2h) → Fonctionnalité visible
4. **Export résumés en PDF** (3h) → Valeur ajoutée

---

## 📝 Notes de suivi

### 2025-12-26
- ✅ Création de la roadmap
- 🚀 Démarrage Phase 1

### À venir
- [ ] Phase 1 complétée
- [ ] Phase 2 démarrée
