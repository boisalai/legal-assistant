#!/bin/bash
# =========================================================
# Test End-to-End Notary Assistant
# =========================================================
# Ce script teste le flux complet:
# 1. Verifier les services
# 2. Creer un dossier
# 3. Telecharger un PDF de test
# 4. Lancer l'analyse
# 5. Recuperer la checklist
# =========================================================

set -e

# Determiner le repertoire du script (racine du projet)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/backend"

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

BACKEND_URL="http://localhost:8000"
FRONTEND_URL="http://localhost:3001"

echo ""
echo "=========================================="
echo "  Test End-to-End Notary Assistant"
echo "=========================================="
echo ""

# =========================================================
# Etape 0: Verifier les services
# =========================================================
echo -e "${YELLOW}Etape 0: Verification des services...${NC}"

# Backend
if curl -s "$BACKEND_URL/health" > /dev/null 2>&1; then
    echo -e "${GREEN}  [OK] Backend FastAPI sur port 8000${NC}"
else
    echo -e "${RED}  [ERREUR] Backend non disponible sur $BACKEND_URL${NC}"
    echo "  Demarrez le backend: cd backend && uv run python main.py"
    exit 1
fi

# Frontend proxy
if curl -s "$FRONTEND_URL/api/dossiers" > /dev/null 2>&1; then
    echo -e "${GREEN}  [OK] Frontend Next.js sur port 3001 (proxy OK)${NC}"
else
    echo -e "${YELLOW}  [WARN] Frontend non disponible ou proxy non configure${NC}"
    echo "  Le test continuera avec l'API directe"
fi

echo ""

# =========================================================
# Etape 1: Creer un dossier
# =========================================================
echo -e "${YELLOW}Etape 1: Creation d'un dossier de test...${NC}"

DOSSIER_RESPONSE=$(curl -s -X POST "$BACKEND_URL/api/dossiers" \
    -H "Content-Type: application/json" \
    -d '{
        "nom_dossier": "Test E2E - Vente 123 Rue Test",
        "type_transaction": "vente",
        "user_id": "user:test_notaire"
    }')

# Extraire l'ID du dossier
DOSSIER_ID=$(echo "$DOSSIER_RESPONSE" | grep -o '"id":"[^"]*"' | head -1 | cut -d'"' -f4)

if [ -z "$DOSSIER_ID" ]; then
    echo -e "${RED}  [ERREUR] Impossible de creer le dossier${NC}"
    echo "  Reponse: $DOSSIER_RESPONSE"
    exit 1
fi

echo -e "${GREEN}  [OK] Dossier cree: $DOSSIER_ID${NC}"
echo ""

# =========================================================
# Etape 2: Generer et telecharger un PDF de test
# =========================================================
echo -e "${YELLOW}Etape 2: Generation et upload d'un PDF de test...${NC}"

# Creer un PDF de test simple avec Python
cd "$BACKEND_DIR"

uv run python << 'EOF'
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

# Creer un PDF de test
c = canvas.Canvas("/tmp/test_document.pdf", pagesize=letter)
c.setFont("Helvetica-Bold", 24)
c.drawString(100, 750, "PROMESSE D'ACHAT")

c.setFont("Helvetica", 12)
c.drawString(100, 700, "Date: 15 novembre 2025")
c.drawString(100, 680, "")
c.drawString(100, 660, "VENDEUR: Jean Tremblay")
c.drawString(100, 640, "ACHETEUR: Marie Gagnon")
c.drawString(100, 620, "")
c.drawString(100, 600, "PROPRIETE:")
c.drawString(100, 580, "123 Rue de l'Exemple")
c.drawString(100, 560, "Montreal, QC H2X 1A1")
c.drawString(100, 540, "")
c.drawString(100, 520, "PRIX DE VENTE: 450 000,00 $")
c.drawString(100, 500, "DEPOT: 25 000,00 $")
c.drawString(100, 480, "")
c.drawString(100, 460, "DATE DE SIGNATURE: 1er decembre 2025")
c.drawString(100, 440, "DATE DE POSSESSION: 15 janvier 2026")
c.drawString(100, 420, "")
c.drawString(100, 400, "CONDITIONS:")
c.drawString(100, 380, "- Inspection sous 7 jours")
c.drawString(100, 360, "- Financement approuve d'ici le 1er decembre 2025")
c.drawString(100, 340, "- Certificat de localisation a jour")

c.save()
print("PDF de test cree: /tmp/test_document.pdf")
EOF

# Upload le PDF
UPLOAD_RESPONSE=$(curl -s -X POST "$BACKEND_URL/api/dossiers/$DOSSIER_ID/upload" \
    -F "file=@/tmp/test_document.pdf")

