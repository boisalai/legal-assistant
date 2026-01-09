"""
Tool Agno pour l'analyse juridique.

Permet à l'Analyste Juridique d'interpréter les textes légaux,
d'identifier les articles applicables et d'extraire la doctrine.
"""

import re
import logging
from typing import Optional

from agno.tools import tool

logger = logging.getLogger(__name__)

# Base de connaissances des articles C.c.Q. par domaine
CCQ_DOMAINS = {
    "vices_caches": {
        "articles": ["1726", "1727", "1728", "1729", "1730", "1731", "1732", "1733"],
        "description": "Garantie de qualité - Vices cachés",
        "keywords": ["vice caché", "vices cachés", "défaut caché", "garantie légale", "impropre à l'usage"],
    },
    "vente_immobiliere": {
        "articles": ["1708", "1709", "1710", "1711", "1712", "1713", "1714", "1715", "1716", "1717", "1718", "1719", "1720", "1721", "1722", "1723", "1724", "1725"],
        "description": "Contrat de vente - Dispositions générales",
        "keywords": ["vente", "vendeur", "acheteur", "transfert", "propriété", "prix"],
    },
    "obligations_vendeur": {
        "articles": ["1716", "1717", "1718", "1719", "1720", "1721", "1722", "1723", "1724", "1725", "1726", "1727", "1728", "1729", "1730", "1731", "1732", "1733"],
        "description": "Obligations du vendeur",
        "keywords": ["obligation", "délivrance", "garantie", "éviction", "qualité"],
    },
    "responsabilite_civile": {
        "articles": ["1457", "1458", "1459", "1460", "1461", "1462", "1463", "1464", "1465", "1466", "1467", "1468", "1469", "1470", "1471", "1472", "1473", "1474", "1475", "1476", "1477", "1478", "1479", "1480", "1481"],
        "description": "Responsabilité civile extracontractuelle et contractuelle",
        "keywords": ["responsabilité", "faute", "dommage", "préjudice", "réparation", "indemnisation"],
    },
    "contrat": {
        "articles": ["1377", "1378", "1379", "1380", "1381", "1382", "1383", "1384", "1385", "1386", "1387", "1388", "1389", "1390", "1391", "1392", "1393", "1394", "1395", "1396", "1397", "1398", "1399", "1400", "1401", "1402", "1403", "1404", "1405", "1406", "1407", "1408", "1409", "1410", "1411", "1412", "1413", "1414", "1415", "1416", "1417", "1418", "1419", "1420", "1421", "1422", "1423", "1424", "1425", "1426", "1427", "1428", "1429", "1430", "1431", "1432", "1433", "1434", "1435", "1436", "1437", "1438", "1439", "1440", "1441", "1442", "1443", "1444", "1445", "1446", "1447", "1448", "1449", "1450", "1451", "1452", "1453", "1454", "1455", "1456"],
        "description": "Formation et effets du contrat",
        "keywords": ["contrat", "consentement", "capacité", "objet", "cause", "nullité", "annulation"],
    },
    "bail": {
        "articles": ["1851", "1852", "1853", "1854", "1855", "1856", "1857", "1858", "1859", "1860", "1861", "1862", "1863", "1864", "1865", "1866", "1867", "1868", "1869", "1870", "1871", "1872", "1873", "1874", "1875", "1876", "1877", "1878", "1879", "1880", "1881", "1882", "1883", "1884", "1885", "1886", "1887", "1888", "1889", "1890", "1891", "1892", "1893", "1894", "1895", "1896", "1897", "1898", "1899", "1900", "1901", "1902", "1903", "1904", "1905", "1906", "1907", "1908", "1909", "1910", "1911", "1912", "1913", "1914", "1915", "1916", "1917", "1918", "1919", "1920", "1921", "1922", "1923", "1924", "1925", "1926", "1927", "1928", "1929", "1930", "1931", "1932", "1933", "1934", "1935", "1936", "1937", "1938", "1939", "1940"],
        "description": "Louage - Bail",
        "keywords": ["bail", "locateur", "locataire", "loyer", "logement", "résiliation"],
    },
    "hypotheque": {
        "articles": ["2660", "2661", "2662", "2663", "2664", "2665", "2666", "2667", "2668", "2669", "2670", "2671", "2672", "2673", "2674", "2675", "2676", "2677", "2678", "2679", "2680", "2681", "2682", "2683", "2684", "2685", "2686", "2687", "2688", "2689", "2690", "2691", "2692", "2693", "2694", "2695", "2696", "2697", "2698", "2699", "2700", "2701", "2702", "2703", "2704", "2705", "2706", "2707", "2708", "2709", "2710", "2711", "2712", "2713", "2714"],
        "description": "Hypothèque",
        "keywords": ["hypothèque", "créancier", "débiteur", "sûreté", "immeuble", "rang"],
    },
    "succession": {
        "articles": ["613", "614", "615", "616", "617", "618", "619", "620", "621", "622", "623", "624", "625", "626", "627", "628", "629", "630", "631", "632", "633", "634", "635", "636", "637", "638", "639", "640", "641", "642", "643", "644", "645", "646", "647", "648", "649", "650", "651", "652", "653", "654", "655", "656", "657", "658", "659", "660", "661", "662", "663", "664", "665", "666", "667", "668", "669", "670", "671", "672", "673", "674", "675", "676", "677", "678", "679", "680", "681", "682", "683", "684", "685", "686", "687", "688", "689", "690", "691", "692", "693", "694", "695", "696", "697", "698", "699", "700", "701", "702"],
        "description": "Successions",
        "keywords": ["succession", "héritier", "testament", "legs", "défunt", "patrimoine"],
    },
    "servitude": {
        "articles": ["1177", "1178", "1179", "1180", "1181", "1182", "1183", "1184", "1185", "1186", "1187", "1188", "1189", "1190", "1191", "1192", "1193", "1194"],
        "description": "Servitudes",
        "keywords": ["servitude", "fonds servant", "fonds dominant", "passage", "vue"],
    },
    "prescription": {
        "articles": ["2875", "2876", "2877", "2878", "2879", "2880", "2881", "2882", "2883", "2884", "2885", "2886", "2887", "2888", "2889", "2890", "2891", "2892", "2893", "2894", "2895", "2896", "2897", "2898", "2899", "2900", "2901", "2902", "2903", "2904", "2905", "2906", "2907", "2908", "2909", "2910", "2911", "2912", "2913", "2914", "2915", "2916", "2917", "2918", "2919", "2920", "2921", "2922", "2923", "2924", "2925", "2926", "2927", "2928", "2929", "2930", "2931", "2932", "2933"],
        "description": "Prescription acquisitive et extinctive",
        "keywords": ["prescription", "délai", "acquisitive", "extinctive", "possession"],
    },
}


