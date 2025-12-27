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
   - **Import depuis YouTube** : Téléchargement audio de vidéos YouTube en MP3
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

9. **Recherche CAIJ** 🆕
   - Intégration avec le Centre d'accès à l'information juridique du Québec
   - Outil Agno pour agents conversationnels
   - Support des 8 rubriques officielles (Législation, Jurisprudence, Doctrine, etc.)
   - Identification automatique des catégories de documents
   - Rate limiting et authentification automatique

10. **Tuteur IA pédagogique** ✨
   - Mode tuteur automatique détectant le document ouvert
   - Génération de résumés structurés avec objectifs d'apprentissage
   - Création de cartes mentales (mind maps) thématiques
   - Quiz interactifs avec explications détaillées
   - Explications de concepts juridiques avec méthode socratique
   - Détection automatique du contexte via activity tracking
   - 4 outils Agno dédiés : `generate_summary`, `generate_mindmap`, `generate_quiz`, `explain_concept`

### Architecture technique

Voir **`ARCHITECTURE.md`** pour la documentation complète.

**Modules clés :**
- `backend/services/document_service.py` - 🆕 Service CRUD documents (centralise logique métier)
- `backend/routes/documents.py` - API de gestion des documents (refactorisé)
- `backend/routes/linked_directory.py` - API de liaison de répertoires
- `backend/routes/docusaurus.py` - API d'import Docusaurus
- `backend/services/youtube_service.py` - Service de téléchargement YouTube
- `backend/services/caij_search_service.py` - Service de recherche CAIJ
- `backend/services/tutor_service.py` - Service de génération de contenu pédagogique
- `backend/tools/caij_search_tool.py` - Outil Agno pour CAIJ
- `backend/tools/tutor_tools.py` - Outils Agno pour le tuteur IA
- `backend/models/document_models.py` - Modèles Pydantic partagés
- `backend/models/caij_models.py` - Modèles CAIJ avec mapping de rubriques
- `backend/tests/test_documents_refactored.py` - 🆕 Tests d'intégration (13 tests, 100%)
- `frontend/src/components/cases/linked-directories-section.tsx` - Interface répertoires liés
- `frontend/src/components/cases/directory-tree-view.tsx` - Vue arborescente
- `frontend/src/components/cases/youtube-download-modal.tsx` - Modal d'import YouTube

---

## Session actuelle (2025-12-27) - Nettoyage et Audit Dette Technique ✅

**Objectif** : Nettoyer les fichiers temporaires et auditer la dette technique.

**Actions complétées** :
- ✅ Suppression fichier debug `test_upload_debug.py`
- ✅ Correction sécurité : Retrait clé API dans `.env.example` (non committée)
- ✅ Audit duplication `DocumentResponse` : Déjà corrigée !
- ✅ Vérification imports : Tous les fichiers utilisent `models/document_models.py`
- ✅ Mise à jour `CLAUDE.md` : Recommandations obsolètes retirées

**Découvertes** :
- La duplication `DocumentResponse` avait déjà été éliminée lors d'une session précédente
- Aucune définition locale restante dans `routes/`
- Pattern d'import correct appliqué partout

**Prochaine session** : Phase 3.2 - Benchmarking et optimisation RAG

---

## Sessions récentes (Résumé)

### 2025-12-26 PM - Refactoring Phase 2 & Tests Phase 3.1 ✅

**Objectif** : Finaliser le refactoring DocumentService et valider avec tests d'intégration.

**Phase 2 - Refactoring (Complété)** :
- Extraction de la logique métier vers `DocumentService`
- 15/18 endpoints refactorisés
- Réduction `routes/documents.py` : 2324 → 1902 lignes (-18.2%)
- Pattern uniforme de récupération de documents

**Phase 3.1 - Tests d'Intégration (Complété)** :
- Création de 13 tests d'intégration pour endpoints refactorisés
- Découverte et correction de **5 bugs critiques** :
  1. ✅ UUID avec tirets incompatible SurrealDB
  2. ✅ ID dupliqué dans CREATE statement
  3. ✅ Ordre des routes FastAPI (`/diagnostic` vs `/{doc_id}`)
  4. ✅ Noms de champs API (serialization_alias)
  5. ✅ Codes de statut HTTP incorrects
- **Résultat final : 13/13 tests passent (100%)** ✅

**Commits créés** :
- `e6f0f8f` - fix: Use hex UUID format for SurrealDB compatibility + add Phase 3 integration tests
- `89792bd` - fix: Correct test expectations and route order for diagnostic endpoint
- `c1a3b8f` - docs: Update ROADMAP - Phase 3.1 completed

