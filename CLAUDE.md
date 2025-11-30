# Legal Assistant - Notes de développement

## État actuel du projet (2025-11-30)

### Fonctionnalités implémentées

1. **Gestion des dossiers (judgments)**
   - CRUD complet via API REST
   - Liste, création, modification, suppression
   - Types de dossiers : civil, pénal, administratif, familial, commercial, travail, constitutionnel

2. **Gestion des documents**
   - Upload de fichiers (PDF, Word, images, audio)
   - Téléchargement et prévisualisation
   - Suppression avec nettoyage des fichiers
   - Indicateur "Texte extrait" pour les fichiers transcrits

3. **Transcription audio**
   - Whisper MLX (modèle large-v3-turbo recommandé)
   - Workflow hybride : Whisper → Agent LLM (formatage) → Sauvegarde
   - Création automatique de fichiers markdown
   - Synchronisation : supprimer une transcription efface `texte_extrait` de l'audio source

4. **Agent conversationnel**
   - Chat avec streaming SSE
   - Outil de transcription intégré (`transcribe_audio`)
   - Support multi-providers : Ollama, Anthropic, OpenAI

5. **Configuration LLM**
   - Interface UI pour changer de modèle
   - Persistance des paramètres dans SurrealDB
   - Chargement automatique de ANTHROPIC_API_KEY depuis .env

### Architecture technique

Voir `ARCHITECTURE.md` pour la documentation complète :
- Structure des dossiers
- Services backend (SurrealDB, Whisper, Model Factory)
- Patterns Agno (Workflow déclaratif, hybride, avec classe)
- Routes API
- Composants frontend

### Fichiers clés modifiés récemment

| Fichier | Description |
|---------|-------------|
| `backend/workflows/transcribe_audio.py` | Workflow de transcription avec pattern Agno |
| `backend/routes/documents.py` | Gestion documents + synchronisation transcription/audio |
| `backend/services/llm_settings.py` | Persistance config LLM |
| `frontend/src/components/cases/tabs/documents-tab.tsx` | UI documents avec indicateur transcription |
| `ARCHITECTURE.md` | Documentation technique complète |

---

## Prochaines étapes suggérées

### Court terme (améliorations immédiates)

1. **Analyse de dossiers**
   - Implémenter `routes/analysis.py` pour analyser les documents d'un dossier
   - Créer un workflow multi-agents : extraction → analyse → synthèse
   - Générer une checklist automatique des points à vérifier

2. **Améliorer l'agent chat**
   - Ajouter un outil de recherche dans les documents du dossier
   - Implémenter la mémoire de conversation (stockage dans SurrealDB)
   - Ajouter des outils pour extraire des entités juridiques

3. **UI/UX**
   - Afficher la progression de transcription en temps réel
   - Prévisualisation des fichiers markdown générés
   - Historique des conversations par dossier

### Moyen terme (nouvelles fonctionnalités)

1. **RAG (Retrieval-Augmented Generation)**
   - Indexer les documents avec embeddings
   - Recherche sémantique dans les documents
   - Contextualiser les réponses de l'agent

2. **Multi-agents**
   - Agent spécialisé pour l'analyse juridique
   - Agent pour la recherche de jurisprudence
   - Orchestration avec Agno Workflow

3. **Intégrations externes**
   - MCP Server pour CanLII (jurisprudence canadienne)
   - MCP Server pour les codes et lois
   - Export vers formats légaux (PDF structuré)

### Patterns Agno à explorer

Voir `ARCHITECTURE.md` section "Patterns d'agents à explorer" :
- Agent avec outils multiples
- Workflow multi-agents
- RAG
- Agent avec mémoire
- MCP (Model Context Protocol)

---

## Démarrage rapide

```bash
# Terminal 1: SurrealDB
surreal start --user root --pass root --bind 0.0.0.0:8002 file:data/surreal.db

# Terminal 2: Backend
cd backend
uv run python main.py

# Terminal 3: Frontend
cd frontend
npm run dev -- -p 3001
```

## Notes techniques

- **Port SurrealDB** : 8002 (modifié de 8001)
- **Port Backend** : 8000
- **Port Frontend** : 3001
- **Whisper** : Nécessite `uv sync --extra whisper` pour l'installation
- **Variables d'environnement** : Voir `.env.example` ou `ARCHITECTURE.md`

## Conventions

- Backend en Python avec FastAPI et Agno
- Frontend en TypeScript avec Next.js 14 (App Router) et shadcn/ui
- Base de données SurrealDB
- Documentation en français
- Commits avec message en anglais + footer Claude Code
