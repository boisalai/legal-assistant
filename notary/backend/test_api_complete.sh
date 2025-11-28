#!/bin/bash
# Test complet de l'API REST

API_URL="http://localhost:8000"

echo "=========================================="
echo "TEST COMPLET API - Notary Assistant"
echo "=========================================="

# 1. Health check
echo ""
echo "1️⃣  Health check"
curl -s "$API_URL/health"
echo ""

# 2. Créer un dossier
echo ""
echo "2️⃣  Créer un dossier"
RESPONSE=$(curl -s -X POST "$API_URL/api/dossiers" \
  -H 'Content-Type: application/json' \
  -d '{"nom_dossier":"Test Complet - Vente Martin","user_id":"user:test_notaire","type_transaction":"vente"}')

echo "$RESPONSE"
DOSSIER_ID=$(echo "$RESPONSE" | grep -o '"id":"[^"]*"' | cut -d'"' -f4)
echo ""
echo "Dossier créé: $DOSSIER_ID"

if [ -z "$DOSSIER_ID" ]; then
    echo "❌ Échec création dossier"
    exit 1
fi

# 3. Récupérer le dossier
echo ""
echo "3️⃣  Récupérer le dossier"
curl -s "$API_URL/api/dossiers/$DOSSIER_ID"
echo ""

# 4. Lister les dossiers
echo ""
echo "4️⃣  Lister tous les dossiers"
curl -s "$API_URL/api/dossiers" | head -c 300
echo "..."

# 5. Mettre à jour le dossier
echo ""
echo "5️⃣  Mettre à jour le statut"
curl -s -X PUT "$API_URL/api/dossiers/$DOSSIER_ID" \
  -H 'Content-Type: application/json' \
  -d '{"statut":"en_analyse"}'
echo ""

# 6. Lister les documents (devrait être vide)
echo ""
echo "6️⃣  Lister les documents (aucun pour l'instant)"
curl -s "$API_URL/api/dossiers/$DOSSIER_ID/documents"
echo ""

echo ""
echo "=========================================="
echo "✅ TESTS TERMINÉS"
echo "=========================================="
echo "Dossier ID: $DOSSIER_ID"
echo ""
echo "Pour uploader un document:"
echo "curl -X POST $API_URL/api/dossiers/$DOSSIER_ID/upload \\"
echo "  -F 'file=@votre_fichier.pdf'"
echo ""
