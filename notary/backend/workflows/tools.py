"""
Tools (fonctions) utilisées par les agents Agno.

Ces tools permettent aux agents d'effectuer des actions concrètes:
- Extraire du texte des PDFs (pypdf ou Docling)
- Parser des dates, montants, noms
- Vérifier des registres (simulé pour le MVP)
"""

import re
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Literal

from pypdf import PdfReader

logger = logging.getLogger(__name__)


# ========================================
# EXTRACTION DE DONNÉES DES PDFS
# ========================================

def extraire_texte_pdf(chemin_pdf: str) -> str:
    """
    Extrait tout le texte d'un fichier PDF.

    Args:
        chemin_pdf: Chemin vers le fichier PDF

    Returns:
        Texte complet extrait du PDF

    Raises:
        FileNotFoundError: Si le fichier n'existe pas
        Exception: Si le PDF ne peut pas être lu
    """
    chemin = Path(chemin_pdf)

    if not chemin.exists():
        raise FileNotFoundError(f"Fichier non trouvé: {chemin_pdf}")

    try:
        reader = PdfReader(str(chemin))
        texte_complet = ""

        for page in reader.pages:
            texte_complet += page.extract_text() + "\n"

        return texte_complet.strip()

    except Exception as e:
        raise Exception(f"Erreur lors de la lecture du PDF: {str(e)}")


def extraire_texte_pdf_avance(
    chemin_pdf: str,
    methode: Literal["pypdf", "docling-standard", "docling-vlm"] = "pypdf",
    use_ocr: bool = False,
) -> dict:
    """
    Extrait le texte d'un PDF avec la methode specifiee.

    Args:
        chemin_pdf: Chemin vers le fichier PDF
        methode: Methode d'extraction:
            - pypdf: Extraction basique (rapide, texte simple)
            - docling-standard: Docling standard (tableaux, layout)
            - docling-vlm: Docling VLM/Granite (OCR avance, PDFs scannes)
        use_ocr: Activer l'OCR (pour docling seulement)

    Returns:
        dict avec:
            - texte: Texte extrait
            - markdown: Texte en markdown (si docling)
            - tableaux: Liste des tableaux extraits (si docling)
            - methode: Methode utilisee
            - success: True si extraction reussie
            - error: Message d'erreur si echec
    """
    chemin = Path(chemin_pdf)

    if not chemin.exists():
        return {
            "texte": "",
            "markdown": "",
            "tableaux": [],
            "methode": methode,
            "success": False,
            "error": f"Fichier non trouve: {chemin_pdf}"
        }

    # Methode pypdf (par defaut, toujours disponible)
    if methode == "pypdf":
        try:
            reader = PdfReader(str(chemin))
            texte_complet = ""
            for page in reader.pages:
                texte_complet += page.extract_text() + "\n"

            return {
                "texte": texte_complet.strip(),
                "markdown": texte_complet.strip(),
                "tableaux": [],
                "methode": "pypdf",
                "success": True,
                "error": None
            }
        except Exception as e:
            return {
                "texte": "",
                "markdown": "",
                "tableaux": [],
                "methode": "pypdf",
                "success": False,
                "error": str(e)
            }

    # Methodes Docling
    if methode in ["docling-standard", "docling-vlm"]:
        try:
            from services.docling_service import DoclingService

            use_vlm = (methode == "docling-vlm")
            service = DoclingService(use_vlm=use_vlm)

            if not service.is_available():
                # Fallback vers pypdf si Docling non installe
                logger.warning("Docling non disponible, fallback vers pypdf")
                return extraire_texte_pdf_avance(chemin_pdf, methode="pypdf")

            # Extraction synchrone (Docling n'est pas async)
            import asyncio
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Si dans un contexte async, creer une tache
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    result = pool.submit(
                        lambda: asyncio.run(service.extract_pdf(chemin_pdf))
                    ).result()
            else:
                result = asyncio.run(service.extract_pdf(chemin_pdf))

            if result.success:
                return {
                    "texte": result.text,
                    "markdown": result.markdown,
                    "tableaux": result.tables,
                    "methode": result.extraction_method,
                    "success": True,
                    "error": None,
                    "metadata": result.metadata
                }
            else:
                # Fallback vers pypdf en cas d'erreur Docling
                logger.warning(f"Erreur Docling: {result.error}, fallback vers pypdf")
                return extraire_texte_pdf_avance(chemin_pdf, methode="pypdf")

        except ImportError:
            logger.warning("Module docling non installe, fallback vers pypdf")
            return extraire_texte_pdf_avance(chemin_pdf, methode="pypdf")
        except Exception as e:
            logger.error(f"Erreur extraction Docling: {e}")
            return extraire_texte_pdf_avance(chemin_pdf, methode="pypdf")

    # Methode non reconnue
    return {
        "texte": "",
        "markdown": "",
        "tableaux": [],
        "methode": methode,
        "success": False,
        "error": f"Methode non reconnue: {methode}"
    }


# ========================================
# EXTRACTION DE MONTANTS
# ========================================

