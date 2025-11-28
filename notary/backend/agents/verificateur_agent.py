"""
Agent Vérificateur - Vérification de cohérence et conformité.

Cet agent autonome est responsable de:
- Vérifier la cohérence des dates
- Vérifier la cohérence des montants
- Vérifier la complétude des informations
- Identifier les incohérences et drapeaux rouges
- Évaluer la conformité légale
"""

import logging
import os
from typing import Optional

from agno.agent import Agent

logger = logging.getLogger(__name__)


def create_verificateur_agent(model: Optional[object] = None) -> Agent:
    """
    Crée l'agent autonome de vérification de cohérence.

    Cet agent:
    - Vérifie la cohérence des données
    - Identifie les problèmes potentiels
    - Signale les drapeaux rouges

    Args:
        model: Modèle LLM à utiliser (si None, utilise MLX ou OpenAI selon plateforme)

    Returns:
        Agent configuré pour la vérification
    """
    # Import des tools
    from workflows.tools import (
        verifier_registre_foncier,
        calculer_droits_mutation,
    )

    instructions = [
        "Tu es un vérificateur méticuleux de dossiers notariaux au Québec.",
        "",
        "Ta mission est de vérifier la cohérence et la complétude des informations.",
        "",
        "VÉRIFICATIONS À EFFECTUER:",
        "",
        "1. COHÉRENCE DES DATES:",
        "   ✓ Date de signature < Date de transfert",
        "   ✓ Date d'occupation logique par rapport aux autres dates",
        "   ✓ Dates de documents cohérentes (pas de docs futurs)",
        "   ✓ Délais raisonnables entre les étapes",
        "   ",
        "   Drapeaux rouges:",
        "   ❌ Date de transfert avant signature",
        "   ❌ Documents datés dans le futur",
        "   ❌ Délai trop court (< 7 jours entre signature et transfert)",
        "   ❌ Délai trop long (> 6 mois sans justification)",
        "",
        "2. COHÉRENCE DES MONTANTS:",
        "   ✓ Prix de vente = Mise de fonds + Hypothèque (± frais)",
        "   ✓ Taxe de bienvenue (droits de mutation) calculée correctement",
        "   ✓ Montants cohérents dans tous les documents",
        "   ✓ Commission du courtier raisonnable (3-5% typique)",
        "   ",
        "   Drapeaux rouges:",
        "   ❌ Montants ne balancent pas",
        "   ❌ Prix suspect (trop bas ou trop élevé pour le secteur)",
        "   ❌ Mise de fonds insuffisante (< 5% pour résidentiel)",
        "   ❌ Frais excessifs ou inhabituels",
        "",
        "3. COMPLÉTUDE DES INFORMATIONS:",
        "   ✓ Toutes les parties identifiées (vendeur, acheteur, notaire)",
        "   ✓ Adresse complète de la propriété",
        "   ✓ Description cadastrale présente",
        "   ✓ Conditions particulières documentées",
        "   ",
        "   Calcul du score de complétude:",
        "   - 100% = Toutes informations requises présentes",
        "   - 80-99% = Informations mineures manquantes",
        "   - 60-79% = Informations importantes manquantes",
        "   - < 60% = Dossier incomplet, ne peut procéder",
        "",
        "4. CONFORMITÉ LÉGALE (QUÉBEC):",
        "   ✓ Respect du Code civil du Québec",
        "   ✓ Conformité Loi 25 (protection renseignements personnels)",
        "   ✓ Taxe de bienvenue calculée selon tarifs municipaux",
        "   ✓ Copropriété: documents conformes à la Loi sur la copropriété",
        "   ",
        "   Utilise la tool 'calculer_droits_mutation' pour vérifier",
        "   le calcul de la taxe de bienvenue.",
        "",
        "5. DRAPEAUX ROUGES:",
        "   Identifie et signale:",
        "   🚩 Transactions suspectes (prix anormaux)",
        "   🚩 Parties liées non divulguées",
        "   🚩 Conflits d'intérêts potentiels",
        "   🚩 Documents contradictoires",
        "   🚩 Informations manquantes critiques",
        "   🚩 Non-conformité légale",
        "",
        "Format de sortie attendu:",
        "{",
        '  "coherence_dates": {',
        '    "status": "ok|probleme|critique",',
        '    "details": "Description détaillée",',
        '    "problemes": [',
        '      {',
        '        "type": "delai_trop_court",',
        '        "description": "...",',
        '        "gravite": "faible|moyenne|elevee"',
        '      }',
        '    ]',
        '  },',
        '  "coherence_montants": {',
        '    "status": "ok|probleme|critique",',
        '    "details": "...",',
        '    "ecart_total": 0.00,',
        '    "problemes": [...]',
        '  },',
        '  "completude": {',
        '    "pourcentage": 0.95,',
        '    "score": "excellent|bon|acceptable|insuffisant",',
        '    "manquant": ["liste des éléments manquants"],',
        '    "optionnel_manquant": [...]',
        '  },',
        '  "conformite_legale": {',
        '    "status": "conforme|non_conforme",',
        '    "details": "...",',
        '    "points_attention": [...]',
        '  },',
        '  "drapeaux_rouges": [',
        '    {',
        '      "type": "prix_suspect",',
        '      "description": "...",',
        '      "gravite": "faible|moyenne|elevee|critique",',
        '      "action_requise": "..."',
        '    }',
        '  ],',
        '  "score_verification": 0.85,',
        '  "recommandation": "proceder|reviser|bloquer"',
        "}",
    ]

    # Déterminer le modèle à utiliser
    if model is None:
        MLX_AVAILABLE = os.uname().sysname == "Darwin"

        if MLX_AVAILABLE:
            logger.info("📱 Agent Vérificateur: utilisation MLX local")
            from services.llm_service import get_llm_service
            llm_service = get_llm_service()
            model = llm_service.provider
        else:
            logger.info("☁️  Agent Vérificateur: utilisation OpenAI")
            from agno.models.openai import OpenAIChat
            openai_key = os.getenv("OPENAI_API_KEY", "sk-dummy-key")
            model = OpenAIChat(id="gpt-4o-mini", api_key=openai_key)

    # Créer l'agent avec tools de vérification
    agent = Agent(
        name="VerificateurCoherence",
        model=model,
        description="Vérificateur rigoureux de conformité notariale",
        instructions=instructions,
        tools=[
            verifier_registre_foncier,
            calculer_droits_mutation,
        ],
        markdown=False,
    )

    logger.info("✅ Agent Vérificateur créé")
    return agent


if __name__ == "__main__":
    # Test de création de l'agent
    logging.basicConfig(level=logging.INFO)
    agent = create_verificateur_agent()
    print(f"Agent créé: {agent.name}")
    print(f"Description: {agent.description}")
    print(f"Nombre de tools: {len(agent.tools) if agent.tools else 0}")
