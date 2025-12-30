#!/bin/bash

# =====================================================
# Legal Assistant - Script d'arrêt
# =====================================================
# Arrête tous les services de développement
# Usage: ./dev-stop.sh

set -e

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${YELLOW}🛑 Arrêt de Legal Assistant...${NC}\n"

# 1. Arrêter les processus Python (backend)
echo -e "${BLUE}🐍 Arrêt du backend...${NC}"
pkill -f "python main.py" 2>/dev/null || echo -e "${YELLOW}   (pas de backend actif)${NC}"

# 2. Arrêter les processus Node (frontend)
echo -e "${CYAN}⚛️  Arrêt du frontend...${NC}"
pkill -f "next dev" 2>/dev/null || echo -e "${YELLOW}   (pas de frontend actif)${NC}"

# 3. Arrêter les processus MLX (si actifs)
echo -e "${CYAN}🤖 Arrêt des serveurs MLX...${NC}"
pkill -f "mlx_lm.server" 2>/dev/null || echo -e "${YELLOW}   (pas de serveur MLX actif)${NC}"

# 4. Arrêter SurrealDB (Docker)
echo -e "${GREEN}📊 Arrêt de SurrealDB...${NC}"
docker-compose down

echo -e "\n${GREEN}======================================${NC}"
echo -e "${GREEN}✅ Tous les services sont arrêtés !${NC}"
echo -e "${GREEN}======================================${NC}\n"
