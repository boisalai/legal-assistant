"""
AgentOS - Système d'agents autonomes pour Notary Assistant.

Ce fichier configure AgentOS comme control plane pour orchestrer
les agents autonomes qui analysent les dossiers notariaux.

Architecture:
- AgentOS gère l'orchestration, les sessions, et le monitoring
- MCP Server activé pour communication standardisée
- Agents autonomes qui communiquent via MCP/A2A
- Interface web via AgentOS UI

Endpoints:
- http://localhost:7777 - UI AgentOS
- http://localhost:7777/mcp - MCP Server
- http://localhost:7777/docs - API documentation
- http://localhost:7777/config - Configuration
"""

import logging
import sys
from pathlib import Path

# Ajouter le répertoire parent au PYTHONPATH pour les imports
sys.path.insert(0, str(Path(__file__).parent))

from agno.agent import Agent
from agno.os import AgentOS

# Import du service LLM (MLX local ou fallback OpenAI)
import os
MLX_AVAILABLE = os.uname().sysname == "Darwin"  # True si macOS

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================================================
# Configuration des agents
# ============================================================================

def load_all_agents() -> list[Agent]:
    """
    Charge tous les agents spécialisés pour l'analyse notariale.

    Crée et configure les 5 agents autonomes:
    1. ExtracteurDocuments - Extraction données PDFs
    2. ClassificateurTransactions - Classification transactions
    3. VerificateurCoherence - Vérification cohérence
    4. GenerateurChecklist - Génération checklists
    5. HumanInLoopManager - Gestion validations humaines

    Returns:
        Liste des agents configurés
    """
    logger.info("📦 Chargement des agents spécialisés...")

    # Import des fonctions de création d'agents
    from agents import (
        create_extracteur_agent,
        create_classificateur_agent,
        create_verificateur_agent,
        create_generateur_agent,
        create_human_loop_agent,
    )

    # Déterminer le modèle à utiliser (MLX ou OpenAI)
    model = None
    if MLX_AVAILABLE:
        logger.info("📱 Utilisation MLX local pour tous les agents")
        try:
            from services.llm_service import get_llm_service
            llm_service = get_llm_service()
            model = llm_service.provider
        except Exception as e:
            logger.error(f"❌ Erreur MLX: {e}, fallback vers OpenAI")
            model = None

    if model is None:
        logger.info("☁️  Utilisation OpenAI pour tous les agents")
        from agno.models.openai import OpenAIChat
        openai_key = os.getenv("OPENAI_API_KEY", "sk-dummy-key-for-testing")
        if openai_key == "sk-dummy-key-for-testing":
            logger.warning("⚠️  OPENAI_API_KEY non définie, agents ne fonctionneront pas correctement")
        model = OpenAIChat(id="gpt-4o-mini", api_key=openai_key)

    # Créer tous les agents avec le même modèle
    agents = []

    try:
        agents.append(create_extracteur_agent(model))
        agents.append(create_classificateur_agent(model))
        agents.append(create_verificateur_agent(model))
        agents.append(create_generateur_agent(model))
        agents.append(create_human_loop_agent(model))

        logger.info(f"✅ {len(agents)} agents chargés avec succès:")
        for agent in agents:
            logger.info(f"   - {agent.name}: {agent.description}")

    except Exception as e:
        logger.error(f"❌ Erreur lors du chargement des agents: {e}")
        raise

    return agents


# ============================================================================
# Configuration AgentOS
# ============================================================================

def create_agent_os() -> AgentOS:
    """
    Crée et configure l'instance AgentOS.

    Features activées:
    - MCP Server pour communication standardisée
    - Multiple agents (à ajouter progressivement)
    - Session management
    - Memory et knowledge

    Returns:
        Instance AgentOS configurée
    """
    logger.info("🚀 Création de AgentOS...")

    # Charger tous les agents spécialisés
    agents = load_all_agents()

    # Créer AgentOS
    agent_os = AgentOS(
        id="notary-assistant-os",
        name="Notary Assistant",
        description="Système d'agents autonomes pour l'analyse de dossiers notariaux au Québec",
        agents=agents,

        # Activer MCP Server
        enable_mcp_server=True,
    )

    logger.info("✅ AgentOS créé avec succès")
    logger.info(f"   - Nombre d'agents: {len(agent_os.agents)}")
    logger.info(f"   - MCP Server: {'Activé' if agent_os.enable_mcp_server else 'Désactivé'}")

    return agent_os


# ============================================================================
# Point d'entrée
# ============================================================================

# Créer l'instance AgentOS
agent_os = create_agent_os()

# Obtenir l'application FastAPI
app = agent_os.get_app()


def main():
    """
    Lance AgentOS en mode standalone.

    Pour le développement, utilisez plutôt:
        uv run uvicorn agent_os:app --reload --port 7777
    """
    logger.info("=" * 70)
    logger.info("🏛️  NOTARY ASSISTANT - AgentOS")
    logger.info("=" * 70)
    logger.info("")
    logger.info("AgentOS Control Plane démarré sur:")
    logger.info("  - UI:            http://localhost:7777")
    logger.info("  - MCP Server:    http://localhost:7777/mcp")
    logger.info("  - API Docs:      http://localhost:7777/docs")
    logger.info("  - Config:        http://localhost:7777/config")
    logger.info("")
    logger.info("Agents disponibles:")
    for agent in agent_os.agents:
        logger.info(f"  - {agent.name}: {agent.description}")
    logger.info("")
    logger.info("=" * 70)

    # Lancer le serveur
    agent_os.serve(
        app="agent_os:app",
        host="0.0.0.0",
        port=7777,
        reload=True,
    )


if __name__ == "__main__":
    main()
