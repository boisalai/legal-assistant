#!/bin/bash
# Script pour exécuter les tests automatisés

set -e  # Arrêter en cas d'erreur

echo "🧪 Exécution des tests automatisés..."
echo ""

# Vérifier que SurrealDB est en cours d'exécution
if ! nc -z localhost 8002 2>/dev/null; then
    echo "❌ Erreur: SurrealDB n'est pas en cours d'exécution sur le port 8002"
    echo ""
    echo "Démarrez SurrealDB avec:"
    echo "  surreal start --user root --pass root --bind 0.0.0.0:8002 file:data/surreal.db"
    exit 1
fi

echo "✅ SurrealDB détecté sur localhost:8002"
echo ""

# Vérifier les dépendances de test
if ! uv run python -c "import pytest" 2>/dev/null; then
    echo "📦 Installation des dépendances de test..."
    uv sync --extra dev
    echo ""
fi

# Exécuter les tests
if [ "$1" == "--cov" ]; then
    echo "🔍 Exécution des tests avec couverture de code..."
    uv run pytest --cov=. --cov-report=term-missing --cov-report=html
    echo ""
    echo "📊 Rapport de couverture généré dans: htmlcov/index.html"
elif [ "$1" == "--watch" ]; then
    echo "👀 Mode watch activé (nécessite pytest-watch)..."
    uv run ptw
else
    echo "🏃 Exécution des tests..."
    uv run pytest -v "$@"
fi

echo ""
echo "✅ Tests terminés!"
