#!/bin/bash
# Script pour vider complètement la base de données SurrealDB

URL="http://localhost:8001/sql"
AUTH="root:root"
NS="notary"
DB="notary_db"

echo "⚠️  ATTENTION : Ce script va SUPPRIMER TOUS les dossiers de la base de données !"
echo ""
read -p "Voulez-vous continuer ? (tapez 'oui' pour confirmer) : " confirmation

if [ "$confirmation" != "oui" ]; then
    echo "❌ Opération annulée."
    exit 0
fi

echo ""
echo "🗑️  Suppression de tous les dossiers..."

# Supprimer tous les dossiers
curl -s -X POST "$URL" \
  -H "Accept: application/json" \
  -H "NS: $NS" \
  -H "DB: $DB" \
  -u "$AUTH" \
  -d "DELETE dossier;"

echo ""
echo "🗑️  Suppression de tous les documents..."

# Supprimer tous les documents
curl -s -X POST "$URL" \
  -H "Accept: application/json" \
  -H "NS: $NS" \
  -H "DB: $DB" \
  -u "$AUTH" \
  -d "DELETE document;"

echo ""
echo "🗑️  Suppression de toutes les checklists..."

# Supprimer toutes les checklists
curl -s -X POST "$URL" \
  -H "Accept: application/json" \
  -H "NS: $NS" \
  -H "DB: $DB" \
  -u "$AUTH" \
  -d "DELETE checklist;"

echo ""
echo "✅ Base de données vidée avec succès !"
echo ""
echo "Vérification..."

# Compter les enregistrements restants
curl -s -X POST "$URL" \
  -H "Accept: application/json" \
  -H "NS: $NS" \
  -H "DB: $DB" \
  -u "$AUTH" \
  -d "SELECT count() FROM dossier GROUP ALL;" | python3 -c "import sys, json; data = json.load(sys.stdin); print(f\"   Dossiers restants: {data[0][0]['count'] if data and data[0] else 0}\")"

echo ""
echo "🎉 La base de données est maintenant vide et prête à l'emploi !"
