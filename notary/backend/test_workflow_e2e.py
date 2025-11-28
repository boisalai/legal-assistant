"""
Test end-to-end du workflow Agno avec SurrealDB.

Ce script teste le flux complet:
1. Génération d'un PDF de test réaliste (promesse d'achat-vente)
2. Création d'un dossier via le service
3. Upload du document PDF
4. Exécution du workflow d'analyse Agno
5. Affichage des résultats

Prérequis:
- SurrealDB actif sur ws://localhost:8001/rpc
- ANTHROPIC_API_KEY configurée dans .env
- uv run python test_workflow_e2e.py
"""

import asyncio
import os
from datetime import datetime
from pathlib import Path
from io import BytesIO

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer

# Imports du projet
from config.settings import settings
from services.surreal_service import SurrealDBService
from services.dossier_service import DossierService
from workflows.analyse_dossier import workflow_analyse_dossier


def generer_pdf_test() -> bytes:
    """
    Génère un PDF de test réaliste pour une promesse d'achat-vente.

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
        "<b>INSPECTION:</b>",
        "",
        "L'acheteur a procédé à une inspection préachat le 2024-12-15.",
        "Rapport d'inspection: Satisfaisant, aucun vice majeur détecté.",
        "",
        "<b>CONDITIONS PARTICULIÈRES:</b>",
        "",
        "- Le vendeur s'engage à réparer la fissure au sous-sol avant le transfert",
        "- Les électroménagers (cuisinière, réfrigérateur, laveuse, sécheuse) sont inclus",
        "- Le cabanon dans la cour arrière est inclus",
        "- La piscine hors-terre et ses accessoires sont inclus",
        "",
        "<b>CERTIFICATS REQUIS:</b>",
        "",
        "- Certificat de localisation (à fournir par le vendeur)",
        "- Certificat de conformité de la ville de Montréal",
        "- Certificat d'approbation de financement (à fournir par l'acheteur avant le 2025-01-30)",
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
        "123 Rue du Notaire, Montréal, QC H3B 2Y5",
        "Tél: (514) 555-1234",
    ]

    for line in content:
        story.append(Paragraph(line, normal_style))
        story.append(Spacer(1, 0.1*inch))

    doc.build(story)

    return buffer.getvalue()


async def test_workflow_complet():
    """Test end-to-end du workflow Agno."""

    print("="*80)
    print("TEST END-TO-END: Workflow Agno + SurrealDB + Claude Anthropic")
    print("="*80)
    print()

    # Vérifier la clé API Anthropic
    if not settings.anthropic_api_key:
        print("❌ ERREUR: ANTHROPIC_API_KEY non configurée!")
        print("   Ajoutez ANTHROPIC_API_KEY=sk-ant-... dans votre fichier backend/.env")
        print(f"   Chemin .env attendu: {Path('.env').absolute()}")
        return

    print("✅ ANTHROPIC_API_KEY trouvée")
    print(f"   Clé: {settings.anthropic_api_key[:20]}...")

    # S'assurer que la clé est dans l'environnement pour Agno
    os.environ["ANTHROPIC_API_KEY"] = settings.anthropic_api_key
    print()

    # 1. Générer le PDF de test
    print("📄 Étape 1: Génération d'un PDF de test...")
    pdf_content = generer_pdf_test()
    print(f"   ✅ PDF généré ({len(pdf_content)} bytes)")
    print()

    # 2. Initialiser les services
    print("📁 Étape 2: Initialisation des services...")

    # Créer le service SurrealDB
    db_service = SurrealDBService(
        url=settings.surreal_url,
        namespace=settings.surreal_namespace,
        database=settings.surreal_database,
        username=settings.surreal_username,
        password=settings.surreal_password,
    )

    # Connecter à SurrealDB
    await db_service.connect()
    print("   ✅ Connecté à SurrealDB")

    # Créer le service des dossiers
    service = DossierService(db=db_service, upload_dir=settings.upload_dir)
    print("   ✅ DossierService initialisé")
    print()

    # 3. Créer un dossier
    print("📁 Étape 3: Création d'un dossier notarial...")
    dossier = await service.create_dossier(
        nom_dossier="Test E2E - Vente Tremblay/Gagnon",
        user_id="user:test_notaire",
        type_transaction="vente",
    )
    print(f"   ✅ Dossier créé: {dossier.id}")
    print(f"      Nom: {dossier.nom_dossier}")
    print(f"      Type: {dossier.type_transaction}")
    print()

    # 4. Upload du document
    print("📤 Étape 4: Upload du document PDF...")
    document = await service.add_document(
        dossier_id=dossier.id,
        file_content=pdf_content,
        filename="promesse_achat_vente_tremblay_gagnon.pdf",
    )
    print(f"   ✅ Document uploadé: {document.id}")
    print(f"      Fichier: {document.nom_fichier}")
    print(f"      Taille: {document.taille_bytes} bytes")
    print(f"      Hash: {document.hash_sha256[:16]}...")
    print()

    # 4. Récupérer la liste des documents pour le workflow
    documents = await service.list_documents(dossier.id)
    fichiers_pdf = [doc.chemin_fichier for doc in documents]

    print(f"📋 Fichiers à analyser: {len(fichiers_pdf)}")
    for f in fichiers_pdf:
        print(f"   - {f}")
    print()

    # 5. Exécuter le workflow Agno
    print("🤖 Étape 5: Exécution du workflow Agno (4 agents)...")
    print("   Ceci peut prendre 1-2 minutes...")
    print()

    metadata = {
        "dossier_id": dossier.id,
        "nom_dossier": dossier.nom_dossier,
        "nb_documents": len(fichiers_pdf),
    }

    try:
        resultat_brut = await workflow_analyse_dossier.arun(
            fichiers_pdf=fichiers_pdf,
            metadata=metadata,
        )

        # Agno retourne un WorkflowRunOutput, pas un dict
        # Le contenu est dans resultat_brut.content
        resultat = resultat_brut.content if hasattr(resultat_brut, 'content') else resultat_brut

        print()
        print("="*80)
        print("✨ RÉSULTATS DE L'ANALYSE")
        print("="*80)
        print()

        if isinstance(resultat, dict) and resultat.get("success"):
            print("✅ Analyse réussie!")
            print()

            # Classification
            if "classification" in resultat:
                classif = resultat["classification"]
                print("🏷️  CLASSIFICATION:")
                print(f"   Type transaction: {classif.get('type_transaction', 'N/A')}")
                print(f"   Type propriété: {classif.get('type_propriete', 'N/A')}")
                print()

            # Vérification
            if "verification" in resultat:
                verif = resultat["verification"]
                print("✅ VÉRIFICATION:")
                print(f"   Score: {verif.get('score_verification', 0):.2%}")
                alertes = verif.get("alertes", [])
                if alertes:
                    print(f"   Alertes: {len(alertes)}")
                    for alerte in alertes[:3]:
                        print(f"      - {alerte}")
                print()

            # Checklist
            if "checklist" in resultat:
                checklist = resultat["checklist"]
                print("📋 CHECKLIST:")
                print(f"   Score de confiance: {resultat.get('score_confiance', 0):.2%}")
                print(f"   Validation requise: {'OUI' if resultat.get('requiert_validation') else 'NON'}")

                items = checklist.get("checklist", [])
                if items:
                    print(f"   Items à vérifier: {len(items)}")
                    for i, item in enumerate(items[:5], 1):
                        priorite = item.get("priorite", "normale")
                        desc = item.get("item", 'N/A')
                        print(f"      {i}. [{priorite.upper()}] {desc}")

                points_attention = checklist.get("points_attention", [])
                if points_attention:
                    print()
                    print("   ⚠️  Points d'attention:")
                    for point in points_attention[:3]:
                        print(f"      - {point}")

                docs_manquants = checklist.get("documents_a_obtenir", [])
                if docs_manquants:
                    print()
                    print("   📄 Documents à obtenir:")
                    for doc in docs_manquants[:3]:
                        print(f"      - {doc}")

                print()

            print(f"Étapes complétées: {', '.join(resultat.get('etapes_completees', []))}")

        else:
            print("❌ Échec de l'analyse")
            print(f"   Erreur à l'étape: {resultat.get('erreur_etape', 'N/A')}")
            print(f"   Message: {resultat.get('erreur_message', 'N/A')}")

    except Exception as e:
        print(f"❌ Erreur pendant l'exécution du workflow: {e}")
        import traceback
        traceback.print_exc()

    print()
    print("="*80)

    # 6. Nettoyage
    print("🧹 Étape 6: Nettoyage...")
    await service.delete_dossier(dossier.id)
    print("   ✅ Dossier supprimé")

    # Déconnecter de SurrealDB
    await db_service.disconnect()
    print("   ✅ Déconnecté de SurrealDB")
    print()

    print("="*80)
    print("✅ TEST TERMINÉ")
    print("="*80)


if __name__ == "__main__":
    asyncio.run(test_workflow_complet())
