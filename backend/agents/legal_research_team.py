"""
Multi-agent team for legal research.

This module defines a 3-agent team (Chercheur + Analyste + Validateur) for legal queries
that require exhaustive search, legal analysis, and citation validation.

Architecture:
    Team Leader → Chercheur (search) → Analyste (interpret) → Validateur (verify) → Final Response

Benefits:
    - Anti-hallucination: All citations are verified
    - Exhaustive search: RAG + CAIJ sources combined
    - Legal analysis: Articles and principles identified
    - Reliability score: Each response includes confidence level
"""

import logging
from typing import Optional, Callable

from agno.agent import Agent
from agno.team import Team
from agno.models.base import Model

from tools.semantic_search_tool import semantic_search
from tools.caij_search_tool import search_caij_jurisprudence
from tools.validation_tool import verify_legal_citations, extract_citations
from tools.legal_analysis_tool import analyze_legal_text, identify_applicable_articles

logger = logging.getLogger(__name__)

# ============================================================================
# Agent Instructions
# ============================================================================

CHERCHEUR_INSTRUCTIONS = """Tu es un chercheur juridique spécialisé en droit québécois.

## MISSION
Rechercher de manière exhaustive dans TOUTES les sources disponibles pour répondre
à la question juridique posée.

## WORKFLOW OBLIGATOIRE
1. **semantic_search** : Chercher dans les documents du cours (RAG)
2. **search_caij_jurisprudence** : Chercher la jurisprudence québécoise sur CAIJ

Tu DOIS utiliser les DEUX outils pour chaque question, sauf si l'un est clairement
non pertinent (ex: question sur un document spécifique → pas besoin de CAIJ).

## RÈGLES STRICTES
- TOUJOURS citer la source exacte (nom du document, article, référence du jugement)
- INCLURE les extraits textuels pertinents entre guillemets
- NE JAMAIS inventer de contenu ou de citation
- Si rien trouvé, dire explicitement "Aucune source trouvée pour [sujet]"

## FORMAT DE SORTIE
```
## Sources trouvées

### Documents du cours
[Résultats de semantic_search avec nom de fichier et pertinence]

### Jurisprudence CAIJ
[Résultats de search_caij avec titre, date, tribunal et URL]

### Synthèse
[Résumé des informations trouvées, avec références]
```
"""

VALIDATEUR_INSTRUCTIONS = """Tu es un validateur juridique expert en détection d'hallucinations.

## MISSION
Vérifier TOUTES les citations juridiques présentes dans le texte du Chercheur
pour garantir leur exactitude avant de les présenter à l'utilisateur.

## WORKFLOW
1. Lire attentivement le rapport du Chercheur
2. Utiliser **verify_legal_citations** sur le texte complet
3. Analyser le rapport de validation
4. Signaler tout problème détecté

## RÈGLES STRICTES
- Vérifier CHAQUE citation mentionnée (articles, jurisprudence, lois)
- Signaler les citations non vérifiables avec une recommandation
- Ne pas modifier le contenu du Chercheur, seulement le valider
- Toujours inclure le niveau de fiabilité dans ta réponse

## FORMAT DE SORTIE
```
## Validation des citations

### Statut de validation
[Résultat de verify_legal_citations]

### Recommandations
- [Ce que l'utilisateur doit savoir sur la fiabilité]
- [Mises en garde éventuelles]

### Verdict
Fiabilité: [HAUTE/MOYENNE/BASSE]
```
"""

ANALYSTE_JURIDIQUE_INSTRUCTIONS = """Tu es un analyste juridique expert en droit civil québécois.

## MISSION
Analyser les résultats de recherche du Chercheur pour:
- Identifier les articles du Code civil du Québec applicables
- Extraire les principes juridiques fondamentaux
- Interpréter la doctrine et la jurisprudence
- Structurer l'argumentation juridique

## WORKFLOW
1. Recevoir les résultats de recherche du Chercheur
2. Utiliser **analyze_legal_text** pour analyser le contenu trouvé
3. Utiliser **identify_applicable_articles** pour trouver les articles pertinents
4. Formuler une interprétation juridique structurée

## RÈGLES STRICTES
- TOUJOURS identifier les articles C.c.Q. applicables avec leur numéro
- EXPLIQUER comment chaque article s'applique à la situation
- DISTINGUER les règles impératives des règles supplétives
- MENTIONNER les exceptions et cas particuliers pertinents
- NE JAMAIS inventer d'articles ou de principes

## FORMAT DE SORTIE
```
## Analyse juridique

### Articles applicables
- Art. [X] C.c.Q. : [description et application]
- Art. [Y] C.c.Q. : [description et application]

### Principes juridiques
1. [Principe fondamental avec référence]
2. [Autre principe applicable]

### Interprétation
[Comment le droit s'applique à la question posée]

### Points d'attention
- [Exceptions ou nuances importantes]
- [Évolutions jurisprudentielles récentes]
```
"""

