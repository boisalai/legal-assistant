#!/usr/bin/env python3
"""
Génère des PDFs de test réalistes pour valider le workflow d'analyse.

Documents générés:
1. Promesse d'achat-vente
2. Offre d'achat
3. Certificat de localisation

Usage:
    uv run python generate_test_pdfs.py
"""

import os
from datetime import datetime, timedelta
from pathlib import Path

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas


def create_output_dir():
    """Crée le répertoire de sortie pour les PDFs."""
    output_dir = Path("data/test_pdfs")
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def generate_promesse_achat_vente(output_path: Path):
    """
    Génère une promesse d'achat-vente réaliste.

    Contient:
    - Vendeur et acheteur
    - Adresse de la propriété
    - Prix de vente
    - Mise de fonds
    - Date de signature
    - Date de transfert prévue
    """
    c = canvas.Canvas(str(output_path / "promesse_achat_vente.pdf"), pagesize=letter)
    width, height = letter

    # En-tête
    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(width / 2, height - 1 * inch, "PROMESSE D'ACHAT-VENTE")

    c.setFont("Helvetica", 11)
    y = height - 1.5 * inch

    # Date du document
    date_signature = datetime(2024, 3, 15)
    c.drawString(1 * inch, y, f"Montréal, le {date_signature.strftime('%d %B %Y')}")
    y -= 0.5 * inch

    # Parties
    c.setFont("Helvetica-Bold", 12)
    c.drawString(1 * inch, y, "ENTRE:")
    y -= 0.3 * inch

    c.setFont("Helvetica", 11)
    c.drawString(1.5 * inch, y, "M. Jean Tremblay et Mme Marie Gagnon")
    y -= 0.2 * inch
    c.drawString(1.5 * inch, y, "123 Rue des Érables, Montréal (Québec) H2X 1Y7")
    y -= 0.2 * inch
    c.drawString(1.5 * inch, y, "Ci-après appelés les « VENDEURS »")
    y -= 0.5 * inch

    c.setFont("Helvetica-Bold", 12)
    c.drawString(1 * inch, y, "ET:")
    y -= 0.3 * inch

    c.setFont("Helvetica", 11)
    c.drawString(1.5 * inch, y, "Mme Sophie Lavoie et M. Marc Bélanger")
    y -= 0.2 * inch
    c.drawString(1.5 * inch, y, "456 Avenue du Parc, Laval (Québec) H7G 2T3")
    y -= 0.2 * inch
    c.drawString(1.5 * inch, y, "Ci-après appelés les « ACHETEURS »")
    y -= 0.5 * inch

    # Objet de la transaction
    c.setFont("Helvetica-Bold", 12)
    c.drawString(1 * inch, y, "1. OBJET DE LA TRANSACTION")
    y -= 0.3 * inch

    c.setFont("Helvetica", 11)
    c.drawString(1 * inch, y, "Les VENDEURS s'engagent à vendre aux ACHETEURS la propriété située au:")
    y -= 0.3 * inch

    c.setFont("Helvetica-Bold", 11)
    c.drawString(1.5 * inch, y, "789 Boulevard Saint-Laurent, Montréal (Québec) H2Z 1J4")
    y -= 0.2 * inch

    c.setFont("Helvetica", 11)
    c.drawString(1 * inch, y, "Désignation cadastrale: Lot 1234567, Cadastre du Québec")
    y -= 0.5 * inch

    # Prix et modalités de paiement
    c.setFont("Helvetica-Bold", 12)
    c.drawString(1 * inch, y, "2. PRIX ET MODALITÉS DE PAIEMENT")
    y -= 0.3 * inch

    c.setFont("Helvetica", 11)
    c.drawString(1 * inch, y, "Prix de vente: 485 000,00 $")
    y -= 0.2 * inch
    c.drawString(1 * inch, y, "Mise de fonds (dépôt): 25 000,00 $ (payé à la signature)")
    y -= 0.2 * inch
    c.drawString(1 * inch, y, "Hypothèque préautorisée: 365 000,00 $ (Banque Nationale)")
    y -= 0.2 * inch
    c.drawString(1 * inch, y, "Solde en argent comptant: 95 000,00 $ (au transfert)")
    y -= 0.5 * inch

    # Taxes applicables
    c.setFont("Helvetica-Bold", 12)
    c.drawString(1 * inch, y, "3. TAXES")
    y -= 0.3 * inch

    c.setFont("Helvetica", 11)
    c.drawString(1 * inch, y, "Droits de mutation (taxe de bienvenue): 7 275,00 $ (à la charge des ACHETEURS)")
    y -= 0.2 * inch
    c.drawString(1 * inch, y, "TPS (exemptée - revente résidentielle): 0,00 $")
    y -= 0.2 * inch
    c.drawString(1 * inch, y, "TVQ (exemptée - revente résidentielle): 0,00 $")
    y -= 0.5 * inch

    # Dates importantes
    c.setFont("Helvetica-Bold", 12)
    c.drawString(1 * inch, y, "4. DATES IMPORTANTES")
    y -= 0.3 * inch

    date_transfert = date_signature + timedelta(days=60)
    date_occupation = date_transfert + timedelta(days=7)

    c.setFont("Helvetica", 11)
    c.drawString(1 * inch, y, f"Date de signature de la promesse: {date_signature.strftime('%d %B %Y')}")
    y -= 0.2 * inch
    c.drawString(1 * inch, y, f"Date de transfert prévue: {date_transfert.strftime('%d %B %Y')}")
    y -= 0.2 * inch
    c.drawString(1 * inch, y, f"Date d'occupation: {date_occupation.strftime('%d %B %Y')}")
    y -= 0.5 * inch

    # Conditions
    c.setFont("Helvetica-Bold", 12)
    c.drawString(1 * inch, y, "5. CONDITIONS")
    y -= 0.3 * inch

    c.setFont("Helvetica", 11)
    c.drawString(1 * inch, y, "- Inspection de la propriété par un inspecteur en bâtiment qualifié")
    y -= 0.2 * inch
    c.drawString(1 * inch, y, "- Obtention d'un financement hypothécaire satisfaisant")
    y -= 0.2 * inch
    c.drawString(1 * inch, y, "- Examen du certificat de localisation par le notaire")
    y -= 0.5 * inch

    # Signatures
    c.setFont("Helvetica-Bold", 12)
    c.drawString(1 * inch, y, "6. SIGNATURES")
    y -= 0.5 * inch

    c.setFont("Helvetica", 10)
    c.drawString(1 * inch, y, "Les VENDEURS:")
    c.drawString(4.5 * inch, y, "Les ACHETEURS:")
    y -= 0.3 * inch

    c.drawString(1 * inch, y, "_________________________")
    c.drawString(4.5 * inch, y, "_________________________")
    y -= 0.15 * inch
    c.drawString(1 * inch, y, "Jean Tremblay")
    c.drawString(4.5 * inch, y, "Sophie Lavoie")
    y -= 0.3 * inch

    c.drawString(1 * inch, y, "_________________________")
    c.drawString(4.5 * inch, y, "_________________________")
    y -= 0.15 * inch
    c.drawString(1 * inch, y, "Marie Gagnon")
    c.drawString(4.5 * inch, y, "Marc Bélanger")

    # Pied de page
    c.setFont("Helvetica-Oblique", 9)
    c.drawCentredString(
        width / 2,
        0.5 * inch,
        "Document généré automatiquement pour tests - Ne constitue pas un document légal"
    )

    c.save()
    print(f"✅ Promesse d'achat-vente générée: {output_path / 'promesse_achat_vente.pdf'}")


