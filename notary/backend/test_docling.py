#!/usr/bin/env python3
"""
Test comparatif des methodes d'extraction PDF.

Compare:
- pypdf (basique)
- docling-standard (tableaux, layout)
- docling-vlm (OCR avance)
"""

import time
from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch

# Ajouter le repertoire parent au path
import sys
sys.path.insert(0, str(Path(__file__).parent))

from workflows.tools import extraire_texte_pdf, extraire_texte_pdf_avance


def creer_pdf_test_complexe(output_path: str = "/tmp/test_notarial.pdf"):
    """Cree un PDF de test plus realiste avec tableaux."""
    c = canvas.Canvas(output_path, pagesize=letter)
    width, height = letter

    # En-tete
    c.setFont("Helvetica-Bold", 18)
    c.drawCentredString(width/2, height - 50, "PROMESSE D'ACHAT")
    c.setFont("Helvetica", 10)
    c.drawCentredString(width/2, height - 65, "Formulaire obligatoire de l'OACIQ")

    y = height - 100

    # Section Parties
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y, "1. IDENTIFICATION DES PARTIES")
    y -= 20

    c.setFont("Helvetica", 10)
    c.drawString(50, y, "VENDEUR:")
    c.drawString(150, y, "Jean-Pierre TREMBLAY")
    y -= 15
    c.drawString(150, y, "123, rue Sainte-Catherine Ouest")
    y -= 15
    c.drawString(150, y, "Montreal, QC H2X 1L4")
    y -= 25

    c.drawString(50, y, "ACHETEUR:")
    c.drawString(150, y, "Marie-Claude GAGNON")
    y -= 15
    c.drawString(150, y, "456, avenue du Parc")
    y -= 15
    c.drawString(150, y, "Montreal, QC H2W 1S6")
    y -= 30

    # Section Immeuble
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y, "2. DESIGNATION DE L'IMMEUBLE")
    y -= 20

    c.setFont("Helvetica", 10)
    c.drawString(50, y, "Adresse:")
    c.drawString(150, y, "789, boulevard Rene-Levesque Est, app. 1204")
    y -= 15
    c.drawString(150, y, "Montreal, QC H2L 2C3")
    y -= 15
    c.drawString(50, y, "Cadastre:")
    c.drawString(150, y, "Lot 1 234 567, Cadastre du Quebec")
    y -= 15
    c.drawString(50, y, "Circonscription:")
    c.drawString(150, y, "Montreal")
    y -= 30

    # Section Prix (tableau)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y, "3. PRIX ET CONDITIONS FINANCIERES")
    y -= 25

    # Tableau des montants
    c.setFont("Helvetica", 10)
    tableau_data = [
        ("Prix de vente:", "575 000,00 $"),
        ("Depot initial:", "25 000,00 $"),
        ("Solde a la signature:", "550 000,00 $"),
        ("Hypotheque a obtenir:", "460 000,00 $"),
        ("Mise de fonds:", "115 000,00 $"),
        ("Taxes municipales (2024):", "4 250,00 $"),
        ("Taxes scolaires (2024):", "875,00 $"),
        ("Droits de mutation estimes:", "8 625,00 $"),
    ]

    for label, value in tableau_data:
        c.drawString(50, y, label)
        c.drawRightString(350, y, value)
        y -= 15

    y -= 20

    # Section Dates
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y, "4. DATES IMPORTANTES")
    y -= 20

    c.setFont("Helvetica", 10)
    dates_data = [
        ("Date de la promesse:", "15 novembre 2025"),
        ("Inspection (avant le):", "25 novembre 2025"),
        ("Financement (avant le):", "1er decembre 2025"),
        ("Acte de vente:", "15 janvier 2026"),
        ("Prise de possession:", "15 janvier 2026"),
    ]

    for label, value in dates_data:
        c.drawString(50, y, label)
        c.drawString(200, y, value)
        y -= 15

    y -= 20

    # Section Conditions
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y, "5. CONDITIONS")
    y -= 20

    c.setFont("Helvetica", 10)
    conditions = [
        "- Inspection satisfaisante par un inspecteur agree",
        "- Obtention du financement hypothecaire",
        "- Certificat de localisation conforme",
        "- Verification du registre foncier sans charge",
    ]

    for cond in conditions:
        c.drawString(50, y, cond)
        y -= 15

    y -= 20

    # Signatures
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y, "6. SIGNATURES")
    y -= 30

    c.setFont("Helvetica", 10)
    c.line(50, y, 250, y)
    c.drawString(50, y - 15, "Jean-Pierre TREMBLAY (Vendeur)")

    c.line(300, y, 500, y)
    c.drawString(300, y - 15, "Marie-Claude GAGNON (Acheteur)")

    y -= 40
    c.drawString(50, y, "Date: 15 novembre 2025")
    c.drawString(300, y, "Date: 15 novembre 2025")

    # Courtier
    y -= 40
    c.setFont("Helvetica", 9)
    c.drawString(50, y, "Courtier immobilier: Sophie LAVOIE, Groupe Sutton")
    c.drawString(50, y - 12, "Permis OACIQ: 12345678")

    c.save()
    print(f"PDF de test cree: {output_path}")
    return output_path


