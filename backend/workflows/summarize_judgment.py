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
    from services.model_factory import create_model

    model = create_model("ollama:qwen2.5:7b")
    workflow = create_summarize_workflow(model=model)

    result = workflow.run(judgment_text="...")
"""

import json
import logging
from typing import Any, Optional

from agno.agent import Agent
from agno.workflow import Workflow

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
   - Autres parties (intervenants, etc.)

3. **Classification:**
   - Domaine de droit (civil, criminel, administratif, familial, etc.)
   - Type de procedure (action, requete, appel, revision judiciaire, etc.)

Reponds en JSON avec cette structure:
{
    "case_name": "...",
    "citation": "...",
    "court": "...",
    "decision_date": "YYYY-MM-DD",
    "judge": "...",
    "parties": [
        {"name": "...", "role": "plaintiff|defendant|appellant|respondent", "lawyer": "..."}
    ],
    "legal_domain": "civil|criminal|administrative|family|commercial|other",
    "procedure_type": "..."
}

Si une information n'est pas disponible, utilise null.
"""

ANALYZER_PROMPT = """Tu es un assistant juridique specialise dans l'analyse de jugements.

A partir du texte du jugement, identifie et extrait:

1. **Faits pertinents:**
   - Liste les faits materiels essentiels a la decision
   - Concentre-toi sur les faits juridiquement significatifs
   - Maximum 10 faits, en ordre chronologique si possible

2. **Questions en litige (Issues):**
   - Quelles sont les questions juridiques que le tribunal doit trancher?
   - Formule chaque question de maniere precise
   - Indique si c'est une question principale ou secondaire

3. **Arguments des parties:**
   - Resume les principaux arguments du demandeur/appelant
   - Resume les principaux arguments du defendeur/intime

4. **Historique procedural:**
   - Decisions anterieures s'il y en a (premiere instance, etc.)
   - Historique pertinent de l'affaire

Reponds en JSON avec cette structure:
{
    "facts": ["Fait 1", "Fait 2", ...],
    "issues": [
        {"question": "...", "importance": "primary|secondary", "answer": "..."}
    ],
    "plaintiff_arguments": ["Argument 1", ...],
    "defendant_arguments": ["Argument 1", ...],
    "procedural_history": "..."
}
"""

SYNTHESIZER_PROMPT = """Tu es un assistant juridique expert en synthese de jurisprudence.

A partir du texte du jugement, identifie:

1. **Regles de droit applicables:**
   - Articles de loi cites (Code civil, Code criminel, etc.)
   - Precedents jurisprudentiels invoques
   - Principes juridiques fondamentaux

2. **Analyse du tribunal:**
   - Comment le tribunal applique les regles aux faits
   - Raisonnement juridique principal

3. **Ratio decidendi:**
   - LA regle de droit etablie par cette decision
   - Le motif essentiel qui fonde la decision
   - C'est la partie CONTRAIGNANTE du jugement

4. **Obiter dicta:**
   - Remarques incidentes du juge
   - Commentaires qui ne sont pas essentiels a la decision
   - Ces elements ne sont PAS contraignants mais peuvent etre persuasifs

5. **Dispositif/Conclusion:**
   - La decision finale du tribunal
   - Les remedes accordes (dommages, injonction, etc.)

Reponds en JSON avec cette structure:
{
    "rules": [
        {"rule": "...", "source": "Art. 1457 C.c.Q.", "source_type": "statute|case_law|doctrine|principle"}
    ],
    "analysis_points": [
        {"point": "...", "is_ratio": true|false, "is_obiter": true|false}
    ],
    "ratio_decidendi": "...",
    "obiter_dicta": ["...", "..."],
    "holding": "...",
    "remedy": "..."
}
"""

FORMATTER_PROMPT = """Tu es un assistant juridique qui cree des fiches de jurisprudence (case briefs).

A partir des informations extraites, genere un case brief complet et bien structure.

Le case brief doit etre:
- Clair et concis
- Utile pour revision et etude
- Structure selon le format standard

Calcule aussi un score de confiance (0-100) base sur:
- Completude des informations extraites
- Clarte des questions en litige
- Identification claire du ratio decidendi

Reponds en JSON avec cette structure finale:
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
        "analysis": [...],
        "ratio_decidendi": "...",
        "obiter_dicta": [...],
        "holding": "...",
        "remedy": "..."
    },
    "confidence_score": 85,
    "key_takeaway": "Une phrase resumant l'apport principal de ce jugement"
}
"""


# ============================================================
# WORKFLOW
# ============================================================

