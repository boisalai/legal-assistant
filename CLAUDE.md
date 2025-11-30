# Legal Assistant - Notes de développement

## État actuel du projet (2025-11-30)

### Fonctionnalités implémentées

1. **Gestion des dossiers (judgments)**
   - CRUD complet via API REST
   - Liste, création, modification, suppression
   - Types de dossiers : civil, pénal, administratif, familial, commercial, travail, constitutionnel

2. **Gestion des documents**
   - Upload de fichiers (PDF, Word, images, audio)
   - Téléchargement et prévisualisation inline (PDF s'affiche dans le navigateur)
   - Suppression avec nettoyage des fichiers
   - Indicateur "Texte extrait" pour les fichiers transcrits
   - Liaison de fichiers locaux (File System Access API)

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
   - Persistance des paramètres dans localStorage
   - Chargement automatique de ANTHROPIC_API_KEY depuis .env

6. **Interface utilisateur (UI/UX)**
   - Panel de prévisualisation de documents avec affichage inline PDF
   - Panel Assistant IA avec split vertical lors de la prévisualisation
   - Panneaux redimensionnables (react-resizable-panels)
   - Messages chat avec padding réduit pour une meilleure densité

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
| `backend/routes/documents.py` | Endpoint download avec paramètre `inline` pour affichage navigateur |
| `frontend/src/app/cases/[id]/page.tsx` | Split panel vertical : document preview + assistant IA |
| `frontend/src/components/cases/document-preview-panel.tsx` | Prévisualisation avec `?inline=true` pour PDF |
| `frontend/src/components/cases/assistant-panel.tsx` | Chat avec padding réduit (`px-3 py-2`) |
| `frontend/src/hooks/use-file-system-access.ts` | Hook pour lier des fichiers locaux |

### Dernières modifications (session actuelle)

1. **Prévisualisation PDF inline** : Les PDF s'affichent maintenant dans le navigateur au lieu de se télécharger
   - Backend : ajout paramètre `inline: bool` dans `/download` endpoint
   - Frontend : ajout `?inline=true` à l'URL de téléchargement

2. **Split panel vertical** : Quand on prévisualise un document, le panneau droit se divise :
   - Haut : prévisualisation du document
   - Bas : Assistant IA (qui reste toujours visible)
   - Séparateur horizontal redimensionnable
   - Fermer la prévisualisation (X) restaure l'Assistant IA en pleine hauteur

3. **Padding des bulles de chat réduit** : `p-4` → `px-3 py-2` pour des messages plus compacts

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