def generate_offre_achat(output_path: Path):
    """
    Génère une offre d'achat réaliste.

    Contient:
    - Acheteur
    - Adresse de la propriété
    - Prix offert
    - Conditions de financement
    - Délai d'acceptation
    """
    c = canvas.Canvas(str(output_path / "offre_achat.pdf"), pagesize=letter)
    width, height = letter

    # En-tête
    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(width / 2, height - 1 * inch, "OFFRE D'ACHAT")

    c.setFont("Helvetica", 11)
    y = height - 1.5 * inch

    # Date
    date_offre = datetime(2024, 2, 28)
    c.drawString(1 * inch, y, f"Québec, le {date_offre.strftime('%d %B %Y')}")
    y -= 0.5 * inch

    # Acheteur
    c.setFont("Helvetica-Bold", 12)
    c.drawString(1 * inch, y, "ACHETEUR:")
    y -= 0.3 * inch

    c.setFont("Helvetica", 11)
    c.drawString(1.5 * inch, y, "M. François Côté")
    y -= 0.2 * inch
    c.drawString(1.5 * inch, y, "321 Rue Cartier, Québec (Québec) G1R 2S5")
    y -= 0.2 * inch
    c.drawString(1.5 * inch, y, "Téléphone: (418) 555-1234")
    y -= 0.5 * inch

    # Propriété visée
    c.setFont("Helvetica-Bold", 12)
    c.drawString(1 * inch, y, "PROPRIÉTÉ VISÉE:")
    y -= 0.3 * inch

    c.setFont("Helvetica", 11)
    c.drawString(1 * inch, y, "Adresse: 456 Chemin Sainte-Foy, Québec (Québec) G1S 2J3")
    y -= 0.2 * inch
    c.drawString(1 * inch, y, "Type: Copropriété (condo) - 3 chambres, 2 salles de bain")
    y -= 0.2 * inch
    c.drawString(1 * inch, y, "Superficie: 1 200 pieds carrés")
    y -= 0.5 * inch

    # Prix et conditions financières
    c.setFont("Helvetica-Bold", 12)
    c.drawString(1 * inch, y, "PRIX ET CONDITIONS FINANCIÈRES:")
    y -= 0.3 * inch

    c.setFont("Helvetica", 11)
    c.drawString(1 * inch, y, "Prix offert: 325 000,00 $")
    y -= 0.2 * inch
    c.drawString(1 * inch, y, "Dépôt initial: 5 000,00 $ (chèque joint à l'offre)")
    y -= 0.2 * inch
    c.drawString(1 * inch, y, "Dépôt additionnel: 15 000,00 $ (dans les 10 jours de l'acceptation)")
    y -= 0.2 * inch
    c.drawString(1 * inch, y, "Hypothèque à obtenir: 260 000,00 $ (taux max 5,5%, amortissement 25 ans)")
    y -= 0.2 * inch
    c.drawString(1 * inch, y, "Solde en argent comptant: 45 000,00 $")
    y -= 0.5 * inch

    # Frais de copropriété
    c.setFont("Helvetica-Bold", 12)
    c.drawString(1 * inch, y, "FRAIS DE COPROPRIÉTÉ:")
    y -= 0.3 * inch

    c.setFont("Helvetica", 11)
    c.drawString(1 * inch, y, "Frais mensuels: 285,00 $ (incluant chauffage, eau, entretien commun)")
    y -= 0.2 * inch
    c.drawString(1 * inch, y, "Taxes municipales annuelles: 2 850,00 $")
    y -= 0.2 * inch
    c.drawString(1 * inch, y, "Taxes scolaires annuelles: 450,00 $")
    y -= 0.5 * inch

    # Conditions
    c.setFont("Helvetica-Bold", 12)
    c.drawString(1 * inch, y, "CONDITIONS:")
    y -= 0.3 * inch

    c.setFont("Helvetica", 11)
    c.drawString(1 * inch, y, "1. Inspection préachat par expert qualifié (délai: 10 jours)")
    y -= 0.2 * inch
    c.drawString(1 * inch, y, "2. Obtention d'un prêt hypothécaire satisfaisant (délai: 30 jours)")
    y -= 0.2 * inch
    c.drawString(1 * inch, y, "3. Examen des documents de copropriété (règlements, budget, PV)")
    y -= 0.2 * inch
    c.drawString(1 * inch, y, "4. Vérification de l'absence de vices cachés ou de problèmes légaux")
    y -= 0.5 * inch

    # Inclusions/Exclusions
    c.setFont("Helvetica-Bold", 12)
    c.drawString(1 * inch, y, "INCLUSIONS:")
    y -= 0.3 * inch

    c.setFont("Helvetica", 11)
    c.drawString(1 * inch, y, "Tous les électroménagers, luminaires, stores, rideaux, climatiseur mural")
    y -= 0.3 * inch

    c.setFont("Helvetica-Bold", 12)
    c.drawString(1 * inch, y, "EXCLUSIONS:")
    y -= 0.3 * inch

    c.setFont("Helvetica", 11)
    c.drawString(1 * inch, y, "Meubles, effets personnels, œuvres d'art")
    y -= 0.5 * inch

    # Délai d'acceptation
    c.setFont("Helvetica-Bold", 12)
    c.drawString(1 * inch, y, "DÉLAI D'ACCEPTATION:")
    y -= 0.3 * inch

    date_expiration = date_offre + timedelta(days=3)
    c.setFont("Helvetica", 11)
    c.drawString(1 * inch, y, f"Cette offre expire le {date_expiration.strftime('%d %B %Y à 17h00')}")
    y -= 0.5 * inch

    # Date de transfert souhaitée
    c.setFont("Helvetica-Bold", 12)
    c.drawString(1 * inch, y, "DATE DE TRANSFERT SOUHAITÉE:")
    y -= 0.3 * inch

    date_transfert = date_offre + timedelta(days=90)
    c.setFont("Helvetica", 11)
    c.drawString(1 * inch, y, f"{date_transfert.strftime('%d %B %Y')} (ou selon entente mutuelle)")
    y -= 0.5 * inch

    # Signature
    c.setFont("Helvetica-Bold", 12)
    c.drawString(1 * inch, y, "SIGNATURE DE L'ACHETEUR:")
    y -= 0.5 * inch

    c.setFont("Helvetica", 10)
    c.drawString(1 * inch, y, "_________________________")
    y -= 0.15 * inch
    c.drawString(1 * inch, y, "François Côté")
    y -= 0.15 * inch
    c.drawString(1 * inch, y, f"Date: {date_offre.strftime('%d %B %Y')}")

    # Pied de page
    c.setFont("Helvetica-Oblique", 9)
    c.drawCentredString(
        width / 2,
        0.5 * inch,
        "Document généré automatiquement pour tests - Ne constitue pas un document légal"
    )

    c.save()
    print(f"✅ Offre d'achat générée: {output_path / 'offre_achat.pdf'}")