def test_extraction(pdf_path: str):
    """Teste les differentes methodes d'extraction."""
    print("\n" + "="*70)
    print("TEST DES METHODES D'EXTRACTION PDF")
    print("="*70)
    print(f"Fichier: {pdf_path}\n")

    methodes = ["pypdf", "docling-standard"]
    resultats = {}

    for methode in methodes:
        print(f"\n--- Test: {methode} ---")
        start_time = time.time()

        try:
            result = extraire_texte_pdf_avance(pdf_path, methode=methode)
            duration = time.time() - start_time

            resultats[methode] = {
                "success": result["success"],
                "duration": duration,
                "texte_length": len(result.get("texte", "")),
                "tableaux": len(result.get("tableaux", [])),
                "methode_utilisee": result.get("methode", methode),
                "error": result.get("error"),
            }

            print(f"  Succes: {result['success']}")
            print(f"  Methode utilisee: {result.get('methode', methode)}")
            print(f"  Duree: {duration:.2f}s")
            print(f"  Longueur texte: {len(result.get('texte', ''))} caracteres")
            print(f"  Tableaux extraits: {len(result.get('tableaux', []))}")

            if result["success"]:
                texte = result.get("texte", "")
                # Verifier les elements cles
                elements = {
                    "Prix (575 000)": "575" in texte or "575000" in texte,
                    "Vendeur (TREMBLAY)": "TREMBLAY" in texte.upper(),
                    "Acheteur (GAGNON)": "GAGNON" in texte.upper(),
                    "Adresse": "Rene-Levesque" in texte or "René-Lévesque" in texte,
                    "Date (novembre 2025)": "novembre 2025" in texte or "2025" in texte,
                }

                print(f"  Elements detectes:")
                for elem, found in elements.items():
                    status = "OK" if found else "MANQUANT"
                    print(f"    - {elem}: {status}")

                # Apercu du texte
                print(f"\n  Apercu (500 premiers caracteres):")
                print("  " + "-"*50)
                apercu = texte[:500].replace("\n", "\n  ")
                print(f"  {apercu}")
                print("  " + "-"*50)
            else:
                print(f"  Erreur: {result.get('error')}")

        except Exception as e:
            print(f"  ERREUR: {e}")
            resultats[methode] = {"success": False, "error": str(e)}

    # Resume comparatif
    print("\n" + "="*70)
    print("RESUME COMPARATIF")
    print("="*70)
    print(f"{'Methode':<20} {'Succes':<10} {'Duree':<10} {'Caracteres':<12} {'Tableaux':<10}")
    print("-"*70)

    for methode, res in resultats.items():
        succes = "OK" if res.get("success") else "ECHEC"
        duree = f"{res.get('duration', 0):.2f}s"
        chars = str(res.get("texte_length", 0))
        tables = str(res.get("tableaux", 0))
        print(f"{methode:<20} {succes:<10} {duree:<10} {chars:<12} {tables:<10}")

    return resultats


if __name__ == "__main__":
    # Creer le PDF de test
    pdf_path = creer_pdf_test_complexe()

    # Tester les methodes d'extraction
    resultats = test_extraction(pdf_path)

    print("\n" + "="*70)
    print("TEST TERMINE")
    print("="*70)
