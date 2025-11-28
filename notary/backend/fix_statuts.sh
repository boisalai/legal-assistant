#!/bin/bash
# Script pour vérifier et corriger tous les statuts des dossiers

URL="http://localhost:8001/sql"
AUTH="root:root"
NS="notary"
DB="notary_db"

echo "🔍 Vérification des statuts actuels..."
echo ""

# Compter les dossiers par statut
curl -s -X POST "$URL" \
  -H "Accept: application/json" \
  -H "NS: $NS" \
  -H "DB: $DB" \
  -u "$AUTH" \
  -d "SELECT statut, count() as total FROM dossier GROUP BY statut;"

echo ""
echo "🔄 Correction de TOUS les statuts invalides..."
echo ""

# Migration: complete → termine (plusieurs fois pour être sûr)
echo "📝 Migration: 'complete' → 'termine'"
for i in {1..3}; do
  curl -s -X POST "$URL" \
    -H "Accept: application/json" \
    -H "NS: $NS" \
    -H "DB: $DB" \
    -u "$AUTH" \
    -d "UPDATE dossier SET statut = 'termine' WHERE statut = 'complete';" > /dev/null
done
echo "  ✅ Terminé"

# Migration: erreur → en_erreur
echo "📝 Migration: 'erreur' → 'en_erreur'"
curl -s -X POST "$URL" \
  -H "Accept: application/json" \
  -H "NS: $NS" \
  -H "DB: $DB" \
  -u "$AUTH" \
  -d "UPDATE dossier SET statut = 'en_erreur' WHERE statut = 'erreur';" > /dev/null
echo "  ✅ Terminé"

# Migration: valide → termine
echo "📝 Migration: 'valide' → 'termine'"
curl -s -X POST "$URL" \
  -H "Accept: application/json" \
  -H "NS: $NS" \
  -H "DB: $DB" \
  -u "$AUTH" \
  -d "UPDATE dossier SET statut = 'termine' WHERE statut = 'valide';" > /dev/null
echo "  ✅ Terminé"

# Migration: analyse_complete → termine
echo "📝 Migration: 'analyse_complete' → 'termine'"
curl -s -X POST "$URL" \
  -H "Accept: application/json" \
  -H "NS: $NS" \
  -H "DB: $DB" \
  -u "$AUTH" \
  -d "UPDATE dossier SET statut = 'termine' WHERE statut = 'analyse_complete';" > /dev/null
echo "  ✅ Terminé"

echo ""
echo "📊 Statuts après correction:"
echo ""

# Vérification finale
curl -s -X POST "$URL" \
  -H "Accept: application/json" \
  -H "NS: $NS" \
  -H "DB: $DB" \
  -u "$AUTH" \
  -d "SELECT statut, count() as total FROM dossier GROUP BY statut;"

echo ""
echo "✅ Correction terminée!"
echo ""
echo "🔍 Vérification des statuts invalides restants:"
curl -s -X POST "$URL" \
  -H "Accept: application/json" \
  -H "NS: $NS" \
  -H "DB: $DB" \
  -u "$AUTH" \
  -d "SELECT id, statut FROM dossier WHERE statut NOT IN ['nouveau', 'en_analyse', 'termine', 'en_erreur', 'archive'];"
