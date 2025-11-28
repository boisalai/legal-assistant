"""
Tests end-to-end pour les workflows Agno.

Ces tests nécessitent:
- SurrealDB actif
- ANTHROPIC_API_KEY configurée
- Connexion Internet

Marqués comme "slow" et "e2e" pour être skippés par défaut.

Usage:
    # Lancer uniquement les tests E2E
    uv run pytest -m e2e

    # Skip les tests E2E
    uv run pytest -m "not e2e"
"""

import pytest
import os
from pathlib import Path
from io import BytesIO

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from datetime import datetime

from config.settings import settings
from workflows.analyse_dossier import workflow_analyse_dossier


def generer_pdf_realiste() -> bytes:
    """
    Génère un PDF réaliste pour une promesse d'achat-vente.

    Returns:
        Contenu du PDF en bytes
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []

    # Titre
    title_style = styles['Title']
    story.append(Paragraph("PROMESSE D'ACHAT-VENTE", title_style))
    story.append(Spacer(1, 0.3*inch))

    # Contenu du document
    normal_style = styles['Normal']

    content = [
        "<b>ENTRE:</b>",
        "",
        "<b>VENDEUR:</b> M. Jean Tremblay et Mme Marie Tremblay",
        "Adresse: 123 Rue des Érables, Montréal, QC H3A 1B2",
        "",
        "<b>ET:</b>",
        "",
        "<b>ACHETEUR:</b> M. Pierre Gagnon et Mme Sophie Gagnon",
        "Adresse: 456 Avenue du Parc, Montréal, QC H2X 2V4",
        "",
        "<b>PROPRIÉTÉ:</b>",
        "",
        "Immeuble situé au 789 Boulevard Saint-Laurent, Montréal, QC H2Z 1J7",
        "Type: Résidence unifamiliale",
        "Lot: 1234567",
        "Cadastre: Quartier Saint-Laurent",
        "",
        "<b>PRIX DE VENTE:</b> 450 000,00 $",
        "",
        "<b>CONDITIONS:</b>",
        "",
        "1. Mise de fonds: 90 000,00 $ (20%)",
        "2. Hypothèque: 360 000,00 $ (80%)",
        "3. Taxe de bienvenue: environ 6 750,00 $",
        "4. Frais de notaire: environ 1 500,00 $",
        "",
        "<b>DATES IMPORTANTES:</b>",
        "",
        f"Date de signature: {datetime.now().strftime('%Y-%m-%d')}",
        "Date de transfert prévue: 2025-02-15",
        "Date d'occupation: 2025-02-15",
        "",
        "<b>SIGNATURES:</b>",
        "",
        "_______________________          _______________________",
        "Jean Tremblay (Vendeur)          Marie Tremblay (Vendeur)",
        "",
        "_______________________          _______________________",
        "Pierre Gagnon (Acheteur)         Sophie Gagnon (Acheteur)",
        "",
        f"Date: {datetime.now().strftime('%Y-%m-%d')}",
        "",
        "Me Antoine Leblanc, notaire",
    ]

    for line in content:
        story.append(Paragraph(line, normal_style))
        story.append(Spacer(1, 0.1*inch))

    doc.build(story)

    return buffer.getvalue()


@pytest.mark.e2e
@pytest.mark.slow
@pytest.mark.asyncio
class TestWorkflowAgno:
    """Tests end-to-end pour le workflow Agno."""

    @pytest.fixture(autouse=True)
    def check_requirements(self):
        """Vérifie que les prérequis sont remplis."""
        if not settings.anthropic_api_key:
            pytest.skip("ANTHROPIC_API_KEY not configured")

        # S'assurer que la clé est dans l'environnement
        os.environ["ANTHROPIC_API_KEY"] = settings.anthropic_api_key

    async def test_workflow_complete(self, tmp_path: Path):
        """Test du workflow complet avec un PDF réaliste."""
        # Générer un PDF de test
        pdf_content = generer_pdf_realiste()
        pdf_path = tmp_path / "promesse_achat_vente.pdf"
        pdf_path.write_bytes(pdf_content)

        # Métadonnées
        metadata = {
            "dossier_id": "test_e2e_dossier",
            "nom_dossier": "Test E2E - Vente Tremblay/Gagnon",
            "nb_documents": 1,
        }

        # Exécuter le workflow
        resultat_brut = await workflow_analyse_dossier.arun(
            fichiers_pdf=[str(pdf_path)],
            metadata=metadata,
        )

        # Extraire le contenu
        resultat = resultat_brut.content if hasattr(resultat_brut, 'content') else resultat_brut

        # Vérifications
        assert resultat is not None
        assert isinstance(resultat, dict)
        assert resultat.get("success") is True

        # Vérifier les étapes complétées
        etapes = resultat.get("etapes_completees", [])
        assert "extraction" in etapes
        assert "classification" in etapes
        assert "verification" in etapes
        assert "checklist" in etapes

        # Vérifier la classification
        classification = resultat.get("classification", {})
        assert classification.get("type_transaction") in ["vente", "achat"]
        assert classification.get("type_propriete") in ["residentielle", "commerciale", "copropriete", "terrain"]

        # Vérifier la vérification
        verification = resultat.get("verification", {})
        assert "score_verification" in verification
        assert 0.0 <= verification["score_verification"] <= 1.0

        # Vérifier la checklist
        checklist = resultat.get("checklist", {})
        assert "checklist" in checklist
        assert isinstance(checklist["checklist"], list)
        assert len(checklist["checklist"]) > 0

        # Vérifier le score de confiance
        score_confiance = resultat.get("score_confiance", 0)
        assert 0.0 <= score_confiance <= 1.0

        print("\n" + "="*70)
        print("RÉSULTATS DU TEST E2E:")
        print(f"  Type transaction: {classification.get('type_transaction')}")
        print(f"  Type propriété: {classification.get('type_propriete')}")
        print(f"  Score vérification: {verification.get('score_verification', 0):.2%}")
        print(f"  Score confiance: {score_confiance:.2%}")
        print(f"  Items checklist: {len(checklist['checklist'])}")
        print(f"  Validation requise: {'OUI' if resultat.get('requiert_validation') else 'NON'}")
        print("="*70)

    async def test_workflow_multiple_documents(self, tmp_path: Path):
        """Test du workflow avec plusieurs documents."""
        if not settings.anthropic_api_key:
            pytest.skip("ANTHROPIC_API_KEY not configured")

        # Générer 2 PDFs
        pdf1_content = generer_pdf_realiste()
        pdf1_path = tmp_path / "doc1.pdf"
        pdf1_path.write_bytes(pdf1_content)

        pdf2_content = generer_pdf_realiste()
        pdf2_path = tmp_path / "doc2.pdf"
        pdf2_path.write_bytes(pdf2_content)

        # Métadonnées
        metadata = {
            "dossier_id": "test_e2e_multi",
            "nom_dossier": "Test E2E - Multiple Documents",
            "nb_documents": 2,
        }

        # Exécuter le workflow
        resultat_brut = await workflow_analyse_dossier.arun(
            fichiers_pdf=[str(pdf1_path), str(pdf2_path)],
            metadata=metadata,
        )

        resultat = resultat_brut.content if hasattr(resultat_brut, 'content') else resultat_brut

        # Vérifications
        assert resultat is not None
        assert resultat.get("success") is True

        # Vérifier que les 2 documents ont été traités
        donnees_extraites = resultat.get("donnees_extraites", {})
        assert "documents" in donnees_extraites
        # NOTE: Dépend de l'implémentation de l'agent extracteur

    async def test_workflow_error_handling_no_files(self):
        """Test de gestion d'erreur: aucun fichier fourni."""
        # Exécuter sans fichiers
        resultat_brut = await workflow_analyse_dossier.arun(
            fichiers_pdf=[],
            metadata={"dossier_id": "test_error"},
        )

        resultat = resultat_brut.content if hasattr(resultat_brut, 'content') else resultat_brut

        # Doit retourner une erreur
        assert resultat.get("success") is False
        assert "erreur" in resultat

    async def test_workflow_error_handling_invalid_pdf(self, tmp_path: Path):
        """Test de gestion d'erreur: fichier invalide."""
        # Créer un fichier qui n'est pas un PDF valide
        fake_pdf = tmp_path / "fake.pdf"
        fake_pdf.write_text("This is not a PDF")

        # Exécuter le workflow
        resultat_brut = await workflow_analyse_dossier.arun(
            fichiers_pdf=[str(fake_pdf)],
            metadata={"dossier_id": "test_invalid"},
        )

        resultat = resultat_brut.content if hasattr(resultat_brut, 'content') else resultat_brut

        # Peut retourner une erreur ou un résultat partiel
        # Dépend de l'implémentation de l'agent extracteur
        assert resultat is not None


