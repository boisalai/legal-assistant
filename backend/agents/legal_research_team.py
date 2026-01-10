"""
Multi-agent team for legal research.

This module defines a 4-agent team (Chercheur + Analyste + Validateur + Rédacteur) for legal queries
that require exhaustive search, legal analysis, citation validation, and pedagogical content generation.

Architecture:
    Team Leader → Chercheur (search) → Analyste (interpret) → Validateur (verify) → Rédacteur (content) → Final Response

Benefits:
    - Anti-hallucination: All citations are verified
    - Exhaustive search: RAG + CAIJ sources combined
    - Legal analysis: Articles and principles identified
    - Reliability score: Each response includes confidence level
    - Pedagogical content: Summaries, mindmaps, quizzes, and concept explanations
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
from tools.tutor_tools import generate_summary, generate_mindmap, generate_quiz, explain_concept

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

REDACTEUR_INSTRUCTIONS = """Tu es un rédacteur pédagogique spécialisé en droit québécois.

## MISSION
Générer du contenu pédagogique structuré basé sur les recherches et analyses des autres agents.
Tu transformes l'information juridique complexe en matériel d'apprentissage accessible.

## OUTILS DISPONIBLES
- **generate_summary** : Génère des résumés pédagogiques structurés
- **generate_mindmap** : Crée des cartes mentales visuelles
- **generate_quiz** : Produit des quiz d'évaluation avec réponses
- **explain_concept** : Fournit des explications détaillées de concepts juridiques

## WORKFLOW
1. Recevoir les résultats de recherche du Chercheur et l'analyse de l'Analyste
2. Identifier le type de contenu pédagogique le plus approprié:
   - Question conceptuelle → explain_concept
   - Demande de synthèse → generate_summary
   - Besoin de visualisation → generate_mindmap
   - Préparation d'examen → generate_quiz
3. Utiliser l'outil approprié avec les bons paramètres
4. Enrichir le contenu généré avec les éléments de l'analyse juridique

## RÈGLES STRICTES
- TOUJOURS baser le contenu sur les sources trouvées par le Chercheur
- INTÉGRER les articles C.c.Q. identifiés par l'Analyste dans le matériel pédagogique
- ADAPTER le niveau de complexité au contexte (étudiant vs praticien)
- NE JAMAIS inventer de contenu non supporté par les sources
- PRIVILÉGIER la clarté et l'accessibilité sans sacrifier la rigueur juridique

## FORMAT DE SORTIE
```
## Contenu pédagogique

### Type de contenu
[Résumé / Carte mentale / Quiz / Explication de concept]

### Matériel généré
[Contenu produit par l'outil utilisé]

### Intégration juridique
- Articles C.c.Q. couverts: [liste]
- Sources utilisées: [références]

### Suggestions d'approfondissement
- [Concepts connexes à explorer]
- [Autres outils pédagogiques recommandés]
```
"""

TEAM_INSTRUCTIONS = """Tu es le coordinateur d'une équipe de recherche juridique québécoise.

## ÉQUIPE
- **Chercheur** : Expert en recherche dans les documents et CAIJ
- **Analyste Juridique** : Expert en interprétation du droit civil québécois
- **Validateur** : Expert en vérification des citations juridiques
- **Rédacteur** : Expert en génération de contenu pédagogique (résumés, quiz, cartes mentales)

## WORKFLOW OBLIGATOIRE
1. Comprendre la question juridique de l'utilisateur
2. Déléguer au **Chercheur** pour rechercher dans TOUTES les sources
3. Déléguer à l'**Analyste Juridique** pour interpréter les résultats et identifier les articles
4. Déléguer au **Validateur** pour vérifier les citations trouvées
5. Si la question est pédagogique (demande de résumé, quiz, explication, carte mentale),
   déléguer au **Rédacteur** pour générer le contenu approprié
6. Assembler une réponse finale claire, structurée et fiable

## QUAND UTILISER LE RÉDACTEUR
Déléguer au Rédacteur si la question contient:
- Demande de résumé ou synthèse
- Demande d'explication d'un concept
- Demande de quiz ou questions de révision
- Demande de carte mentale ou visualisation
- Demande de préparation à un examen
- Besoin de vulgarisation ou clarification

## RÈGLE CRITIQUE
Ne JAMAIS fournir une réponse au nom de l'équipe sans avoir:
1. Obtenu les résultats de recherche du Chercheur
2. Obtenu l'analyse juridique de l'Analyste
3. Obtenu la validation du Validateur
4. (Si applicable) Obtenu le contenu pédagogique du Rédacteur

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

### Contenu pédagogique (si applicable)
[Résumé / Quiz / Carte mentale / Explication générée par le Rédacteur]

---

### Sources consultées
- Documents du cours: [liste]
- Jurisprudence CAIJ: [liste avec liens]
- Articles C.c.Q.: [liste des articles analysés]