def _identify_legal_domains(text: str) -> list[dict]:
    """
    Identifie les domaines juridiques pertinents dans un texte.

    Args:
        text: Texte à analyser

    Returns:
        Liste des domaines identifiés avec leur score de pertinence
    """
    text_lower = text.lower()
    results = []

    for domain_key, domain_info in CCQ_DOMAINS.items():
        score = 0
        matched_keywords = []

        for keyword in domain_info["keywords"]:
            if keyword.lower() in text_lower:
                score += 1
                matched_keywords.append(keyword)

        if score > 0:
            results.append({
                "domain": domain_key,
                "description": domain_info["description"],
                "articles": domain_info["articles"],
                "score": score,
                "matched_keywords": matched_keywords,
            })

    # Trier par score décroissant
    results.sort(key=lambda x: x["score"], reverse=True)

    return results


def _extract_legal_principles(text: str, domains: list[dict]) -> list[str]:
    """
    Extrait les principes juridiques applicables basés sur les domaines identifiés.
    """
    principles = []

    for domain in domains[:3]:  # Top 3 domains
        domain_key = domain["domain"]

        if domain_key == "vices_caches":
            principles.extend([
                "Le vendeur garantit que le bien est exempt de vices cachés (art. 1726 C.c.Q.)",
                "Le vice doit être grave, caché et antérieur à la vente",
                "L'acheteur peut demander la résolution ou une diminution du prix (art. 1728 C.c.Q.)",
                "Le vendeur professionnel est présumé connaître les vices (art. 1729 C.c.Q.)",
            ])
        elif domain_key == "responsabilite_civile":
            principles.extend([
                "Toute personne a le devoir de respecter les règles de conduite (art. 1457 C.c.Q.)",
                "La faute, le dommage et le lien causal doivent être prouvés",
                "La responsabilité peut être contractuelle ou extracontractuelle",
            ])
        elif domain_key == "contrat":
            principles.extend([
                "Le contrat se forme par l'échange de consentements (art. 1385 C.c.Q.)",
                "Les parties doivent avoir la capacité de contracter",
                "Le contrat lie les parties et doit être exécuté de bonne foi (art. 1434 C.c.Q.)",
            ])
        elif domain_key == "bail":
            principles.extend([
                "Le locateur doit délivrer le bien en bon état (art. 1854 C.c.Q.)",
                "Le locataire doit payer le loyer et user du bien avec prudence",
                "Le bail résidentiel est protégé par des dispositions impératives",
            ])
        elif domain_key == "hypotheque":
            principles.extend([
                "L'hypothèque grève un bien pour garantir une obligation (art. 2660 C.c.Q.)",
                "Elle confère au créancier le droit de suite et de préférence",
                "L'hypothèque doit être publiée pour être opposable aux tiers",
            ])
        elif domain_key == "succession":
            principles.extend([
                "La succession s'ouvre au décès (art. 613 C.c.Q.)",
                "L'héritier peut accepter ou renoncer à la succession",
                "Le testament doit respecter les formes prescrites",
            ])

    return list(set(principles))  # Dédupliquer