TEAM_INSTRUCTIONS = """Tu es le coordinateur d'une équipe de recherche juridique québécoise.

## ÉQUIPE
- **Chercheur** : Expert en recherche dans les documents et CAIJ
- **Analyste Juridique** : Expert en interprétation du droit civil québécois
- **Validateur** : Expert en vérification des citations juridiques

## WORKFLOW OBLIGATOIRE
1. Comprendre la question juridique de l'utilisateur
2. Déléguer au **Chercheur** pour rechercher dans TOUTES les sources
3. Déléguer à l'**Analyste Juridique** pour interpréter les résultats et identifier les articles
4. Déléguer au **Validateur** pour vérifier les citations trouvées
5. Assembler une réponse finale claire, structurée et fiable

## RÈGLE CRITIQUE
Ne JAMAIS fournir une réponse au nom de l'équipe sans avoir:
1. Obtenu les résultats de recherche du Chercheur
2. Obtenu l'analyse juridique de l'Analyste
3. Obtenu la validation du Validateur

Si le Validateur signale des problèmes (citations invalides ou non vérifiées),
tu DOIS les mentionner clairement à l'utilisateur.

## FORMAT DE RÉPONSE FINALE
```
## Réponse à votre question

[Réponse structurée basée sur l'analyse juridique]

### Cadre juridique
[Articles C.c.Q. applicables identifiés par l'Analyste]

### Analyse
[Interprétation et application au cas d'espèce]

---

### Sources consultées
- Documents du cours: [liste]
- Jurisprudence CAIJ: [liste avec liens]
- Articles C.c.Q.: [liste des articles analysés]

### Fiabilité
[Score du Validateur + explications si nécessaire]
```

## PRIORITÉS
Fiabilité > Rigueur juridique > Complétude > Rapidité

Mieux vaut une réponse partielle mais juridiquement solide qu'une réponse complète mais approximative.
"""


# ============================================================================
# Team Factory
# ============================================================================

def create_legal_research_team(
    model: Model,
    case_id: str,
    debug_mode: bool = False
) -> Team:
    """
    Crée une équipe de recherche juridique avec 3 agents spécialisés.

    Cette équipe est optimisée pour les questions juridiques complexes
    nécessitant une recherche exhaustive, une analyse juridique et une validation.

    Agents:
        - Chercheur: Recherche dans documents (RAG) et CAIJ
        - Analyste Juridique: Identifie articles C.c.Q. et principes
        - Validateur: Vérifie citations et prévient hallucinations

    Args:
        model: Modèle LLM à utiliser pour les agents (ex: Claude)
        case_id: ID du cours pour la recherche dans les documents
        debug_mode: Activer les logs de debug (défaut: False)

    Returns:
        Team: Équipe Agno prête à être utilisée

    Example:
        >>> from services.model_factory import create_model
        >>> model = create_model("anthropic:claude-sonnet-4-20250514")
        >>> team = create_legal_research_team(model, "course:abc123")
        >>> response = await team.arun("Quels sont les recours pour vices cachés?")
    """
    logger.info(f"[create_legal_research_team] Creating 3-agent team for case_id={case_id}")

    # Injecter le case_id dans les instructions du Chercheur
    chercheur_instructions_with_context = CHERCHEUR_INSTRUCTIONS + f"""

## CONTEXTE
- ID du cours: {case_id}
- Utilise cet ID pour semantic_search: case_id="{case_id}"
"""

    # Instructions de l'Analyste Juridique (pas besoin de case_id)
    analyste_instructions = ANALYSTE_JURIDIQUE_INSTRUCTIONS

    # Injecter le case_id dans les instructions du Validateur
    validateur_instructions_with_context = VALIDATEUR_INSTRUCTIONS + f"""

## CONTEXTE
- ID du cours: {case_id}
- Utilise cet ID pour verify_legal_citations: case_id="{case_id}"
"""

    # Agent Chercheur
    chercheur = Agent(
        name="Chercheur",
        role="Recherche exhaustive dans les documents et CAIJ",
        model=model,
        tools=[semantic_search, search_caij_jurisprudence],
        instructions=chercheur_instructions_with_context,
        markdown=True,
    )

    # Agent Analyste Juridique
    analyste = Agent(
        name="Analyste Juridique",
        role="Interprétation du droit et identification des articles applicables",
        model=model,
        tools=[analyze_legal_text, identify_applicable_articles],
        instructions=analyste_instructions,
        markdown=True,
    )

    # Agent Validateur
    validateur = Agent(
        name="Validateur",
        role="Vérification des citations et prévention des hallucinations",
        model=model,
        tools=[verify_legal_citations, extract_citations],
        instructions=validateur_instructions_with_context,
        markdown=True,
    )

    # Créer l'équipe
    team = Team(
        name="Équipe Recherche Juridique",
        model=model,  # Modèle pour le coordinateur d'équipe
        members=[chercheur, analyste, validateur],
        instructions=TEAM_INSTRUCTIONS,
        markdown=True,
        debug_mode=debug_mode,
        # Configuration de la coordination
        share_member_interactions=True,  # Partager les résultats entre membres
    )

    logger.info(f"[create_legal_research_team] Team created with {len(team.members)} agents")

    return team


def is_legal_research_query(message: str) -> bool:
    """
    Détermine si une question nécessite une recherche juridique approfondie.

    Heuristique simple basée sur des mots-clés juridiques.

    Args:
        message: Message de l'utilisateur

    Returns:
        True si la question semble nécessiter une recherche juridique multi-source
    """
    # Mots-clés indiquant une question juridique complexe
    legal_keywords = [
        # Termes juridiques généraux
        "article", "loi", "code civil", "c.c.q.", "jurisprudence",
        "jugement", "arrêt", "décision", "tribunal",
        # Questions de recherche
        "quels sont les recours", "qu'est-ce que", "comment fonctionne",
        "quelle est la procédure", "quelles sont les conditions",
        # Domaines juridiques
        "vices cachés", "responsabilité", "contrat", "bail",
        "succession", "mariage", "divorce", "hypothèque",
        "servitude", "copropriété", "mandat",
    ]

    message_lower = message.lower()

    # Vérifie si au moins 2 mots-clés sont présents
    # ou si un mot-clé fort (article, loi, code civil) est présent
    strong_keywords = ["article", "loi", "code civil", "c.c.q.", "jurisprudence"]

    keyword_count = sum(1 for kw in legal_keywords if kw in message_lower)
    has_strong_keyword = any(kw in message_lower for kw in strong_keywords)

    return has_strong_keyword or keyword_count >= 2