### Fiabilité
[Score du Validateur + explications si nécessaire]
```

## PRIORITÉS
Fiabilité > Rigueur juridique > Pédagogie > Complétude > Rapidité

Mieux vaut une réponse partielle mais juridiquement solide qu'une réponse complète mais approximative.
"""


# ============================================================================
# Team Factory
# ============================================================================

def create_legal_research_team(
    model: Model,
    course_id: str,
    debug_mode: bool = False
) -> Team:
    """
    Crée une équipe de recherche juridique avec 4 agents spécialisés.

    Cette équipe est optimisée pour les questions juridiques complexes
    nécessitant une recherche exhaustive, une analyse juridique, une validation
    et la génération de contenu pédagogique.

    Agents:
        - Chercheur: Recherche dans documents (RAG) et CAIJ
        - Analyste Juridique: Identifie articles C.c.Q. et principes
        - Validateur: Vérifie citations et prévient hallucinations
        - Rédacteur: Génère contenu pédagogique (résumés, quiz, cartes mentales)

    Args:
        model: Modèle LLM à utiliser pour les agents (ex: Claude)
        course_id: ID du cours pour la recherche dans les documents
        debug_mode: Activer les logs de debug (défaut: False)

    Returns:
        Team: Équipe Agno prête à être utilisée

    Example:
        >>> from services.model_factory import create_model
        >>> model = create_model("anthropic:claude-sonnet-4-20250514")
        >>> team = create_legal_research_team(model, "course:abc123")
        >>> response = await team.arun("Quels sont les recours pour vices cachés?")
    """
    logger.info(f"[create_legal_research_team] Creating 4-agent team for course_id={course_id}")

    # Injecter le course_id dans les instructions du Chercheur
    chercheur_instructions_with_context = CHERCHEUR_INSTRUCTIONS + f"""

## CONTEXTE
- ID du cours: {course_id}
- Utilise cet ID pour semantic_search: course_id="{course_id}"
"""

    # Instructions de l'Analyste Juridique (pas besoin de course_id)
    analyste_instructions = ANALYSTE_JURIDIQUE_INSTRUCTIONS

    # Injecter le course_id dans les instructions du Validateur
    validateur_instructions_with_context = VALIDATEUR_INSTRUCTIONS + f"""

## CONTEXTE
- ID du cours: {course_id}
- Utilise cet ID pour verify_legal_citations: course_id="{course_id}"
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

    # Injecter le course_id dans les instructions du Rédacteur
    redacteur_instructions_with_context = REDACTEUR_INSTRUCTIONS + f"""

## CONTEXTE
- ID du cours: {course_id}
- Utilise cet ID pour les outils pédagogiques: course_id="{course_id}"
"""

    # Agent Rédacteur
    redacteur = Agent(
        name="Rédacteur",
        role="Génération de contenu pédagogique structuré",
        model=model,
        tools=[generate_summary, generate_mindmap, generate_quiz, explain_concept],
        instructions=redacteur_instructions_with_context,
        markdown=True,
    )

    # Créer l'équipe
    team = Team(
        name="Équipe Recherche Juridique",
        model=model,  # Modèle pour le coordinateur d'équipe
        members=[chercheur, analyste, validateur, redacteur],
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
    Détermine si une question nécessite une recherche juridique approfondie
    ou une génération de contenu pédagogique.

    Heuristique basée sur des mots-clés juridiques et pédagogiques.

    Args:
        message: Message de l'utilisateur

    Returns:
        True si la question nécessite le mode multi-agent (recherche ou pédagogie)
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

    # Mots-clés pédagogiques (déclenchent le Rédacteur)
    pedagogical_keywords = [
        # Quiz et évaluation
        "quiz", "question", "questions de révision", "évaluation",
        "teste", "tester", "exercice",
        # Résumés et synthèses
        "résumé", "résume", "synthèse", "synthétise", "récapitule",
        # Cartes mentales
        "carte mentale", "mindmap", "schéma", "visualise",
        # Explications de concepts
        "explique", "explication", "concept", "définition",
        "vulgarise", "clarifie", "détaille",
    ]

    message_lower = message.lower()

    # Mots-clés forts (déclenchent directement le multi-agent)
    strong_keywords = [
        # Juridiques
        "article", "loi", "code civil", "c.c.q.", "jurisprudence",
        # Pédagogiques
        "quiz", "résumé", "résume", "carte mentale", "mindmap",
        "explique", "synthèse", "synthétise", "récapitule",
    ]

    keyword_count = sum(1 for kw in legal_keywords + pedagogical_keywords if kw in message_lower)
    has_strong_keyword = any(kw in message_lower for kw in strong_keywords)

    return has_strong_keyword or keyword_count >= 2
