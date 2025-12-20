# Legal Assistant - Documentation de développement

> **Note:** Historique détaillé des sessions archivé dans `docs/archive/SESSIONS_2025-12.md`

---

## 🎉 Nouveauté : Support MLX (Apple Silicon)

**3 modèles Hugging Face locaux optimisés M1/M2/M3 :**
- ⭐ Qwen 2.5 3B (4-bit) - Recommandé pour français
- Llama 3.2 3B (4-bit) - Ultra-rapide
- Mistral 7B (4-bit) - Meilleure qualité

**Avantages :**
- 2x plus rapide qu'Ollama sur Apple Silicon (~50-60 tok/s)
- RAM réduite (~2 GB pour Qwen 2.5 3B)
- Support complet de function calling
- **Auto-démarrage** : Le backend démarre automatiquement le serveur MLX
- 100% gratuit et local

**Installation :** `uv sync` (installé par défaut)
**Guides :** `backend/MLX_GUIDE.md` et `backend/MLX_AUTO_START.md`

---

## État actuel du projet

### Fonctionnalités implémentées

1. **Gestion des dossiers**
   - CRUD complet via API REST
   - Types : civil, pénal, administratif, familial, commercial, travail, constitutionnel
   - Suppression en cascade : documents, conversations, chunks d'embeddings

2. **Gestion des documents**
   - Upload de fichiers (PDF, Word, images, audio)
   - **Liaison de répertoires locaux** : Indexation automatique de dossiers entiers
   - DataTable avec filtres (nom, type) et tri
   - Fichiers dérivés automatiquement liés (transcription, extraction PDF, TTS)
   - Actions contextuelles selon le type de fichier

3. **Répertoires liés** ✨
   - Liaison de dossiers locaux avec indexation automatique
   - Tracking des fichiers avec hash SHA-256 et mtime
   - Interface arborescente pour visualiser la structure
   - Groupement par link_id dans l'interface
   - Support des mises à jour et réindexation

4. **Import Docusaurus**
   - Import de fichiers Markdown depuis documentation Docusaurus
   - Scan automatique du répertoire avec sélection par dossier
   - Indexation automatique pour RAG
   - Tracking des mises à jour (hash SHA-256, mtime)

5. **Transcription audio**
   - Whisper MLX (modèle large-v3-turbo recommandé)
   - Workflow hybride : Whisper → Agent LLM (formatage) → Sauvegarde
   - Création automatique de fichiers markdown

6. **Agent conversationnel**
   - Chat avec streaming SSE
   - Support multi-providers : **Claude, Ollama, MLX**
   - **Recherche sémantique intégrée** : utilise automatiquement `semantic_search`
   - Mémoire de conversation dans SurrealDB
   - **Règle de citation des sources** appliquée dans le prompt système

7. **Indexation vectorielle et RAG**
   - Embeddings BGE-M3 via sentence-transformers
   - Accélération GPU : MPS (Apple Silicon) / CUDA / CPU
   - Chunking intelligent (400 mots, 50 mots overlap)
   - Recherche sémantique dans les documents

8. **Synthèse vocale (TTS)**
   - Service edge-tts (Microsoft Edge TTS)
   - 15 voix : 13 françaises + 2 anglaises
   - Génération audio MP3 depuis documents markdown
   - Configuration des voix par défaut dans Settings

### Architecture technique

Voir **`ARCHITECTURE.md`** pour la documentation complète.

**Modules clés :**
- `backend/routes/linked_directory.py` - API de liaison de répertoires
- `backend/routes/docusaurus.py` - API d'import Docusaurus
- `backend/models/document_models.py` - Modèles Pydantic partagés
- `frontend/src/components/cases/linked-directories-section.tsx` - Interface répertoires liés
- `frontend/src/components/cases/directory-tree-view.tsx` - Vue arborescente

---

## Dernière session (2025-12-20 PM) - Correction bugs validation `/transcribe` 🔐

### Objectif

Corriger les bugs de validation identifiés lors de la session précédente pour atteindre 100% de tests passants (55/55).

### Résultats

**État initial** : 53/55 tests passaient (96%), 2 tests skipped

