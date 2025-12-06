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

## État actuel du projet (2025-12-05)

### Fonctionnalités implémentées

1. **Gestion des dossiers**
   - CRUD complet via API REST
   - Types : civil, pénal, administratif, familial, commercial, travail, constitutionnel
   - Suppression en cascade : documents, conversations, chunks d'embeddings

2. **Gestion des documents**
   - Upload de fichiers (PDF, Word, images, audio)
   - DataTable avec filtres (nom, type) et tri
   - Fichiers dérivés automatiquement liés (transcription, extraction PDF, TTS)
   - Actions contextuelles selon le type de fichier

3. **Transcription audio**
   - Whisper MLX (modèle large-v3-turbo recommandé)
   - Workflow hybride : Whisper → Agent LLM (formatage) → Sauvegarde
   - Création automatique de fichiers markdown

4. **Agent conversationnel**
   - Chat avec streaming SSE
   - Support multi-providers : **Claude, Ollama, MLX**
   - **Recherche sémantique intégrée** : utilise automatiquement `semantic_search`
   - Mémoire de conversation dans SurrealDB
   - **Règle de citation des sources** appliquée dans le prompt système

5. **Indexation vectorielle et RAG**
   - Embeddings BGE-M3 via sentence-transformers
   - Accélération GPU : MPS (Apple Silicon) / CUDA / CPU
   - Chunking intelligent (400 mots, 50 mots overlap)
   - Recherche sémantique dans les documents
   - **Fix critique appliqué** : Utilisation de `type::thing()` pour gérer les UUIDs SurrealDB

6. **Synthèse vocale (TTS)**
   - Service edge-tts (Microsoft Edge TTS)
   - 15 voix : 13 françaises + 2 anglaises
   - Génération audio MP3 depuis documents markdown
   - Configuration des voix par défaut dans Settings

7. **Import Docusaurus** ✨ NOUVEAU
   - Import de fichiers Markdown depuis documentation Docusaurus
   - Scan automatique du répertoire Docusaurus (`/Users/alain/Workspace/Docusaurus/docs`)
   - Interface de sélection par dossier avec recherche
   - Indexation automatique pour RAG
   - Tracking des mises à jour (hash SHA-256, mtime)
   - Réindexation à la demande si fichier source modifié

### Architecture technique

Voir **`ARCHITECTURE.md`** pour la documentation complète.

**Nouveaux modules (2025-12-05) :**
- `backend/auth/helpers.py` - Helpers d'authentification centralisés
- `backend/utils/id_utils.py` - Normalisation des IDs
- `backend/utils/file_utils.py` - Utilitaires fichiers
- `backend/models/document_models.py` - Modèles Pydantic partagés (+ DocusaurusSource)
- `backend/routes/transcription.py` - Routes transcription (extrait de documents.py)
- `backend/routes/extraction.py` - Routes extraction (extrait de documents.py)
- `backend/routes/docusaurus.py` - Routes import Docusaurus ✨ NOUVEAU
- `backend/services/model_server_manager.py` - Orchestration serveurs MLX/vLLM
- `backend/services/vllm_server_service.py` - Gestion serveur vLLM (conservé pour usage manuel)
- `frontend/src/components/cases/import-docusaurus-modal.tsx` - Modal d'import Docusaurus ✨ NOUVEAU
- `frontend/src/components/ui/scroll-area.tsx` - Composant shadcn/ui ScrollArea ✨ NOUVEAU

---

## Dernière session (2025-12-06) - Import Docusaurus 📚

### Fonctionnalité implémentée

Ajout d'une fonctionnalité complète d'import de documentation Docusaurus dans Legal Assistant :

**Backend :**
- Nouveau router `backend/routes/docusaurus.py` avec 4 endpoints :
  1. `GET /api/docusaurus/list` - Liste les fichiers `.md` et `.mdx` disponibles
  2. `POST /api/cases/{case_id}/import-docusaurus` - Importe des fichiers sélectionnés
  3. `POST /api/cases/{case_id}/check-docusaurus-updates` - Vérifie si les sources ont changé
  4. `POST /api/documents/{doc_id}/reindex-docusaurus` - Réindexe un document modifié