**Détails complets** : Voir `docs/ROADMAP_2025.md` et `docs/archive/SESSIONS_2025-12.md`

### 2025-12-26 AM - Tuteur IA pédagogique ✨

**Objectif** : Transformer le chat en tuteur IA détectant automatiquement le document ouvert.

**Implémentation** :
- `backend/services/tutor_service.py` - Service de génération pédagogique
- `backend/tools/tutor_tools.py` - 4 outils Agno
- `backend/routes/chat.py` - Détection contexte via activity tracking

**Fonctionnalités** :
- Résumés structurés, cartes mentales, quiz interactifs, explications socratiques
- Ancrage dans `semantic_search` (anti-hallucination)

### 2025-12-26 AM - Intégration CAIJ ✅

**Solution** : Playwright pour web scraping de CAIJ (jurisprudence québécoise)

**Implémentation** :
- `backend/services/caij_search_service.py` - Authentification automatique, extraction résultats
- `backend/models/caij_models.py` - Modèles avec mapping 8 rubriques (100% précision)
- `backend/tools/caij_search_tool.py` - Outil Agno `search_caij_jurisprudence`
- Tests complets passent (13/13 mapping, 5 résultats en ~5.3s)

**Configuration** : `.env` avec `CAIJ_EMAIL` et `CAIJ_PASSWORD` + `playwright install chromium`

### 2025-12-21 - Import YouTube 🎥

**Fonctionnalité complète** pour télécharger l'audio de vidéos YouTube :
- `backend/services/youtube_service.py` - yt-dlp + ffmpeg
- `backend/routes/documents.py` - 2 endpoints (info + download)
- `frontend/src/components/cases/youtube-download-modal.tsx` - Modal avec workflow complet
- Support `auto_transcribe` (backend seulement, pas encore dans UI)

### 2025-12-20 - Corrections bugs validation 🔐

**Failles de sécurité corrigées** dans `/transcribe` :
- Validation `course_id` manquante ajoutée
- Validation ownership du document ajoutée
- 62/62 tests passent (100%)

### 2025-12-20 AM - Tests d'intégration ✅

**Résultats** : 53/55 tests passent (96%), 2 bugs backend documentés
- Timeout augmenté 120s → 300s pour opérations ML
- Corrections SSE et format de réponse API

### 2025-12-08 - Fix affichage répertoires liés 🔧

**Problème** : Section "Répertoires liés" n'apparaissait pas malgré données en DB

**Cause racine** : Duplication de `DocumentResponse` (models/document_models.py vs routes/documents.py)
- Définition locale dans routes manquait le champ `linked_source`
- Pydantic omettait silencieusement le champ lors de la sérialisation

**Solution initiale** : Ajout `linked_source: Optional[dict]` dans `routes/documents.py`

**Solution finale** : ✅ Duplication complètement éliminée (session ultérieure)
- Utilisation unique de `models/document_models.py`
- Import correct dans tous les fichiers de routes

**Leçon** : Toujours suivre le flux de données : DB → Query → Serialization → API → Frontend

### 2025-12-06 - Import Docusaurus 📚

**Fonctionnalité complète** d'import de documentation Docusaurus :
- `backend/routes/docusaurus.py` - 4 endpoints avec tracking SHA-256
- `frontend/src/components/cases/import-docusaurus-modal.tsx` - Modal avec sélection par dossier
- Workflow : Copie → Hash → Stockage → Indexation RAG

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

1. **Mettre à jour README.md** (~1h) ✅ **FAIT** (2025-12-26)
   - ✅ Synchronisé avec l'état actuel du projet
   - ✅ Ajouté section Tuteur IA pédagogique
   - ✅ Mis à jour structure du projet avec nouveaux fichiers
   - ✅ Ajouté documentation complète dans section Utilisation
   - ✅ Mis à jour liste des technologies

2. **Refactoring DocumentResponse** (~2h) ✅ **FAIT** (2025-12-27)
   - ✅ Duplication complètement éliminée
   - ✅ Utilisation unique de `models/document_models.py`
   - ✅ Import correct dans tous les fichiers de routes
   - Aucune définition locale restante

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

1. ~~**Mettre à jour README.md** (1h)~~ ✅ **COMPLÉTÉ**
2. **Refactoring DocumentResponse** (2h) - Éliminer duplication critique
3. **Tests d'intégration de base** (4-6h) - Assurer stabilité avant nouvelles features

**Ensuite** : Logos providers + Épingler cours (amélioration UX immédiatement visible)

**Nouvelles fonctionnalités complétées** :
- ✅ **Tuteur IA pédagogique** (2025-12-26) - Résumés, mind maps, quiz, explications

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
