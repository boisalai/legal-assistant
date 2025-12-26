# Legal Assistant

Assistant d'études juridiques pour étudiants en droit avec IA conversationnelle et recherche sémantique.

## 🎯 Fonctionnalités principales

### 📚 Gestion de cours
- Organisation par cours (civil, pénal, administratif, familial, commercial, travail, constitutionnel)
- CRUD complet via interface web
- Suppression en cascade (documents, conversations, embeddings)

### 📄 Gestion de documents
- **Upload de fichiers** : PDF, Word, images, audio
- **Liaison de répertoires locaux** : Indexation automatique de dossiers entiers
- **Import Docusaurus** : Import de documentation Markdown
- **Import YouTube** : Téléchargement audio de vidéos YouTube en MP3
- **Tracking intelligent** : Hash SHA-256 et détection de modifications
- Actions contextuelles selon le type de fichier

### 🎤 Transcription audio
- Whisper MLX (optimisé Apple Silicon)
- Modèle large-v3-turbo recommandé
- Workflow hybride : Whisper → Agent LLM (formatage) → Markdown

### 💬 Agent conversationnel
- Chat avec streaming en temps réel (SSE)
- **Recherche sémantique intégrée** : Accès automatique aux documents du cours
- Multi-providers : Claude, Ollama, MLX
- Mémoire de conversation persistante
- Citation automatique des sources

### 🔍 RAG et recherche sémantique
- Embeddings BGE-M3 (local) ou OpenAI
- Accélération GPU : MPS (Apple Silicon) / CUDA / CPU
- Chunking intelligent (400 mots, 50 mots overlap)
- Support multi-modèles d'embedding

### 🔊 Synthèse vocale (TTS)
- Service edge-tts (Microsoft Edge TTS)
- 15 voix : 13 françaises + 2 anglaises
- Génération MP3 depuis documents Markdown

### ⚡ MLX - Optimisation Apple Silicon
- Modèles locaux 2x plus rapides qu'Ollama
- Qwen 2.5 3B (4-bit) recommandé pour français
- Auto-démarrage par le backend
- RAM réduite (~2 GB)

### ⚖️ Recherche juridique CAIJ
- Intégration avec le Centre d'accès à l'information juridique du Québec
- Outil Agno pour agents conversationnels
- Support de 8 rubriques (Législation, Jurisprudence, Doctrine, Dictionnaires, etc.)
- Identification automatique des catégories de documents
- Authentification et rate limiting

### 🎓 Tuteur IA pédagogique
- **Détection automatique du document ouvert** via activity tracking
- **Génération de résumés structurés** avec objectifs d'apprentissage
- **Création de cartes mentales** thématiques avec emojis
- **Quiz interactifs** avec explications détaillées
- **Explications de concepts** juridiques avec méthode socratique
- Mode adaptatif : document spécifique vs cours complet
- 4 outils Agno dédiés à l'apprentissage

## 🏗️ Structure du projet

```
legal-assistant/
├── backend/
│   ├── config/              # Configuration (settings, models)
│   ├── models/              # Modèles Pydantic (Course, Document, CAIJ)
│   ├── routes/              # Endpoints API REST
│   ├── services/            # Services métier
│   │   ├── document_indexing_service.py
│   │   ├── transcription_service.py
│   │   ├── tts_service.py
│   │   ├── caij_search_service.py
│   │   └── tutor_service.py
│   ├── tools/               # Outils Agno
│   │   ├── tutor_tools.py
│   │   ├── caij_search_tool.py
│   │   └── semantic_search_tool.py
│   ├── workflows/           # Workflows Agno
│   └── main.py              # Point d'entrée FastAPI
├── frontend/
│   ├── src/
│   │   ├── app/             # Next.js App Router
│   │   ├── components/      # Composants React + shadcn/ui
│   │   └── lib/             # Utilities
│   └── package.json
├── docs/                    # Documentation
├── docker-compose.yml       # SurrealDB
└── CLAUDE.md               # Documentation développement
```

## 🚀 Installation rapide

### Prérequis

- **Python 3.12+**
- **uv** (gestionnaire de packages Python)
- **Node.js 18+** et **npm**
- **Docker** (pour SurrealDB)
- *Optionnel* : **Ollama** pour modèles locaux

### Étapes

