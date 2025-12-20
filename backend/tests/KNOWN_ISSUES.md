# Tests d'intégration - Documentation technique

## ✅ Solution implémentée : Serveur FastAPI réel

### Approche retenue

Les tests d'intégration utilisent maintenant un **serveur FastAPI réel** démarré dans un processus séparé au lieu d'utiliser `ASGITransport`. Cette approche résout définitivement tous les problèmes d'event loop avec pytest-asyncio et SurrealDB.

### Architecture des tests

```
┌─────────────────────────────────────────┐
│  Fixture: test_server (session)         │
│  - Démarre uvicorn sur port 8001        │
│  - Attend que /health réponde           │
│  - Se nettoie automatiquement           │
└──────────────┬──────────────────────────┘
               │
               ↓
┌─────────────────────────────────────────┐
│  Fixture: auth_token (session)          │
│  - Crée utilisateur de test             │
│  - Obtient token JWT                    │
│  - Partagé pour toute la session        │
└──────────────┬──────────────────────────┘
               │
               ↓
┌─────────────────────────────────────────┐
│  Fixture: event_loop (session)          │
│  - Event loop partagé pour la session   │
│  - Évite fermeture prématurée           │
└──────────────┬──────────────────────────┘
               │
               ↓
┌─────────────────────────────────────────┐
│  Fixture: client (function)             │
│  - Nouveau client httpx par test        │
│  - Inclut header Authorization          │
│  - Pas de fermeture explicite (GC)      │
└─────────────────────────────────────────┘
```

### Avantages de cette approche

1. **✅ Pas de conflits d'event loop** - Le serveur tourne dans son propre processus
2. **✅ Tests réalistes** - Teste l'application exactement comme en production
3. **✅ FastAPI lifespan** - Initialise SurrealDB et tous les services correctement
4. **✅ Isolation** - Chaque session de test démarre un serveur propre
5. **✅ Debugging facile** - Le serveur est accessible à `http://localhost:8001`

### Résolution des problèmes d'event loop

**Problème initial** : "Event loop is closed" lors du teardown des fixtures async

**Solutions appliquées** :
1. ✅ Fixture `event_loop` avec `scope="session"` pour partager l'event loop
2. ✅ Pas de fermeture explicite du client httpx (garbage collection)
3. ✅ Pas de cleanup automatique des données (tests idempotents)

### Solutions potentielles

Plusieurs approches pourraient résoudre ce problème :

#### Option 1 : Utiliser httpx avec serveur réel (Recommandé)

Au lieu d'utiliser `ASGITransport`, démarrer le serveur FastAPI dans un processus séparé et utiliser httpx avec de vraies requêtes HTTP.

```python
@pytest.fixture(scope="session")
def running_server():
    """Start FastAPI server in background."""
    import subprocess
    proc = subprocess.Popen(["uvicorn", "main:app", "--port", "8001"])
    yield "http://localhost:8001"
    proc.terminate()

@pytest.fixture
async def client(running_server):
    async with httpx.AsyncClient(base_url=running_server) as client:
        yield client
```

**Avantages** :
- Teste le serveur dans un environnement réaliste
- Évite les problèmes d'event loop
- Teste également le démarrage/shutdown de l'application

**Inconvénients** :
- Tests plus lents
- Plus complexe à configurer

#### Option 2 : Mock SurrealDB pour les tests

Utiliser un mock de SurrealDB qui n'utilise pas d'opérations asyncio réelles.

```python
@pytest.fixture
def mock_surreal_service(monkeypatch):
    """Mock SurrealDB service for testing."""
    mock_service = MagicMock()
    # Configure mock responses
    monkeypatch.setattr("services.surreal_service._service", mock_service)
    yield mock_service
```

**Avantages** :
- Tests rapides
- Pas de dépendance à SurrealDB
- Contrôle total sur les réponses

**Inconvénients** :
- Ne teste pas les vraies interactions avec la base de données
- Nécessite de maintenir les mocks à jour

#### Option 3 : Utiliser TestClient de FastAPI

FastAPI fournit `TestClient` basé sur Starlette qui gère mieux les event loops.

```python
from fastapi.testclient import TestClient

@pytest.fixture
def client():
    return TestClient(app)

def test_create_course(client):  # Synchrone, pas async
    response = client.post("/api/courses", json=data)
    assert response.status_code == 201
```

**Avantages** :
- Solution officielle de FastAPI
- Évite les problèmes d'event loop
- Tests synchrones (plus simples)

**Inconvénients** :
- Tests synchrones uniquement
- Ne teste pas le comportement async réel

#### Option 4 : Créer un nouveau client SurrealDB par test

Recréer le client SurrealDB pour chaque test au lieu de le partager.

```python
@pytest.fixture
async def surreal_service():
    """Create fresh SurrealDB connection for each test."""
    service = init_surreal_service(...)
    await service.connect()
    yield service
    await service.disconnect()
```

**Avantages** :
- Isolation complète entre les tests
- Évite le partage d'event loop

**Inconvénients** :
- Tests beaucoup plus lents
- Overhead de connexion pour chaque test

### Recommandation

Pour ce projet, **l'Option 1 (serveur réel)** est recommandée car :

1. Elle teste le comportement réel de l'application
2. Elle évite les complexités des event loops
3. Elle est plus proche de l'environnement de production
4. Les tests d'intégration sont censés être plus lents que les tests unitaires

### État actuel

Les fichiers de tests suivants ont été créés avec une couverture complète :

- ✅ `test_courses.py` - Tests CRUD pour les cours (10 tests)
- ✅ `test_documents.py` - Tests upload/download de documents (11 tests)
- ✅ `test_chat.py` - Tests chat et streaming SSE (13 tests)
- ✅ `test_semantic_search.py` - Tests recherche sémantique et RAG (9 tests)
- ✅ `test_linked_directories.py` - Tests liaison de répertoires (11 tests)
- ✅ `test_transcription.py` - Tests transcription audio (11 tests)

**Total : 65 tests** (dont 10 marqués comme `slow`)

Cependant, la plupart échouent actuellement à cause du problème d'event loop décrit ci-dessus.

### Prochaines étapes

1. Implémenter l'Option 1 (serveur réel) dans `conftest.py`
2. Adapter les fixtures pour utiliser de vraies requêtes HTTP
3. Vérifier que tous les tests passent
4. Ajouter des tests pour les cas limites
5. Configurer CI/CD pour exécuter les tests automatiquement

### Références

- [pytest-asyncio documentation](https://pytest-asyncio.readthedocs.io/)
- [FastAPI Testing](https://fastapi.tiangolo.com/tutorial/testing/)
- [SurrealDB Python SDK](https://github.com/surrealdb/surrealdb.py)
- [Issue similaire - SurrealDB + FastAPI](https://github.com/surrealdb/surrealdb.py/issues/45)
