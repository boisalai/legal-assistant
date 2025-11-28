"""
Agent Extracteur - Extraction de données des documents PDF.

Cet agent autonome est responsable de:
- Lire les documents PDF
- Extraire les informations structurées (montants, dates, noms, adresses)
- Utiliser des tools spécialisées pour chaque type de donnée
- Retourner un JSON avec toutes les données extraites
"""

import logging
import os
from typing import Optional

from agno.agent import Agent

logger = logging.getLogger(__name__)


def create_extracteur_agent(model: Optional[object] = None) -> Agent:
    """
    Crée l'agent autonome d'extraction de données.

    Cet agent:
    - Lit les documents PDF
    - Extrait les informations structurées
    - Utilise des tools spécialisées pour chaque type de donnée

    Args:
        model: Modèle LLM à utiliser (si None, utilise MLX ou OpenAI selon plateforme)

    Returns:
        Agent configuré pour l'extraction
    """
    # Import des tools
    from workflows.tools import (
        extraire_texte_pdf,
        extraire_montants,
        extraire_dates,
        extraire_noms,
        extraire_adresses,
    )

    # Instructions détaillées pour l'agent
    instructions = [
        "Tu es un expert en lecture et analyse de documents notariaux du Québec.",
        "",
        "Ta mission est d'extraire les informations suivantes avec précision:",
        "- Adresses de propriété (numéro civique, rue, ville, code postal)",
        "- Noms des parties (vendeur, acheteur, notaire) avec titres (M./Mme/Me)",
        "- Montants en dollars canadiens (prix de vente, mise de fonds, taxes)",
        "- Dates importantes (signature, transfert, occupation)",
        "- Conditions particulières et clauses spéciales",
        "",
        "Processus d'extraction:",
        "1. Utilise la tool 'extraire_texte_pdf' pour lire le contenu du PDF",
        "2. Utilise 'extraire_montants' pour identifier tous les montants ($)",
        "3. Utilise 'extraire_dates' pour identifier toutes les dates",
        "4. Utilise 'extraire_noms' pour identifier les personnes (M./Mme/Me)",
        "5. Utilise 'extraire_adresses' pour identifier les adresses québécoises",
        "",
        "Règles importantes:",
        "- Si une information est absente ou illisible, indique-le clairement",
        "- Retourne TOUJOURS un JSON valide avec toutes les données extraites",
        "- Sois précis dans les montants (ex: 325,000.00$ pas 325k$)",
        "- Respecte les formats de dates québécois (JJ/MM/AAAA)",
        "- Identifie clairement le rôle de chaque personne",
        "",
        "Format de sortie attendu:",
        "{",
        '  "documents": [',
        '    {',
        '      "nom_fichier": "...",',
        '      "texte_complet": "...",',
        '      "montants": [{',
        '        "valeur": 325000.00,',
        '        "devise": "CAD",',
        '        "contexte": "Prix de vente"',
        '      }],',
        '      "dates": [{',
        '        "date": "2024-03-15",',
        '        "type": "signature",',
        '        "contexte": "Promesse d\'achat"',
        '      }],',
        '      "noms": [{',
        '        "nom_complet": "Jean Tremblay",',
        '        "titre": "M.",',
        '        "role": "acheteur"',
        '      }],',
        '      "adresses": [{',
        '        "adresse_complete": "123 Rue Principale, Montréal, QC H1A 1A1",',
        '        "type": "propriété"',
        '      }]',
        '    }',
        '  ],',
        '  "score_confiance": 0.95,',
        '  "alertes": []',
        "}",
    ]

    # Déterminer le modèle à utiliser
    if model is None:
        MLX_AVAILABLE = os.uname().sysname == "Darwin"

        if MLX_AVAILABLE:
            logger.info("📱 Agent Extracteur: utilisation MLX local")
            from services.llm_service import get_llm_service
            llm_service = get_llm_service()
            model = llm_service.provider
        else:
            logger.info("☁️  Agent Extracteur: utilisation OpenAI")
            from agno.models.openai import OpenAIChat
            openai_key = os.getenv("OPENAI_API_KEY", "sk-dummy-key")
            model = OpenAIChat(id="gpt-4o-mini", api_key=openai_key)

    # Créer l'agent
    agent = Agent(
        name="ExtracteurDocuments",
        model=model,
        description="Expert en extraction de données de documents notariaux québécois",
        instructions=instructions,
        tools=[
            extraire_texte_pdf,
            extraire_montants,
            extraire_dates,
            extraire_noms,
            extraire_adresses,
        ],
        markdown=False,
    )

    logger.info("✅ Agent Extracteur créé")
    return agent


if __name__ == "__main__":
    # Test de création de l'agent
    logging.basicConfig(level=logging.INFO)
    agent = create_extracteur_agent()
    print(f"Agent créé: {agent.name}")
    print(f"Description: {agent.description}")
    print(f"Nombre de tools: {len(agent.tools) if agent.tools else 0}")
