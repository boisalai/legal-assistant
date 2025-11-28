"""
Tests pour Notary Assistant Backend.

Structure:
- unit/: Tests unitaires pour les services et models
- integration/: Tests d'integration pour l'API et les workflows
- e2e/: Tests end-to-end complets

Utilisation:
    # Lancer tous les tests
    uv run pytest

    # Tests unitaires seulement
    uv run pytest -m unit

    # Tests d'integration
    uv run pytest -m integration

    # Tests E2E (lents)
    uv run pytest -m e2e

    # Avec coverage
    uv run pytest --cov=. --cov-report=html
"""