def generate_certificat_localisation(output_path: Path):
    """
    Génère un certificat de localisation simplifié.

    Contient:
    - Propriétaire
    - Adresse de la propriété
    - Dimensions du terrain
    - Arpenteur-géomètre
    - Date du certificat
    """
    c = canvas.Canvas(str(output_path / "certificat_localisation.pdf"), pagesize=letter)
    width, height = letter

    # En-tête
    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(width / 2, height - 1 * inch, "CERTIFICAT DE LOCALISATION")

    c.setFont("Helvetica", 11)
    y = height - 1.5 * inch

    # Arpenteur-géomètre
    c.setFont("Helvetica-Bold", 11)
    c.drawString(1 * inch, y, "Préparé par:")
    y -= 0.2 * inch

    c.setFont("Helvetica", 11)
    c.drawString(1.5 * inch, y, "Me Daniel Laplante, arpenteur-géomètre")
    y -= 0.15 * inch
    c.drawString(1.5 * inch, y, "Ordre des arpenteurs-géomètres du Québec - Permis #12345")
    y -= 0.15 * inch
    c.drawString(1.5 * inch, y, "123 Rue des Professionnels, Sherbrooke (Québec) J1H 1Z2")
    y -= 0.15 * inch
    c.drawString(1.5 * inch, y, "Téléphone: (819) 555-7890")
    y -= 0.5 * inch

    # Date
    date_cert = datetime(2024, 1, 15)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(1 * inch, y, f"Date du certificat: {date_cert.strftime('%d %B %Y')}")
    y -= 0.5 * inch

    # Propriétaire
    c.setFont("Helvetica-Bold", 12)
    c.drawString(1 * inch, y, "PROPRIÉTAIRE:")
    y -= 0.3 * inch

    c.setFont("Helvetica", 11)
    c.drawString(1.5 * inch, y, "M. Pierre Lefebvre et Mme Julie Roy")
    y -= 0.2 * inch
    c.drawString(1.5 * inch, y, "987 Rue King Ouest, Sherbrooke (Québec) J1H 1R7")
    y -= 0.5 * inch

    # Immeuble
    c.setFont("Helvetica-Bold", 12)
    c.drawString(1 * inch, y, "IMMEUBLE LOCALISÉ:")
    y -= 0.3 * inch

    c.setFont("Helvetica", 11)
    c.drawString(1 * inch, y, "Adresse civique: 987 Rue King Ouest, Sherbrooke (Québec) J1H 1R7")
    y -= 0.2 * inch
    c.drawString(1 * inch, y, "Désignation cadastrale: Lot 2345678, Cadastre du Québec")
    y -= 0.2 * inch
    c.drawString(1 * inch, y, "Circonscription foncière: Sherbrooke")
    y -= 0.5 * inch

    # Dimensions et superficie
    c.setFont("Helvetica-Bold", 12)
    c.drawString(1 * inch, y, "DIMENSIONS ET SUPERFICIE:")
    y -= 0.3 * inch

    c.setFont("Helvetica", 11)
    c.drawString(1 * inch, y, "Terrain:")
    y -= 0.2 * inch
    c.drawString(1.5 * inch, y, "Largeur (façade): 15,24 mètres (50 pieds)")
    y -= 0.2 * inch
    c.drawString(1.5 * inch, y, "Profondeur: 30,48 mètres (100 pieds)")
    y -= 0.2 * inch
    c.drawString(1.5 * inch, y, "Superficie totale: 464,51 mètres carrés (5 000 pieds carrés)")
    y -= 0.3 * inch

    c.drawString(1 * inch, y, "Bâtiment principal:")
    y -= 0.2 * inch
    c.drawString(1.5 * inch, y, "Résidence unifamiliale - 2 étages")
    y -= 0.2 * inch
    c.drawString(1.5 * inch, y, "Dimensions: 9,14 m × 12,19 m (30 pi × 40 pi)")
    y -= 0.2 * inch
    c.drawString(1.5 * inch, y, "Superficie au sol: 111,48 m² (1 200 pi²)")
    y -= 0.5 * inch

    # Bâtiments accessoires
    c.setFont("Helvetica-Bold", 12)
    c.drawString(1 * inch, y, "BÂTIMENTS ACCESSOIRES:")
    y -= 0.3 * inch

    c.setFont("Helvetica", 11)
    c.drawString(1.5 * inch, y, "Garage détaché: 6,10 m × 6,10 m (20 pi × 20 pi)")
    y -= 0.2 * inch
    c.drawString(1.5 * inch, y, "Cabanon: 2,44 m × 3,05 m (8 pi × 10 pi)")
    y -= 0.5 * inch

    # Limites et empiétements
    c.setFont("Helvetica-Bold", 12)
    c.drawString(1 * inch, y, "LIMITES ET EMPIÉTEMENTS:")
    y -= 0.3 * inch

    c.setFont("Helvetica", 11)
    c.drawString(1 * inch, y, "Les bâtiments sont situés à l'intérieur des limites du lot.")
    y -= 0.2 * inch
    c.drawString(1 * inch, y, "Aucun empiétement détecté sur les lots voisins.")
    y -= 0.2 * inch
    c.drawString(1 * inch, y, "Marges de recul conformes au règlement de zonage municipal:")
    y -= 0.2 * inch
    c.drawString(1.5 * inch, y, "- Avant: 6,10 mètres (20 pieds)")
    y -= 0.2 * inch
    c.drawString(1.5 * inch, y, "- Arrière: 7,62 mètres (25 pieds)")
    y -= 0.2 * inch
    c.drawString(1.5 * inch, y, "- Latérales: 1,52 mètres (5 pieds) de chaque côté")
    y -= 0.5 * inch

    # Observations
    c.setFont("Helvetica-Bold", 12)
    c.drawString(1 * inch, y, "OBSERVATIONS:")
    y -= 0.3 * inch

    c.setFont("Helvetica", 11)
    c.drawString(1 * inch, y, "- Clôture en bois le long de la limite arrière")
    y -= 0.2 * inch
    c.drawString(1 * inch, y, "- Entrée asphaltée menant au garage")
    y -= 0.2 * inch
    c.drawString(1 * inch, y, "- Piscine creusée dans la cour arrière (4,88 m × 9,14 m)")
    y -= 0.5 * inch

    # Signature de l'arpenteur
    c.setFont("Helvetica-Bold", 12)
    c.drawString(1 * inch, y, "CERTIFICATION:")
    y -= 0.3 * inch

    c.setFont("Helvetica", 10)
    c.drawString(1 * inch, y, "Je certifie que ce certificat de localisation a été préparé conformément")
    y -= 0.15 * inch
    c.drawString(1 * inch, y, "aux normes de pratique de l'Ordre des arpenteurs-géomètres du Québec.")
    y -= 0.5 * inch

    c.drawString(1 * inch, y, "_______________________________")
    y -= 0.15 * inch
    c.drawString(1 * inch, y, "Me Daniel Laplante, a.-g.")
    y -= 0.15 * inch
    c.drawString(1 * inch, y, f"Date: {date_cert.strftime('%d %B %Y')}")

    # Sceau professionnel (simulé)
    c.setFont("Helvetica-Oblique", 9)
    c.drawString(4.5 * inch, y + 0.3 * inch, "[Sceau de l'arpenteur-géomètre]")

    # Pied de page
    c.setFont("Helvetica-Oblique", 9)
    c.drawCentredString(
        width / 2,
        0.5 * inch,
        "Document généré automatiquement pour tests - Ne constitue pas un document légal"
    )

    c.save()
    print(f"✅ Certificat de localisation généré: {output_path / 'certificat_localisation.pdf'}")


def main():
    """Fonction principale."""
    print("=" * 70)
    print("📄 GÉNÉRATION DE PDFs DE TEST")
    print("=" * 70)
    print()

    # Créer le répertoire de sortie
    output_dir = create_output_dir()
    print(f"📁 Répertoire de sortie: {output_dir}")
    print()

    # Générer les PDFs
    print("Génération des documents...")
    print()

    generate_promesse_achat_vente(output_dir)
    generate_offre_achat(output_dir)
    generate_certificat_localisation(output_dir)

    print()
    print("=" * 70)
    print("✨ GÉNÉRATION COMPLÉTÉE")
    print("=" * 70)
    print()
    print(f"📂 Fichiers générés dans: {output_dir}")
    print()
    print("Prochaines étapes:")
    print("  1. Tester l'extraction avec: uv run python test_extraction.py")
    print("  2. Lancer le workflow complet via l'API")
    print("  3. Valider la qualité des extractions")
    print()


if __name__ == "__main__":
    main()
