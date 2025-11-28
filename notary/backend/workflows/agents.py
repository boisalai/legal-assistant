"""
Agents Agno pour l'analyse de dossiers notariaux.

Ce module définit les agents spécialisés utilisés par le workflow d'analyse:
- Agent Extracteur: Extraction de données des PDFs
- Agent Classificateur: Classification du type de transaction
- Agent Vérificateur: Vérification de cohérence
- Agent Générateur: Génération de checklist

Chaque agent est configuré avec son propre rôle, instructions et tools.
"""

import logging
from typing import Optional

from agno.agent import Agent, Toolkit
from agno.db.sqlite import SqliteDb

from services.agno_mlx_model import create_mlx_model
from workflows.tools import (
    extraire_texte_pdf,
    extraire_montants,
    extraire_dates,
    extraire_noms,
    extraire_adresses,
    verifier_registre_foncier,
    calculer_droits_mutation,
)

logger = logging.getLogger(__name__)


# ============================================================================
# Configuration du modèle MLX
# ============================================================================

def get_mlx_model():
    """
    Retourne le modèle MLX configuré pour les agents.

    Returns:
        Instance de AgnoMLXModel
    """
    return create_mlx_model(
        model_name="mlx-community/Phi-3-mini-4k-instruct-4bit",
        max_tokens=2000,
        temperature=0.7
    )


# ============================================================================
# Agent Extracteur
# ============================================================================

def create_agent_extracteur(
    model: Optional[object] = None,
    db: Optional[SqliteDb] = None
) -> Agent:
    """
    Crée l'agent responsable de l'extraction de données des PDFs.

    Cet agent:
    - Lit les documents PDF
    - Extrait les informations structurées
    - Utilise des tools spécialisées pour chaque type de donnée

    Args:
        model: Modèle LLM à utiliser (défaut: MLX)
        db: Base de données pour stocker l'historique

    Returns:
        Agent configuré
    """
    if model is None:
        model = get_mlx_model()

    return Agent(
        name="ExtracteurDocuments",
        model=model,
        db=db,
        description="Expert en extraction de données de documents notariaux québécois",
        instructions=[
            "Tu es un expert en lecture et analyse de documents notariaux du Québec",
            "Tu extrais les informations suivantes avec précision:",
            "- Adresses de propriété",
            "- Noms des parties (vendeur, acheteur, notaire)",
            "- Montants (prix de vente, mise de fonds, taxes)",
            "- Dates (signature, transfert, occupation)",
            "- Conditions particulières",
            "",
            "Utilise les tools disponibles pour extraire chaque type d'information",
            "Si une information est absente ou illisible, indique-le clairement",
            "Retourne toujours un JSON valide avec toutes les données extraites",
        ],
        tools=[
            extraire_texte_pdf,
            extraire_montants,
            extraire_dates,
            extraire_noms,
            extraire_adresses,
        ],
        markdown=False,
        add_history_to_context=True,
        debug_mode=False,
    )


# ============================================================================
# Agent Classificateur
# ============================================================================

def create_agent_classificateur(
    model: Optional[object] = None,
    db: Optional[SqliteDb] = None
) -> Agent:
    """
    Crée l'agent responsable de la classification du type de transaction.

    Identifie:
    - Type de transaction (vente, hypothèque, testament, etc.)
    - Type de propriété (résidentielle, commerciale, terrain)
    - Documents présents vs manquants

    Args:
        model: Modèle LLM à utiliser (défaut: MLX)
        db: Base de données pour stocker l'historique

    Returns:
        Agent configuré
    """
    if model is None:
        model = get_mlx_model()

    return Agent(
        name="ClassificateurTransactions",
        model=model,
        db=db,
        description="Expert en droit notarial québécois et classification de transactions",
        instructions=[
            "Tu es un expert en droit notarial du Québec",
            "À partir des documents fournis, tu identifies:",
            "- Le type de transaction (vente, achat, hypothèque, testament, etc.)",
            "- Le type de propriété (résidentielle, commerciale, copropriété, terrain)",
            "- Les documents présents dans le dossier",
            "- Les documents manquants habituellement requis",
            "",
            "Tu connais la législation québécoise (Code civil du Québec)",
            "Retourne un JSON avec la classification complète",
            "",
            "Format de réponse attendu:",
            "{",
            '  "type_transaction": "vente|achat|hypotheque|testament|autre",',
            '  "type_propriete": "residentielle|commerciale|terrain|copropriete",',
            '  "documents_identifies": ["liste des types de docs présents"],',
            '  "documents_manquants": ["liste des docs typiquement requis mais absents"]',
            "}",
        ],
        tools=[],
        markdown=False,
        add_history_to_context=True,
        debug_mode=False,
    )


# ============================================================================
# Agent Vérificateur
# ============================================================================

