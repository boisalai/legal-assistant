# Legal Assistant - Documentation de développement

> **Note:** Historique détaillé des sessions de développement archivé dans `docs/archive/SESSIONS_2025-12.md`

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
- Auto-démarrage : Le backend démarre automatiquement le serveur MLX
- 100% gratuit et local

**Installation :** `uv sync` (installé par défaut)
**Guides complets :** `backend/MLX_GUIDE.md` et `backend/MLX_AUTO_START.md`

---

## État actuel du projet

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
   - Support multi-providers : Claude (Anthropic), Ollama, MLX
   - **Recherche sémantique intégrée** : utilise automatiquement `semantic_search`
   - Mémoire de conversation dans SurrealDB

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

### Architecture technique

Voir **`ARCHITECTURE.md`** pour la documentation complète :
- Structure des dossiers
- Services backend (SurrealDB, Whisper, Model Factory)
- Patterns Agno (Workflow déclaratif, hybride, avec classe)
- Routes API
- Composants frontend

### Fichiers clés

| Fichier | Description |
|---------|-------------|
| `backend/auth/helpers.py` | **NOUVEAU** - Helpers d'authentification centralisés |
| `backend/utils/id_utils.py` | **NOUVEAU** - Utilitaires pour normalisation des IDs |
| `frontend/src/components/cases/documents-data-table.tsx` | DataTable avec filtres et actions |
| `backend/tools/semantic_search_tool.py` | Outil de recherche sémantique (fix `type::thing()` appliqué) |
| `backend/routes/chat.py` | Agent conversationnel avec règle de citation des sources |

---

## Guide de sélection du modèle LLM

### 🎯 Règle d'or

- **Documents du dossier nécessaires ?** → **Claude Sonnet 4.5**
- **Conversation simple sans documents (Mac) ?** → **MLX Qwen 2.5 3B** ⭐ (plus rapide)
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
- Nécessite une connexion Internet

### Ollama Qwen 2.5 7B - ⚠️ CONVERSATIONS SIMPLES UNIQUEMENT

**Utiliser pour :**
- Conversations générales ("Bonjour", "Merci")
- Questions sur l'assistant
- Clarifications

**Avantages :**
- Gratuit (modèle local)
- Rapide, fonctionne hors ligne

**Inconvénients :**
- ❌ **NE SUPPORTE PAS function calling correctement**
- ❌ **Hallucine du contenu** si on lui demande de résumer des documents
- ❌ Ne cite pas les sources

### MLX Qwen 2.5 3B - ⭐ NOUVEAU

**Utiliser pour :**
- Conversations générales sur Apple Silicon (M1/M2/M3)
- Développement et tests rapides
- Alternative plus rapide qu'Ollama sur Mac