class SummarizeJudgmentWorkflow:
    """
    Workflow pour resumer un jugement juridique.

    Ce workflow orchestre 4 agents specialises pour produire
    un case brief structure.
    """

    def __init__(self, model: Any, db: Optional[Any] = None):
        """
        Initialise le workflow.

        Args:
            model: Instance de modele Agno (Ollama, Claude, etc.)
            db: Instance de base de donnees Agno (optionnel, pour persistance)
        """
        self.model = model
        self.db = db

        # Creer les agents
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

        # Creer le workflow
        workflow_kwargs = {
            "name": "SummarizeJudgment",
            "agents": [self.extractor, self.analyzer, self.synthesizer, self.formatter],
        }

        if db:
            workflow_kwargs["db"] = db

        self.workflow = Workflow(**workflow_kwargs)

    def run(self, judgment_text: str) -> dict:
        """
        Execute le workflow sur un texte de jugement.

        Args:
            judgment_text: Texte complet du jugement a analyser

        Returns:
            dict: Case brief structure avec score de confiance
        """
        logger.info("Starting judgment summarization workflow")

        try:
            # Etape 1: Extraction des informations de base
            logger.info("Step 1/4: Extracting basic information...")
            extraction_result = self.extractor.run(
                f"Analyse ce jugement et extrait les informations:\n\n{judgment_text}"
            )
            extraction_data = self._parse_json_response(extraction_result.content)

            # Etape 2: Analyse des faits et questions en litige
            logger.info("Step 2/4: Analyzing facts and issues...")
            analysis_result = self.analyzer.run(
                f"Analyse ce jugement:\n\n{judgment_text}"
            )
            analysis_data = self._parse_json_response(analysis_result.content)

            # Etape 3: Synthese du ratio decidendi
            logger.info("Step 3/4: Synthesizing ratio decidendi...")
            synthesis_result = self.synthesizer.run(
                f"Synthetise ce jugement:\n\n{judgment_text}"
            )
            synthesis_data = self._parse_json_response(synthesis_result.content)

            # Etape 4: Formatage final
            logger.info("Step 4/4: Formatting case brief...")
            combined_data = {
                "extraction": extraction_data,
                "analysis": analysis_data,
                "synthesis": synthesis_data
            }
            format_result = self.formatter.run(
                f"Genere le case brief final a partir de ces donnees:\n\n{json.dumps(combined_data, ensure_ascii=False, indent=2)}"
            )
            final_data = self._parse_json_response(format_result.content)

            logger.info("Workflow completed successfully")
            return {
                "success": True,
                "case_brief": final_data.get("case_brief", {}),
                "confidence_score": final_data.get("confidence_score", 0) / 100,  # Normaliser 0-1
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

    def _parse_json_response(self, content: str) -> dict:
        """
        Parse une reponse JSON d'un agent.

        Args:
            content: Reponse de l'agent (peut contenir du texte autour du JSON)

        Returns:
            dict: Donnees JSON parsees
        """
        try:
            # Essayer de parser directement
            return json.loads(content)
        except json.JSONDecodeError:
            # Chercher un bloc JSON dans le texte
            import re
            json_match = re.search(r'\{[\s\S]*\}', content)
            if json_match:
                try:
                    return json.loads(json_match.group())
                except json.JSONDecodeError:
                    pass

            logger.warning(f"Could not parse JSON from response: {content[:200]}...")
            return {}


def create_summarize_workflow(model: Any, db: Optional[Any] = None) -> SummarizeJudgmentWorkflow:
    """
    Factory function pour creer un workflow de resume.

    Args:
        model: Instance de modele Agno
        db: Instance de base de donnees Agno (optionnel)

    Returns:
        SummarizeJudgmentWorkflow: Instance du workflow
    """
    return SummarizeJudgmentWorkflow(model=model, db=db)


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":
    # Test avec un exemple simple
    import sys
    sys.path.insert(0, str(__file__).rsplit("/", 2)[0])

    from services.model_factory import create_model

    # Creer un modele Ollama
    model = create_model("ollama:qwen2.5:7b")

    # Creer le workflow
    workflow = create_summarize_workflow(model=model)

    # Texte de test (exemple simplifie)
    test_judgment = """
    COUR SUPERIEURE DU QUEBEC

    Dossier: 500-17-123456-789

    DATE: 15 janvier 2024

    JUGE: L'honorable Jean Tremblay, j.c.s.

    ENTRE:
    MARIE DUPONT
    Demanderesse

    ET:
    JEAN LAVOIE
    Defendeur

    JUGEMENT

    [1] La demanderesse reclame des dommages-interets de 50 000 $ pour
    bris de contrat suite a la vente d'un vehicule defectueux.

    FAITS

    [2] Le 1er juin 2023, la demanderesse a achete du defendeur un vehicule
    d'occasion pour la somme de 15 000 $.

    [3] Le defendeur a garanti que le vehicule etait en bon etat mecanique.

    [4] Deux semaines apres l'achat, le moteur a cesse de fonctionner.
    L'expertise revele un vice cache connu du vendeur.

    QUESTION EN LITIGE

    [5] Le defendeur est-il responsable du vice cache?

    ANALYSE

    [6] Selon l'article 1726 C.c.Q., le vendeur est tenu de garantir
    l'acheteur contre les vices caches.

    [7] La preuve demontre que le defendeur connaissait le vice.

    CONCLUSION

    [8] ACCUEILLE l'action de la demanderesse;
    [9] CONDAMNE le defendeur a payer 25 000 $ plus interets.

    ________________________________
    Jean Tremblay, j.c.s.
    """

    print("=" * 60)
    print("TEST: Workflow de resume de jugement")
    print("=" * 60)

    result = workflow.run(test_judgment)

    if result["success"]:
        print("\n✅ Succes!")
        print(f"\nScore de confiance: {result['confidence_score']:.0%}")
        print(f"\nA retenir: {result['key_takeaway']}")
        print("\nCase Brief:")
        print(json.dumps(result["case_brief"], ensure_ascii=False, indent=2))
    else:
        print(f"\n❌ Erreur: {result['error']}")
