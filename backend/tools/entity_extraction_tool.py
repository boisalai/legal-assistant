"""
Entity extraction tool for the Agno agent.

This tool allows the AI agent to extract legal entities from documents.
"""

import logging
import json
from typing import Optional, List, Dict, Any
from pathlib import Path

from agno.tools import tool
from agno.agent import Agent

from services.surreal_service import get_surreal_service
from services.model_factory import create_model

logger = logging.getLogger(__name__)


async def _get_document_content(course_id: str, document_name: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Get document content by name or return all documents.

    Args:
        course_id: ID of the course
        document_name: Optional specific document name

    Returns:
        Document dict or None
    """
    service = get_surreal_service()
    if not service.db:
        await service.connect()

    # Normalize course_id
    if not course_id.startswith("course:"):
        course_id = f"course:{course_id}"

    # Get documents for this course
    docs_result = await service.query(
        "SELECT * FROM document WHERE course_id = $course_id ORDER BY created_at DESC",
        {"course_id": course_id}
    )

    documents = []
    if docs_result and len(docs_result) > 0:
        first_item = docs_result[0]
        if isinstance(first_item, dict):
            if "result" in first_item:
                documents = first_item["result"] if isinstance(first_item["result"], list) else []
            elif "id" in first_item or "nom_fichier" in first_item:
                documents = docs_result
        elif isinstance(first_item, list):
            documents = first_item

    # Filter documents with content
    docs_with_content = [
        doc for doc in documents
        if doc.get("texte_extrait") and len(doc.get("texte_extrait", "").strip()) > 0
    ]

    if not docs_with_content:
        return None

    # If document_name specified, find matching document
    if document_name:
        for doc in docs_with_content:
            doc_name = doc.get("nom_fichier", "")
            if document_name.lower() in doc_name.lower() or doc_name.lower() in document_name.lower():
                return doc

    # Return all documents combined
    if len(docs_with_content) == 1:
        return docs_with_content[0]

    # Combine multiple documents
    combined_content = ""
    for doc in docs_with_content:
        doc_name = doc.get("nom_fichier", "Document")
        content = doc.get("texte_extrait", "")
        combined_content += f"\n\n### {doc_name}\n\n{content}"

    return {
        "nom_fichier": f"{len(docs_with_content)} documents combinés",
        "texte_extrait": combined_content
    }


@tool(name="extract_entities")
async def extract_entities(
    course_id: str,
    document_name: Optional[str] = None,
    entity_types: str = "personnes,dates,montants,références légales"
) -> str:
    """
    Extrait des entités juridiques importantes des documents d'un cours.

    Cet outil analyse les documents et extrait des informations structurées comme
    les noms de personnes, dates importantes, montants financiers, et références légales.

    Args:
        course_id: L'identifiant du cours (ex: "1f9fc70e" ou "course:1f9fc70e")
        document_name: Nom d'un document spécifique à analyser (optionnel - si non spécifié, analyse tous les documents)
        entity_types: Types d'entités à extraire, séparés par des virgules (défaut: "personnes,dates,montants,références légales")

    Returns:
        Une liste structurée des entités extraites avec leur contexte
    """
    try:
        # Get document content
        document = await _get_document_content(course_id, document_name)

        if not document:
            if document_name:
                return f"Aucun document nommé '{document_name}' avec du contenu extractible trouvé dans ce cours."
            return "Aucun document avec du contenu extractible trouvé dans ce cours."

        doc_name = document.get("nom_fichier", "Document")
        content = document.get("texte_extrait", "")

        if len(content) > 15000:
            content = content[:15000] + "\n\n[... contenu tronqué pour l'analyse ...]"

        # Parse entity types
        entity_list = [e.strip() for e in entity_types.split(",")]

        # Create extraction prompt
        extraction_prompt = f"""Analyse le document suivant et extrais les entités juridiques importantes.

Document: {doc_name}

Types d'entités à extraire:
{chr(10).join([f"- {e}" for e in entity_list])}

Contenu du document:
{content}

Instructions:
- Extrait UNIQUEMENT les entités qui apparaissent réellement dans le texte
- Pour chaque entité, fournis un court extrait du contexte où elle apparaît
- Organise les entités par type
- Si un type d'entité n'est pas trouvé, indique "Aucune trouvée"

Format de réponse attendu (en JSON):
{{
    "personnes": [
        {{"nom": "Jean Dupont", "contexte": "M. Jean Dupont, partie demanderesse..."}},
        ...
    ],
    "dates": [
        {{"date": "2024-03-15", "description": "Date de signature du contrat", "contexte": "signé le 15 mars 2024..."}},
        ...
    ],
    "montants": [
        {{"montant": "450 000$", "description": "Prix de vente", "contexte": "pour la somme de 450 000$..."}},
        ...
    ],
    "références légales": [
        {{"référence": "Art. 1457 C.c.Q.", "contexte": "en vertu de l'article 1457 du Code civil..."}},
        ...
    ]
}}

Réponds UNIQUEMENT avec le JSON, sans texte avant ou après."""

        # Use Agno Agent for extraction
        model = create_model("ollama:qwen2.5:7b")  # Use a local model for extraction

        agent = Agent(
            name="EntityExtractor",
            model=model,
            instructions="Tu es un expert en extraction d'entités juridiques. Tu réponds UNIQUEMENT en JSON valide, sans texte additionnel.",
            markdown=False,
        )

        logger.info(f"Extracting entities from document: {doc_name}")
        response = await agent.arun(extraction_prompt)

        if not response or not hasattr(response, 'content'):
            return "Erreur: Impossible d'extraire les entités du document."

        # Parse JSON response
        content_str = response.content.strip()

        # Remove markdown code blocks if present
        if content_str.startswith("```"):
            lines = content_str.split("\n")
            # Remove first and last lines (``` markers)
            content_str = "\n".join(lines[1:-1]) if len(lines) > 2 else content_str
            if content_str.startswith("json"):
                content_str = content_str[4:].strip()

        try:
            entities = json.loads(content_str)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            logger.error(f"Response content: {content_str[:500]}")
            return f"Erreur lors de l'extraction des entités: Réponse invalide du modèle.\n\nContenu brut:\n{content_str[:500]}"

        # Format response
        response_text = f"**Entités extraites du document: {doc_name}**\n\n"

        total_entities = 0

        # Format each entity type
        for entity_type, items in entities.items():
            if not items or not isinstance(items, list):
                response_text += f"### {entity_type.title()}\n*Aucune trouvée*\n\n"
                continue

            response_text += f"### {entity_type.title()}\n"
            response_text += f"*{len(items)} trouvée(s)*\n\n"
            total_entities += len(items)

            for i, item in enumerate(items[:10], 1):  # Limit to 10 per type
                if entity_type == "personnes":
                    nom = item.get("nom", "Nom inconnu")
                    contexte = item.get("contexte", "")
                    response_text += f"{i}. **{nom}**\n"
                    if contexte:
                        response_text += f"   *{contexte[:150]}...*\n\n"
                    else:
                        response_text += "\n"

                elif entity_type == "dates":
                    date = item.get("date", "Date inconnue")
                    description = item.get("description", "")
                    contexte = item.get("contexte", "")
                    response_text += f"{i}. **{date}**"
                    if description:
                        response_text += f" - {description}"
                    response_text += "\n"
                    if contexte:
                        response_text += f"   *{contexte[:150]}...*\n\n"
                    else:
                        response_text += "\n"

                elif entity_type == "montants":
                    montant = item.get("montant", "Montant inconnu")
                    description = item.get("description", "")
                    contexte = item.get("contexte", "")
                    response_text += f"{i}. **{montant}**"
                    if description:
                        response_text += f" - {description}"
                    response_text += "\n"
                    if contexte:
                        response_text += f"   *{contexte[:150]}...*\n\n"
                    else:
                        response_text += "\n"

                elif entity_type == "références légales":
                    ref = item.get("référence", "Référence inconnue")
                    contexte = item.get("contexte", "")
                    response_text += f"{i}. **{ref}**\n"
                    if contexte:
                        response_text += f"   *{contexte[:150]}...*\n\n"
                    else:
                        response_text += "\n"

                else:
                    # Generic format for other entity types
                    response_text += f"{i}. {json.dumps(item, ensure_ascii=False)}\n\n"

            if len(items) > 10:
                response_text += f"*... et {len(items) - 10} autres*\n\n"

        response_text += f"\n**Total: {total_entities} entités extraites**"

        return response_text

    except Exception as e:
        logger.error(f"Entity extraction error: {e}", exc_info=True)
        return f"Erreur lors de l'extraction des entités: {str(e)}"


@tool(name="find_entity")
async def find_entity(
    course_id: str,
    entity_name: str,
    entity_type: str = "personne"
) -> str:
    """
    Recherche une entité spécifique dans les documents d'un cours.

    Cet outil permet de rechercher rapidement une personne, une date, un montant
    ou une référence légale spécifique et voir tous les contextes où elle apparaît.

    Args:
        course_id: L'identifiant du cours (ex: "1f9fc70e" ou "course:1f9fc70e")
        entity_name: Le nom de l'entité à rechercher (ex: "Jean Dupont", "450000", "Art. 1457")
        entity_type: Type d'entité (défaut: "personne"). Options: personne, date, montant, référence

    Returns:
        Tous les contextes où l'entité apparaît dans les documents
    """
    try:
        # Get document content
        document = await _get_document_content(course_id, None)

        if not document:
            return "Aucun document avec du contenu extractible trouvé dans ce cours."

        content = document.get("texte_extrait", "")
        doc_name = document.get("nom_fichier", "Documents")

        # Search for the entity in the content
        import re

        matches = []
        content_lower = content.lower()
        entity_lower = entity_name.lower()

        # Find all occurrences
        start = 0
        while True:
            pos = content_lower.find(entity_lower, start)
            if pos == -1:
                break

            # Extract context (200 chars before and after)
            context_start = max(0, pos - 200)
            context_end = min(len(content), pos + len(entity_name) + 200)
            context = content[context_start:context_end]

            # Add ellipsis
            if context_start > 0:
                context = "..." + context
            if context_end < len(content):
                context = context + "..."

            matches.append(context)
            start = pos + len(entity_name)

        if not matches:
            return f"L'entité **{entity_name}** ({entity_type}) n'a pas été trouvée dans les documents du cours."

        # Format response
        response_text = f"**Recherche de l'entité: {entity_name}** ({entity_type})\n\n"
        response_text += f"*Trouvée {len(matches)} fois dans {doc_name}*\n\n"

        for i, context in enumerate(matches[:10], 1):
            # Highlight the entity in the context
            highlighted = re.sub(
                re.escape(entity_name),
                f"**{entity_name}**",
                context,
                flags=re.IGNORECASE
            )
            response_text += f"**Occurrence {i}:**\n{highlighted}\n\n"

        if len(matches) > 10:
            response_text += f"*... et {len(matches) - 10} autres occurrences*"

        return response_text

    except Exception as e:
        logger.error(f"Find entity error: {e}", exc_info=True)
        return f"Erreur lors de la recherche de l'entité: {str(e)}"