def extraire_montants(texte: str) -> list[dict[str, any]]:
    """
    Extrait tous les montants d'argent d'un texte.

    Formats reconnus:
    - 450,000 $
    - 450 000 $
    - $450,000
    - 450000$
    - 450 000.00 $

    Args:
        texte: Texte à analyser

    Returns:
        Liste de dictionnaires avec:
        - montant: Le montant numérique
        - format: Le format original trouvé
        - contexte: Quelques mots autour du montant
    """
    montants = []

    # Patterns pour différents formats de montants
    patterns = [
        # 450,000 $ ou 450 000 $
        r'([\d\s,]+)\s*\$',
        # $450,000
        r'\$\s*([\d\s,]+)',
        # 450000$
        r'(\d+)\$',
    ]

    for pattern in patterns:
        matches = re.finditer(pattern, texte)

        for match in matches:
            montant_str = match.group(1).replace(' ', '').replace(',', '')

            try:
                montant_numerique = float(montant_str)

                # Contexte: 30 caractères avant et après
                start = max(0, match.start() - 30)
                end = min(len(texte), match.end() + 30)
                contexte = texte[start:end].strip()

                montants.append({
                    "montant": montant_numerique,
                    "format_original": match.group(0),
                    "contexte": contexte
                })

            except ValueError:
                continue

    return montants


# ========================================
# EXTRACTION DE DATES
# ========================================

def extraire_dates(texte: str) -> list[dict[str, any]]:
    """
    Extrait toutes les dates d'un texte.

    Formats reconnus:
    - 2024-01-15
    - 15 janvier 2024
    - 15/01/2024
    - 01/15/2024

    Args:
        texte: Texte à analyser

    Returns:
        Liste de dictionnaires avec:
        - date: Date au format ISO (YYYY-MM-DD)
        - format_original: Format trouvé dans le texte
        - contexte: Quelques mots autour
    """
    dates = []

    # Mois en français
    mois_fr = {
        'janvier': '01', 'février': '02', 'mars': '03', 'avril': '04',
        'mai': '05', 'juin': '06', 'juillet': '07', 'août': '08',
        'septembre': '09', 'octobre': '10', 'novembre': '11', 'décembre': '12'
    }

    # Pattern 1: 15 janvier 2024
    pattern_fr = r'(\d{1,2})\s+(janvier|février|mars|avril|mai|juin|juillet|août|septembre|octobre|novembre|décembre)\s+(\d{4})'
    for match in re.finditer(pattern_fr, texte, re.IGNORECASE):
        jour = match.group(1).zfill(2)
        mois = mois_fr[match.group(2).lower()]
        annee = match.group(3)

        date_iso = f"{annee}-{mois}-{jour}"

        start = max(0, match.start() - 30)
        end = min(len(texte), match.end() + 30)
        contexte = texte[start:end].strip()

        dates.append({
            "date": date_iso,
            "format_original": match.group(0),
            "contexte": contexte
        })

    # Pattern 2: 2024-01-15
    pattern_iso = r'(\d{4})-(\d{2})-(\d{2})'
    for match in re.finditer(pattern_iso, texte):
        dates.append({
            "date": match.group(0),
            "format_original": match.group(0),
            "contexte": texte[max(0, match.start()-30):match.end()+30].strip()
        })

    # Pattern 3: 15/01/2024 ou 01/15/2024
    pattern_slash = r'(\d{1,2})/(\d{1,2})/(\d{4})'
    for match in re.finditer(pattern_slash, texte):
        # Ambigu: suppose jour/mois/année (standard canadien)
        jour = match.group(1).zfill(2)
        mois = match.group(2).zfill(2)
        annee = match.group(3)

        date_iso = f"{annee}-{mois}-{jour}"

        dates.append({
            "date": date_iso,
            "format_original": match.group(0),
            "contexte": texte[max(0, match.start()-30):match.end()+30].strip(),
            "note": "Format ambigu, suppose JJ/MM/AAAA"
        })

    return dates


# ========================================
# EXTRACTION DE NOMS
# ========================================

