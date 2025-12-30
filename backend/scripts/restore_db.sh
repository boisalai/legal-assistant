#!/bin/bash
# Script de restauration SurrealDB
# Usage: ./scripts/restore_db.sh [backup_file]

set -e

# Configuration
BACKUP_DIR="/Users/alain/Workspace/GitHub/legal-assistant/backend/backups"

# Vérifier si un fichier de backup est spécifié
if [ -z "$1" ]; then
  echo "📋 Backups disponibles:"
  ls -lht "$BACKUP_DIR"/backup_*.surql.gz | head -10
  echo ""
  echo "Usage: $0 <backup_file.surql.gz>"
  echo "Exemple: $0 $BACKUP_DIR/backup_20251228_132500.surql.gz"
  exit 1
fi

BACKUP_FILE="$1"

# Vérifier que le fichier existe
if [ ! -f "$BACKUP_FILE" ]; then
  echo "❌ Fichier de backup introuvable: $BACKUP_FILE"
  exit 1
fi

# Décompresser si nécessaire
if [[ "$BACKUP_FILE" == *.gz ]]; then
  echo "📦 Décompression du backup..."
  UNCOMPRESSED="${BACKUP_FILE%.gz}"
  gunzip -k "$BACKUP_FILE"  # -k garde le .gz original
  IMPORT_FILE="$UNCOMPRESSED"
else
  IMPORT_FILE="$BACKUP_FILE"
fi

# Demander confirmation
echo "⚠️  Attention: Cette opération va ÉCRASER la base de données actuelle!"
echo "📁 Backup à restaurer: $(basename "$IMPORT_FILE")"
read -p "Continuer? (yes/no): " CONFIRM

if [ "$CONFIRM" != "yes" ]; then
  echo "❌ Restauration annulée"
  # Nettoyer le fichier décompressé temporaire
  if [[ "$BACKUP_FILE" == *.gz ]]; then
    rm -f "$IMPORT_FILE"
  fi
  exit 1
fi

# Effectuer la restauration
echo "🔄 Restauration en cours..."
surreal import \
  --conn http://localhost:8002 \
  --user root \
  --pass root \
  --ns legal \
  --db legal_db \
  "$IMPORT_FILE"

if [ $? -eq 0 ]; then
  echo "✅ Restauration réussie!"

  # Nettoyer le fichier décompressé temporaire
  if [[ "$BACKUP_FILE" == *.gz ]]; then
    rm -f "$IMPORT_FILE"
  fi

else
  echo "❌ Erreur lors de la restauration"
  exit 1
fi
