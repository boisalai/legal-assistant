# Tests automatisés - Legal Assistant

Ce répertoire contient les tests automatisés pour l'application Legal Assistant.

## 🎉 Tests fonctionnels avec serveur réel!

Les tests d'intégration utilisent maintenant un **serveur FastAPI réel** démarré automatiquement sur le port 8001. Cette approche garantit des tests réalistes sans conflits d'event loop.

## ✅ État actuel (2025-12-20)

- **62 tests passent** (100% des tests non-skipped) ✅
- **4 tests skipped** (tests ML avec données réelles)
- **99 secondes** d'exécution
- **14% de couverture** de code (API endpoints)

**Session actuelle** : Correction des bugs de validation dans l'endpoint `/transcribe`
**Détails complets** : Voir [`IMPLEMENTATION_SUMMARY.md`](./IMPLEMENTATION_SUMMARY.md)

## Installation des dépendances de test

```bash
# Installer les dépendances de développement
uv sync --extra dev
```

## Prérequis

**SurrealDB doit être en cours d'exécution** sur `localhost:8002` :

```bash
# Depuis la racine du projet
docker-compose up -d
# OU en natif
surreal start --user root --pass root --bind 0.0.0.0:8002 file:backend/data/surrealdb/legal.db
```

## Exécution des tests

### Tous les tests (rapides uniquement)

```bash
# Depuis le répertoire backend
cd backend
uv run pytest -m "not slow"

# Avec couverture de code
uv run pytest -m "not slow" --cov=. --cov-report=html
```

### Tous les tests (incluant les tests lents)

```bash
uv run pytest
```

### Tests spécifiques

```bash
# Tests pour les cours uniquement
uv run pytest tests/test_courses.py

# Test spécifique
uv run pytest tests/test_courses.py::TestCoursesCRUD::test_create_course

# Tests avec sortie détaillée
uv run pytest -v

# Tests avec couverture de code
uv run pytest --cov=. --cov-report=html
```

### Options utiles

```bash
# Arrêter au premier échec
uv run pytest -x

# Afficher les print statements
uv run pytest -s

# Tests parallèles (plus rapide)
uv run pytest -n auto  # Nécessite pytest-xdist

# Tests avec markers
uv run pytest -m unit        # Uniquement les tests unitaires
uv run pytest -m integration # Uniquement les tests d'intégration
```

## Structure des tests

```
tests/
├── __init__.py                      # Package de tests
├── conftest.py                      # Configuration pytest et fixtures globales
├── test_courses.py                  # Tests CRUD pour les cours (12 tests)
├── test_documents.py                # Tests upload/download de documents (11 tests)
├── test_chat.py                     # Tests chat et streaming SSE (13 tests)
├── test_semantic_search.py          # Tests recherche sémantique et RAG (9 tests)
├── test_linked_directories.py       # Tests liaison de répertoires (11 tests)
├── test_transcription.py            # Tests transcription audio (11 tests)
├── KNOWN_ISSUES.md                  # Documentation technique et solutions
└── README.md                        # Ce fichier
```

**Total : 66 tests** (55 rapides, 11 marqués comme `slow`)

## Écriture de nouveaux tests

### Structure d'un test

```python
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_example(client: AsyncClient):
    """Description du test."""
    # Arrange - Préparer les données
    data = {"title": "Test"}

    # Act - Exécuter l'action
    response = await client.post("/api/courses", json=data)

    # Assert - Vérifier les résultats
    assert response.status_code == 201
    assert response.json()["title"] == "Test"
```

### Fixtures disponibles (conftest.py)

#### Fixtures de session (partagées entre tous les tests)

- `test_server`: Serveur FastAPI réel sur http://localhost:8001
- `auth_token`: Token JWT pour l'authentification
- `event_loop`: Event loop partagé pour éviter les problèmes de fermeture

#### Fixtures par fonction (nouvelles pour chaque test)

- `client`: Client HTTP asynchrone avec authentification
  - Base URL: `http://localhost:8001`
  - Headers: `Authorization: Bearer <token>`
  - Timeout: 60 secondes

#### Fixtures spécifiques par fichier de test

Chaque fichier de test définit ses propres fixtures pour créer des données de test (cours, documents, etc.).

## Couverture de code

Après avoir exécuté les tests avec `--cov`, ouvrez le rapport HTML :

```bash
# Générer le rapport
uv run pytest --cov=. --cov-report=html

# Ouvrir le rapport (macOS)
open htmlcov/index.html

# Linux
xdg-open htmlcov/index.html
```

## Bonnes pratiques

1. **Isolation** : Chaque test doit être indépendant
2. **Nettoyage** : Utiliser les fixtures pour nettoyer après les tests
3. **Nommage** : Noms descriptifs (`test_create_course_with_valid_data`)
4. **Arrange-Act-Assert** : Structure claire en 3 parties
5. **Tests asynchrones** : Utiliser `@pytest.mark.asyncio` pour les tests async

## CI/CD

Les tests peuvent être intégrés dans un pipeline CI/CD :

```yaml
# Exemple GitHub Actions
- name: Run tests
  run: |
    cd backend
    uv sync --extra dev
    uv run pytest --cov=. --cov-report=xml
```

## Dépannage

### Erreur de connexion à SurrealDB

```
ERROR: Connection refused
```

**Solution** : Vérifiez que SurrealDB est en cours d'exécution.

### Tests qui échouent de manière aléatoire

**Cause possible** : Tests non isolés, données partagées

**Solution** : Vérifiez que `clean_test_data` fonctionne correctement et que chaque test crée ses propres données.

### ImportError

```
ImportError: cannot import name 'app' from 'main'
```

**Solution** : Assurez-vous d'être dans le répertoire `backend` et que l'environnement virtuel est activé.
