"""
Workflow de resume de jugements juridiques.

Ce workflow utilise 4 agents specialises pour analyser un jugement
et produire un resume structure (Case Brief).

Agents:
1. ExtractorAgent - Extrait les informations de base (parties, tribunal, date)
2. AnalyzerAgent - Identifie les faits, questions en litige, arguments
3. SynthesizerAgent - Extrait le ratio decidendi et la conclusion
4. FormatterAgent - Genere le case brief final structure

Usage:
    from workflows.summarize_judgment import create_summarize_workflow
    from agno.models.anthropic import Claude

    model = Claude(id="claude-sonnet-4-5-20250929")
    workflow = create_summarize_workflow(model)

    result = workflow.run(input="texte du jugement...")
"""

import json
import logging
from typing import Any, Optional

from agno.agent import Agent
from agno.workflow import Workflow, Step

logger = logging.getLogger(__name__)


# ============================================================
# PROMPTS POUR CHAQUE AGENT
# ============================================================

EXTRACTOR_PROMPT = """Tu es un assistant juridique specialise dans l'extraction d'informations
des jugements de tribunaux quebecois et canadiens.

Analyse le texte du jugement fourni et extrait les informations suivantes:

1. **Identification de l'affaire:**
   - Nom de l'affaire (ex: "Doe c. Smith" ou "R. c. Tremblay")
   - Reference/citation (ex: "2024 QCCS 1234")
   - Tribunal (ex: "Cour superieure du Quebec")
   - Date de la decision
   - Nom du juge

2. **Parties:**
   - Demandeur/Appelant (et son avocat si mentionne)
   - Defendeur/Intime (et son avocat si mentionne)

3. **Classification:**
   - Domaine de droit (civil, criminel, administratif, familial, etc.)
   - Type de procedure (action, requete, appel, etc.)

Reponds UNIQUEMENT en JSON valide avec cette structure:
{
    "case_name": "...",
    "citation": "...",
    "court": "...",
    "decision_date": "YYYY-MM-DD",
    "judge": "...",
    "parties": [{"name": "...", "role": "plaintiff|defendant", "lawyer": null}],
    "legal_domain": "civil|criminal|administrative|family|commercial|other",
    "procedure_type": "..."
}
"""

ANALYZER_PROMPT = """Tu es un assistant juridique specialise dans l'analyse de jugements.

A partir du texte du jugement, identifie et extrait:

1. **Faits pertinents** (max 10, en ordre chronologique)
2. **Questions en litige** avec leur importance (primary/secondary)
3. **Arguments des parties**
4. **Historique procedural**

Reponds UNIQUEMENT en JSON valide avec cette structure:
{
    "facts": ["Fait 1", "Fait 2"],
    "issues": [{"question": "...", "importance": "primary|secondary", "answer": "..."}],
    "plaintiff_arguments": ["Argument 1"],
    "defendant_arguments": ["Argument 1"],
    "procedural_history": "..."
}
"""

SYNTHESIZER_PROMPT = """Tu es un assistant juridique expert en synthese de jurisprudence.

A partir du texte du jugement, identifie:

1. **Regles de droit applicables** (articles de loi, precedents)
2. **Ratio decidendi** (la regle contraignante)
3. **Obiter dicta** (remarques incidentes)
4. **Dispositif** (decision finale et remedes)

Reponds UNIQUEMENT en JSON valide avec cette structure:
{
    "rules": [{"rule": "...", "source": "Art. X C.c.Q.", "source_type": "statute|case_law|doctrine|principle"}],
    "analysis_points": [{"point": "...", "is_ratio": true, "is_obiter": false}],
    "ratio_decidendi": "...",
    "obiter_dicta": ["..."],
    "holding": "...",
    "remedy": "..."
}
"""

FORMATTER_PROMPT = """Tu es un assistant juridique qui cree des fiches de jurisprudence (case briefs).

A partir des informations extraites, genere un case brief complet.
Calcule un score de confiance (0-100) base sur la completude des informations.

Reponds UNIQUEMENT en JSON valide avec cette structure:
{
    "case_brief": {
        "case_name": "...",
        "citation": "...",
        "court": "...",
        "decision_date": "...",
        "judge": "...",
        "parties": [...],
        "facts": [...],
        "procedural_history": "...",
        "issues": [...],
        "rules": [...],
        "ratio_decidendi": "...",
        "obiter_dicta": [...],
        "holding": "...",
        "remedy": "..."
    },
    "confidence_score": 85,
    "key_takeaway": "Resume en une phrase"
}
"""


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def parse_json_response(content: str) -> dict:
    """Parse une reponse JSON d'un agent."""
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        import re
        json_match = re.search(r'\{[\s\S]*\}', content)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass
        logger.warning(f"Could not parse JSON: {content[:200]}...")
        return {}