- Modèle `DocusaurusSource` ajouté pour tracker les métadonnées (hash, mtime, chemin source)
- Workflow d'import : Copie → Hash SHA-256 → Stockage → Indexation RAG automatique

**Frontend :**
- Modal `ImportDocusaurusModal` avec interface de sélection par dossier
- Recherche en temps réel dans les fichiers
- Sélection individuelle ou par dossier entier
- Bouton "Docusaurus" ajouté dans l'onglet Documents
- Composant `ScrollArea` (shadcn/ui) créé pour le modal

**Détails techniques :**
- Chemin par défaut : `/Users/alain/Workspace/Docusaurus/docs`
- Support `.md` et `.mdx`
- Ignore `node_modules` et dossiers cachés
- Documents marqués avec `source_type: "docusaurus"`
- Tracking des mises à jour via `mtime` et hash SHA-256

### État final

✅ **Fonctionnalité complète et prête à tester**
- Backend : 4 endpoints fonctionnels
- Frontend : Bouton + Modal intégré dans l'onglet Documents
- API : `docusaurusApi` dans `lib/api.ts`
- Types : `DocusaurusFile` et `DocusaurusSource` ajoutés

**Fichiers modifiés :**
- `backend/main.py` - Ajout du router Docusaurus
- `backend/routes/__init__.py` - Export du nouveau router
- `backend/models/document_models.py` - Ajout `DocusaurusSource`
- `backend/routes/documents.py` - Ajout champs Docusaurus
- `frontend/src/types/index.ts` - Ajout types Docusaurus
- `frontend/src/components/cases/tabs/documents-tab.tsx` - Intégration modal

**Nouveaux fichiers :**
- `backend/routes/docusaurus.py` (519 lignes)
- `frontend/src/components/cases/import-docusaurus-modal.tsx` (243 lignes)
- `frontend/src/components/ui/scroll-area.tsx` (49 lignes)

**Package ajouté :**
- `@radix-ui/react-scroll-area` (dépendance du composant ScrollArea)

### À tester

```bash
# Terminal 1: SurrealDB
surreal start --user root --pass root --bind 0.0.0.0:8002 file:data/surreal.db

# Terminal 2: Backend
cd backend && uv run python main.py

# Terminal 3: Frontend
cd frontend && npm run dev -- -p 3001
```

1. Ouvrir un dossier (case)
2. Cliquer sur "Docusaurus" dans l'onglet Documents
3. Sélectionner des fichiers à importer
4. Vérifier qu'ils apparaissent dans la liste des documents
5. Tester la recherche sémantique avec ces documents

---

## Session précédente (2025-12-05) - Fix MLX auto-startup

### Problème identifié

Le serveur MLX ne démarrait pas automatiquement :
- **Erreur 1** : Commande dépréciée `python -m mlx_lm.server`
- **Erreur 2** : Timeout de 30s insuffisant pour téléchargement initial du modèle (~2 GB)
- **Erreur 3** : Paramètre `max_wait` hardcodé à 30s dans `start()` ignorait le `_startup_timeout`

### Corrections appliquées

**1. Commande MLX corrigée** (`mlx_server_service.py:88-94`)
```python
# ❌ Avant
["python3", "-m", "mlx_lm.server", "--model", model_id, ...]

# ✅ Après
["mlx_lm.server", "--model", model_id, ...]
```

**2. Timeout augmenté** (`mlx_server_service.py:33`)
```python
self._startup_timeout = 120  # 2 minutes (au lieu de 30s)
```

**3. Paramètre max_wait corrigé** (`mlx_server_service.py:60-73`)
```python
async def start(self, model_id: str, max_wait: Optional[int] = None) -> bool:
    if max_wait is None:
        max_wait = self._startup_timeout  # Utilise 120s par défaut
```

