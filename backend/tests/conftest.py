"""
Configuration pytest pour les tests.

Ce module contient les fixtures globales et la configuration
pour tous les tests.
"""

import os
import time
import subprocess
import asyncio
import pytest
import httpx
from typing import Generator
from surrealdb import AsyncSurreal

from services.surreal_service import init_surreal_service

# Configurer l'environnement de test
os.environ["TESTING"] = "true"
os.environ["DATABASE_URL"] = "ws://localhost:8002"

# Port pour le serveur de test (différent du port de développement)
TEST_SERVER_PORT = 8001
TEST_SERVER_URL = f"http://localhost:{TEST_SERVER_PORT}"


# ============================================================================
# Cleanup automatique des données de test
# ============================================================================

async def cleanup_test_data():
    """
    Nettoie les données de test de la base de données.

    Supprime tous les cours qui ont :
    - Un course_code commençant par "TEST"
    - Un titre contenant "Test" ou "test"
    - Un titre égal à "Cours minimal"
    """
    db = AsyncSurreal("http://localhost:8002")
    await db.signin({"username": "root", "password": "root"})
    await db.use("legal", "legal_db")

    try:
        # Get all courses
        all_courses = await db.query("SELECT * FROM course")

        # Filter test courses
        test_courses = [
            c for c in all_courses
            if (c.get('course_code') or '').startswith('TEST')
            or 'Test' in (c.get('title') or '')
            or 'test' in (c.get('title') or '')
            or c.get('title') == 'Cours minimal'
        ]

        # Delete test courses
        for course in test_courses:
            course_id = str(course.get('id'))
            await db.delete(course_id)

        if test_courses:
            print(f"\n🧹 Nettoyage : {len(test_courses)} cours de test supprimés")

    finally:
        # Note: db.close() not implemented in AsyncHttpSurrealConnection
        pass


@pytest.fixture(scope="session", autouse=True)
def cleanup_after_tests():
    """
    Fixture qui nettoie automatiquement les données de test après TOUS les tests.

    autouse=True : s'exécute automatiquement sans être explicitement appelée
    scope="session" : s'exécute une fois après toute la session de tests
    """
    # Setup (avant les tests) - on ne fait rien
    yield

    # Teardown (après les tests) - on nettoie
    print("\n" + "="*60)
    print("🧹 NETTOYAGE AUTOMATIQUE DES DONNÉES DE TEST")
    print("="*60)
    asyncio.run(cleanup_test_data())
    print("✅ Nettoyage terminé\n")


# Create a session-scoped event loop to avoid "Event loop is closed" errors
@pytest.fixture(scope="session")
def event_loop():
    """
    Create an event loop for the entire test session.

    This prevents "Event loop is closed" errors when using session-scoped
    async fixtures.
    """
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def test_server() -> Generator[str, None, None]:
    """
    Start a real FastAPI server for testing.

    This avoids event loop conflicts by running the server in a separate process.
    The server will use the real SurrealDB instance and properly initialize
    all services through FastAPI's lifespan events.
    """
    # Start uvicorn server in subprocess using uv to ensure correct Python environment
    process = subprocess.Popen(
        [
            "uv", "run", "uvicorn",
            "main:app",
            "--host", "0.0.0.0",
            "--port", str(TEST_SERVER_PORT),
            "--log-level", "warning",  # Reduce noise in test output
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd="/Users/alain/Workspace/GitHub/legal-assistant/backend",  # Ensure correct working directory
    )

    # Wait for server to be ready (max 10 seconds)
    max_retries = 50
    retry_delay = 0.2  # 200ms
    server_ready = False

    for i in range(max_retries):
        try:
            response = httpx.get(f"{TEST_SERVER_URL}/health", timeout=1.0)
            if response.status_code == 200:
                server_ready = True
                print(f"\n✅ Test server ready at {TEST_SERVER_URL}")
                break
        except (httpx.ConnectError, httpx.TimeoutException):
            time.sleep(retry_delay)

    if not server_ready:
        process.terminate()
        process.wait(timeout=5)
        raise RuntimeError(
            f"Test server failed to start after {max_retries * retry_delay} seconds"
        )

    yield TEST_SERVER_URL

    # Cleanup: stop server
    print("\n🛑 Stopping test server...")
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()


@pytest.fixture(scope="session")
def auth_token(test_server: str) -> str:
    """
    Fixture pour obtenir un token d'authentification pour les tests.

    Crée un utilisateur de test et retourne le token.
    Uses synchronous httpx client since it's session-scoped.

    Note: Les routes utilisent auto_error=False, donc l'auth est optionnelle.
    Si l'authentification échoue, on retourne un token factice.
    """
    with httpx.Client(base_url=test_server, timeout=30.0) as client:
        # Try to create test user
        try:
            register_response = client.post(
                "/api/auth/register",
                json={
                    "name": "Test User",
                    "email": "test@example.com",
                    "password": "testpassword123",
                }
            )

            # If user already exists, login
            if register_response.status_code == 400:
                login_response = client.post(
                    "/api/auth/login",
                    data={
                        "username": "test@example.com",
                        "password": "testpassword123",
                    },
                    headers={"Content-Type": "application/x-www-form-urlencoded"}
                )
                if login_response.status_code == 200:
                    return login_response.json()["access_token"]

            # User created, now login
            if register_response.status_code == 200:
                login_response = client.post(
                    "/api/auth/login",
                    data={
                        "username": "test@example.com",
                        "password": "testpassword123",
                    },
                    headers={"Content-Type": "application/x-www-form-urlencoded"}
                )
                if login_response.status_code == 200:
                    return login_response.json()["access_token"]
        except Exception as e:
            print(f"\n⚠️ Auth failed: {e}")

    # Auth is optional (auto_error=False), return dummy token
    print("\n⚠️ Using dummy token - auth is optional for most endpoints")
    return "dummy_test_token"


@pytest.fixture
async def client(test_server: str, auth_token: str):
    """
    Fixture pour le client HTTP asynchrone avec authentification.

    Uses the real test server and includes authentication headers.
    Creates a fresh client for each test to avoid cleanup issues.
    """
    headers = {"Authorization": f"Bearer {auth_token}"}

    async with httpx.AsyncClient(
        base_url=test_server,
        headers=headers,
        timeout=300.0,  # 5 minutes timeout for ML operations (transcription, indexing)
    ) as client:
        yield client


@pytest.fixture(scope="session")
def surreal_service_initialized(test_server: str):
    """
    Initialize SurrealDB service for tests that need direct service access.

    This allows tests to call services directly instead of going through the API.
    The service is initialized once per test session.
    """
    # Initialize the SurrealDB service
    service = init_surreal_service(
        url="ws://localhost:8002",
        namespace="test",
        database="test",
        username="root",
        password="root"
    )

    # Connect to the database
    import asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(service.connect())

    yield service

    # Cleanup
    # Note: SurrealDBService doesn't have a close() method
    # The connection will be cleaned up automatically
    loop.close()


# Note: Automatic cleanup is disabled to avoid event loop issues
# Tests should be idempotent and handle existing data gracefully
#
# @pytest.fixture(scope="function", autouse=True)
# async def clean_test_data(test_server: str):
#     """Clean test data after each test."""
#     yield
#     # Cleanup logic here


# Configuration pytest-asyncio
def pytest_configure(config):
    """Configuration de pytest."""
    config.addinivalue_line(
        "markers", "asyncio: mark test as an async test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow (deselect with '-m \"not slow\"')"
    )