```bash
# 1. Cloner le projet
git clone <repo-url>
cd legal-assistant

# 2. Démarrer SurrealDB
docker-compose up -d

# 3. Backend - Installer les dépendances
cd backend
uv sync

# 4. (Optionnel) Créer le fichier .env
cp .env.example .env
# Éditer pour ajouter ANTHROPIC_API_KEY si nécessaire

# 5. Démarrer le backend
uv run python main.py
# Backend disponible sur http://localhost:8000

# 6. Frontend - Installer les dépendances
cd ../frontend
npm install

# 7. Démarrer le frontend
npm run dev -- -p 3001
# Frontend disponible sur http://localhost:3001
```

### Démarrage avec 3 terminaux

```bash
# Terminal 1 - SurrealDB
docker-compose up -d
# ou
surreal start --user root --pass root --bind 0.0.0.0:8002 file:data/surreal.db

# Terminal 2 - Backend
cd backend && uv run python main.py

# Terminal 3 - Frontend
cd frontend && npm run dev -- -p 3001
```

## ⚙️ Configuration

### Modèles LLM

Le projet supporte plusieurs providers LLM :

#### Claude Sonnet 4.5 (Recommandé pour RAG)
```bash
# Dans .env
ANTHROPIC_API_KEY=sk-ant-...
```
- Support natif de function calling
- Meilleur pour recherche sémantique et citation de sources
- Nécessite API key Anthropic

#### MLX (Apple Silicon uniquement)
```bash
# Configuration dans frontend/Settings
Model: "MLX Qwen 2.5 3B"
```
- Gratuit, très rapide (~50-60 tok/s)
- Auto-démarrage par le backend
- Recommandé pour conversations générales

#### Ollama (Cross-platform)
```bash
# Installer Ollama: https://ollama.ai
ollama pull qwen2.5:7b
```
- Gratuit, fonctionne hors ligne
- Bon pour conversations simples
- Moins performant pour RAG

### Modèles d'embedding

Le projet supporte plusieurs modèles d'embedding :

| Provider | Modèle                    | Dimensions | Coût         |
|----------|---------------------------|------------|--------------|
| Local    | BGE-M3 (Recommandé)       | 1024       | Gratuit      |
| OpenAI   | text-embedding-3-small    | 1536       | ~$0.00002/1K |
| OpenAI   | text-embedding-3-large    | 3072       | ~$0.00013/1K |

Configuration dans `Settings > Paramètres avancés > Modèle d'Embedding`

**Important** : Changer de modèle d'embedding nécessite de réindexer tous les documents.

## 📖 Utilisation

### 1. Créer un cours

```
Interface web > "Nouveau cours"
- Titre du cours
- Code du cours (ex: DRT-1000)
- Professeur
- Crédits
- Type de droit
```

### 2. Ajouter des documents

**Upload de fichiers** :
- Glisser-déposer ou sélectionner des fichiers
- Formats supportés : PDF, DOCX, images, audio

**Lier un répertoire local** :
- Section "Répertoires liés"
- Sélectionner un dossier
- Indexation automatique de tous les fichiers

**Import Docusaurus** :
- Bouton "Importer depuis Docusaurus"
- Sélectionner les dossiers à importer
- Indexation automatique pour RAG

**Import YouTube** :
- Bouton "YouTube" dans l'onglet Documents
- Coller l'URL d'une vidéo YouTube
- Téléchargement automatique de l'audio en MP3
- Métadonnées conservées (titre, durée, auteur)

### 3. Poser des questions

```
Chat > Sélectionner un cours > Poser une question
```

L'agent va :
1. Rechercher les passages pertinents dans les documents
2. Formuler une réponse basée sur les sources
3. Citer automatiquement les sources utilisées

### 4. Transcrire un audio

```
Upload fichier audio > Action "Transcrire"
```

Workflow :
- Extraction audio avec Whisper MLX
- Formatage par agent LLM
- Sauvegarde en Markdown avec lien automatique

### 5. Générer une synthèse vocale

```
Document Markdown > Action "Générer audio"
```

Options :
- 13 voix françaises + 2 anglaises
- Configuration de la voix par défaut dans Settings
- Format MP3

### 6. Utiliser le Tuteur IA pédagogique

Le tuteur IA détecte automatiquement le document que vous consultez et adapte son comportement :

**Mode document spécifique** (document ouvert dans le visualiseur) :
```
"Résume ce document"              → Résumé structuré avec objectifs d'apprentissage
"Fais une carte mentale"          → Mind map thématique avec emojis
"Génère un quiz"                  → Quiz interactif de 5 questions
"Explique-moi [concept]"          → Explication détaillée avec sources
"Qu'est-ce que [concept] ?"       → Questions socratiques guidées
```