def extraire_noms(texte: str) -> list[dict[str, str]]:
    """
    Extrait les noms de personnes d'un texte.

    Stratégie:
    - Cherche des patterns comme "M./Mme Prénom Nom"
    - Cherche des mots en majuscules (noms de famille)
    - Utilise des indices contextuels (vendeur, acheteur, notaire)

    Args:
        texte: Texte à analyser

    Returns:
        Liste de dictionnaires avec:
        - nom: Le nom complet
        - role: Role identifié (vendeur, acheteur, notaire, inconnu)
        - contexte: Quelques mots autour
    """
    noms = []

    # Pattern 1: M./Mme/Me Prénom Nom
    pattern_titre = r'(M\.|Mme|Me)\s+([A-Z][a-zé]+)\s+([A-Z][A-ZÉ]+)'
    for match in re.finditer(pattern_titre, texte):
        titre = match.group(1)
        prenom = match.group(2)
        nom = match.group(3)

        # Déterminer le rôle basé sur le contexte
        contexte = texte[max(0, match.start()-50):match.end()+50].lower()
        role = "inconnu"

        if "vendeur" in contexte or "vend" in contexte:
            role = "vendeur"
        elif "acheteur" in contexte or "acquéreur" in contexte:
            role = "acheteur"
        elif "notaire" in contexte or "me " in contexte.lower():
            role = "notaire"

        noms.append({
            "nom": f"{titre} {prenom} {nom}",
            "role": role,
            "contexte": contexte.strip()
        })

    # Pattern 2: NOM en majuscules (nom de famille)
    # (Plus basique, pour détecter ce qu'on aurait manqué)
    pattern_majuscules = r'\b([A-Z]{2,})\b'
    for match in re.finditer(pattern_majuscules, texte):
        nom_famille = match.group(1)

        # Ignorer les mots courants en majuscules
        mots_ignores = {'ENTRE', 'PRIX', 'DATE', 'ACTE', 'VENTE', 'ACHAT', 'QUEBEC'}
        if nom_famille in mots_ignores:
            continue

        # Vérifier si déjà capturé
        if any(nom_famille in n["nom"] for n in noms):
            continue

        contexte = texte[max(0, match.start()-30):match.end()+30]

        noms.append({
            "nom": nom_famille,
            "role": "inconnu",
            "contexte": contexte.strip()
        })

    return noms


# ========================================
# EXTRACTION D'ADRESSES
# ========================================

def extraire_adresses(texte: str) -> list[dict[str, str]]:
    """
    Extrait les adresses de propriété d'un texte.

    Cherche des patterns typiques:
    - Numéro + rue + ville + code postal
    - Ex: 123 rue Principale, Montréal, QC H1A 2B3

    Args:
        texte: Texte à analyser

    Returns:
        Liste de dictionnaires avec:
        - adresse_complete: L'adresse formatée
        - numero_civique: Le numéro
        - rue: Nom de rue
        - ville: Ville
        - code_postal: Code postal (si trouvé)
    """
    adresses = []

    # Pattern: 123 rue/avenue/boulevard Nom, Ville, QC H1A 2B3
    pattern = r'(\d+)\s+(rue|avenue|boulevard|av\.|boul\.)\s+([A-Za-zÉéèêàâ\s\-]+),\s+([A-Za-zÉéèêàâ\s\-]+)(?:,\s*(?:QC|Québec))?\s*([A-Z]\d[A-Z]\s*\d[A-Z]\d)?'

    for match in re.finditer(pattern, texte, re.IGNORECASE):
        numero = match.group(1)
        type_rue = match.group(2)
        nom_rue = match.group(3).strip()
        ville = match.group(4).strip()
        code_postal = match.group(5).strip() if match.group(5) else None

        adresse_complete = f"{numero} {type_rue} {nom_rue}, {ville}"
        if code_postal:
            adresse_complete += f", QC {code_postal}"

        adresses.append({
            "adresse_complete": adresse_complete,
            "numero_civique": numero,
            "rue": f"{type_rue} {nom_rue}",
            "ville": ville,
            "code_postal": code_postal
        })

    return adresses


# ========================================
# VÉRIFICATIONS (SIMULÉES POUR LE MVP)
# ========================================

def verifier_registre_foncier(adresse: str) -> dict[str, any]:
    """
    Vérifie les informations au registre foncier du Québec.

    ⚠️  SIMULÉ POUR LE MVP
    En production, ceci ferait un vrai appel API au registre foncier.

    Args:
        adresse: Adresse de la propriété

    Returns:
        Informations du registre (simulées)
    """
    # Simulation pour le MVP
    return {
        "adresse": adresse,
        "proprietaire_actuel": "SIMULATION - À VÉRIFIER",
        "charges": [],
        "hypotheques": [],
        "servitudes": [],
        "date_derniere_transaction": "2020-01-15",
        "valeur_municipale": 450000,
        "note": "⚠️  Données simulées - Vérification réelle requise"
    }


def calculer_droits_mutation(prix_vente: float, type_propriete: str = "residentielle") -> dict[str, float]:
    """
    Calcule les droits de mutation (taxe de bienvenue) au Québec.

    Basé sur les taux de 2024 à Montréal:
    - 0-58,900$: 0.5%
    - 58,900-117,800$: 1.0%
    - 117,800+: 1.5%

    Args:
        prix_vente: Prix de vente de la propriété
        type_propriete: Type de propriété

    Returns:
        Dictionnaire avec les calculs
    """
    # Tranches de 2024
    tranche1 = 58900
    tranche2 = 117800

    droits = 0.0

    if prix_vente <= tranche1:
        droits = prix_vente * 0.005
    elif prix_vente <= tranche2:
        droits = (tranche1 * 0.005) + ((prix_vente - tranche1) * 0.01)
    else:
        droits = (tranche1 * 0.005) + ((tranche2 - tranche1) * 0.01) + ((prix_vente - tranche2) * 0.015)

    return {
        "prix_vente": prix_vente,
        "droits_mutation": round(droits, 2),
        "taux_effectif": round((droits / prix_vente) * 100, 3),
        "type_propriete": type_propriete,
        "note": "Calcul basé sur les taux de Montréal 2024"
    }
