"""
Tool Agno pour la validation des citations juridiques.

Permet au Validateur de vérifier l'existence des citations légales
et de prévenir les hallucinations dans les réponses juridiques.
"""

import re
import logging
from typing import Optional

from agno.tools import tool

from services.document_indexing_service import get_document_indexing_service
from services.surreal_service import get_surreal_service
from tools.caij_search_tool import _search_caij_implementation

logger = logging.getLogger(__name__)

# Patterns pour les citations juridiques québécoises
CCQ_ARTICLE_PATTERN = re.compile(
    r"(?:art(?:icle)?\.?\s*)?(\d+(?:\.\d+)?)\s*(?:C\.?c\.?Q\.?|Code civil du Québec)|"
    r"(?:art(?:icle)?\.?\s*)(\d+(?:\.\d+)?)\s+du\s+Code\s+civil(?:\s+du\s+Québec)?",
    re.IGNORECASE
)

JURISPRUDENCE_PATTERN = re.compile(
    r"([A-ZÀ-Ü][a-zà-ü]+)\s+c\.\s+([A-ZÀ-Ü][a-zà-ü]+)(?:,?\s*(\d{4})\s*(QC(?:CA|CS|CQ|TDP)?|SCR?)?)?",
    re.IGNORECASE
)

LOI_PATTERN = re.compile(
    r"L\.?R\.?Q\.?\s*,?\s*c\.?\s*([A-Z]-?\d+(?:\.\d+)?)",
    re.IGNORECASE
)


def _extract_citations_from_text(text: str) -> dict:
    """
    Extrait les citations juridiques d'un texte.

    Returns:
        Dict avec 'articles', 'jurisprudence', 'lois' comme clés.
    """
    citations = {
        "articles": [],
        "jurisprudence": [],
        "lois": []
    }

    # Extraire articles C.c.Q.
    for match in CCQ_ARTICLE_PATTERN.finditer(text):
        # The regex has two capture groups, one for each pattern variant
        article_num = match.group(1) or match.group(2)
        if article_num:
            citations["articles"].append(f"art. {article_num} C.c.Q.")

    # Extraire jurisprudence (format: Partie c. Partie, année tribunal)
    for match in JURISPRUDENCE_PATTERN.finditer(text):
        partie1 = match.group(1)
        partie2 = match.group(2)
        annee = match.group(3) or ""
        tribunal = match.group(4) or ""
        citation = f"{partie1} c. {partie2}"
        if annee:
            citation += f", {annee}"
        if tribunal:
            citation += f" {tribunal}"
        citations["jurisprudence"].append(citation)

    # Extraire lois (format: L.R.Q., c. X-1)
    for match in LOI_PATTERN.finditer(text):
        chapitre = match.group(1)
        citations["lois"].append(f"L.R.Q., c. {chapitre}")

    # Dédupliquer
    citations["articles"] = list(set(citations["articles"]))
    citations["jurisprudence"] = list(set(citations["jurisprudence"]))
    citations["lois"] = list(set(citations["lois"]))

    return citations


async def _verify_article_ccq(article_num: str) -> dict:
    """
    Vérifie si un article du Code civil du Québec existe.

    Le C.c.Q. contient les articles 1 à 3168.
    Certains articles ont été abrogés mais les numéros existent.
    """
    try:
        # Extraire le numéro principal (avant le point si applicable)
        num_str = article_num.split(".")[0]
        num = int(num_str)

        # Le C.c.Q. va de 1 à 3168
        if 1 <= num <= 3168:
            return {
                "citation": f"art. {article_num} C.c.Q.",
                "valid": True,
                "source": "Code civil du Québec",
                "note": "Numéro d'article dans la plage valide (1-3168)"
            }
        else:
            return {
                "citation": f"art. {article_num} C.c.Q.",
                "valid": False,
                "source": None,
                "note": f"Article hors plage: le C.c.Q. contient les articles 1 à 3168"
            }
    except ValueError:
        return {
            "citation": f"art. {article_num} C.c.Q.",
            "valid": False,
            "source": None,
            "note": "Format d'article invalide"
        }