**Mode cours complet** (aucun document ouvert) :
```
"Résume le cours"                 → Vue d'ensemble du cours
"Fais une carte mentale du cours" → Mind map global
"Quiz sur le cours"               → Quiz couvrant tous les documents
```

**Méthode socratique** :
- Le tuteur pose des questions pour guider votre réflexion
- Pour obtenir une explication directe : "Explique-moi directement"

**Avantages** :
- Toutes les réponses ancrées dans vos documents (anti-hallucination)
- Citations des sources automatiques
- Format optimisé pour l'apprentissage
- Zéro configuration requise

## 🔧 API REST

Documentation complète disponible sur :
- **Swagger UI** : http://localhost:8000/docs
- **ReDoc** : http://localhost:8000/redoc

Principaux endpoints :

```
GET    /api/courses              # Liste des cours
POST   /api/courses              # Créer un cours
GET    /api/courses/{id}         # Détails d'un cours
DELETE /api/courses/{id}         # Supprimer un cours

GET    /api/documents            # Liste des documents
POST   /api/documents/upload     # Upload de fichiers
POST   /api/linked-directories   # Lier un répertoire local
POST   /api/docusaurus/import    # Importer depuis Docusaurus
POST   /api/courses/{id}/documents/youtube/info    # Info vidéo YouTube
POST   /api/courses/{id}/documents/youtube         # Télécharger audio YouTube

POST   /api/transcribe           # Transcrire un audio
POST   /api/tts                  # Générer une synthèse vocale

POST   /api/chat                 # Chat avec streaming SSE
GET    /api/conversations        # Historique des conversations

# Recherche juridique CAIJ (via outil Agno)
# Utilisation dans les agents conversationnels uniquement
```

### Outil CAIJ pour agents Agno

L'intégration CAIJ est disponible comme outil pour les agents conversationnels :

```python
from agno import Agent
from tools.caij_search_tool import search_caij_jurisprudence

# Créer un agent avec accès à CAIJ
legal_agent = Agent(
    name="Assistant juridique",
    tools=[search_caij_jurisprudence],
    instructions="Tu es un assistant juridique québécois..."
)
```

**Configuration** : Ajouter `CAIJ_EMAIL` et `CAIJ_PASSWORD` dans `.env`

```bash
# Dans .env
CAIJ_EMAIL=your.email@example.com
CAIJ_PASSWORD=your_password
```

## 🧪 Développement

### Linter et formatage

```bash
cd backend
uv run ruff check .
uv run ruff format .
```

### Tests

```bash
cd backend
uv run pytest
```

### Hot reload

```bash
# Backend
cd backend
uv run uvicorn main:app --reload

# Frontend
cd frontend
npm run dev
```

## 📦 Technologies

- **Backend** : Python 3.12 + FastAPI + Agno
- **Frontend** : Next.js 14 (App Router) + TypeScript + shadcn/ui
- **Base de données** : SurrealDB
- **IA** : Claude / Ollama / MLX / HuggingFace
- **Embeddings** : sentence-transformers (BGE-M3) / OpenAI
- **Transcription** : Whisper MLX (mlx-whisper)
- **TTS** : edge-tts (Microsoft Edge TTS)
- **PDF** : Docling (extraction avancée avec OCR)
- **Recherche juridique** : Playwright (web scraping CAIJ)
- **Tuteur IA** : Agno framework avec 4 outils pédagogiques

## 🌐 Ports

- **SurrealDB** : 8002
- **Backend** : 8000
- **Frontend** : 3001
- **MLX Server** : 8080 (auto-démarré si modèle MLX sélectionné)

## 📚 Documentation complète

- **CLAUDE.md** : Documentation de développement et historique des sessions
- **ARCHITECTURE.md** : Architecture technique détaillée
- **backend/MLX_GUIDE.md** : Guide MLX pour Apple Silicon
- **backend/LOCAL_MODELS_GUIDE.md** : Guide des modèles locaux
- **backend/TUTEUR_IA_IMPLEMENTATION.md** : Implémentation du tuteur IA pédagogique

## 🤝 Contribution

Ce projet est développé pour un usage personnel éducatif. Les contributions sont les bienvenues pour améliorer les fonctionnalités existantes.

## 📄 License

MIT