@tool
async def analyze_legal_text(
    text: str,
    context: str = ""
) -> str:
    """
    Analyse un texte juridique pour identifier les domaines, articles et principes applicables.

    Cet outil examine le contenu textuel et identifie:
    - Les domaines du droit concernés (vente, responsabilité, bail, etc.)
    - Les articles du Code civil du Québec potentiellement applicables
    - Les principes juridiques fondamentaux en jeu

    UTILISATION:
    - Appeler après avoir obtenu des résultats de recherche du Chercheur
    - Fournir le texte des sources trouvées pour analyse
    - Utiliser les résultats pour structurer la réponse juridique

    Args:
        text: Texte juridique à analyser (résultats de recherche, extraits de documents)
        context: Contexte additionnel (question originale de l'utilisateur)

    Returns:
        Analyse structurée avec domaines, articles et principes identifiés.

    Examples:
        >>> await analyze_legal_text("Le vendeur doit garantir l'acheteur contre les vices cachés...")
        >>> await analyze_legal_text(search_results, context="Question sur les vices cachés")
    """
    try:
        logger.info(f"[analyze_legal_text] Analyzing text ({len(text)} chars)")

        # Combiner texte et contexte pour l'analyse
        full_text = f"{context}\n\n{text}" if context else text

        # Identifier les domaines juridiques
        domains = _identify_legal_domains(full_text)

        if not domains:
            return """## Analyse juridique

**Aucun domaine juridique spécifique identifié** dans le texte fourni.

Le texte ne contient pas suffisamment de termes juridiques reconnaissables
pour identifier les domaines du Code civil du Québec applicables.

**Suggestion**: Reformulez la question avec des termes juridiques plus précis
ou fournissez plus de contexte sur la situation factuelle."""

        # Extraire les principes juridiques
        principles = _extract_legal_principles(full_text, domains)

        # Construire le rapport d'analyse
        output = ["## Analyse juridique\n"]

        # Domaines identifiés
        output.append("### Domaines du droit identifiés\n")
        for i, domain in enumerate(domains[:3], 1):
            output.append(f"**{i}. {domain['description']}** (pertinence: {domain['score']} mots-clés)")
            output.append(f"   - Mots-clés trouvés: {', '.join(domain['matched_keywords'])}")
            output.append(f"   - Articles C.c.Q.: {', '.join(domain['articles'][:5])}{'...' if len(domain['articles']) > 5 else ''}")
            output.append("")

        # Articles applicables (top 10)
        output.append("### Articles du Code civil potentiellement applicables\n")
        all_articles = []
        for domain in domains[:3]:
            all_articles.extend(domain["articles"][:5])
        unique_articles = list(dict.fromkeys(all_articles))[:10]

        for art in unique_articles:
            output.append(f"- **Art. {art} C.c.Q.**")
        output.append("")

        # Principes juridiques
        if principles:
            output.append("### Principes juridiques fondamentaux\n")
            for principle in principles[:5]:
                output.append(f"- {principle}")
            output.append("")

        # Recommandations
        output.append("### Recommandations d'analyse\n")
        output.append("Pour une analyse complète, il est recommandé de:")
        output.append("1. Consulter le texte exact des articles identifiés")
        output.append("2. Rechercher la jurisprudence récente sur ces questions")
        output.append("3. Vérifier si des exceptions ou dispositions particulières s'appliquent")

        return "\n".join(output)

    except Exception as e:
        logger.error(f"Erreur analyze_legal_text: {e}", exc_info=True)
        return f"❌ Erreur lors de l'analyse juridique: {str(e)}"