async def _verify_jurisprudence_in_documents(
    citation: str,
    case_id: str
) -> dict:
    """
    Vérifie si une jurisprudence est mentionnée dans les documents du cours.
    """
    try:
        indexing_service = get_document_indexing_service()

        # Normaliser case_id
        if not case_id.startswith("case:"):
            case_id = f"case:{case_id}"

        # Recherche sémantique
        results = await indexing_service.search_similar(
            query_text=citation,
            case_id=case_id,
            top_k=3,
            min_similarity=0.6
        )

        if results:
            best_match = results[0]
            return {
                "citation": citation,
                "valid": True,
                "source": f"Documents du cours (similarité: {int(best_match['similarity_score'] * 100)}%)",
                "note": f"Trouvé dans: {best_match.get('document_id', 'document inconnu')}"
            }

        return {
            "citation": citation,
            "valid": None,  # Indéterminé
            "source": None,
            "note": "Non trouvé dans les documents du cours"
        }

    except Exception as e:
        logger.error(f"Erreur vérification jurisprudence: {e}")
        return {
            "citation": citation,
            "valid": None,
            "source": None,
            "note": f"Erreur de vérification: {str(e)}"
        }


async def _verify_jurisprudence_in_caij(citation: str) -> dict:
    """
    Vérifie si une jurisprudence existe sur CAIJ.
    """
    try:
        # Recherche sur CAIJ
        result = await _search_caij_implementation(citation, max_results=3)

        if "Aucun résultat" in result or "Erreur" in result:
            return {
                "citation": citation,
                "valid": None,
                "source": None,
                "note": "Non trouvé sur CAIJ"
            }

        return {
            "citation": citation,
            "valid": True,
            "source": "CAIJ (jurisprudence québécoise)",
            "note": "Trouvé dans la base CAIJ"
        }

    except Exception as e:
        logger.error(f"Erreur vérification CAIJ: {e}")
        return {
            "citation": citation,
            "valid": None,
            "source": None,
            "note": f"Erreur CAIJ: {str(e)}"
        }