**État final** : ✅ **62/62 tests passent** (100% des tests non-skipped) ✅

- ⏱️ **99 secondes** d'exécution
- 📊 **14% de couverture** de code
- 🔐 **Failles de sécurité corrigées** dans 2 endpoints

### Problèmes corrigés

#### 1. Validation `course_id` manquante
**Fichiers** : `routes/documents.py`, `routes/transcription.py`
**Problème** : Les endpoints `/transcribe` ne vérifiaient pas l'existence du `course_id`
**Solution** :
```python
clean_course_id = course_id.replace("course:", "")
course_check = await service.query(
    "SELECT * FROM course WHERE id = type::thing('course', $course_id)",
    {"course_id": clean_course_id}
)
if not course_check or len(course_check) == 0:
    raise HTTPException(status_code=404, detail="Course not found")
```

#### 2. Validation ownership du document
**Fichiers** : `routes/documents.py`, `routes/transcription.py`
**Problème** : Aucune vérification que le document appartient au cours demandé
**Solution** :
```python
if item.get("course_id") != course_id:
    raise HTTPException(status_code=403, detail="Document does not belong to this course")
```

#### 3. Duplication de routes `/transcribe`
**Découverte** : Deux routers gèrent la même route :
- `routes/documents.py` (nomenclature moderne : `course`)
- `routes/transcription.py` (nomenclature obsolète : `case`)

**Solution** : Corrections appliquées aux DEUX fichiers + support rétrocompatible `case:` → `course:`

#### 4. Syntaxe SurrealDB incorrecte
**Problème** : Utilisation de `WHERE id = $course_id` avec préfixe vs sans préfixe
**Solution** : Utiliser systématiquement `type::thing('course', $clean_id)` avec ID sans préfixe

### Impact sécurité

Les bugs corrigés représentaient une **faille de sécurité critique** :
- Un utilisateur pouvait transcrire n'importe quel document avec un `course_id` invalide
- Un utilisateur pouvait accéder aux documents d'autres cours

**Endpoints sécurisés** :
- `POST /api/courses/{course_id}/documents/{doc_id}/transcribe`
- `POST /api/courses/{course_id}/documents/{doc_id}/transcribe-workflow`

### Fichiers modifiés

- `backend/routes/documents.py` - Ajout validations course_id et ownership (2 endpoints)
- `backend/routes/transcription.py` - Ajout validations + support rétrocompatible case/course (2 endpoints)
- `backend/tests/test_transcription.py` - Retrait des `@pytest.mark.skip`

### Leçon apprise

**Gestion du serveur de test** : Le fixture `test_server` utilise `scope="session"`, donc le serveur ne redémarre pas entre les tests. Pour que les modifications de code soient prises en compte, il faut tuer manuellement le processus uvicorn avec `pkill -f "uvicorn main:app.*--port 8001"`.

---

## Session précédente (2025-12-20 AM) - Tests d'intégration fonctionnels ✅

### Objectif

Exécuter et corriger les tests d'intégration créés lors de sessions précédentes pour atteindre un taux de réussite initial élevé.

### Résultats

**État initial** : 45/55 tests passaient (82%), 10 erreurs de timeout

**État final** : ✅ 53/55 tests passent (96%), 2 tests skipped (bugs documentés)

- ⏱️ **82 secondes** d'exécution (vs 21 minutes initialement)
- 📊 **12% de couverture** de code (API endpoints)
- 🔧 **4 problèmes corrigés**, **2 bugs backend identifiés**

### Problèmes corrigés

#### 1. Timeouts HTTP (10 tests)
**Cause** : Le timeout de 120s était insuffisant pour les opérations ML (transcription, indexation).
**Solution** : Augmentation à 300s (5 minutes) dans `conftest.py:161`.

#### 2. Test `test_get_derived_documents`
**Cause** : Test attendait `{"derived_documents": [...]}`, API retourne `{"derived": [...]}`.
**Solution** : Correction du test pour accepter le format réel.

#### 3. Test `test_transcription_creates_markdown`
**Cause** : Tentative de parser JSON sur un endpoint SSE (Server-Sent Events).
**Solution** : Vérification du header `content-type: text/event-stream` au lieu de parser JSON.

