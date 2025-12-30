#!/bin/bash
# Script de backup automatique SurrealDB
# Usage: ./scripts/backup_db.sh

set -e  # Arrêt en cas d'erreur

# Configuration
BACKUP_DIR="/Users/alain/Workspace/GitHub/legal-assistant/backend/backups"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="$BACKUP_DIR/backup_$TIMESTAMP.surql"
MAX_BACKUPS=30  # Garder les 30 derniers backups

# Créer le dossier de backup s'il n'existe pas
mkdir -p "$BACKUP_DIR"

# Effectuer le backup
echo "🔄 Backup SurrealDB en cours..."
surreal export \
  --conn http://localhost:8002 \
  --user root \
  --pass root \
  --ns legal \
  --db legal_db \
  "$BACKUP_FILE"

if [ $? -eq 0 ]; then
  echo "✅ Backup créé: $BACKUP_FILE"

  # Compression du backup
  gzip "$BACKUP_FILE"
  echo "📦 Backup compressé: ${BACKUP_FILE}.gz"

  # Afficher la taille
  SIZE=$(du -h "${BACKUP_FILE}.gz" | cut -f1)
  echo "📊 Taille: $SIZE"

  # Nettoyer les vieux backups (garder les MAX_BACKUPS plus récents)
  BACKUP_COUNT=$(ls -1 "$BACKUP_DIR"/backup_*.surql.gz 2>/dev/null | wc -l)
  if [ "$BACKUP_COUNT" -gt "$MAX_BACKUPS" ]; then
    echo "🧹 Nettoyage des anciens backups..."
    ls -1t "$BACKUP_DIR"/backup_*.surql.gz | tail -n +$((MAX_BACKUPS + 1)) | xargs rm -f
    echo "✅ Anciens backups supprimés (gardé les $MAX_BACKUPS plus récents)"
  fi

else
  echo "❌ Erreur lors du backup"
  exit 1
fi
