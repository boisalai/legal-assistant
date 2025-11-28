#!/bin/bash
# Script pour supprimer uniquement les dossiers avec des statuts invalides

URL="http://localhost:8001/sql"
AUTH="root:root"
NS="notary"
DB="notary_db"

echo "🔍 Recherche des dossiers avec statuts invalides..."
echo ""

# Afficher les dossiers avec statuts invalides
curl -s -X POST "$URL" \
  -H "Accept: application/json" \
  -H "NS: $NS" \
  -H "DB: $DB" \
  -u "$AUTH" \
  -d "SELECT id, nom_dossier, statut FROM dossier WHERE statut NOT IN ['nouveau', 'en_analyse', 'termine', 'en_erreur', 'archive'];"

echo ""
echo "⚠️  Ces dossiers seront SUPPRIMÉS."
echo ""
read -p "Voulez-vous continuer ? (tapez 'oui' pour confirmer) : " confirmation

if [ "$confirmation" != "oui" ]; then
    echo "❌ Opération annulée."
    exit 0
fi

echo ""
echo "🗑️  Suppression des dossiers avec statuts invalides..."

# Supprimer les dossiers avec statuts invalides
curl -s -X POST "$URL" \
  -H "Accept: application/json" \
  -H "NS: $NS" \
  -H "DB: $DB" \
  -u "$AUTH" \
  -d "DELETE dossier WHERE statut NOT IN ['nouveau', 'en_analyse', 'termine', 'en_erreur', 'archive'];"

echo ""
echo "✅ Dossiers invalides supprimés !"
echo ""
echo "Vérification..."

# Vérifier qu'il ne reste plus de statuts invalides
curl -s -X POST "$URL" \
  -H "Accept: application/json" \
  -H "NS: $NS" \
  -H "DB: $DB" \
  -u "$AUTH" \
  -d "SELECT id, nom_dossier, statut FROM dossier WHERE statut NOT IN ['nouveau', 'en_analyse', 'termine', 'en_erreur', 'archive'];"

echo ""
echo "🎉 Terminé ! Votre application devrait maintenant fonctionner."