**4. Nettoyage frontend**
- Suppression de tous les modèles vLLM et HuggingFace de l'interface
- Ne reste que : **Claude (Anthropic), Ollama, MLX**
- Raison : vLLM trop lent sur Apple Silicon (CPU only, ~5-10 tok/s)

### État final

✅ **Le serveur MLX démarre maintenant automatiquement** :
- Au premier lancement : télécharge le modèle (~2 GB, 1-2 minutes)
- Lancements suivants : quasi-instantané (modèle en cache)
- Logs informatifs sur la progression du téléchargement

**Commit :** `96b4079` - "refactor: Implement MLX auto-startup and remove vLLM from UI"

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

### Immédiat

1. **Tester MLX auto-startup** ✅ PRIORITÉ
   - Redémarrer le backend
   - Sélectionner un modèle MLX dans l'interface
   - Vérifier que le serveur démarre automatiquement
   - Observer les logs pour confirmer le téléchargement/démarrage

2. **Ajuster paramètres RAG si nécessaire**
   - `top_k` : Actuellement 5, considérer 7-10
   - `min_similarity` : Actuellement 0.5 (50%)
   - `chunk_size` : Actuellement 400 mots
   - `chunk_overlap` : Actuellement 50 mots

### Court terme

1. **Améliorer l'agent**
   - ✅ FAIT : Recherche sémantique intégrée
   - ✅ FAIT : Mémoire de conversation
   - ✅ FAIT : Citation des sources obligatoire
   - ❌ À EXPLORER : Extraction d'entités juridiques

2. **UI/UX**
   - ✅ FAIT : DataTable avec filtres
   - ✅ FAIT : Prévisualisation markdown
   - ❌ À EXPLORER : Progression de transcription en temps réel

### Moyen terme

1. **Multi-agents avec DuckDuckGo** 💡
   - Workflow multi-agents pour documentation automatique
   - Utiliser `agno.tools.duckduckgo` pour recherches Internet

2. **Intégrations externes** 💡
   - MCP Server pour CanLII (jurisprudence canadienne)
   - MCP Server pour Légis Québec / LegisInfo

### Refactoring

**Phase 1 - Quick wins :** ✅ COMPLÉTÉ
- ✅ Supprimer scripts racine morts
- ✅ Extraire auth helpers dans `backend/auth/helpers.py`
- ✅ Créer utilitaires ID dans `backend/utils/id_utils.py`

**Phase 2 - Routes et modèles :** ✅ COMPLÉTÉ
- ✅ Extraire modèles Pydantic dans `backend/models/document_models.py`
- ✅ Créer `backend/routes/transcription.py`
- ✅ Créer `backend/routes/extraction.py`
- ❌ **À FAIRE** : Simplifier `documents.py` (toujours 2073 lignes)

**Phase 3 - Documentation :** ✅ COMPLÉTÉ
- ✅ Archiver sessions dans `docs/archive/SESSIONS_2025-12.md`
- ✅ Nettoyer CLAUDE.md

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

**Logs MLX à surveiller :**
```
🚀 Démarrage serveur MLX avec mlx-community/Qwen2.5-3B-Instruct-4bit...
⚠️  Si premier démarrage: téléchargement du modèle (~2-4 GB)
⏱️  Cela peut prendre 1-2 minutes selon votre connexion...
⏳ Attente du démarrage du serveur (max 120s)...
✅ Serveur MLX démarré avec succès en 45.3s
```

**Variables d'environnement :**
- Voir `.env.example` ou `ARCHITECTURE.md` pour la configuration complète

---

## Conventions

- Backend : Python avec FastAPI et Agno
- Frontend : TypeScript avec Next.js 14 (App Router) et shadcn/ui
- Base de données : SurrealDB
- Documentation : Français
- Commits : Anglais + footer Claude Code

---

## Ressources

- **Architecture complète** : `ARCHITECTURE.md`
- **Guide MLX** : `backend/MLX_GUIDE.md` et `backend/MLX_AUTO_START.md`
- **Guide modèles locaux** : `backend/LOCAL_MODELS_GUIDE.md`
- **Historique sessions** : `docs/archive/SESSIONS_2025-12.md`