DOCUMENT_ID=$(echo "$UPLOAD_RESPONSE" | grep -o '"id":"[^"]*"' | head -1 | cut -d'"' -f4)

if [ -z "$DOCUMENT_ID" ]; then
    echo -e "${RED}  [ERREUR] Impossible d'uploader le document${NC}"
    echo "  Reponse: $UPLOAD_RESPONSE"
    exit 1
fi

echo -e "${GREEN}  [OK] Document uploade: $DOCUMENT_ID${NC}"
echo ""

# =========================================================
# Etape 3: Lancer l'analyse
# =========================================================
echo -e "${YELLOW}Etape 3: Lancement de l'analyse...${NC}"
echo "  (cela peut prendre quelques minutes selon le modele LLM)"

ANALYSE_RESPONSE=$(curl -s -X POST "$BACKEND_URL/api/dossiers/$DOSSIER_ID/analyser-stream")

if echo "$ANALYSE_RESPONSE" | grep -q '"message":"Analysis started"'; then
    echo -e "${GREEN}  [OK] Analyse demarree${NC}"
else
    echo -e "${RED}  [ERREUR] Impossible de demarrer l'analyse${NC}"
    echo "  Reponse: $ANALYSE_RESPONSE"
    exit 1
fi

# Attendre que l'analyse se termine (polling)
echo "  Attente de la fin de l'analyse..."
MAX_WAIT=180  # 3 minutes max
WAITED=0

while [ $WAITED -lt $MAX_WAIT ]; do
    sleep 5
    WAITED=$((WAITED + 5))

    DOSSIER_STATUS=$(curl -s "$BACKEND_URL/api/dossiers/$DOSSIER_ID" | grep -o '"statut":"[^"]*"' | cut -d'"' -f4)

    if [ "$DOSSIER_STATUS" = "complete" ] || [ "$DOSSIER_STATUS" = "analyse_complete" ]; then
        echo -e "${GREEN}  [OK] Analyse terminee (${WAITED}s)${NC}"
        break
    elif [ "$DOSSIER_STATUS" = "erreur" ]; then
        echo -e "${RED}  [ERREUR] L'analyse a echoue${NC}"
        exit 1
    else
        echo "  ... en cours (${WAITED}s) - statut: $DOSSIER_STATUS"
    fi
done

if [ $WAITED -ge $MAX_WAIT ]; then
    echo -e "${YELLOW}  [TIMEOUT] L'analyse n'est pas terminee apres ${MAX_WAIT}s${NC}"
    echo "  Verifiez les logs du backend pour plus de details"
fi

echo ""

# =========================================================
# Etape 4: Recuperer la checklist
# =========================================================
echo -e "${YELLOW}Etape 4: Recuperation de la checklist...${NC}"

CHECKLIST_RESPONSE=$(curl -s "$BACKEND_URL/api/dossiers/$DOSSIER_ID/checklist")

if echo "$CHECKLIST_RESPONSE" | grep -q '"items"'; then
    SCORE=$(echo "$CHECKLIST_RESPONSE" | grep -o '"score_confiance":[0-9.]*' | cut -d':' -f2)
    ITEMS_COUNT=$(echo "$CHECKLIST_RESPONSE" | grep -o '"titre"' | wc -l)

    echo -e "${GREEN}  [OK] Checklist recuperee${NC}"
    echo "  - Score de confiance: ${SCORE:-N/A}"
    echo "  - Nombre d'items: $ITEMS_COUNT"
else
    echo -e "${YELLOW}  [WARN] Checklist non disponible ou incomplete${NC}"
    echo "  Reponse: ${CHECKLIST_RESPONSE:0:200}..."
fi

echo ""

# =========================================================
# Etape 5: Nettoyage (optionnel)
# =========================================================
echo -e "${YELLOW}Etape 5: Nettoyage...${NC}"

# Supprimer le dossier de test
DELETE_RESPONSE=$(curl -s -X DELETE "$BACKEND_URL/api/dossiers/$DOSSIER_ID" -w "%{http_code}")

if [ "$DELETE_RESPONSE" = "204" ]; then
    echo -e "${GREEN}  [OK] Dossier de test supprime${NC}"
else
    echo -e "${YELLOW}  [INFO] Dossier conserve pour inspection manuelle${NC}"
fi

# Supprimer le PDF temporaire
rm -f /tmp/test_document.pdf

echo ""
echo "=========================================="
echo -e "${GREEN}  TEST END-TO-END TERMINE${NC}"
echo "=========================================="
echo ""
echo "Resume:"
echo "  - Dossier cree: OK"
echo "  - Document uploade: OK"
echo "  - Analyse lancee: OK"
echo "  - Checklist generee: ${SCORE:-En attente}"
echo ""
echo "Pour tester manuellement, ouvrez:"
echo "  http://localhost:3001/dashboard"
echo ""
