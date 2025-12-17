# Tests automatisés - Legal Assistant

Ce répertoire contient les tests automatisés pour l'application Legal Assistant.

## Installation des dépendances de test

```bash
# Installer les dépendances de développement
uv sync --extra dev
```

## Exécution des tests

### Tous les tests

```bash
# Depuis le répertoire backend
cd backend
uv run pytest

# Ou avec pytest directement si l'environnement est activé
pytest
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
├── __init__.py              # Package de tests
├── conftest.py              # Configuration pytest et fixtures globales
├── test_courses.py          # Tests CRUD pour les cours
└── README.md                # Ce fichier
```

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

### Fixtures disponibles

- `client`: Client HTTP asynchrone pour les requêtes API
- `course_data`: Données de test pour un cours
- `clean_test_data`: Nettoyage automatique après chaque test

## Prérequis

**SurrealDB doit être en cours d'exécution** sur `localhost:8002` :

```bash
surreal start --user root --pass root --bind 0.0.0.0:8002 file:data/surreal.db
```

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