**Avantages :**
- Gratuit, très rapide (~50-60 tok/s, 2x plus rapide qu'Ollama)
- Excellent en français
- Support complet de function calling
- RAM réduite (~2 GB)
- Auto-démarrage par le backend

**Inconvénients :**
- ❌ Apple Silicon uniquement (pas Intel)
- ⚠️ Qualité légèrement inférieure à Claude pour RAG

**💡 En cas de doute :** Choisissez Claude Sonnet 4.5 pour garantir l'accès aux documents.

---

## Prochaines étapes suggérées

### Immédiat

1. **Tester le RAG complet** ✅ PRIORITÉ
   - Vérifier que l'agent utilise `semantic_search`
   - Mesurer la qualité des réponses

2. **Ajuster paramètres RAG**
   - `top_k` : Actuellement 5, considérer 7-10
   - `min_similarity` : Actuellement 0.5 (50%)
   - `chunk_size` : Actuellement 400 mots
   - `chunk_overlap` : Actuellement 50 mots

### Court terme

1. **Améliorer l'agent chat**
   - ✅ FAIT : Recherche sémantique intégrée
   - ✅ FAIT : Mémoire de conversation
   - ❌ REPORTER : Extraction d'entités juridiques

2. **UI/UX**
   - ❌ REPORTER : Progression de transcription en temps réel
   - ✅ FAIT : Prévisualisation markdown
   - ✅ FAIT : Historique des conversations (API prête)

### Moyen terme

1. **RAG** ✅ FAIT
   - Indexation avec embeddings BGE-M3
   - Recherche sémantique fonctionnelle

2. **Multi-agents avec DuckDuckGo** 💡 À EXPLORER
   - Workflow multi-agents pour documentation automatique
   - Utiliser `agno.tools.duckduckgo`

3. **Intégrations externes** 💡 BONNE IDÉE
   - MCP Server pour CanLII (jurisprudence canadienne)
   - MCP Server pour Légis Québec / LegisInfo

### Refactoring identifié (2025-12-05)

**Phase 1 - Quick wins :**
- ✅ FAIT : Supprimer scripts racine morts (`debug_surreal.py`, `fix_malformed_doc.py`)
- ✅ FAIT : Extraire auth helpers dans `backend/auth/helpers.py`
- ✅ FAIT : Créer utilitaire ID normalization dans `backend/utils/id_utils.py`

**Phase 2 - Refactoring majeur :**
- ❌ À FAIRE : Diviser `documents.py` (2073 lignes) en 3-4 fichiers thématiques
  - `documents.py` : CRUD de base + TTS
  - `transcription.py` : Transcription audio + YouTube
  - `extraction.py` : Extraction PDF/texte

**Phase 3 - Documentation :**
- ✅ FAIT : Simplifier CLAUDE.md (archivé sessions dans `docs/archive/SESSIONS_2025-12.md`)

---

## Démarrage rapide

```bash
# Terminal 1: SurrealDB
surreal start --user root --pass root --bind 0.0.0.0:8002 file:data/surreal.db

# Terminal 2: Backend (démarre auto le serveur MLX si configuré)
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
- MLX Server : 8080 (OpenAI-compatible API)

**Installation :**
- `uv sync` installe toutes les dépendances par défaut :
  - Whisper (mlx-whisper pour transcription audio)
  - Embeddings (sentence-transformers avec GPU: MPS/CUDA/CPU)
  - TTS (edge-tts pour synthèse vocale)
  - Docling (extraction avancée PDF avec OCR)
  - MLX-LM (modèles HuggingFace via MLX)

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
# 15 voix disponibles au total
```

**Configuration MLX :**
```python
# backend/config/models.py
# Top 3 modèles recommandés pour M1 Pro 16 GB
"mlx-community/Qwen2.5-3B-Instruct-4bit"      # ~2 GB RAM, ~50 tok/s
"mlx-community/Llama-3.2-3B-Instruct-4bit"    # ~1.5 GB RAM, ~60 tok/s
"mlx-community/Mistral-7B-Instruct-v0.3-4bit" # ~4 GB RAM, ~35 tok/s
```

**Logs à surveiller :**
```
# Embeddings
MPS (Metal Performance Shaders) detecte - utilisation du GPU Apple Silicon
Modele BAAI/bge-m3 charge sur mps

# TTS
Service TTS initialisé avec edge-tts
Audio généré avec succès: /path/to/file.mp3

# MLX (si configuré)
MLX server started on http://localhost:8080
```

**Variables d'environnement :**
- Voir `.env.example` ou `ARCHITECTURE.md` pour la configuration complète

---

## Conventions

- Backend en Python avec FastAPI et Agno
- Frontend en TypeScript avec Next.js 14 (App Router) et shadcn/ui
- Base de données SurrealDB
- Documentation en français
- Commits avec message en anglais + footer Claude Code

---

## Ressources

- **Architecture complète** : `ARCHITECTURE.md`
- **Guide MLX** : `backend/MLX_GUIDE.md` et `backend/MLX_AUTO_START.md`
- **Historique sessions** : `docs/archive/SESSIONS_2025-12.md`
