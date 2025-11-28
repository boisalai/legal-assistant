"""
Agents autonomes pour Notary Assistant.

Ce module contient les 5 agents spécialisés qui composent le système
d'analyse de dossiers notariaux:

1. ExtracteurDocuments - Extraction de données des PDFs
2. ClassificateurTransactions - Classification des transactions
3. VerificateurCoherence - Vérification de cohérence et conformité
4. GenerateurChecklist - Génération de checklists pour notaires
5. HumanInLoopManager - Gestion des validations humaines

Chaque agent est autonome et peut être utilisé indépendamment via AgentOS.
"""

from agents.extracteur_agent import create_extracteur_agent
from agents.classificateur_agent import create_classificateur_agent
from agents.verificateur_agent import create_verificateur_agent
from agents.generateur_agent import create_generateur_agent
from agents.human_loop_agent import create_human_loop_agent

__all__ = [
    "create_extracteur_agent",
    "create_classificateur_agent",
    "create_verificateur_agent",
    "create_generateur_agent",
    "create_human_loop_agent",
]
