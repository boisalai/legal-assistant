"""
Configuration pytest pour les tests Notary Assistant.

Ce fichier configure:
- Le PYTHONPATH pour que les imports fonctionnent depuis tests/
- Les fixtures communes à tous les tests
- Les hooks pytest personnalisés
"""

import sys
from pathlib import Path

# Ajouter le répertoire parent (backend/) au PYTHONPATH
# Cela permet d'importer config, services, models, etc. depuis les tests
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))


# ========================================
# Fixtures communes
# ========================================

import asyncio
import pytest
from pathlib import Path
from typing import AsyncGenerator
from unittest.mock import Mock, AsyncMock

from httpx import AsyncClient, ASGITransport
from faker import Faker

# Imports du projet
from config.settings import settings
from main import app
from services.surreal_service import SurrealDBService
from services.dossier_service import DossierService


# ========================================
# Configuration
# ========================================

@pytest.fixture(scope="session")
def event_loop():
    """
    Crée une event loop pour toute la session de tests.
    Nécessaire pour pytest-asyncio.
    """
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def faker_instance():
    """Instance Faker pour générer des données de test."""
    return Faker('fr_CA')  # Français canadien


# ========================================
# Fixtures Base de Données
# ========================================

@pytest.fixture(scope="session")
async def db_service(event_loop) -> AsyncGenerator[SurrealDBService, None]:
    """
    Fixture pour un service SurrealDB de test (scope: session).

    Utilise un namespace et une database dédiés aux tests.
    Crée UNE connexion pour toute la session de tests (comme en production).

    Cette approche:
    - Simule le comportement réel de l'application (connexion globale)
    - Améliore la performance (pas de reconnexion à chaque test)
    - Évite les problèmes de persistance entre tests
    - Résout le bug où les données créées dans une connexion n'étaient pas
      visibles dans une autre connexion
    """
    # Utiliser une base de test différente
    db = SurrealDBService(
        url=settings.surreal_url,
        namespace="notary_test",
        database="notary_test_db",
        username=settings.surreal_username,
        password=settings.surreal_password,
    )

    await db.connect()

    yield db

    # Nettoyage final: supprimer toutes les données de test
    try:
        await db.query("DELETE FROM dossier")
        await db.query("DELETE FROM document")
        await db.query("DELETE FROM checklist")
        await db.query("DELETE FROM agent_execution")
        await db.query("DELETE FROM user WHERE id != 'user:test_notaire'")
    except Exception as e:
        print(f"Warning: Cleanup failed: {e}")

    await db.disconnect()


@pytest.fixture(autouse=True)
async def cleanup_between_tests(db_service: SurrealDBService):
    """
    Nettoyage automatique AVANT chaque test.

    Supprime les données de test créées par les tests précédents.
    autouse=True signifie que cette fixture s'exécute automatiquement.
    """
    # Cleanup AVANT le test (pas après, car on veut garder les données en cas d'échec pour debug)
    try:
        await db_service.query("DELETE FROM dossier")
        await db_service.query("DELETE FROM document")
        await db_service.query("DELETE FROM checklist")
        await db_service.query("DELETE FROM agent_execution")
        # Note: on ne supprime pas user:test_notaire car il est utilisé partout
    except Exception as e:
        print(f"Warning: Pre-test cleanup failed: {e}")

    yield  # Le test s'exécute ici


@pytest.fixture
async def dossier_service(db_service: SurrealDBService, tmp_path: Path) -> DossierService:
    """
    Fixture pour le service de gestion des dossiers.

    Utilise un répertoire temporaire pour les uploads.
    """
    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir(exist_ok=True)

    return DossierService(db=db_service, upload_dir=upload_dir)


# ========================================
# Fixtures API
# ========================================

@pytest.fixture
async def api_client() -> AsyncGenerator[AsyncClient, None]:
    """
    Fixture pour un client HTTP de test pour l'API FastAPI.

    Utilise httpx.AsyncClient avec ASGITransport pour tester l'API
    sans avoir besoin de la lancer sur un port.

    IMPORTANT: Cette fixture initialise également la connexion SurrealDB globale
    en déclenchant les événements startup de l'app, comme en production.
    """
    # Déclencher les événements startup de l'app (initialise la connexion SurrealDB globale)
    # Note: avec ASGITransport, les événements startup/shutdown sont déclenchés automatiquement
    # mais on peut aussi les appeler manuellement si nécessaire

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as client:
        yield client

    # Les événements shutdown sont déclenchés automatiquement à la fin du context manager


# ========================================
# Fixtures Données de Test
# ========================================

@pytest.fixture
def sample_dossier_data(faker_instance: Faker) -> dict:
    """Données de test pour créer un dossier."""
    return {
        "nom_dossier": f"Test - {faker_instance.address()}",
        "user_id": "user:test_notaire",
        "type_transaction": "vente",
    }


@pytest.fixture
def sample_pdf_content() -> bytes:
    """
    Contenu PDF minimal valide pour les tests.

    NOTE: Pour les tests complets, utilisez ReportLab pour générer
    des PDFs plus réalistes.
    """
    # PDF minimal valide (1 page vide)
    return b"""%PDF-1.4
1 0 obj
<<
/Type /Catalog
/Pages 2 0 R
>>
endobj
2 0 obj
<<
/Type /Pages
/Kids [3 0 R]
/Count 1
>>
endobj
3 0 obj
<<
/Type /Page
/Parent 2 0 R
/MediaBox [0 0 612 792]
/Contents 4 0 R
/Resources <<
/ProcSet [/PDF /Text]
>>
>>
endobj
4 0 obj
<<
/Length 44
>>
stream
BT
/F1 12 Tf
100 700 Td
(Test PDF) Tj
ET
endstream
endobj
xref
0 5
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000115 00000 n
0000000262 00000 n
trailer
<<
/Size 5
/Root 1 0 R
>>
startxref
355
%%EOF"""


# ========================================
# Fixtures Mocks
# ========================================

@pytest.fixture
def mock_llm_service(mocker):
    """
    Mock du service LLM pour éviter les appels réels à l'API.

    Utilise pytest-mock pour créer un mock.
    """
    mock = Mock()
    mock.generate = AsyncMock(return_value="Réponse de test du LLM")
    mock.initialize = AsyncMock()
    mock.is_initialized = True

    return mock


@pytest.fixture
def mock_workflow(mocker):
    """
    Mock du workflow Agno pour les tests rapides.

    Retourne un résultat de workflow simulé.
    """
    mock = Mock()
    mock.arun = AsyncMock(return_value={
        "success": True,
        "donnees_extraites": {"documents": []},
        "classification": {
            "type_transaction": "vente",
            "type_propriete": "residentielle",
        },
        "verification": {
            "score_verification": 0.85,
            "alertes": [],
        },
        "checklist": {
            "checklist": [
                {"item": "Test item 1", "priorite": "haute", "complete": False}
            ],
            "score_confiance": 0.90,
        },
        "score_confiance": 0.90,
        "requiert_validation": False,
        "etapes_completees": ["extraction", "classification", "verification", "checklist"],
    })

    return mock