#### 4. Tests de validation (2 tests → skipped)
**Cause** : Bugs de validation dans l'endpoint `/transcribe` :
- Ne vérifie pas l'existence du `course_id`
- Ne vérifie pas que le document appartient au cours

**Solution** : Tests marqués avec `@pytest.mark.skip` et bugs documentés avec références au code source.

### Fichiers modifiés

- `backend/tests/conftest.py` - Timeout augmenté de 120s → 300s
- `backend/tests/test_transcription.py` - 4 tests corrigés/skipped

### Documentation mise à jour

- `backend/tests/IMPLEMENTATION_SUMMARY.md` - Résultats détaillés de la session
- `backend/tests/README.md` - État actuel des tests (53/55 passent)

### Leçon apprise

**Méthodologie de debugging** : Lors de l'analyse des erreurs de tests, toujours :
1. Distinguer les **vraies erreurs** (bugs de code) des **erreurs de tests** (assertions incorrectes)
2. Vérifier la **documentation de l'API** avant de modifier les tests
3. Documenter les bugs identifiés avec références précises au code source

**Commit :** `97955a6` - "test: Fix integration test timeouts and SSE test assertions"

---

## Session précédente (2025-12-08) - Fix affichage répertoires liés 🔧

### Problème

La section "Répertoires liés" n'apparaissait pas dans l'interface malgré la création réussie de 26 documents avec `source_type: "linked"` et métadonnées `linked_source` complètes dans la base de données.

### Diagnostic

**Méthodologie incorrecte initiale** : Commencé par le frontend au lieu de suivre le flux de données.

**Approche correcte appliquée** :
1. ✅ **SurrealDB** - Données `linked_source` présentes
2. ✅ **Backend Query** - Requête récupère bien les données (logs confirmés)
3. ❌ **Backend Serialization** - **PROBLÈME IDENTIFIÉ ICI**
4. ❌ **API Response** - `curl` montrait `linked_source` absent du JSON
5. ❌ **Frontend** - Composant retournait `null` car pas de données

### Cause racine

**Deux définitions de `DocumentResponse`** :
- `models/document_models.py` ligne 17-35 (mise à jour mais NON utilisée)
- `routes/documents.py` ligne 61-78 (**utilisée, mais SANS le champ `linked_source`**)

Le code utilisait la définition locale dans `routes/documents.py` qui ne définissait pas `linked_source`, causant Pydantic à silencieusement omettre ce champ lors de la sérialisation.

### Solution

Ajout du champ `linked_source: Optional[dict] = None` à la classe `DocumentResponse` dans `/backend/routes/documents.py` ligne 76.

**Fichiers modifiés :**
- `backend/routes/documents.py` - Ajout champ `linked_source` au modèle et au constructeur

**Commit :** `b380c83` - "fix: Add linked_source field to DocumentResponse model"

### Leçon apprise

**Toujours suivre le flux des données de la source à la destination :**
1. Base de données → 2. Requête backend → 3. Sérialisation → 4. API → 5. Frontend

Au lieu de déboguer de manière désorganisée, identifier méthodiquement où les données sont perdues à chaque étape.

---

## Session précédente (2025-12-06) - Import Docusaurus 📚

Ajout d'une fonctionnalité complète d'import de documentation Docusaurus :

**Backend :**
- Router `backend/routes/docusaurus.py` avec 4 endpoints
- Modèle `DocusaurusSource` pour tracking métadonnées
- Workflow : Copie → Hash SHA-256 → Stockage → Indexation RAG

**Frontend :**
- Modal `ImportDocusaurusModal` avec sélection par dossier
- Recherche en temps réel et sélection multiple
- Composant `ScrollArea` (shadcn/ui)

**Commit :** Sessions archivées dans `docs/archive/SESSIONS_2025-12.md`

---

## Guide de sélection du modèle LLM

### 🎯 Règle d'or

- **Documents du dossier nécessaires ?** → **Claude Sonnet 4.5**
- **Conversation simple sans documents (Mac) ?** → **MLX Qwen 2.5 3B** ⭐
- **Conversation simple sans documents (autre) ?** → **Ollama Qwen 2.5 7B**