def create_summarize_workflow(model: Any, db: Optional[Any] = None) -> Workflow:
    """
    Cree un workflow Agno pour resumer un jugement juridique.

    Args:
        model: Instance de modele Agno (Claude, Ollama, etc.)
        db: Base de donnees Agno optionnelle pour la persistance

    Returns:
        Workflow: Instance du workflow configuree
    """

    # Creer les agents
    extractor = Agent(
        name="Extracteur",
        model=model,
        instructions=EXTRACTOR_PROMPT,
        markdown=False,
    )

    analyzer = Agent(
        name="Analyseur",
        model=model,
        instructions=ANALYZER_PROMPT,
        markdown=False,
    )

    synthesizer = Agent(
        name="Synthetiseur",
        model=model,
        instructions=SYNTHESIZER_PROMPT,
        markdown=False,
    )

    formatter = Agent(
        name="Formateur",
        model=model,
        instructions=FORMATTER_PROMPT,
        markdown=False,
    )

    # Creer les steps du workflow
    steps = [
        Step(name="extraction", agent=extractor, description="Extrait les informations de base"),
        Step(name="analysis", agent=analyzer, description="Analyse les faits et questions"),
        Step(name="synthesis", agent=synthesizer, description="Synthetise le ratio decidendi"),
        Step(name="formatting", agent=formatter, description="Genere le case brief final"),
    ]

    # Creer le workflow
    workflow_kwargs = {
        "name": "SummarizeJudgment",
        "description": "Workflow de resume de jugements juridiques avec 4 agents",
        "steps": steps,
    }

    if db:
        workflow_kwargs["db"] = db

    return Workflow(**workflow_kwargs)


def run_summarize_workflow(model: Any, judgment_text: str, db: Optional[Any] = None) -> dict:
    """
    Execute le workflow et retourne le resultat structure.

    Args:
        model: Instance de modele Agno
        judgment_text: Texte du jugement a analyser
        db: Base de donnees optionnelle

    Returns:
        dict: Resultat avec case_brief, confidence_score, etc.
    """
    workflow = create_summarize_workflow(model=model, db=db)

    logger.info("Starting judgment summarization workflow")

    try:
        # Executer le workflow
        result = workflow.run(input=judgment_text)

        # Extraire les resultats de chaque step
        extraction_data = {}
        analysis_data = {}
        synthesis_data = {}
        final_data = {}

        if hasattr(result, 'outputs') and result.outputs:
            for step_output in result.outputs:
                if hasattr(step_output, 'content'):
                    content = step_output.content
                    parsed = parse_json_response(content)

                    if hasattr(step_output, 'step_name'):
                        if step_output.step_name == "extraction":
                            extraction_data = parsed
                        elif step_output.step_name == "analysis":
                            analysis_data = parsed
                        elif step_output.step_name == "synthesis":
                            synthesis_data = parsed
                        elif step_output.step_name == "formatting":
                            final_data = parsed

        # Si on n'a pas de resultats structures, essayer d'extraire du contenu global
        if not final_data and hasattr(result, 'content'):
            final_data = parse_json_response(result.content)

        logger.info("Workflow completed successfully")

        return {
            "success": True,
            "case_brief": final_data.get("case_brief", {}),
            "confidence_score": final_data.get("confidence_score", 0) / 100 if final_data.get("confidence_score") else 0,
            "key_takeaway": final_data.get("key_takeaway", ""),
            "intermediate_results": {
                "extraction": extraction_data,
                "analysis": analysis_data,
                "synthesis": synthesis_data
            }
        }

    except Exception as e:
        logger.error(f"Workflow error: {e}")
        return {
            "success": False,
            "error": str(e),
            "case_brief": {},
            "confidence_score": 0
        }


# ============================================================
# SIMPLE SEQUENTIAL EXECUTION (Alternative sans Workflow)
# ============================================================

