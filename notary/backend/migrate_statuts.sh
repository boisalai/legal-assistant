#!/bin/bash
# Script de migration pour mettre à jour les statuts des dossiers

echo "🔍 Vérification et migration des statuts..."

# URL et credentials SurrealDB
URL="http://localhost:8001/sql"
AUTH="root:root"
NS="notary"
DB="notary_db"

echo ""
echo "📊 Statuts avant migration:"
curl -s -X POST "$URL" \
  -H "Accept: application/json" \
  -H "NS: $NS" \
  -H "DB: $DB" \
  -u "$AUTH" \
  -d "SELECT statut, count() as total FROM dossier GROUP BY statut;" | jq -r '.[0][] | "  - \(.statut): \(.total)"'

echo ""
echo "🔄 Migration des statuts..."

# Migration: complete → termine
echo ""
echo "📝 Migration: 'complete' → 'termine'"
RESULT=$(curl -s -X POST "$URL" \
  -H "Accept: application/json" \
  -H "NS: $NS" \
  -H "DB: $DB" \
  -u "$AUTH" \
  -d "UPDATE dossier SET statut = 'termine' WHERE statut = 'complete';" | jq -r '.[0] | length')
echo "  ✅ $RESULT dossier(s) mis à jour"

# Migration: erreur → en_erreur
echo ""
echo "📝 Migration: 'erreur' → 'en_erreur'"
RESULT=$(curl -s -X POST "$URL" \
  -H "Accept: application/json" \
  -H "NS: $NS" \
  -H "DB: $DB" \
  -u "$AUTH" \
  -d "UPDATE dossier SET statut = 'en_erreur' WHERE statut = 'erreur';" | jq -r '.[0] | length')
echo "  ✅ $RESULT dossier(s) mis à jour"

# Migration: valide → termine
echo ""
echo "📝 Migration: 'valide' → 'termine'"
RESULT=$(curl -s -X POST "$URL" \
  -H "Accept: application/json" \
  -H "NS: $NS" \
  -H "DB: $DB" \
  -u "$AUTH" \
  -d "UPDATE dossier SET statut = 'termine' WHERE statut = 'valide';" | jq -r '.[0] | length')
echo "  ✅ $RESULT dossier(s) mis à jour"

# Migration: analyse_complete → termine
echo ""
echo "📝 Migration: 'analyse_complete' → 'termine'"
RESULT=$(curl -s -X POST "$URL" \
  -H "Accept: application/json" \
  -H "NS: $NS" \
  -H "DB: $DB" \
  -u "$AUTH" \
  -d "UPDATE dossier SET statut = 'termine' WHERE statut = 'analyse_complete';" | jq -r '.[0] | length')
echo "  ✅ $RESULT dossier(s) mis à jour"

echo ""
echo "📊 Statuts après migration:"
curl -s -X POST "$URL" \
  -H "Accept: application/json" \
  -H "NS: $NS" \
  -H "DB: $DB" \
  -u "$AUTH" \
  -d "SELECT statut, count() as total FROM dossier GROUP BY statut;" | jq -r '.[0][] | "  - \(.statut): \(.total)"'

echo ""
echo "✅ Migration terminée avec succès!"