### Claude Sonnet 4.5 - ✅ RECOMMANDÉ POUR RAG

**Utiliser pour :**
- Questions nécessitant l'accès aux documents
- Recherche sémantique ("Résume l'arrêt X", "Qu'est-ce que...")
- Analyse juridique approfondie
- Citation de sources précises

**Avantages :**
- Support natif de function calling → utilise correctement `semantic_search`
- Comprend les instructions de citation des sources
- Raisonnement juridique de haute qualité
- Ne hallucine pas

**Inconvénients :**
- Coût par token (API Anthropic)
- Nécessite connexion Internet

### MLX Qwen 2.5 3B - ⭐ RAPIDE SUR MAC

**Utiliser pour :**
- Conversations générales sur Apple Silicon (M1/M2/M3)
- Développement et tests rapides
- Alternative plus rapide qu'Ollama

**Avantages :**
- Gratuit, très rapide (~50-60 tok/s, 2x plus rapide qu'Ollama)
- Excellent en français
- Support complet de function calling
- RAM réduite (~2 GB)
- **Auto-démarrage par le backend** ✅

**Inconvénients :**
- ❌ Apple Silicon uniquement (pas Intel)
- ⚠️ Qualité légèrement inférieure à Claude pour RAG

### Ollama Qwen 2.5 7B - ⚠️ CONVERSATIONS SIMPLES

**Utiliser pour :**
- Conversations générales ("Bonjour", "Merci")
- Questions sur l'assistant
- Cross-platform (Mac, Linux, Windows)

**Avantages :**
- Gratuit, fonctionne hors ligne

**Inconvénients :**
- ❌ **NE SUPPORTE PAS function calling correctement**
- ❌ **Hallucine** si on lui demande de résumer des documents
- ❌ Ne cite pas les sources

💡 **En cas de doute :** Choisissez Claude Sonnet 4.5.

---

## Prochaines étapes suggérées

> **Plan consolidé 2025-12-19** - Synthèse des recommandations après analyse README.md, CLAUDE.md et Docusaurus

### 🔴 Urgent - Incohérences et Dette Technique

1. **Mettre à jour README.md** (~1h)
   - Synchroniser avec l'état actuel du projet
   - Remplacer "Résumé de jugements" par les vraies fonctionnalités
   - Corriger "cases/judgments" → "courses"
   - Documenter le frontend existant
   - Retirer mentions du workflow obsolète de 4 agents

2. **Refactoring DocumentResponse** (~2h)
   - ❌ **À FAIRE** : Supprimer la duplication dans `routes/documents.py` (lignes 61-78)
   - Utiliser uniquement `models/document_models.py`
   - Importer au lieu de redéfinir localement
   - **Critique** : Cette duplication a déjà causé des bugs (session 2025-12-08)

3. **Simplification documents.py** (~4-6h)
   - ❌ **À FAIRE** : Fichier trop long (~2100 lignes)
   - Extraire logique métier en services dédiés :
     - `services/document_service.py` - CRUD et gestion fichiers
     - `services/linked_directory_service.py` - Logique répertoires liés
     - `services/docusaurus_service.py` - Logique import Docusaurus
   - Garder uniquement les endpoints et validations dans `routes/documents.py`

4. **Nettoyer les logs de debug**
   - Retirer les `logger.info("🔍 ...")` ajoutés temporairement
   - Garder uniquement les logs essentiels (erreurs, warnings)

### 🎯 Priorité Haute - Stabilité et Qualité

5. **Tests d'intégration** (~4-6h)
   - Tests API endpoints critiques :
     - `/api/courses` - CRUD complet
     - `/api/documents` - Upload, liaison, suppression
     - `/api/chat` - Streaming SSE avec RAG
   - Tests recherche sémantique avec différents modèles d'embedding
   - Tests workflow transcription audio
   - Tests upload et liaison de répertoires

6. **Ajuster paramètres RAG** (~2h)
   - Tester et optimiser :
     - `top_k` : Actuellement 5 → considérer 7-10
     - `min_similarity` : Actuellement 0.5 (50%)
     - `chunk_size` : Actuellement 400 mots
     - `chunk_overlap` : Actuellement 50 mots
   - Benchmarker avec différentes configurations
   - Documenter les résultats dans ARCHITECTURE.md

### 🚀 Priorité Moyenne - UX et Fonctionnalités

7. **Logos des providers** (~2h)
   - Remplacer textes par logos officiels :
     - Anthropic : `https://github.com/images/modules/marketplace/models/families/anthropic.svg`
     - OpenAI : `https://github.com/images/modules/marketplace/models/families/openai.svg`
     - Gemini : `https://github.com/images/modules/marketplace/models/families/gemini.svg`
     - Ollama : `https://lobehub.com/fr/icons/ollama`
     - HuggingFace : `https://huggingface.co/datasets/huggingface/brand-assets/resolve/main/hf-logo.svg`
   - Afficher dans sélecteur de modèles (LLM et Embedding)

8. **Épingler cours favoris** (~3h)
   - Ajouter champ `pinned: bool` à la table `course`
   - Icône "pin" dans la liste des cours
   - Tri automatique : cours épinglés en premier
   - Persistence dans SurrealDB

9. **Progression temps réel** (~4h)
   - Afficher progression transcription audio (WebSocket ou SSE)
   - Afficher progression indexation documents
   - Barre de progression dans l'UI
   - Notifications de fin de traitement

10. **Page de connexion et authentification** (~6-8h)
    - Système d'authentification simple (email/password)
    - JWT tokens avec refresh
    - Middleware de protection des routes
    - Page de connexion/inscription
    - Ajuster bouton "Déconnexion"

11. **OCR avancé avec Docling** (~4h)
    - Exploiter Docling (déjà installé) pour PDF scannés
    - Améliorer extraction tableaux et structures complexes
    - Tester avec PDF de jurisprudence québécoise
    - Comparer avec l'extraction actuelle

### 💡 Priorité Basse - Innovation

12. **Extraction d'entités juridiques** (~8-12h)
    - Identifier automatiquement :
      - Parties (demandeur, défendeur)
      - Dates importantes (jugement, événements)
      - Tribunaux et juridictions
      - Références légales (articles, lois)
    - Enrichir l'indexation avec ces métadonnées
    - Créer des filtres de recherche par entité

13. **Multi-agents avec DuckDuckGo** (~6-10h)
    - Workflow multi-agents pour documentation automatique
    - Utiliser `agno.tools.duckduckgo` pour recherches Internet
    - Validation croisée des informations
    - Génération de synthèses enrichies

14. **Intégrations MCP externes** (~10-15h chacune)
    - MCP Server pour CanLII (jurisprudence canadienne)
    - MCP Server pour Légis Québec / LegisInfo
    - SurrealMCP (déjà disponible dans Agno)
    - Agent OS inter-communication

15. **Modèles d'actes notariés** (~8-12h)
    - Importer templates depuis https://www.transports.gouv.qc.ca
    - Types : vente, achat, prêt hypothécaire, etc.
    - Génération assistée par IA
    - Remplissage automatique des champs

### 📚 Idées à explorer (Backlog)

- **Notar'IA** - Explorer l'intégration
- **Lexis+ AI** - Analyse de la concurrence
- **OCR avec modèles open-source** - HuggingFace alternatives
- **VineVoice** - TTS avancé pour remplacer edge-tts
- **Déploiement Render** - Production (https://render.com/pricing)
- **Agent OS** - Communication MCP entre agents
- **Culture partagée** - Apprentissage collectif (Agno feature)
- **Couleurs Anthropic Interviewer** - Inspiration UI (https://www.anthropic.com/news/anthropic-interviewer)
- **GitHub Copilot design** - S'inspirer de https://github.com/copilot/c/1a58622c-405c-4ae3-988e-9d4e8c459ab6

---

### 🎯 Recommandation Top 3 (Démarrage)

1. **Mettre à jour README.md** (1h) - Première impression correcte du projet
2. **Refactoring DocumentResponse** (2h) - Éliminer duplication critique
3. **Tests d'intégration de base** (4-6h) - Assurer stabilité avant nouvelles features

**Ensuite** : Logos providers + Épingler cours (amélioration UX immédiatement visible)

---

## Démarrage rapide

```bash
# Terminal 1: SurrealDB
surreal start --user root --pass root --bind 0.0.0.0:8002 file:data/surreal.db

# Terminal 2: Backend (démarre auto MLX si configuré)
cd backend
uv run python main.py

# Terminal 3: Frontend
cd frontend
npm run dev -- -p 3001
```

## Notes techniques

**Ports :**
- SurrealDB : 8002
- Backend : 8000
- Frontend : 3001
- MLX Server : 8080 (auto-démarré si modèle MLX sélectionné)

**Installation :**
- `uv sync` installe toutes les dépendances :
  - Whisper (mlx-whisper)
  - Embeddings (sentence-transformers avec GPU: MPS/CUDA/CPU)
  - TTS (edge-tts)
  - Docling (extraction PDF avancée avec OCR)
  - MLX-LM (modèles HuggingFace optimisés Apple Silicon)

**Configuration embeddings :**
```python
# backend/services/document_indexing_service.py
embedding_provider = "local"           # local, ollama, ou openai
embedding_model = "BAAI/bge-m3"       # Modèle HuggingFace
chunk_size = 400                       # Mots par chunk
chunk_overlap = 50                     # Mots d'overlap
```

**Configuration TTS :**
```python
# backend/services/tts_service.py
DEFAULT_VOICES = {
    "fr": "fr-FR-DeniseNeural",  # Voix féminine française
    "en": "en-CA-ClaraNeural",   # Voix féminine anglaise (Canada)
}
# 15 voix disponibles
```

**Configuration MLX :**
```python
# backend/config/models.py
# Top 3 modèles recommandés pour M1 Pro 16 GB
"mlx-community/Qwen2.5-3B-Instruct-4bit"      # ~2 GB RAM, ~50 tok/s
"mlx-community/Llama-3.2-3B-Instruct-4bit"    # ~1.5 GB RAM, ~60 tok/s
"mlx-community/Mistral-7B-Instruct-v0.3-4bit" # ~4 GB RAM, ~35 tok/s
```

---

## Conventions

- Backend : Python avec FastAPI et Agno
- Frontend : TypeScript avec Next.js 14 (App Router) et shadcn/ui
- Base de données : SurrealDB
- Documentation : Français
- Commits : Anglais + footer Claude Code

### Politique shadcn/ui

**Règle stricte : Utiliser uniquement les versions officielles des composants shadcn/ui sans modification.**

**Composants shadcn/ui officiels (24)** - À maintenir en sync :
- `button`, `card`, `dialog`, `input`, `label`, `select`, `checkbox`, `avatar`, `separator`
- `collapsible`, `progress`, `slider`, `switch`, `tabs`, `tooltip`, `alert`, `badge`, `table`
- `textarea`, `skeleton`, `alert-dialog`, `dropdown-menu`, `sheet`, `scroll-area`

**Composants personnalisés autorisés (4)** :
- `audio-recorder.tsx` - Enregistrement audio avec visualisation
- `file-upload.tsx` - Upload drag-and-drop de fichiers
- `language-selector.tsx` - Sélecteur de locale i18n
- `markdown.tsx` - Rendu Markdown avec remark-gfm

**Procédure de mise à jour** :
1. Vérifier les nouvelles versions : https://ui.shadcn.com/docs/components
2. Mettre à jour : `npx shadcn@latest add <component-name>`
3. Accepter l'écrasement si demandé
4. Tester l'UI pour détecter les régressions

**Interdictions** :
- ❌ Modifier les composants shadcn/ui officiels
- ❌ Copier/coller du code shadcn/ui sans la CLI
- ❌ Créer des variantes personnalisées de composants existants
- ✅ Composer plusieurs composants shadcn/ui pour créer de nouvelles fonctionnalités

---

## Ressources

- **Architecture complète** : `ARCHITECTURE.md`
- **Guide MLX** : `backend/MLX_GUIDE.md` et `backend/MLX_AUTO_START.md`
- **Guide modèles locaux** : `backend/LOCAL_MODELS_GUIDE.md`
- **Historique sessions** : `docs/archive/SESSIONS_2025-12.md`
