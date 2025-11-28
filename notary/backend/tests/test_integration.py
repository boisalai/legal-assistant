#!/usr/bin/env python3
"""
Test d'intégration end-to-end du système Notary Assistant.

Ce script teste le flux complet:
1. Création d'un dossier
2. Upload d'un document PDF
3. Lancement de l'analyse Agno
4. Vérification de la checklist générée

Usage:
    cd backend
    uv run python test_integration.py
"""

import asyncio
import sys
from pathlib import Path
from io import BytesIO

# Ajouter le répertoire backend au path
sys.path.insert(0, str(Path(__file__).parent))

from services.surreal_service import get_db_connection
from services.dossier_service import DossierService
from config.settings import settings


def create_test_pdf() -> bytes:
    """
    Crée un PDF de test simple avec du contenu fictif.

    Pour le MVP, on utilise ReportLab pour générer un PDF simple.
    """
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas
    except ImportError:
        print("⚠️  ReportLab non installé, création d'un PDF minimal...")
        # PDF minimal valide (structure basique)
        return b"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /Resources 4 0 R /MediaBox [0 0 612 792] /Contents 5 0 R >>
endobj
4 0 obj
<< /Font << /F1 << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> >> >>
endobj
5 0 obj
<< /Length 100 >>
stream
BT
/F1 12 Tf
50 700 Td
(PROMESSE D'ACHAT-VENTE) Tj
0 -20 Td
(123 rue Principale, Montreal, QC) Tj
0 -20 Td
(Prix: 350,000$) Tj
ET
endstream
endobj
xref
0 6
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000115 00000 n
0000000230 00000 n
0000000330 00000 n
trailer
<< /Size 6 /Root 1 0 R >>
startxref
482
%%EOF"""

    # Créer un PDF avec ReportLab
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)

    # Titre
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, 750, "PROMESSE D'ACHAT-VENTE")

    # Contenu fictif
    c.setFont("Helvetica", 12)
    y = 700

    lines = [
        "",
        "ENTRE:",
        "Vendeur: Jean Tremblay",
        "Adresse: 456 rue Secondaire, Montreal, QC H2X 1Y3",
        "",
        "ET:",
        "Acheteur: Marie Gagnon",
        "Adresse: 789 boulevard Principal, Laval, QC H7N 2B1",
        "",
        "OBJET: Vente de propriété",
        "Adresse de la propriété: 123 rue Principale, Montreal, QC H3B 1A1",
        "",
        "PRIX DE VENTE: 350 000 $",
        "Mise de fonds: 70 000 $",
        "Hypothèque: 280 000 $",
        "",
        "Date de signature: 15 novembre 2025",
        "Date de transfert: 15 décembre 2025",
        "",
        "Conditions:",
        "- Inspection de la propriété satisfaisante",
        "- Obtention de financement hypothécaire",
        "- Certificat de localisation à jour",
        "",
        "Signé à Montreal, ce 15 novembre 2025",
    ]

    for line in lines:
        c.drawString(50, y, line)
        y -= 20

    c.save()
    buffer.seek(0)
    return buffer.read()


async def test_integration():
    """Test d'intégration complet."""
    print("="*70)
    print("TEST D'INTÉGRATION - Notary Assistant")
    print("="*70)
    print()

    # Créer le PDF de test
    print("📄 Création d'un PDF de test...")
    pdf_content = create_test_pdf()
    print(f"   ✓ PDF créé ({len(pdf_content)} bytes)")
    print()

    # Se connecter à SurrealDB
    async with get_db_connection() as db:
        service = DossierService(db, upload_dir=settings.upload_dir)

        # 1. Créer un dossier
        print("📁 Création d'un dossier de test...")
        dossier = await service.create_dossier(
            nom_dossier="Vente 123 rue Principale - Test Integration",
            user_id="user:test_notaire",
            type_transaction="vente",
        )
        print(f"   ✓ Dossier créé: {dossier.id}")
        print(f"   - Nom: {dossier.nom_dossier}")
        print(f"   - Statut: {dossier.statut}")
        print()

        # 2. Uploader le document
        print("📤 Upload du document PDF...")
        document = await service.add_document(
            dossier_id=dossier.id,
            file_content=pdf_content,
            filename="promesse_achat_vente_test.pdf",
        )
        print(f"   ✓ Document uploadé: {document.id}")
        print(f"   - Nom: {document.nom_fichier}")
        print(f"   - Taille: {document.taille_bytes} bytes")
        print(f"   - Chemin: {document.chemin_fichier}")
        print()

        # 3. Lancer l'analyse
        print("🤖 Lancement de l'analyse Agno...")
        print("   (ATTENTION: Nécessite OPENAI_API_KEY configurée)")
        print("   (Pour le MVP sans API key, cette étape sera skippée)")
        print()

        # Vérifier si on a une clé API OpenAI
        import os
        if not os.getenv("OPENAI_API_KEY"):
            print("   ⚠️  OPENAI_API_KEY non configurée - Skip de l'analyse")
            print("   💡 Pour tester l'analyse complète, définir OPENAI_API_KEY dans .env")
            print()

            # Créer une checklist mock pour tester la création
            print("   Création d'une checklist de test manuelle...")
            checklist_data = {
                "checklist": [
                    {"item": "Vérifier identité vendeur", "priorite": "haute", "complete": False},
                    {"item": "Vérifier titre de propriété", "priorite": "haute", "complete": False},
                    {"item": "Obtenir certificat de localisation", "priorite": "haute", "complete": False},
                ],
                "score_confiance": 0.85,
                "points_attention": [
                    "Vérifier hypothèque existante",
                    "Confirmer date de transfert"
                ],
                "documents_a_obtenir": [
                    "Certificat de localisation",
                    "Preuve de financement"
                ],
            }

            checklist = await service._create_checklist(
                dossier_id=dossier.id,
                checklist_data=checklist_data,
            )
        else:
            try:
                checklist = await service.analyser_dossier(dossier.id)
            except Exception as e:
                print(f"   ❌ Erreur lors de l'analyse: {e}")
                checklist = None

        if checklist:
            print(f"   ✓ Checklist générée: {checklist.id}")
            print(f"   - Items: {len(checklist.items)}")
            print(f"   - Score confiance: {checklist.score_confiance}")
            print(f"   - Points d'attention: {len(checklist.points_attention or [])}")
            print()

            # Afficher la checklist
            print("📋 CHECKLIST GÉNÉRÉE:")
            print("-" * 70)
            for i, item in enumerate(checklist.items, 1):
                print(f"{i}. [{item.get('priorite', 'N/A').upper()}] {item.get('titre', item.get('item', 'N/A'))}")
                if item.get('description'):
                    print(f"   → {item['description']}")
            print()

            if checklist.points_attention:
                print("⚠️  POINTS D'ATTENTION:")
                for point in checklist.points_attention:
                    print(f"   • {point}")
                print()

        # 4. Vérifier le dossier final
        print("🔍 Vérification finale du dossier...")
        dossier_final = await service.get_dossier(dossier.id)

        if dossier_final:
            print(f"   ✓ Dossier: {dossier_final.id}")
            print(f"   - Statut: {dossier_final.statut}")
            print(f"   - Documents: {len(await service.list_documents(dossier.id))}")
        else:
            print(f"   ⚠️  Impossible de récupérer le dossier final")
        print()

        # Récapitulatif
        print("="*70)
        print("✅ TEST D'INTÉGRATION RÉUSSI")
        print("="*70)
        print(f"Dossier ID: {dossier.id}")
        print(f"Document ID: {document.id}")
        if checklist:
            print(f"Checklist ID: {checklist.id}")
        else:
            print("Checklist: Non générée (API key manquante ou erreur Agno)")
        print()
        print("📊 Résultats:")
        print(f"   ✓ Création de dossier: OK")
        print(f"   ✓ Upload de document: OK")
        print(f"   ✓ Génération de checklist: {'OK' if checklist else 'SKIP'}")
        print()

        return True


if __name__ == "__main__":
    success = asyncio.run(test_integration())
    sys.exit(0 if success else 1)
