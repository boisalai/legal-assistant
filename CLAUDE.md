# Legal Assistant - Documentation de développement

> **Note:** Historique détaillé des sessions archivé dans `docs/archive/SESSIONS_2025-12.md`

---

## Fonctionnalités

### 1. Gestion des dossiers
- CRUD complet via API REST
- Types : civil, pénal, administratif, familial, commercial, travail
- Suppression en cascade : documents, conversations, chunks d'embeddings

### 2. Gestion des documents
- Upload de fichiers (PDF, Word, images, audio)
- Liaison de répertoires locaux avec indexation automatique
- Import depuis YouTube (téléchargement audio MP3)
- Fichiers dérivés automatiquement liés (transcription, extraction PDF, TTS)

### 3. Répertoires liés
- Synchronisation automatique (toutes les 5 min)
- Tracking SHA-256 et mtime
- Interface arborescente
- Config : `AUTO_SYNC_INTERVAL`, `AUTO_SYNC_ENABLED`

### 4. Transcription audio
- Whisper MLX (large-v3-turbo)
- Workflow : Whisper → Agent LLM (formatage) → Markdown

### 5. Agent conversationnel
- Chat avec streaming SSE
- Support multi-providers : Claude, Ollama, MLX
- Recherche sémantique intégrée (`semantic_search`)
- Mémoire de conversation dans SurrealDB

### 6. Indexation vectorielle (RAG)
- Embeddings BGE-M3 via sentence-transformers
- Accélération GPU : MPS / CUDA / CPU
- Chunking : 400 mots, 50 mots overlap

### 7. Synthèse vocale (TTS)
- edge-tts (Microsoft Edge TTS)
- 15 voix : 13 françaises + 2 anglaises

### 8. Recherche CAIJ
- Intégration Centre d'accès à l'information juridique du Québec
- Outil Agno `search_caij_jurisprudence`
- 8 rubriques officielles
- Config : `CAIJ_EMAIL`, `CAIJ_PASSWORD`

### 9. Tuteur IA pédagogique
- Détection automatique du document ouvert
- 4 outils Agno : `generate_summary`, `generate_mindmap`, `generate_quiz`, `explain_concept`

### 10. Fiches de révision (Flashcards)
- Génération LLM depuis documents markdown
- Interface flip card avec animation CSS 3D
- Raccourcis : `Espace` (flip), flèches (navigation)
- TTS audio (fr-CA-SylvieNeural)

### 11. Modules d'étude
- CRUD pour organiser documents par module/chapitre
- Interface DataTable avec tri

### 12. OCR automatique des PDF
- Extraction OCR automatique à l'upload
- Docling VLM (optimisé Apple Silicon)
- Document markdown dérivé + indexation RAG

### 13. Multi-agents juridiques

Équipe de 4 agents spécialisés pour les questions juridiques complexes.

**Architecture :**
```
Question → Chercheur (RAG + CAIJ) → Analyste (C.c.Q.) → Validateur (citations) → Rédacteur (pédagogie) → Réponse
```

**Agents :**
| Agent | Rôle | Outils |
|-------|------|--------|
| **Chercheur** | Recherche exhaustive | `semantic_search`, `search_caij_jurisprudence` |
| **Analyste Juridique** | Interprétation du droit | `analyze_legal_text`, `identify_applicable_articles` |
| **Validateur** | Anti-hallucination | `verify_legal_citations`, `extract_citations` |
| **Rédacteur** | Contenu pédagogique | `generate_summary`, `generate_mindmap`, `generate_quiz`, `explain_concept` |

**Fichiers :**
- `backend/agents/legal_research_team.py` - Définition de l'équipe (Team + 4 agents)
- `backend/tools/validation_tool.py` - Vérification des citations juridiques
- `backend/tools/legal_analysis_tool.py` - Analyse juridique avec 10 domaines C.c.Q.
- `backend/tools/tutor_tools.py` - Outils pédagogiques (résumés, quiz, cartes mentales)

**Activation :** Toggle dans le panneau Assistant ou `use_multi_agent: true` dans l'API.

**Avantages :**
- Anti-hallucination : toutes les citations vérifiées
- Recherche exhaustive : RAG + CAIJ combinés
- Analyse juridique : articles C.c.Q. identifiés
- Score de fiabilité : chaque réponse inclut un niveau de confiance
- Contenu pédagogique : résumés, quiz et cartes mentales générés automatiquement

---

## Architecture technique

Voir **`ARCHITECTURE.md`** pour la documentation complète.

**Modules clés :**

| Catégorie | Fichiers |
|-----------|----------|
| **Documents** | `services/document_service.py`, `services/document_ocr_task.py`, `routes/documents.py` |
| **Multi-agents** | `agents/legal_research_team.py`, `tools/validation_tool.py`, `tools/legal_analysis_tool.py`, `tools/tutor_tools.py` |
| **RAG** | `services/document_indexing_service.py`, `tools/semantic_search_tool.py` |
| **CAIJ** | `services/caij_search_service.py`, `tools/caij_search_tool.py` |
| **Tuteur** | `services/tutor_service.py`, `tools/tutor_tools.py` |
| **Transcription** | `services/transcription_service.py`, `routes/transcription.py` |
| **Flashcards** | `services/flashcard_service.py`, `routes/flashcards.py` |

---

## Activity Tracking (Contexte IA)

Le système permet à l'assistant IA de savoir ce que l'utilisateur consulte.

