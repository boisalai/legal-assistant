#!/bin/bash
# Script de test de l'API via cURL

API_URL="http://localhost:8000"

echo "=========================================="
echo "TEST API Notary Assistant"
echo "=========================================="
echo ""

# 1. Santé de l'API
echo "1. Health check..."
curl -s "$API_URL/health"
echo -e "\n"

# 2. Liste des dossiers
echo "2. Lister les dossiers..."
curl -s "$API_URL/api/dossiers"
echo -e "\n"

# 3. Créer un dossier
echo "3. Créer un nouveau dossier..."
RESPONSE=$(curl -s -X POST "$API_URL/api/dossiers" \
  -H "Content-Type: application/json" \
  -d '{"nom_dossier":"Test API - Vente Dupont","user_id":"user:test_notaire","type_transaction":"vente"}')

echo "$RESPONSE"
DOSSIER_ID=$(echo "$RESPONSE" | grep -o '"id":"[^"]*"' | cut -d'"' -f4)
echo -e "\nDossier créé: $DOSSIER_ID\n"

# 4. Récupérer le dossier
if [ -n "$DOSSIER_ID" ]; then
    echo "4. Récupérer le dossier $DOSSIER_ID..."
    curl -s "$API_URL/api/dossiers/$DOSSIER_ID"
    echo -e "\n"
fi

echo "=========================================="
echo "Tests terminés"
echo "=========================================="
