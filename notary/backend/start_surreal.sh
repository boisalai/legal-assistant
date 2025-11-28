#!/bin/bash
# Script pour démarrer SurrealDB localement via Homebrew
#
# Usage:
#   chmod +x start_surreal.sh
#   ./start_surreal.sh

echo "🚀 Démarrage de SurrealDB..."
echo "📂 Données stockées dans: data/surrealdb"
echo "🌐 URL: http://localhost:8000"
echo "👤 Utilisateur: root / root"
echo ""
echo "Pour vous connecter:"
echo "  • API: http://localhost:8000"
echo "  • Namespace: notary"
echo "  • Database: notary_db"
echo ""
echo "Appuyez sur Ctrl+C pour arrêter"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Créer le répertoire de données s'il n'existe pas
mkdir -p data/surrealdb

# Démarrer SurrealDB avec RocksDB (comme Docker)
surreal start \
  --log trace \
  --user root \
  --pass root \
  --bind 0.0.0.0:8000 \
  rocksdb://data/surrealdb
