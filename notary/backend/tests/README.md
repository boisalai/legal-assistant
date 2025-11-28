# Tests Notary Assistant

Suite de tests complète pour le backend Notary Assistant.

## Structure

```
tests/
├── __init__.py
├── conftest.py              # Fixtures communes à tous les tests
├── unit/                    # Tests unitaires (rapides, sans dépendances externes)
│   ├── test_surreal_service.py
│   ├── test_dossier_service.py
│   └── test_llm_service.py
├── integration/             # Tests d'intégration (API, DB)
│   ├── test_api_dossiers.py
│   └── test_api_health.py
└── e2e/                     # Tests end-to-end (lents, nécessitent services externes)
    └── test_workflow_agno.py
```

## Prérequis

### Installation des dépendances

```bash
cd backend
uv sync --extra dev
```

### Services requis

**Pour tous les tests:**
- SurrealDB actif sur `ws://localhost:8001/rpc`

**Pour les tests E2E uniquement:**
- ANTHROPIC_API_KEY configurée dans `.env`
- Connexion Internet

### Démarrer SurrealDB

```bash
# Avec Docker Compose
docker-compose up -d surrealdb

# Ou manuellement
surreal start --log trace --user root --pass root memory --bind 0.0.0.0:8001
```

## Lancer les tests

### Tous les tests

```bash
uv run pytest
```

### Tests par catégorie

```bash
# Tests unitaires seulement (rapides)
uv run pytest -m unit

# Tests d'intégration
uv run pytest -m integration

# Tests E2E (lents, nécessitent ANTHROPIC_API_KEY)
uv run pytest -m e2e

# Skip les tests lents
uv run pytest -m "not slow"

# Skip les tests E2E
uv run pytest -m "not e2e"
```

### Tests spécifiques

```bash
# Un fichier de tests
uv run pytest tests/unit/test_dossier_service.py

# Une classe de tests
uv run pytest tests/unit/test_dossier_service.py::TestDossierService

# Un test spécifique
uv run pytest tests/unit/test_dossier_service.py::TestDossierService::test_create_dossier
```

### Avec coverage

```bash
# Coverage complet
uv run pytest --cov=. --cov-report=html

# Voir le rapport HTML
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
```

### Mode verbose

```bash
# Afficher tous les détails
uv run pytest -vv

# Afficher les print() statements
uv run pytest -s

# Les deux
uv run pytest -vvs
```

## Configuration

La configuration pytest se trouve dans `pyproject.toml`:

```toml
[tool.pytest.ini_options]
minversion = "8.0"
asyncio_mode = "auto"
testpaths = ["tests"]
addopts = [
    "-v",
    "--strict-markers",
    "--tb=short",
    "--cov=.",
    "--cov-report=term-missing",
    "--cov-report=html",
]
markers = [
    "unit: Unit tests",
    "integration: Integration tests",
    "e2e: End-to-end tests",
    "slow: Slow tests",
]
```

## Fixtures disponibles

### Base de données

- `db_service`: Service SurrealDB connecté à une base de test
- `dossier_service`: Service de gestion des dossiers avec DB de test

### API

- `api_client`: Client HTTP AsyncClient pour tester l'API FastAPI

### Données de test

- `faker_instance`: Instance Faker (français canadien) pour générer des données
- `sample_dossier_data`: Données d'exemple pour créer un dossier
- `sample_pdf_content`: Contenu PDF minimal valide

### Mocks

- `mock_llm_service`: Mock du service LLM (évite les appels API réels)
- `mock_workflow`: Mock du workflow Agno

## Bonnes pratiques

### Nommage

- Fichiers: `test_*.py`
- Classes: `Test*`
- Fonctions: `test_*`

### Markers

Utilisez les markers pour catégoriser vos tests:

```python
@pytest.mark.unit
def test_something():
    ...

@pytest.mark.integration
async def test_api():
    ...

@pytest.mark.e2e
@pytest.mark.slow
async def test_workflow():
    ...
```

### Tests asynchrones

Utilisez `@pytest.mark.asyncio` pour les tests async:

```python
@pytest.mark.asyncio
async def test_async_function():
    result = await some_async_function()
    assert result is not None
```

### Fixtures

Utilisez les fixtures pour partager la logique:

```python
@pytest.fixture
def my_fixture():
    # Setup
    data = create_test_data()

    yield data

    # Teardown
    cleanup_test_data(data)

def test_with_fixture(my_fixture):
    assert my_fixture is not None
```

### Mocking

Utilisez `pytest-mock` pour mocker les dépendances:

```python
def test_with_mock(mocker):
    mock_api = mocker.patch('module.api_call')
    mock_api.return_value = {"status": "ok"}

    result = function_that_calls_api()

    assert result["status"] == "ok"
    mock_api.assert_called_once()
```

## Debugging

### Debugger un test

```bash
# Avec pdb
uv run pytest --pdb

# Avec ipdb (si installé)
uv run pytest --pdb --pdbcls=IPython.terminal.debugger:Pdb
```

### Afficher les logs

```bash
# Logs de l'application
uv run pytest --log-cli-level=DEBUG

# Print statements
uv run pytest -s
```

### Tester un seul test en échec

```bash
# Arrêter au premier échec
uv run pytest -x

# Relancer seulement les tests en échec
uv run pytest --lf

# Relancer les tests en échec d'abord
uv run pytest --ff
```

## CI/CD

Pour intégrer dans un pipeline CI/CD, utilisez:

```bash
# Tests rapides (skip E2E et slow)
uv run pytest -m "not e2e and not slow"

# Avec JUnit XML pour les rapports CI
uv run pytest --junitxml=junit.xml

# Avec coverage en XML pour SonarQube, Codecov, etc.
uv run pytest --cov=. --cov-report=xml
```

## Troubleshooting

### SurrealDB non connecté

```
Error: Connection refused
```

**Solution:** Démarrez SurrealDB avec `docker-compose up -d surrealdb`

### Tests E2E échouent

```
Error: ANTHROPIC_API_KEY not configured
```

**Solution:** Ajoutez `ANTHROPIC_API_KEY=sk-ant-...` dans `backend/.env`

### Tests lents

**Solution:** Utilisez les markers pour skip les tests lents:

```bash
uv run pytest -m "not slow"
```

### Cleanup de la base de test

Si la base de test contient des données anciennes:

```bash
# Se connecter à SurrealDB
surreal sql --conn http://localhost:8001 --user root --pass root --ns notary_test --db notary_test_db

# Supprimer toutes les données
DELETE FROM dossier;
DELETE FROM document;
DELETE FROM checklist;
DELETE FROM agent_execution;
```

## Ressources

- [pytest Documentation](https://docs.pytest.org/)
- [pytest-asyncio](https://pytest-asyncio.readthedocs.io/)
- [pytest-cov](https://pytest-cov.readthedocs.io/)
- [pytest-mock](https://pytest-mock.readthedocs.io/)
- [Faker](https://faker.readthedocs.io/)