**Types d'activité :**
| Type | Description |
|------|-------------|
| `view_case` | Page principale du cours |
| `view_document` | Document ouvert |
| `view_module` | Module ouvert |
| `view_flashcard_study` | Étude des flashcards |
| `view_directory` | Répertoire lié |

**Ajouter une nouvelle vue :**

1. `frontend/src/types/index.ts` - Ajouter le type
2. `backend/services/user_activity_service.py` - Ajouter dans enum + labels
3. `backend/routes/chat.py` - Ajouter dans `_VIEW_CHANGE_ACTIONS`
4. Composant - Appeler `trackActivity()` au montage

---

## Guide de sélection LLM

| Besoin | Modèle recommandé |
|--------|-------------------|
| Questions avec documents (RAG) | **Claude Sonnet 4.5** |
| Conversation simple (Mac) | **MLX Qwen 2.5 3B** |
| Cross-platform | **Ollama Qwen 2.5 7B** |

**Claude Sonnet 4.5** : Function calling natif, anti-hallucination, qualité juridique
**MLX Qwen 2.5 3B** : Gratuit, ~50-60 tok/s, 2 GB RAM, auto-démarrage
**Ollama** : Cross-platform mais ne supporte pas bien function calling

---

## Démarrage rapide

```bash
# Méthode recommandée
./dev.sh

# Arrêter
./dev-stop.sh
```

**Méthode manuelle (3 terminaux) :**
```bash
# Terminal 1: SurrealDB
docker-compose up -d

# Terminal 2: Backend
cd backend && uv run python main.py

# Terminal 3: Frontend
cd frontend && npm run dev -- -p 3001
```

**Ports :** SurrealDB (8002), Backend (8000), Frontend (3001), MLX (8080)

---

## Configuration

**Embeddings :**
```python
embedding_provider = "local"
embedding_model = "BAAI/bge-m3"
chunk_size = 400
chunk_overlap = 50
```

**MLX (Apple Silicon) :**
```python
"mlx-community/Qwen2.5-3B-Instruct-4bit"      # ~2 GB, ~50 tok/s
"mlx-community/Llama-3.2-3B-Instruct-4bit"    # ~1.5 GB, ~60 tok/s
"mlx-community/Mistral-7B-Instruct-v0.3-4bit" # ~4 GB, ~35 tok/s
```

---

## Conventions

- **Backend** : Python + FastAPI + Agno
- **Frontend** : TypeScript + Next.js 14 + shadcn/ui
- **Base de données** : SurrealDB
- **Documentation** : Français
- **Commits** : Anglais + `Co-Authored-By: Claude`

### Nommage des IDs

**Important :** Utiliser `course_id` partout (jamais `case_id`).

| Contexte | Format |
|----------|--------|
| Paramètre Python | `course_id: str` |
| Prefix SurrealDB | `"course:"` |
| Champ DB | `course_id` |
| URL API | `/{course_id}/...` |

### shadcn/ui

**Règle :** Utiliser uniquement les versions officielles sans modification.

**Composants personnalisés autorisés :**
- `audio-recorder.tsx`, `file-upload.tsx`, `language-selector.tsx`, `markdown.tsx`

### Style UI

| Élément | Classe |
|---------|--------|
| Titre de page | `text-xl font-bold` |
| Titre de section | `text-base font-semibold` |
| Texte courant | `text-sm` |
| Icônes titres | `h-4 w-4` |
| Icônes boutons | `h-3 w-3` |

---

## Prochaines étapes

### Session actuelle - Migration course_id (2026-01-10)

**Complété :**
- ✅ Migration complète `case_id` → `course_id` dans tout le codebase (351 occurrences)
- ✅ Migration DB : `migrations/005_rename_case_id_to_course_id.surql`
- ✅ Tables migrées : `document`, `conversation`, `user_activity`
- ✅ Fichiers corrigés : 20 fichiers (tools, services, routes, agents)
- ✅ Bug corrigé : l'assistant ne voyait pas les documents (requêtes SQL utilisaient `case_id` au lieu de `course_id`)

**Fichiers modifiés :**
- Tools : `document_search_tool.py`, `semantic_search_tool.py`, `tutor_tools.py`, `validation_tool.py`, `transcription_tool.py`, `entity_extraction_tool.py`
- Services : `document_indexing_service.py`, `conversation_service.py`, `tutor_service.py`, `user_activity_service.py`
- Routes : `activity.py`, `chat.py`, `extraction.py`, `transcription.py`, `linked_directory.py`, `settings.py`
- Agents : `legal_research_team.py`

### Session précédente - Multi-agent (2026-01-09)

- ✅ Agent Rédacteur ajouté (4ème agent) avec 4 outils tutor_tools
- ✅ Mots-clés pédagogiques ajoutés à `is_legal_research_query()`

### Priorité haute
- Tests d'intégration API endpoints critiques
- Ajuster paramètres RAG (top_k, min_similarity)

### Priorité moyenne
- Logos providers dans sélecteur de modèles
- Épingler cours favoris
- Progression temps réel (transcription, indexation)

### Backlog
- Extraction d'entités juridiques
- MCP Server CanLII / Légis Québec

---

## Ressources

- `ARCHITECTURE.md` - Architecture complète
- `docs/MULTI_AGENT_DESIGN.md` - Design multi-agent détaillé
- `backend/MLX_GUIDE.md` - Guide MLX
- `docs/archive/SESSIONS_2025-12.md` - Historique des sessions
