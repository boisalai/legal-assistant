#!/bin/bash
# Script de démarrage SurrealDB avec backup automatique
# Usage: ./scripts/start_surreal.sh

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
DB_PATH="$PROJECT_ROOT/backend/data/surrealdb/legal.db"

echo "🚀 Démarrage SurrealDB avec backup automatique..."

# Vérifier si SurrealDB tourne déjà
if pgrep -f "surreal start" > /dev/null; then
  echo "⚠️  SurrealDB est déjà en cours d'exécution"
  echo "Pour redémarrer, arrêtez d'abord le processus:"
  echo "  pkill -f 'surreal start'"
  exit 1
fi

# Si la base existe, faire un backup avant de démarrer
if [ -d "$DB_PATH" ]; then
  echo "💾 Backup automatique avant démarrage..."

  # Démarrer SurrealDB temporairement en background pour le backup
  surreal start --user root --pass root --bind 0.0.0.0:8002 "file:$DB_PATH" > /dev/null 2>&1 &
  TEMP_PID=$!

  # Attendre que SurrealDB soit prêt
  sleep 2

  # Faire le backup
  "$SCRIPT_DIR/backup_db.sh" || {
    echo "⚠️  Backup automatique échoué (peut-être base vide)"
  }

  # Arrêter le processus temporaire
  kill $TEMP_PID 2>/dev/null || true
  sleep 1
fi

# Démarrer SurrealDB en utilisant le chemin absolu
echo "🔄 Démarrage de SurrealDB..."
echo "📂 Base de données: $DB_PATH"
echo "🌐 Port: 8002"
echo ""
echo "Pour arrêter: pkill -f 'surreal start'"
echo ""

surreal start \
  --user root \
  --pass root \
  --bind 0.0.0.0:8002 \
  "file:$DB_PATH"
