# Backend - Notary Assistant API

API FastAPI pour l'assistant IA de verification notariale.

## Structure du projet

```
backend/
├── config/              # Configuration centralisee
│   ├── settings.py      # Variables d'environnement
│   └── models.py        # Configuration des modeles LLM
├── workflows/           # Workflows Agno (agents IA)
│   └── analyse_dossier.py  # Workflow principal
├── models/              # Modeles de donnees (Pydantic)
├── routes/              # Endpoints API (controllers)
├── services/            # Logique metier
│   ├── case_service.py      # Service dossiers
│   ├── model_factory.py     # Factory pour modeles LLM
│   └── agno_db_service.py   # Service SurrealDB Agno
├── tests/               # Tests unitaires et d'integration
├── data/                # Donnees locales
│   ├── surreal/         # Schema SurrealDB
│   └── uploads/         # Fichiers uploades
├── main.py              # Point d'entree de l'API
├── pyproject.toml       # Configuration Python et dependances
└── .env                 # Variables d'environnement (a creer)
```

## Installation

### Prerequis
- Python 3.12+
- uv (gestionnaire de packages)
- Docker (pour SurrealDB)

### Etapes

1. **Creer le fichier .env**
   ```bash
   cp .env.example .env
   # Editer .env avec vos valeurs
   ```

2. **Installer les dependances avec uv**
   ```bash
   uv sync
   ```

3. **Lancer la base de donnees (Docker)**
   ```bash
   cd ..  # Retour a la racine
   docker-compose up -d surrealdb
   ```

4. **Initialiser le schema SurrealDB**
   ```bash
   uv run python init_schema.py
   ```

5. **Lancer l'API**
   ```bash
   uv run python main.py
   # ou
   uv run uvicorn main:app --reload
   ```

6. **Acceder a la documentation**
   - API: http://localhost:8000
   - Swagger UI: http://localhost:8000/docs
   - ReDoc: http://localhost:8000/redoc

## Developpement

### Lancer en mode developpement
```bash
uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Lancer les tests
```bash
uv run pytest
```

### Linter et formatage
```bash
uv run ruff check .
uv run ruff format .
```

## Configuration LLM

Le projet utilise un `ModelFactory` pour creer des modeles LLM de maniere uniforme.

### Option 1: Ollama (recommande pour developpement local)
```bash
# Installer Ollama: https://ollama.ai
ollama pull qwen2.5:7b  # Meilleur score (80%)
ollama pull llama3.2    # Plus rapide (38s)
```
Dans `.env`:
```
MODEL_ID=ollama:qwen2.5:7b
```

### Option 2: Anthropic Claude (production)
Dans `.env`:
```
MODEL_ID=anthropic:claude-sonnet-4-5-20250929
ANTHROPIC_API_KEY=sk-ant-xxx
```

### Option 3: MLX (Mac Apple Silicon)
```bash
uv sync --extra mlx
# Demarrer le serveur MLX OpenAI-compatible
mlx_lm.server --model mlx-community/Phi-3-mini-4k-instruct-4bit
```
Dans `.env`:
```
MODEL_ID=mlx:mlx-community/Phi-3-mini-4k-instruct-4bit
```

### Modeles recommandes

| Modele | Environnement | Score | Vitesse |
|--------|---------------|-------|---------|
| qwen2.5:7b | Dev local | 80% | 83s |
| llama3.2 | Dev rapide | 70% | 38s |
| claude-sonnet-4-5 | Production | 90%+ | Variable |

## Architecture

### FastAPI
Framework web moderne et rapide pour Python, avec:
- Auto-documentation (Swagger/OpenAPI)
- Validation automatique avec Pydantic
- Support async/await natif
- Performance comparable a Node.js

### Agno
Framework pour creer des workflows d'agents IA:
- Orchestration multi-agents (4 agents: Extracteur, Classificateur, Verificateur, Generateur)
- Gestion d'etat avec SurrealDB
- Persistance automatique des workflows
- Deterministe et testable

### SurrealDB
Base de donnees multi-modele:
- Relationnel + Document + Graphe
- Namespace `notary`: Tables metier (dossier, document, user, checklist)
- Namespace `agno`: Tables Agno (workflow_runs, agent_sessions)

### Pydantic
Validation de donnees type-safe:
- Settings: chargement des variables d'environnement
- Models: validation des requetes/reponses API

## Exemples d'utilisation

### Health check
```bash
curl http://localhost:8000/health
```

### Creer un dossier
```bash
curl -X POST http://localhost:8000/api/dossiers \
  -H "Content-Type: application/json" \
  -d '{"nom_dossier": "Vente Dupont", "type_transaction": "vente"}'
```

### Uploader un document
```bash
curl -X POST http://localhost:8000/api/dossiers/{id}/documents \
  -F "file=@document.pdf"
```

### Analyser un dossier
```bash
curl -X POST http://localhost:8000/api/dossiers/{id}/analyze
```

## Documentation supplementaire

- [Guide Agno](../docs/agno-concepts.md)
- [Architecture SurrealDB](../docs/surrealdb-architecture.md)
- [Index documentation](../docs/INDEX.md)
