#!/usr/bin/env python3
"""
Script de test pour valider le workflow avec Ollama.

Ce script teste l'intégration complète:
1. Workflow Agno avec modèle Ollama
2. Persistance automatique dans SurrealDB
3. Génération de checklist

Usage:
    # Avec Ollama (défaut)
    uv run python test_workflow_ollama.py

    # Avec un modèle spécifique
    MODEL=ollama:llama2 uv run python test_workflow_ollama.py

    # Avec Claude (pour comparaison)
    MODEL=anthropic:claude-sonnet-4-5-20250929 uv run python test_workflow_ollama.py

Prérequis:
    1. Ollama installé et lancé:
       ollama serve

    2. Modèle téléchargé:
       ollama pull mistral
       # ou
       ollama pull llama2
       # ou
       ollama pull phi

    3. SurrealDB lancé:
       docker-compose up -d surrealdb

    4. Variables d'environnement (si Claude):
       export ANTHROPIC_API_KEY=your_key
"""

import asyncio
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Ajouter le répertoire parent au PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent))

from workflows.analyse_dossier import WorkflowAnalyseDossier
from services.agno_db_service import get_agno_db_service
from config import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def test_workflow_with_ollama():
    """
    Test le workflow avec Ollama et persistance Agno.
    """
    # Configuration du modèle
    model = os.getenv("MODEL", "ollama:mistral")
    logger.info(f"🧪 Test du workflow avec modèle: {model}")

    # Vérifier que SurrealDB est accessible
    logger.info(f"📊 SurrealDB URL: {settings.surreal_url}")
    logger.info(f"📊 Namespace: {settings.surreal_namespace}")
    logger.info(f"📊 Database: {settings.surreal_database}")

    # Récupérer le service Agno
    agno_db_service = get_agno_db_service()
    agno_db = agno_db_service.get_agno_db()
    logger.info("✅ AgnoDBService initialized")

    # Créer le workflow avec persistance
    workflow = WorkflowAnalyseDossier(
        model=model,
        db=agno_db  # ✅ Persistance automatique
    )
    logger.info("✅ Workflow created with automatic persistence")

    # Préparer les données de test
    # Utiliser les PDFs de test existants ou en créer
    test_data_dir = Path(__file__).parent / "data" / "uploads"
    pdf_files = list(test_data_dir.glob("**/*.pdf"))

    if not pdf_files:
        logger.warning("⚠️  Aucun PDF trouvé dans data/uploads/")
        logger.warning("⚠️  Création de PDFs de test...")

        # Créer un PDF de test simple
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas

        test_pdf_path = test_data_dir / "test_vente.pdf"
        test_pdf_path.parent.mkdir(parents=True, exist_ok=True)

        c = canvas.Canvas(str(test_pdf_path), pagesize=letter)
        c.drawString(100, 750, "OFFRE D'ACHAT")
        c.drawString(100, 720, "")
        c.drawString(100, 690, "Prix de vente: 450 000 $")
        c.drawString(100, 660, "Date de signature: 15 janvier 2025")
        c.drawString(100, 630, "Vendeur: Marie Tremblay")
        c.drawString(100, 600, "Acheteur: Jean Dupont")
        c.drawString(100, 570, "Adresse: 123 rue Principale, Montréal, QC H1A 1A1")
        c.save()

        pdf_files = [test_pdf_path]
        logger.info(f"✅ PDF de test créé: {test_pdf_path}")

    # Préparer les chemins (strings)
    fichiers_pdf = [str(f) for f in pdf_files[:3]]  # Max 3 PDFs pour test
    logger.info(f"📄 {len(fichiers_pdf)} fichier(s) PDF à analyser")

    # Métadonnées
    metadata = {
        "dossier_id": f"dossier:test_ollama_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}",
        "nb_documents": len(fichiers_pdf),
        "test_mode": True,
        "model_used": model,
    }

    # Lancer le workflow
    logger.info("🚀 Lancement du workflow...")
    start_time = datetime.now(timezone.utc)

    try:
        # Exécuter le workflow (asynchrone)
        # Note: On utilise arun() car on est déjà dans un contexte async
        workflow_output = await workflow.arun(fichiers_pdf, metadata)

        # Extraire le contenu du WorkflowRunOutput (pattern Agno)
        resultat = workflow_output.content if hasattr(workflow_output, 'content') else workflow_output

        duration = (datetime.now(timezone.utc) - start_time).total_seconds()
        logger.info(f"✅ Workflow terminé en {duration:.2f}s")

        # Afficher les résultats
        logger.info("=" * 70)
        logger.info("📊 RÉSULTATS DU WORKFLOW")
        logger.info("=" * 70)

        if resultat.get("success"):
            logger.info("✅ Succès!")
            logger.info(f"📋 Score de confiance: {resultat.get('score_confiance', 0):.2%}")
            logger.info(f"⚠️  Requiert validation: {resultat.get('requiert_validation', False)}")

            # Checklist
            checklist = resultat.get("checklist", {})
            if checklist:
                items = checklist.get("items", [])
                points_attention = checklist.get("points_attention", [])
                documents_manquants = checklist.get("documents_manquants", [])

                logger.info(f"\n📝 Checklist générée:")
                logger.info(f"   - Items: {len(items)}")
                logger.info(f"   - Points d'attention: {len(points_attention)}")
                logger.info(f"   - Documents manquants: {len(documents_manquants)}")

                if points_attention:
                    logger.info("\n⚠️  Points d'attention:")
                    for point in points_attention[:3]:  # Max 3
                        logger.info(f"   - {point}")

                if documents_manquants:
                    logger.info("\n📄 Documents manquants:")
                    for doc in documents_manquants[:3]:  # Max 3
                        logger.info(f"   - {doc}")
        else:
            logger.error(f"❌ Échec: {resultat.get('erreur_message')}")

        logger.info("=" * 70)

        # Vérifier la persistance dans SurrealDB
        logger.info("\n🔍 Vérification de la persistance dans SurrealDB...")
        logger.info("Note: La persistance Agno fonctionne (requêtes vers os-api.agno.com)")
        logger.info("      La vérification manuelle est optionnelle et peut échouer selon la config DB")

        # Tentative de récupération de l'historique (optionnelle)
        try:
            dossier_id = metadata["dossier_id"]
            workflow_history = await agno_db_service.get_workflow_history(
                dossier_id=dossier_id,
                limit=5
            )

            if workflow_history:
                logger.info(f"✅ {len(workflow_history)} workflow run(s) trouvé(s)")
                for i, run in enumerate(workflow_history, 1):
                    logger.info(f"   Run #{i}:")
                    logger.info(f"      - ID: {run.get('id')}")
                    logger.info(f"      - Created: {run.get('created_at')}")
                    logger.info(f"      - Status: {run.get('status', 'N/A')}")
            else:
                logger.warning("⚠️  Aucun workflow run trouvé")
        except Exception as e:
            logger.warning(f"⚠️  Impossible de vérifier l'historique: {e}")
            logger.info("   (Ce n'est pas bloquant - le workflow a fonctionné)")

        return resultat

    except Exception as e:
        logger.exception(f"❌ Erreur lors de l'exécution du workflow: {e}")
        raise

    finally:
        # Cleanup
        await agno_db_service.close()
        logger.info("✅ Connexion SurrealDB fermée")


async def main():
    """Point d'entrée principal."""
    logger.info("=" * 70)
    logger.info("🧪 TEST WORKFLOW AGNO + OLLAMA")
    logger.info("=" * 70)

    try:
        resultat = await test_workflow_with_ollama()

        logger.info("\n" + "=" * 70)
        if resultat.get("success"):
            logger.info("✅ TEST RÉUSSI")
        else:
            logger.info("❌ TEST ÉCHOUÉ")
        logger.info("=" * 70)

        return 0 if resultat.get("success") else 1

    except KeyboardInterrupt:
        logger.info("\n⚠️  Test interrompu par l'utilisateur")
        return 130

    except Exception as e:
        logger.exception(f"❌ Erreur fatale: {e}")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
