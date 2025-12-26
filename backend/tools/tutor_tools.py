"""
Tutor Tools for Agno Agent.

Provides pedagogical tools for learning: summaries, mind maps, quizzes, and explanations.
"""

import logging
from typing import Optional

from agno.tools import tool

from services.tutor_service import get_tutor_service

logger = logging.getLogger(__name__)


@tool(name="generate_summary")
async def generate_summary(
    case_id: str,
    document_id: Optional[str] = None,
    summary_type: str = "comprehensive"
) -> str:
    """
    Génère un résumé pédagogique d'un document ou du cours complet.

    Args:
        case_id: ID du cours (format: "course:xxx" ou "xxx")
        document_id: ID du document spécifique (si None, résume tout le cours)
        summary_type: Type de résumé ("comprehensive", "key_points", "executive")

    Returns:
        Résumé formaté en markdown avec structure pédagogique
    """
    logger.info(f"Tool: generate_summary called with case_id={case_id}, document_id={document_id}")

    try:
        # Normalize case_id
        if not case_id.startswith("course:"):
            case_id = f"course:{case_id}"

        tutor_service = get_tutor_service()
        summary = await tutor_service.generate_summary_content(
            case_id=case_id,
            document_id=document_id,
            summary_type=summary_type
        )

        return summary

    except Exception as e:
        logger.error(f"Error generating summary: {e}", exc_info=True)
        return f"❌ Erreur lors de la génération du résumé: {str(e)}"


@tool(name="generate_mindmap")
async def generate_mindmap(
    case_id: str,
    document_id: Optional[str] = None,
    focus_topic: Optional[str] = None
) -> str:
    """
    Génère une carte mentale (mindmap) en format markdown avec emojis.

    Args:
        case_id: ID du cours (format: "course:xxx" ou "xxx")
        document_id: ID du document spécifique (si None, carte du cours complet)
        focus_topic: Sujet spécifique à développer dans la carte (optionnel)

    Returns:
        Carte mentale en markdown avec emojis et indentation hiérarchique
    """
    logger.info(f"Tool: generate_mindmap called with case_id={case_id}, document_id={document_id}, topic={focus_topic}")

    try:
        # Normalize case_id
        if not case_id.startswith("course:"):
            case_id = f"course:{case_id}"

        tutor_service = get_tutor_service()
        mindmap = await tutor_service.generate_mindmap_content(
            case_id=case_id,
            document_id=document_id,
            focus_topic=focus_topic
        )

        return mindmap

    except Exception as e:
        logger.error(f"Error generating mind map: {e}", exc_info=True)
        return f"❌ Erreur lors de la génération de la carte mentale: {str(e)}"


@tool(name="generate_quiz")
async def generate_quiz(
    case_id: str,
    document_id: Optional[str] = None,
    num_questions: int = 5,
    difficulty: str = "medium"
) -> str:
    """
    Génère un quiz pédagogique avec questions et réponses détaillées.

    Args:
        case_id: ID du cours (format: "course:xxx" ou "xxx")
        document_id: ID du document source (si None, quiz sur tout le cours)
        num_questions: Nombre de questions à générer (1-10, défaut: 5)
        difficulty: Niveau de difficulté ("easy", "medium", "hard")

    Returns:
        Quiz formaté en markdown avec questions à choix multiples et explications
    """
    logger.info(f"Tool: generate_quiz called with case_id={case_id}, num_questions={num_questions}, difficulty={difficulty}")

    try:
        # Normalize case_id
        if not case_id.startswith("course:"):
            case_id = f"course:{case_id}"

        # Validate num_questions
        if num_questions < 1:
            num_questions = 1
        elif num_questions > 10:
            num_questions = 10

        tutor_service = get_tutor_service()
        quiz = await tutor_service.generate_quiz_content(
            case_id=case_id,
            document_id=document_id,
            num_questions=num_questions,
            difficulty=difficulty
        )

        return quiz

    except Exception as e:
        logger.error(f"Error generating quiz: {e}", exc_info=True)
        return f"❌ Erreur lors de la génération du quiz: {str(e)}"


@tool(name="explain_concept")
async def explain_concept(
    case_id: str,
    concept: str,
    document_id: Optional[str] = None,
    detail_level: str = "standard"
) -> str:
    """
    Explique un concept de manière pédagogique avec exemples et sources.

    Args:
        case_id: ID du cours (format: "course:xxx" ou "xxx")
        concept: Le concept à expliquer (ex: "prescription acquisitive", "contrat de vente")
        document_id: Limiter la recherche à un document spécifique (optionnel)
        detail_level: Niveau de détail ("simple", "standard", "advanced")

    Returns:
        Explication structurée en markdown avec définition, exemples, et sources
    """
    logger.info(f"Tool: explain_concept called with case_id={case_id}, concept='{concept}', level={detail_level}")

    try:
        # Normalize case_id
        if not case_id.startswith("course:"):
            case_id = f"course:{case_id}"

        tutor_service = get_tutor_service()
        explanation = await tutor_service.generate_concept_explanation(
            case_id=case_id,
            concept=concept,
            document_id=document_id,
            detail_level=detail_level
        )

        return explanation

    except Exception as e:
        logger.error(f"Error explaining concept: {e}", exc_info=True)
        return f"❌ Erreur lors de l'explication du concept: {str(e)}"
