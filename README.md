# Legal Assistant

Assistant d'etudes juridiques pour etudiants en droit - Resume automatique de jugements.

## Fonctionnalites

- **Resume de jugements**: Analyse automatique de jugements pour generer des case briefs structures
- **Multi-providers LLM**: Support Ollama, Claude, MLX, HuggingFace
- **Persistance**: SurrealDB pour stocker jugements et resumes
- **API REST**: FastAPI avec documentation Swagger

## Structure du projet

```
legal-assistant/
├── backend/
│   ├── config/          # Configuration (settings, models LLM)
│   ├── models/          # Modeles Pydantic (Judgment, Summary)
│   ├── workflows/       # Workflows Agno (summarize_judgment)
│   ├── services/        # Services (model_factory)
│   ├── routes/          # Endpoints API
│   └── main.py          # Point d'entree FastAPI
├── frontend/            # Next.js 15 + React 19
│   ├── src/
│   │   ├── app/         # Pages (App Router)
│   │   ├── components/  # Composants React (UI, layout)
│   │   ├── lib/         # Utilitaires et API client
│   │   └── types/       # Types TypeScript
│   └── package.json
├── notary/              # Ancien systeme (reference seulement)
├── docs/                # Documentation
└── docker-compose.yml   # SurrealDB
```

## Installation rapide

### Prerequisites

- Python 3.12+
- uv (gestionnaire de packages)
- Docker (pour SurrealDB)
- Ollama (recommande pour dev local)

### Etapes

```bash
# 1. Cloner et entrer dans le projet
cd legal-assistant

# 2. Demarrer SurrealDB
docker-compose up -d

# 3. Installer les dependances Python
cd backend
uv sync

# 4. (Optionnel) Installer Ollama et telecharger un modele
# Voir https://ollama.ai
ollama pull qwen2.5:7b

# 5. Creer le fichier .env
cp .env.example .env
# Editer si necessaire

# 6. Lancer l'API
uv run python main.py
```

L'API sera disponible sur http://localhost:8000

- Documentation Swagger: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Configuration LLM

### Ollama (recommande pour developpement)

```bash
# Installer Ollama: https://ollama.ai
ollama pull qwen2.5:7b  # Meilleur score (80%)
ollama pull llama3.2    # Plus rapide
```

Dans `.env`:
```
MODEL_ID=ollama:qwen2.5:7b
```

### Claude (production)

Dans `.env`:
```
MODEL_ID=anthropic:claude-sonnet-4-5-20250929
ANTHROPIC_API_KEY=sk-ant-...
```

## Utilisation

### Test du workflow de resume

```bash
cd backend
uv run python workflows/summarize_judgment.py
```

### Via l'API (a venir)

```bash
# Upload un jugement
curl -X POST http://localhost:8000/api/judgments \
  -F "file=@jugement.pdf"

# Generer un resume
curl -X POST http://localhost:8000/api/judgments/{id}/summarize
```

## Developpement

### Backend

```bash
cd backend

# Lancer en mode dev (hot reload)
uv run uvicorn main:app --reload

# Linter
uv run ruff check .
uv run ruff format .

# Tests
uv run pytest
```

### Frontend

```bash
cd frontend

# Installer les dependances
npm install

# Lancer en mode dev
npm run dev
# Le frontend sera disponible sur http://localhost:3001

# Build production
npm run build
```

## Modeles de donnees

### Judgment (Jugement)

- Identification (titre, citation, tribunal, date)
- Parties (demandeur, defendeur)
- Classification (domaine de droit)
- Texte original

### CaseBrief (Resume)

- Faits pertinents
- Questions en litige
- Regles de droit applicables
- Ratio decidendi
- Obiter dicta
- Conclusion/Dispositif

## Workflow de resume

Le workflow utilise 4 agents specialises:

1. **Extracteur**: Extrait les informations de base (parties, tribunal, date)
2. **Analyseur**: Identifie les faits, questions en litige, arguments
3. **Synthetiseur**: Extrait le ratio decidendi et la conclusion
4. **Formateur**: Genere le case brief final structure

## Technologies

- **Backend**: Python 3.12 + FastAPI + Agno
- **Base de donnees**: SurrealDB
- **IA**: Ollama / Claude / MLX / HuggingFace
- **Frontend**: Next.js 15 + React 19 + Tailwind CSS + shadcn/ui

## License

MIT