class SimpleJudgmentSummarizer:
    """
    Version simplifiee qui execute les agents sequentiellement.

    Cette version n'utilise pas le Workflow Agno mais execute
    directement les agents l'un apres l'autre.
    """

    def __init__(self, model: Any):
        self.model = model

        self.extractor = Agent(
            name="Extracteur",
            model=model,
            instructions=EXTRACTOR_PROMPT,
            markdown=False,
        )

        self.analyzer = Agent(
            name="Analyseur",
            model=model,
            instructions=ANALYZER_PROMPT,
            markdown=False,
        )

        self.synthesizer = Agent(
            name="Synthetiseur",
            model=model,
            instructions=SYNTHESIZER_PROMPT,
            markdown=False,
        )

        self.formatter = Agent(
            name="Formateur",
            model=model,
            instructions=FORMATTER_PROMPT,
            markdown=False,
        )

    def summarize(self, judgment_text: str) -> dict:
        """
        Resume un jugement en executant 4 agents sequentiellement.

        Args:
            judgment_text: Texte du jugement

        Returns:
            dict: Resultat structure
        """
        logger.info("Starting simple judgment summarization")

        try:
            # Step 1: Extraction
            logger.info("Step 1/4: Extraction...")
            extraction_result = self.extractor.run(
                f"Analyse ce jugement:\n\n{judgment_text}"
            )
            extraction_data = parse_json_response(extraction_result.content)

            # Step 2: Analysis
            logger.info("Step 2/4: Analysis...")
            analysis_result = self.analyzer.run(
                f"Analyse ce jugement:\n\n{judgment_text}"
            )
            analysis_data = parse_json_response(analysis_result.content)

            # Step 3: Synthesis
            logger.info("Step 3/4: Synthesis...")
            synthesis_result = self.synthesizer.run(
                f"Synthetise ce jugement:\n\n{judgment_text}"
            )
            synthesis_data = parse_json_response(synthesis_result.content)

            # Step 4: Formatting
            logger.info("Step 4/4: Formatting...")
            combined = {
                "extraction": extraction_data,
                "analysis": analysis_data,
                "synthesis": synthesis_data
            }
            format_result = self.formatter.run(
                f"Genere le case brief:\n\n{json.dumps(combined, ensure_ascii=False, indent=2)}"
            )
            final_data = parse_json_response(format_result.content)

            logger.info("Summarization completed successfully")

            return {
                "success": True,
                "case_brief": final_data.get("case_brief", {}),
                "confidence_score": final_data.get("confidence_score", 0) / 100 if final_data.get("confidence_score") else 0,
                "key_takeaway": final_data.get("key_takeaway", ""),
                "intermediate_results": {
                    "extraction": extraction_data,
                    "analysis": analysis_data,
                    "synthesis": synthesis_data
                }
            }

        except Exception as e:
            logger.error(f"Summarization error: {e}")
            return {
                "success": False,
                "error": str(e),
                "case_brief": {},
                "confidence_score": 0
            }


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":
    import os
    import sys

    test_judgment = """
    COUR SUPERIEURE DU QUEBEC

    Dossier: 500-17-123456-789
    DATE: 15 janvier 2024
    JUGE: L'honorable Jean Tremblay, j.c.s.

    ENTRE:
    MARIE DUPONT, Demanderesse
    ET:
    JEAN LAVOIE, Defendeur

    JUGEMENT

    [1] La demanderesse reclame 50 000 $ pour bris de contrat.

    FAITS

    [2] Le 1er juin 2023, la demanderesse a achete un vehicule d'occasion
    du defendeur pour 15 000 $.

    [3] Le defendeur a garanti que le vehicule etait en bon etat.

    [4] Deux semaines apres, le moteur a cesse de fonctionner.
    L'expertise revele un vice cache connu du vendeur.

    QUESTION EN LITIGE

    [5] Le defendeur est-il responsable du vice cache?

    ANALYSE

    [6] Selon l'article 1726 C.c.Q., le vendeur garantit l'acheteur
    contre les vices caches.

    [7] La preuve demontre que le defendeur connaissait le vice.

    CONCLUSION

    [8] ACCUEILLE l'action;
    [9] CONDAMNE le defendeur a payer 25 000 $ plus interets.

    Jean Tremblay, j.c.s.
    """

    print("=" * 60)
    print("TEST: Summarize Judgment Workflow")
    print("=" * 60)

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("\nERREUR: ANTHROPIC_API_KEY non definie")
        sys.exit(1)

    from agno.models.anthropic import Claude
    model = Claude(id="claude-sonnet-4-5-20250929", api_key=api_key)

    print("\n1. Using SimpleJudgmentSummarizer...")
    summarizer = SimpleJudgmentSummarizer(model=model)

    print("\n2. Executing summarization (30-60s)...\n")
    result = summarizer.summarize(test_judgment)

    print("=" * 60)
    print("RESULTS")
    print("=" * 60)
    print(f"\nSuccess: {result.get('success')}")
    print(f"Confidence: {result.get('confidence_score', 0):.0%}")
    print(f"\nKey takeaway: {result.get('key_takeaway', 'N/A')}")
    print("\nCase Brief:")
    print(json.dumps(result.get("case_brief", {}), ensure_ascii=False, indent=2))
