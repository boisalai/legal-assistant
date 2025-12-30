#!/bin/bash

# =====================================================
# Legal Assistant - Script de développement
# =====================================================
# Lance SurrealDB (Docker), Backend et Frontend en parallèle
# Usage: ./dev.sh
# Arrêt: CTRL+C

set -e

# Couleurs pour les logs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# PID des processus
BACKEND_PID=""
FRONTEND_PID=""

# Fonction de nettoyage
cleanup() {
    echo -e "\n${YELLOW}🛑 Arrêt des services...${NC}"

    # Arrêter le frontend
    if [ ! -z "$FRONTEND_PID" ]; then
        echo -e "${CYAN}   Arrêt du frontend (PID: $FRONTEND_PID)${NC}"
        kill $FRONTEND_PID 2>/dev/null || true
    fi

    # Arrêter le backend
    if [ ! -z "$BACKEND_PID" ]; then
        echo -e "${BLUE}   Arrêt du backend (PID: $BACKEND_PID)${NC}"
        kill $BACKEND_PID 2>/dev/null || true
    fi

    # Arrêter SurrealDB
    echo -e "${GREEN}   Arrêt de SurrealDB${NC}"
    docker-compose down

    echo -e "${GREEN}✅ Tous les services sont arrêtés${NC}"
    exit 0
}

# Capturer CTRL+C
trap cleanup SIGINT SIGTERM

echo -e "${GREEN}🚀 Démarrage de Legal Assistant...${NC}\n"

# 1. Démarrer SurrealDB
echo -e "${GREEN}📊 Démarrage de SurrealDB (Docker)...${NC}"
docker-compose up -d surrealdb

# Attendre que SurrealDB soit prêt
echo -e "${YELLOW}⏳ Attente de SurrealDB...${NC}"
for i in {1..30}; do
    if nc -z localhost 8002 2>/dev/null; then
        echo -e "${GREEN}✅ SurrealDB est prêt${NC}\n"
        break
    fi
    if [ $i -eq 30 ]; then
        echo -e "${RED}❌ Timeout: SurrealDB n'a pas démarré${NC}"
        echo -e "${YELLOW}Logs Docker:${NC}"
        docker logs legal-assistant-surrealdb --tail 20
        cleanup
    fi
    sleep 1
done

# 2. Démarrer le backend
echo -e "${BLUE}🐍 Démarrage du backend (port 8000)...${NC}"
cd backend
uv run python main.py > ../logs/backend.log 2>&1 &
BACKEND_PID=$!
cd ..
echo -e "${BLUE}   Backend PID: $BACKEND_PID${NC}\n"

# Attendre que le backend soit prêt
echo -e "${YELLOW}⏳ Attente du backend...${NC}"
sleep 3
if ps -p $BACKEND_PID > /dev/null; then
    echo -e "${GREEN}✅ Backend démarré${NC}\n"
else
    echo -e "${RED}❌ Le backend n'a pas démarré. Vérifiez logs/backend.log${NC}"
    cleanup
fi

# 3. Démarrer le frontend
echo -e "${CYAN}⚛️  Démarrage du frontend (port 3001)...${NC}"
cd frontend
npm run dev -- -p 3001 > ../logs/frontend.log 2>&1 &
FRONTEND_PID=$!
cd ..
echo -e "${CYAN}   Frontend PID: $FRONTEND_PID${NC}\n"

# Attendre que le frontend soit prêt
echo -e "${YELLOW}⏳ Attente du frontend...${NC}"
sleep 5
if ps -p $FRONTEND_PID > /dev/null; then
    echo -e "${GREEN}✅ Frontend démarré${NC}\n"
else
    echo -e "${RED}❌ Le frontend n'a pas démarré. Vérifiez logs/frontend.log${NC}"
    cleanup
fi

# Afficher les informations
echo -e "${GREEN}======================================${NC}"
echo -e "${GREEN}✅ Tous les services sont démarrés !${NC}"
echo -e "${GREEN}======================================${NC}\n"
echo -e "${CYAN}Frontend:${NC}    http://localhost:3001"
echo -e "${BLUE}Backend:${NC}     http://localhost:8000"
echo -e "${GREEN}SurrealDB:${NC}   http://localhost:8002\n"
echo -e "${YELLOW}Logs:${NC}"
echo -e "  - Backend:  tail -f logs/backend.log"
echo -e "  - Frontend: tail -f logs/frontend.log\n"
echo -e "${YELLOW}Appuyez sur CTRL+C pour arrêter tous les services${NC}\n"

# Garder le script actif
wait