@tool
async def identify_applicable_articles(
    question: str,
    domain: str = ""
) -> str:
    """
    Identifie les articles du Code civil du Québec applicables à une question juridique.

    Analyse la question posée et retourne les articles C.c.Q. les plus pertinents
    avec une brève description de leur application.

    Args:
        question: Question juridique de l'utilisateur
        domain: Domaine juridique spécifique (optionnel: vente, bail, responsabilite, etc.)

    Returns:
        Liste des articles applicables avec explications.

    Examples:
        >>> await identify_applicable_articles("Puis-je annuler une vente pour vice caché?")
        >>> await identify_applicable_articles("Délai pour poursuivre", domain="prescription")
    """
    try:
        logger.info(f"[identify_applicable_articles] Question: {question[:50]}...")

        # Si un domaine est spécifié, utiliser directement
        if domain and domain.lower() in CCQ_DOMAINS:
            domains = [{
                "domain": domain.lower(),
                **CCQ_DOMAINS[domain.lower()],
                "score": 10,
                "matched_keywords": ["domaine spécifié"],
            }]
        else:
            domains = _identify_legal_domains(question)

        if not domains:
            return """## Articles applicables

**Impossible d'identifier les articles applicables** sans plus de contexte.

Veuillez préciser:
- La nature de la situation (vente, bail, responsabilité, etc.)
- Les faits pertinents
- Le type de recours envisagé"""

        output = ["## Articles du Code civil du Québec applicables\n"]

        for domain in domains[:2]:
            output.append(f"### {domain['description']}\n")

            # Afficher les articles principaux avec contexte
            articles = domain["articles"][:8]
            for art in articles:
                # Ajouter une description contextuelle
                desc = _get_article_description(art, domain["domain"])
                output.append(f"- **Art. {art} C.c.Q.** - {desc}")

            output.append("")

        output.append("---")
        output.append("*Note: Cette liste est indicative. Consultez le texte officiel des articles pour l'application exacte.*")

        return "\n".join(output)

    except Exception as e:
        logger.error(f"Erreur identify_applicable_articles: {e}", exc_info=True)
        return f"❌ Erreur: {str(e)}"


def _get_article_description(article: str, domain: str) -> str:
    """Retourne une description contextuelle d'un article."""
    descriptions = {
        # Vices cachés
        "1726": "Garantie de qualité - le bien doit être exempt de vices cachés",
        "1727": "Vice apparent vs vice caché",
        "1728": "Recours: résolution ou diminution du prix",
        "1729": "Présomption de connaissance du vendeur professionnel",
        "1730": "Exclusion de garantie et ses limites",
        "1731": "Vice connu de l'acheteur",
        "1732": "Délai pour dénoncer le vice",
        "1733": "Responsabilité du vendeur professionnel",

        # Responsabilité
        "1457": "Devoir général de ne pas causer préjudice à autrui",
        "1458": "Responsabilité contractuelle",
        "1459": "Titulaire de l'autorité parentale",
        "1463": "Responsabilité du commettant",
        "1465": "Gardien d'un bien",
        "1468": "Fabricant et vendeur professionnel",
        "1469": "Vice de sécurité",

        # Contrat
        "1377": "Règles applicables aux obligations",
        "1385": "Formation du contrat",
        "1399": "Consentement vicié",
        "1400": "Erreur",
        "1401": "Dol",
        "1402": "Crainte",
        "1434": "Exécution de bonne foi",

        # Prescription
        "2875": "Prescription acquisitive et extinctive",
        "2925": "Délai de prescription de droit commun (3 ans)",
        "2926": "Actions personnelles (3 ans)",
        "2927": "Préjudice corporel (3 ans)",
    }

    return descriptions.get(article, "Disposition applicable au domaine")
