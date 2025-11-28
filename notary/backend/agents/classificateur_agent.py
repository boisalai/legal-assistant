"""
Agent Classificateur - Classification des transactions notariales.

Cet agent autonome est responsable de:
- Identifier le type de transaction (vente, hypothèque, testament, etc.)
- Déterminer le type de propriété (résidentielle, commerciale, terrain)
- Identifier les documents présents dans le dossier
- Signaler les documents manquants habituellement requis
"""

import logging
import os
from typing import Optional

from agno.agent import Agent

logger = logging.getLogger(__name__)


def create_classificateur_agent(model: Optional[object] = None) -> Agent:
    """
    Crée l'agent autonome de classification de transactions.

    Cet agent:
    - Identifie le type de transaction
    - Détermine le type de propriété
    - Liste les documents présents et manquants

    Args:
        model: Modèle LLM à utiliser (si None, utilise MLX ou OpenAI selon plateforme)

    Returns:
        Agent configuré pour la classification
    """
    instructions = [
        "Tu es un expert en droit notarial du Québec et en classification de transactions immobilières.",
        "",
        "Ta mission est de classifier avec précision les transactions notariales.",
        "",
        "Analyse requise:",
        "1. TYPE DE TRANSACTION:",
        "   - Vente immobilière (promesse d'achat-vente)",
        "   - Achat (offre d'achat)",
        "   - Hypothèque / Refinancement",
        "   - Testament",
        "   - Donation",
        "   - Servitude",
        "   - Autre (préciser)",
        "",
        "2. TYPE DE PROPRIÉTÉ:",
        "   - Résidentielle (unifamiliale, duplex, triplex, etc.)",
        "   - Commerciale",
        "   - Copropriété (condo)",
        "   - Terrain vacant",
        "   - Mixte (résidentiel-commercial)",
        "",
        "3. DOCUMENTS IDENTIFIÉS:",
        "   Analyse les documents fournis et identifie leur type:",
        "   - Promesse d'achat-vente",
        "   - Offre d'achat",
        "   - Titre de propriété",
        "   - Certificat de localisation",
        "   - Déclaration du vendeur",
        "   - Rapport d'inspection",
        "   - Etc.",
        "",
        "4. DOCUMENTS MANQUANTS:",
        "   Selon le type de transaction, identifie les documents",
        "   habituellement requis mais absents:",
        "   ",
        "   Pour une VENTE:",
        "   - Titre de propriété",
        "   - Certificat de localisation (moins de 10 ans)",
        "   - Déclaration du vendeur",
        "   - Autorisation municipale (si applicable)",
        "   - Quittance de taxes",
        "   - Documents de copropriété (si condo)",
        "",
        "   Pour une HYPOTHÈQUE:",
        "   - Acte d'hypothèque",
        "   - Évaluation de la propriété",
        "   - Preuve d'assurance",
        "",
        "Connaissance juridique:",
        "- Code civil du Québec",
        "- Loi sur le courtage immobilier",
        "- Règlements municipaux courants",
        "- Pratiques notariales standard au Québec",
        "",
        "Format de sortie attendu:",
        "{",
        '  "type_transaction": "vente|achat|hypotheque|testament|donation|servitude|autre",',
        '  "sous_type": "description spécifique si nécessaire",',
        '  "type_propriete": "residentielle|commerciale|terrain|copropriete|mixte",',
        '  "sous_type_propriete": "unifamiliale|duplex|triplex|...",',
        '  "documents_identifies": [',
        '    {',
        '      "type": "promesse_achat_vente",',
        '      "nom_fichier": "...",',
        '      "date": "...",',
        '      "present": true',
        '    }',
        '  ],',
        '  "documents_manquants": [',
        '    {',
        '      "type": "certificat_localisation",',
        '      "requis": true,',
        '      "raison": "Obligatoire pour vente immobilière",',
        '      "delai_obtention": "2-4 semaines"',
        '    }',
        '  ],',
        '  "niveau_urgence": "bas|moyen|eleve",',
        '  "notes": "Commentaires additionnels"',
        "}",
    ]

    # Déterminer le modèle à utiliser
    if model is None:
        MLX_AVAILABLE = os.uname().sysname == "Darwin"

        if MLX_AVAILABLE:
            logger.info("📱 Agent Classificateur: utilisation MLX local")
            from services.llm_service import get_llm_service
            llm_service = get_llm_service()
            model = llm_service.provider
        else:
            logger.info("☁️  Agent Classificateur: utilisation OpenAI")
            from agno.models.openai import OpenAIChat
            openai_key = os.getenv("OPENAI_API_KEY", "sk-dummy-key")
            model = OpenAIChat(id="gpt-4o-mini", api_key=openai_key)

    # Créer l'agent (pas de tools externes nécessaires)
    agent = Agent(
        name="ClassificateurTransactions",
        model=model,
        description="Expert en droit notarial québécois et classification de transactions",
        instructions=instructions,
        tools=[],  # Cet agent utilise uniquement sa connaissance du LLM
        markdown=False,
    )

    logger.info("✅ Agent Classificateur créé")
    return agent


if __name__ == "__main__":
    # Test de création de l'agent
    logging.basicConfig(level=logging.INFO)
    agent = create_classificateur_agent()
    print(f"Agent créé: {agent.name}")
    print(f"Description: {agent.description}")
