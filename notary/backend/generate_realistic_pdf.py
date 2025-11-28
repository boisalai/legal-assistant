#!/usr/bin/env python3
"""
Générateur de PDF de test réaliste pour Notary Assistant
Crée une promesse d'achat-vente immobilière au Québec

Usage:
    uv run python generate_realistic_pdf.py
"""

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_RIGHT
from reportlab.lib import colors
from datetime import datetime
import os

def create_realistic_vente_pdf(output_path: str):
    """
    Crée un PDF réaliste d'une promesse d'achat-vente immobilière

    Contient:
    - Montants (prix de vente, acompte, taxes)
    - Dates (signature, occupation, conditions)
    - Noms (acheteur, vendeur, courtier)
    - Adresses (propriété, parties)
    - Détails juridiques (cadastre, servitudes, etc.)
    """

    # Créer le PDF
    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        rightMargin=0.75*inch,
        leftMargin=0.75*inch,
        topMargin=0.75*inch,
        bottomMargin=0.75*inch
    )

    # Styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        textColor=colors.HexColor('#1a1a1a'),
        spaceAfter=30,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )

    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=12,
        textColor=colors.HexColor('#2c3e50'),
        spaceAfter=12,
        spaceBefore=12,
        fontName='Helvetica-Bold'
    )

    body_style = ParagraphStyle(
        'CustomBody',
        parent=styles['BodyText'],
        fontSize=10,
        textColor=colors.HexColor('#333333'),
        spaceAfter=6,
        alignment=TA_JUSTIFY,
        leading=14
    )

    # Contenu du document
    story = []

    # === EN-TÊTE ===
    story.append(Paragraph("PROMESSE D'ACHAT-VENTE", title_style))
    story.append(Paragraph("Transaction Immobilière Résidentielle", heading_style))
    story.append(Spacer(1, 0.2*inch))

    # === SECTION 1: IDENTIFICATION DES PARTIES ===
    story.append(Paragraph("1. IDENTIFICATION DES PARTIES", heading_style))

    story.append(Paragraph(
        "<b>VENDEUR:</b> M. Jean-Pierre Tremblay et Mme Marie-Claude Gagnon<br/>"
        "Adresse: 1234 rue des Érables, Québec (Québec) G1R 2T5<br/>"
        "Téléphone: (418) 555-1234<br/>"
        "Courriel: jtremblay@example.com",
        body_style
    ))

    story.append(Spacer(1, 0.1*inch))

    story.append(Paragraph(
        "<b>ACHETEUR:</b> M. François Bélanger et Mme Sophie Côté<br/>"
        "Adresse: 5678 avenue Cartier, Québec (Québec) G1R 3B4<br/>"
        "Téléphone: (418) 555-5678<br/>"
        "Courriel: fbelanger@example.com",
        body_style
    ))

    story.append(Spacer(1, 0.1*inch))

    story.append(Paragraph(
        "<b>COURTIER IMMOBILIER:</b> Me Catherine Desrochers<br/>"
        "Royal LePage du Quartier<br/>"
        "Téléphone: (418) 555-9876<br/>"
        "Licence: C-1234-5678",
        body_style
    ))

    story.append(Spacer(1, 0.2*inch))

    # === SECTION 2: DÉSIGNATION DE L'IMMEUBLE ===
    story.append(Paragraph("2. DÉSIGNATION DE L'IMMEUBLE", heading_style))

    story.append(Paragraph(
        "<b>Adresse civique:</b> 456 rue Champlain, Québec (Québec) G1K 4H2",
        body_style
    ))

    story.append(Paragraph(
        "<b>Désignation cadastrale:</b> Lot 3 456 789 du cadastre du Québec, "
        "circonscription foncière de Québec",
        body_style
    ))

    story.append(Paragraph(
        "<b>Type de propriété:</b> Maison unifamiliale de deux étages avec garage attaché",
        body_style
    ))

    story.append(Paragraph(
        "<b>Superficie du terrain:</b> 5 240 pieds carrés (487 mètres carrés)",
        body_style
    ))

    story.append(Paragraph(
        "<b>Année de construction:</b> 1985, rénovations majeures en 2018",
        body_style
    ))

    story.append(Spacer(1, 0.2*inch))

    # === SECTION 3: PRIX ET CONDITIONS FINANCIÈRES ===
    story.append(Paragraph("3. PRIX ET CONDITIONS FINANCIÈRES", heading_style))

    # Table des montants
    montants_data = [
        ['Description', 'Montant'],
        ['Prix de vente', '485 000,00 $'],
        ['Acompte (dépôt)', '25 000,00 $'],
        ['Mise de fonds additionnelle', '72 500,00 $'],
        ['Hypothèque à obtenir', '387 500,00 $'],
        ['<b>TOTAL</b>', '<b>485 000,00 $</b>']
    ]

    montants_table = Table(montants_data, colWidths=[3.5*inch, 1.5*inch])
    montants_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3498db')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 11),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -2), colors.HexColor('#ecf0f1')),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
    ]))

    story.append(montants_table)
    story.append(Spacer(1, 0.2*inch))

    story.append(Paragraph(
        "<b>Taxe de bienvenue (estimation):</b> 7 425,00 $ (à la charge de l'acheteur)",
        body_style
    ))

    story.append(Paragraph(
        "<b>Taxes municipales (2024):</b> 4 850,00 $ / an",
        body_style
    ))

    story.append(Paragraph(
        "<b>Taxes scolaires (2024):</b> 1 245,00 $ / an",
        body_style
    ))

    story.append(Spacer(1, 0.2*inch))

    # === SECTION 4: DATES IMPORTANTES ===
    story.append(Paragraph("4. DATES ET ÉCHÉANCIER", heading_style))

    dates_data = [
        ['Événement', 'Date'],
        ['Signature de la promesse', '15 novembre 2024'],
        ['Expiration de l\'offre', '20 novembre 2024, 17h00'],
        ['Inspection pré-achat', '25 novembre 2024'],
        ['Acceptation finale', '30 novembre 2024'],
        ['Signature de l\'acte notarié', '20 décembre 2024'],
        ['Occupation de l\'immeuble', '20 décembre 2024'],
    ]

    dates_table = Table(dates_data, colWidths=[3*inch, 2*inch])
    dates_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2ecc71')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 11),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#ecf0f1')),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))

    story.append(dates_table)
    story.append(Spacer(1, 0.2*inch))

    # === SECTION 5: CONDITIONS PARTICULIÈRES ===
    story.append(Paragraph("5. CONDITIONS PARTICULIÈRES", heading_style))

    story.append(Paragraph(
        "5.1 <b>Inspection:</b> L'acheteur s'engage à faire effectuer une inspection préachat "
        "par un inspecteur qualifié au plus tard le 25 novembre 2024. Le rapport d'inspection "
        "devra être remis au vendeur dans les 48 heures suivant l'inspection.",
        body_style
    ))

    story.append(Paragraph(
        "5.2 <b>Financement hypothécaire:</b> La présente offre est conditionnelle à "
        "l'obtention par l'acheteur d'un prêt hypothécaire de 387 500,00 $ au taux "
        "d'intérêt maximum de 5,5% par année, amortissable sur 25 ans, au plus tard "
        "le 30 novembre 2024.",
        body_style
    ))

    story.append(Paragraph(
        "5.3 <b>Certificat de localisation:</b> Le vendeur s'engage à fournir à ses frais "
        "un certificat de localisation préparé par un arpenteur-géomètre, conforme aux "
        "exigences de la Loi sur le cadastre, daté de moins de 10 ans.",
        body_style
    ))

    story.append(Paragraph(
        "5.4 <b>Vérification de titre:</b> L'acheteur aura 15 jours à compter de la signature "
        "pour faire vérifier le titre de propriété et signaler toute irrégularité au vendeur.",
        body_style
    ))

    story.append(Spacer(1, 0.2*inch))

    # === SECTION 6: INCLUSIONS ET EXCLUSIONS ===
    story.append(Paragraph("6. INCLUSIONS ET EXCLUSIONS", heading_style))

    story.append(Paragraph(
        "<b>INCLUSIONS (sans garantie):</b>",
        body_style
    ))

    story.append(Paragraph(
        "• Tous les luminaires fixés au plafond<br/>"
        "• Thermopompe murale Daikin (salon)<br/>"
        "• Lave-vaisselle Bosch (cuisine)<br/>"
        "• Laveuse et sécheuse Samsung (sous-sol)<br/>"
        "• Système d'alarme Securitas (location transférée)<br/>"
        "• Tous les stores et rideaux<br/>"
        "• Cabanon de jardin en acier<br/>"
        "• Piscine hors-terre et accessoires",
        body_style
    ))

    story.append(Spacer(1, 0.1*inch))

    story.append(Paragraph(
        "<b>EXCLUSIONS:</b>",
        body_style
    ))

    story.append(Paragraph(
        "• Lustre de la salle à manger (antique familial)<br/>"
        "• Étagères murales du bureau<br/>"
        "• Barbecue Weber du patio<br/>"
        "• Tous les effets personnels du vendeur",
        body_style
    ))

    story.append(PageBreak())

    # === SECTION 7: DÉCLARATIONS DU VENDEUR ===
    story.append(Paragraph("7. DÉCLARATIONS DU VENDEUR", heading_style))

    story.append(Paragraph(
        "Le vendeur déclare qu'à sa connaissance:",
        body_style
    ))

    story.append(Paragraph(
        "• L'immeuble est conforme aux règlements municipaux de zonage et de construction<br/>"
        "• Aucune servitude ni restriction ne grève l'immeuble, sauf celles publiées au registre foncier<br/>"
        "• Aucune réclamation n'a été déposée concernant des vices de construction<br/>"
        "• Le système septique (fosse et champ d'épuration) est conforme et fonctionnel<br/>"
        "• Aucune inondation n'a affecté le sous-sol au cours des 5 dernières années<br/>"
        "• Le toit a été refait en 2018 avec garantie de 25 ans (copie à fournir)<br/>"
        "• Fondation en béton coulé, aucune fissure majeure connue",
        body_style
    ))

    story.append(Spacer(1, 0.2*inch))

    # === SECTION 8: DROITS ET SERVITUDES ===
    story.append(Paragraph("8. DROITS ET SERVITUDES", heading_style))

    story.append(Paragraph(
        "L'immeuble est vendu avec tous les droits y attachés, incluant:",
        body_style
    ))

    story.append(Paragraph(
        "• Servitude de passage en faveur du lot 3 456 790 (accès au garage commun)<br/>"
        "• Servitude d'aqueduc municipal traversant le coin sud-ouest du terrain<br/>"
        "• Droit d'usage du parc municipal adjacent (usage commun du quartier)",
        body_style
    ))

    story.append(Spacer(1, 0.2*inch))

    # === SECTION 9: OBLIGATIONS DU NOTAIRE ===
    story.append(Paragraph("9. OBLIGATIONS DU NOTAIRE", heading_style))

    story.append(Paragraph(
        "Le notaire instrumentant devra s'assurer de:",
        body_style
    ))

    story.append(Paragraph(
        "• Vérifier les titres de propriété et l'historique des 20 dernières années<br/>"
        "• Obtenir un certificat de recherche au registre foncier<br/>"
        "• Vérifier l'absence de charges, hypothèques ou privilèges non déclarés<br/>"
        "• S'assurer que toutes les taxes municipales et scolaires sont acquittées<br/>"
        "• Effectuer le calcul et la perception de la taxe de bienvenue<br/>"
        "• Rédiger l'acte de vente définitif conforme aux lois du Québec",
        body_style
    ))

    story.append(Spacer(1, 0.3*inch))

    # === SIGNATURES ===
    story.append(Paragraph("10. SIGNATURES", heading_style))

    story.append(Spacer(1, 0.2*inch))

    # Table des signatures
    signatures = Table([
        ['_____________________________', '_____________________________'],
        ['Jean-Pierre Tremblay (Vendeur)', 'François Bélanger (Acheteur)'],
        ['', ''],
        ['Date: 15 novembre 2024', 'Date: 15 novembre 2024'],
        ['', ''],
        ['_____________________________', '_____________________________'],
        ['Marie-Claude Gagnon (Vendeur)', 'Sophie Côté (Acheteur)'],
        ['', ''],
        ['Date: 15 novembre 2024', 'Date: 15 novembre 2024'],
    ], colWidths=[2.5*inch, 2.5*inch])

    signatures.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
    ]))

    story.append(signatures)

    story.append(Spacer(1, 0.3*inch))

    # Pied de page
    story.append(Paragraph(
        "<i>Document préparé par Me Catherine Desrochers, courtier immobilier agréé<br/>"
        "Royal LePage du Quartier - 789 Grande Allée Est, Québec (Québec) G1R 2K5<br/>"
        "Téléphone: (418) 555-9876 | Courriel: cdesrochers@royallepage.ca</i>",
        ParagraphStyle(
            'Footer',
            parent=styles['Normal'],
            fontSize=8,
            textColor=colors.HexColor('#7f8c8d'),
            alignment=TA_CENTER
        )
    ))

    # Construire le PDF
    doc.build(story)
    print(f"✅ PDF créé avec succès: {output_path}")

    # Statistiques du document
    print("\n📊 Informations extraites dans le PDF:")
    print("   Montants: 485 000 $, 25 000 $, 72 500 $, 387 500 $, 7 425 $, 4 850 $, 1 245 $")
    print("   Dates: 15 nov 2024, 20 nov 2024, 25 nov 2024, 30 nov 2024, 20 déc 2024")
    print("   Vendeurs: Jean-Pierre Tremblay, Marie-Claude Gagnon")
    print("   Acheteurs: François Bélanger, Sophie Côté")
    print("   Courtier: Me Catherine Desrochers")
    print("   Adresse propriété: 456 rue Champlain, Québec (Québec) G1K 4H2")
    print("   Cadastre: Lot 3 456 789 du cadastre du Québec")


if __name__ == "__main__":
    # Créer le répertoire de sortie si nécessaire
    output_dir = "./data/uploads"
    os.makedirs(output_dir, exist_ok=True)

    # Générer le PDF
    output_path = os.path.join(output_dir, "promesse_achat_vente_realiste.pdf")
    create_realistic_vente_pdf(output_path)

    print(f"\n🎯 Utilisez ce PDF pour tester:")
    print(f"   MODEL=anthropic:claude-sonnet-4-5-20250929 uv run python test_sprint1_validation.py")