@pytest.mark.e2e
@pytest.mark.slow
@pytest.mark.asyncio
class TestWorkflowTools:
    """Tests pour les tools utilisés par les agents."""

    def test_extraire_texte_pdf(self, tmp_path: Path):
        """Test de l'extraction de texte PDF."""
        from workflows.tools import extraire_texte_pdf

        # Générer un PDF
        pdf_content = generer_pdf_realiste()
        pdf_path = tmp_path / "test.pdf"
        pdf_path.write_bytes(pdf_content)

        # Extraire le texte
        texte = extraire_texte_pdf(str(pdf_path))

        # Vérifications
        assert texte is not None
        assert isinstance(texte, str)
        assert len(texte) > 0
        assert "PROMESSE" in texte or "ACHAT" in texte

    def test_extraire_montants(self):
        """Test de l'extraction de montants."""
        from workflows.tools import extraire_montants

        texte = """
        Prix de vente: 450 000,00 $
        Mise de fonds: 90 000 $
        Hypothèque: 360000$
        """

        montants = extraire_montants(texte)

        assert len(montants) >= 3
        assert any("450" in m for m in montants)
        assert any("90" in m for m in montants)

    def test_extraire_dates(self):
        """Test de l'extraction de dates."""
        from workflows.tools import extraire_dates

        texte = """
        Date de signature: 2025-01-15
        Date de transfert: 2025-02-15
        Date d'occupation: 15/03/2025
        """

        dates = extraire_dates(texte)

        assert len(dates) >= 3

    def test_extraire_noms(self):
        """Test de l'extraction de noms."""
        from workflows.tools import extraire_noms

        texte = """
        VENDEUR: M. Jean Tremblay et Mme Marie Tremblay
        ACHETEUR: M. Pierre Gagnon
        Me Antoine Leblanc, notaire
        """

        noms = extraire_noms(texte)

        assert len(noms) >= 3
        assert any("Tremblay" in n for n in noms)
        assert any("Gagnon" in n for n in noms)

    def test_extraire_adresses(self):
        """Test de l'extraction d'adresses."""
        from workflows.tools import extraire_adresses

        texte = """
        123 Rue des Érables, Montréal, QC H3A 1B2
        456 Avenue du Parc, Montréal, QC H2X 2V4
        789 Boulevard Saint-Laurent
        """

        adresses = extraire_adresses(texte)

        assert len(adresses) >= 2
        assert any("Érables" in a for a in adresses)
        assert any("Parc" in a for a in adresses)
