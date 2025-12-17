"""
Configuration pytest pour les tests.

Ce module contient les fixtures globales et la configuration
pour tous les tests.
"""

import os
import asyncio
import pytest
from typing import AsyncGenerator

# Configurer l'environnement de test
os.environ["TESTING"] = "true"
os.environ["DATABASE_URL"] = "ws://localhost:8002"


@pytest.fixture(scope="session", autouse=True)
async def init_services():
    """Initialize services before running tests."""
    from services.surreal_service import init_surreal_service

    # Initialize SurrealDB service
    service = init_surreal_service(
        url="ws://localhost:8002",
        namespace="test",
        database="test",
        username="root",
        password="root"
    )
    await service.connect()

    yield

    # Cleanup
    if service.db:
        await service.close()


@pytest.fixture(scope="session")
def event_loop():
    """
    Créer une boucle d'événements pour toute la session de test.

    Nécessaire pour les tests asynchrones avec pytest-asyncio.
    """
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def auth_token():
    """
    Fixture pour obtenir un token d'authentification pour les tests.

    Crée un utilisateur de test et retourne le token.
    """
    from httpx import AsyncClient, ASGITransport
    from main import app

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as client:
        # Essayer de créer un utilisateur de test
        register_response = await client.post(
            "/api/auth/register",
            json={
                "name": "Test User",
                "email": "test@example.com",
                "password": "testpassword123",
            }
        )

        # Si l'utilisateur existe déjà, se connecter
        if register_response.status_code == 400:
            login_response = await client.post(
                "/api/auth/login",
                data={
                    "username": "test@example.com",
                    "password": "testpassword123",
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            if login_response.status_code == 200:
                return login_response.json()["access_token"]

        # Utilisateur créé, se connecter
        if register_response.status_code == 200:
            login_response = await client.post(
                "/api/auth/login",
                data={
                    "username": "test@example.com",
                    "password": "testpassword123",
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            if login_response.status_code == 200:
                return login_response.json()["access_token"]

    # Si tout échoue, retourner None (les tests devront gérer ce cas)
    return None


@pytest.fixture(scope="function", autouse=True)
async def clean_test_data():
    """
    Nettoyer les données de test après chaque test.

    Cette fixture s'exécute automatiquement après chaque test
    pour garantir un état propre.
    """
    yield  # Le test s'exécute ici

    # Nettoyage après le test
    try:
        from services.surreal_service import get_surreal_service
        service = get_surreal_service()

        if service.db:
            # Supprimer tous les cours de test
            await service.query(
                "DELETE FROM course WHERE title CONTAINS 'Test' OR title CONTAINS 'Workflow'"
            )
    except Exception as e:
        # Ne pas faire échouer les tests si le nettoyage échoue
        print(f"Warning: Failed to clean test data: {e}")


# Configuration pytest-asyncio
def pytest_configure(config):
    """Configuration de pytest."""
    config.addinivalue_line(
        "markers", "asyncio: mark test as an async test"
    )