@tool
async def verify_legal_citations(
    text_to_verify: str,
    case_id: str = ""
) -> str:
    """
    Vérifie les citations juridiques dans un texte.

    Extrait automatiquement les citations (articles C.c.Q., jurisprudence, lois)
    et vérifie leur existence dans les sources disponibles.

    UTILISATION:
    - Appeler après avoir reçu une réponse du Chercheur
    - Vérifier avant de présenter les résultats à l'utilisateur
    - Signaler toute citation non vérifiable

    Args:
        text_to_verify: Texte contenant les citations à vérifier
        case_id: ID du cours pour recherche dans documents locaux (optionnel)

    Returns:
        Rapport de validation détaillé avec statut de chaque citation.

    Examples:
        >>> await verify_legal_citations("L'article 1726 C.c.Q. prévoit les vices cachés...")
        >>> await verify_legal_citations("Selon Tremblay c. Gagnon, 2024 QCCS...", "course:abc123")
    """
    try:
        logger.info(f"[verify_legal_citations] Vérification du texte ({len(text_to_verify)} chars)")

        # Extraire les citations
        citations = _extract_citations_from_text(text_to_verify)
        total_citations = (
            len(citations["articles"]) +
            len(citations["jurisprudence"]) +
            len(citations["lois"])
        )

        if total_citations == 0:
            return """## Rapport de validation

**Aucune citation juridique détectée dans le texte.**

Patterns recherchés:
- Articles du Code civil du Québec (art. X C.c.Q.)
- Jurisprudence (Partie c. Partie, année tribunal)
- Lois refondues (L.R.Q., c. X-X)

Si le texte contient des références juridiques dans un format différent,
elles n'ont pas pu être analysées automatiquement."""

        results = {
            "verified": [],
            "unverified": [],
            "invalid": []
        }

        # Vérifier les articles C.c.Q.
        for article in citations["articles"]:
            # Extraire le numéro
            match = re.search(r"(\d+(?:\.\d+)?)", article)
            if match:
                article_num = match.group(1)
                result = await _verify_article_ccq(article_num)

                if result["valid"] is True:
                    results["verified"].append(result)
                elif result["valid"] is False:
                    results["invalid"].append(result)
                else:
                    results["unverified"].append(result)

        # Vérifier la jurisprudence
        for juris in citations["jurisprudence"]:
            # D'abord chercher dans les documents locaux
            if case_id:
                result = await _verify_jurisprudence_in_documents(juris, case_id)
                if result["valid"] is True:
                    results["verified"].append(result)
                    continue

            # Sinon chercher sur CAIJ
            result = await _verify_jurisprudence_in_caij(juris)
            if result["valid"] is True:
                results["verified"].append(result)
            else:
                results["unverified"].append(result)

        # Les lois sont notées comme non vérifiées (pas de source automatique)
        for loi in citations["lois"]:
            results["unverified"].append({
                "citation": loi,
                "valid": None,
                "source": None,
                "note": "Vérification automatique non disponible pour les lois"
            })

        # Construire le rapport
        output = ["## Rapport de validation\n"]
        output.append(f"**{total_citations} citation(s) analysée(s)**\n")

        # Citations vérifiées
        if results["verified"]:
            output.append("### Citations vérifiées ✅\n")
            for r in results["verified"]:
                output.append(f"- **{r['citation']}**")
                output.append(f"  - Source: {r['source']}")
                if r.get("note"):
                    output.append(f"  - Note: {r['note']}")
                output.append("")

        # Citations invalides
        if results["invalid"]:
            output.append("### Citations invalides ❌\n")
            for r in results["invalid"]:
                output.append(f"- **{r['citation']}**")
                output.append(f"  - Raison: {r['note']}")
                output.append("")

        # Citations non vérifiées
        if results["unverified"]:
            output.append("### Citations non vérifiées ⚠️\n")
            for r in results["unverified"]:
                output.append(f"- **{r['citation']}**")
                output.append(f"  - Statut: {r['note']}")
                output.append("")

        # Niveau de fiabilité
        verified_count = len(results["verified"])
        invalid_count = len(results["invalid"])
        unverified_count = len(results["unverified"])

        if invalid_count > 0:
            fiabilite = "⚠️ **BASSE** - Citations invalides détectées"
        elif unverified_count > verified_count:
            fiabilite = "🔶 **MOYENNE** - Plusieurs citations non vérifiables"
        elif verified_count > 0 and unverified_count == 0:
            fiabilite = "✅ **HAUTE** - Toutes les citations vérifiées"
        else:
            fiabilite = "🔶 **MOYENNE** - Certaines citations non vérifiables"

        output.append("---\n")
        output.append(f"### Fiabilité globale: {fiabilite}\n")
        output.append(f"- Vérifiées: {verified_count}")
        output.append(f"- Non vérifiées: {unverified_count}")
        output.append(f"- Invalides: {invalid_count}")

        return "\n".join(output)

    except Exception as e:
        logger.error(f"Erreur verify_legal_citations: {e}", exc_info=True)
        return f"❌ Erreur lors de la vérification des citations: {str(e)}"


@tool
async def extract_citations(text: str) -> str:
    """
    Extrait les citations juridiques d'un texte sans les vérifier.

    Utile pour identifier rapidement les références légales mentionnées.

    Args:
        text: Texte à analyser

    Returns:
        Liste des citations extraites par catégorie.
    """
    citations = _extract_citations_from_text(text)

    output = ["## Citations juridiques extraites\n"]

    if citations["articles"]:
        output.append("### Articles du Code civil du Québec")
        for art in citations["articles"]:
            output.append(f"- {art}")
        output.append("")

    if citations["jurisprudence"]:
        output.append("### Jurisprudence")
        for juris in citations["jurisprudence"]:
            output.append(f"- {juris}")
        output.append("")

    if citations["lois"]:
        output.append("### Lois et règlements")
        for loi in citations["lois"]:
            output.append(f"- {loi}")
        output.append("")

    total = len(citations["articles"]) + len(citations["jurisprudence"]) + len(citations["lois"])
    if total == 0:
        output.append("*Aucune citation juridique détectée.*")
    else:
        output.append(f"\n**Total: {total} citation(s)**")

    return "\n".join(output)