def create_agent_verificateur(
    model: Optional[object] = None,
    db: Optional[SqliteDb] = None
) -> Agent:
    """
    Crée l'agent responsable de la vérification de cohérence.

    Vérifie:
    - Cohérence des dates
    - Cohérence des montants
    - Présence de toutes les informations requises
    - Conformité légale (Québec)

    Args:
        model: Modèle LLM à utiliser (défaut: MLX)
        db: Base de données pour stocker l'historique

    Returns:
        Agent configuré
    """
    if model is None:
        model = get_mlx_model()

    return Agent(
        name="VerificateurCoherence",
        model=model,
        db=db,
        description="Vérificateur rigoureux de conformité notariale",
        instructions=[
            "Tu es un vérificateur méticuleux de dossiers notariaux",
            "Tu vérifies la cohérence et la complétude des informations:",
            "- Les dates sont-elles logiques? (signature avant transfert, etc.)",
            "- Les montants sont-ils cohérents? (prix = mise de fonds + hypothèque)",
            "- Toutes les parties sont-elles identifiées?",
            "- Y a-t-il des incohérences ou contradictions?",
            "- Quelles informations sont manquantes?",
            "",
            "Tu identifies les problèmes potentiels et les drapeaux rouges",
            "Retourne un JSON avec les vérifications et les alertes",
            "",
            "Format de réponse attendu:",
            "{",
            '  "coherence_dates": {"status": "ok|probleme", "details": "..."},',
            '  "coherence_montants": {"status": "ok|probleme", "details": "..."},',
            '  "completude": {"pourcentage": 0.0-1.0, "manquant": [...]},',
            '  "alertes": ["liste des drapeaux rouges"],',
            '  "score_verification": 0.0-1.0',
            "}",
        ],
        tools=[
            verifier_registre_foncier,
            calculer_droits_mutation,
        ],
        markdown=False,
        add_history_to_context=True,
        debug_mode=False,
    )


# ============================================================================
# Agent Générateur
# ============================================================================

def create_agent_generateur(
    model: Optional[object] = None,
    db: Optional[SqliteDb] = None
) -> Agent:
    """
    Crée l'agent responsable de la génération de la checklist finale.

    Crée:
    - Checklist de vérification pour le notaire
    - Score de confiance global
    - Points d'attention prioritaires
    - Prochaines étapes recommandées

    Args:
        model: Modèle LLM à utiliser (défaut: MLX)
        db: Base de données pour stocker l'historique

    Returns:
        Agent configuré
    """
    if model is None:
        model = get_mlx_model()

    return Agent(
        name="GenerateurChecklist",
        model=model,
        db=db,
        description="Assistant organisationnel pour notaires",
        instructions=[
            "Tu es un assistant pour notaires expérimenté",
            "À partir de toutes les analyses précédentes, tu génères:",
            "",
            "1. Une checklist claire et actionnelle pour le notaire",
            "2. Un score de confiance (0.0 à 1.0) basé sur:",
            "   - Complétude des informations",
            "   - Cohérence des données",
            "   - Absence de drapeaux rouges",
            "3. Les points d'attention prioritaires (top 5)",
            "4. Un échéancier recommandé des prochaines étapes",
            "5. Les documents à obtenir",
            "",
            "Ta checklist doit être pratique et immédiatement utilisable",
            "Retourne un JSON structuré avec tous ces éléments",
            "",
            "Format de réponse attendu:",
            "{",
            '  "checklist": [',
            '    {"item": "Description", "priorite": "haute|moyenne|basse", "complete": false}',
            "  ],",
            '  "points_attention": ["top 5 des points importants"],',
            '  "documents_a_obtenir": ["liste"],',
            '  "prochaines_etapes": [',
            '    {"etape": "...", "delai": "...", "responsable": "..."}',
            "  ],",
            '  "score_confiance": 0.0-1.0,',
            '  "commentaires": "Commentaires généraux du workflow"',
            "}",
        ],
        tools=[],
        markdown=False,
        add_history_to_context=True,
        debug_mode=False,
    )


# ============================================================================
# Fonction utilitaire pour créer tous les agents
# ============================================================================

def create_all_agents(
    model: Optional[object] = None,
    db_file: str = "data/agno.db"
) -> dict[str, Agent]:
    """
    Crée tous les agents nécessaires pour le workflow d'analyse.

    Args:
        model: Modèle LLM à utiliser (défaut: MLX)
        db_file: Chemin vers la base de données SQLite

    Returns:
        Dictionnaire avec tous les agents:
        {
            "extracteur": Agent,
            "classificateur": Agent,
            "verificateur": Agent,
            "generateur": Agent,
        }
    """
    # Créer la base de données partagée
    db = SqliteDb(db_file=db_file)

    # Créer le modèle partagé
    if model is None:
        model = get_mlx_model()

    # Créer les agents
    agents = {
        "extracteur": create_agent_extracteur(model=model, db=db),
        "classificateur": create_agent_classificateur(model=model, db=db),
        "verificateur": create_agent_verificateur(model=model, db=db),
        "generateur": create_agent_generateur(model=model, db=db),
    }

    logger.info(f"✓ {len(agents)} agents créés avec succès")

    return agents
