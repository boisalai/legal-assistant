#!/usr/bin/env python3
"""
Teste le workflow Agno complet d'analyse de dossier avec Claude.

Ce script:
1. Charge les 3 PDFs de test
2. Lance le workflow Agno avec les 4 agents (extraction, classification, vérification, checklist)
3. Affiche les résultats détaillés

Usage:
    uv run python test_workflow_complete.py
"""

import asyncio
import json
from pathlib import Path

from workflows.analyse_dossier import workflow_analyse_dossier


async def main():
    """Fonction principale."""
    print("=" * 70)
    print("🧪 TEST DU WORKFLOW AGNO COMPLET")
    print("=" * 70)
    print()

    # Chemins des PDFs
    test_dir = Path("data/test_pdfs")
    fichiers_pdf = [
        str(test_dir / "promesse_achat_vente.pdf"),
        str(test_dir / "offre_achat.pdf"),
        str(test_dir / "certificat_localisation.pdf"),
    ]

    # Vérifier que les PDFs existent
    missing = [f for f in fichiers_pdf if not Path(f).exists()]
    if missing:
        print("❌ PDFs manquants:")
        for f in missing:
            print(f"   - {f}")
        print("\n💡 Lancez d'abord: uv run python generate_test_pdfs.py")
        return 1

    print(f"📂 Dossier de test avec {len(fichiers_pdf)} documents:")
    for f in fichiers_pdf:
        print(f"   - {Path(f).name}")
    print()

    # Métadonnées du dossier
    metadata = {
        "nom_dossier": "Vente 789 Boulevard Saint-Laurent",
        "type_attendu": "vente",
        "nb_documents": len(fichiers_pdf),
    }

    print("📋 Métadonnées du dossier:")
    print(json.dumps(metadata, indent=2, ensure_ascii=False))
    print()

    # Lancer le workflow
    print("🚀 Lancement du workflow Agno...")
    print("⏳ Ceci peut prendre quelques minutes (4 agents Claude)...")
    print()

    try:
        workflow_output = await workflow_analyse_dossier.arun(
            fichiers_pdf=fichiers_pdf,
            metadata=metadata,
        )

        # Le workflow Agno retourne un WorkflowRunOutput
        # Le résultat de notre fonction analyse_dossier_execution est dans .content
        if hasattr(workflow_output, 'content'):
            resultat = workflow_output.content
        elif hasattr(workflow_output, 'result'):
            resultat = workflow_output.result
        elif hasattr(workflow_output, 'output'):
            resultat = workflow_output.output
        elif isinstance(workflow_output, dict):
            resultat = workflow_output
        else:
            resultat = {}

        # Afficher les résultats
        print("\n" + "=" * 70)
        print("📊 RÉSULTATS DE L'ANALYSE")
        print("=" * 70)
        print()

        # Succès ou échec
        if isinstance(resultat, dict) and resultat.get("success"):
            print("✅ Analyse complétée avec succès!")
        elif isinstance(resultat, dict) and not resultat.get("success"):
            print("❌ Analyse échouée")
            if "erreur_message" in resultat:
                print(f"   Erreur: {resultat['erreur_message']}")
            return 1
        else:
            print("⚠️  Format de résultat inattendu")
            print(f"Type: {type(resultat)}")
            return 1

        # Étapes complétées
        print(f"\nÉtapes complétées: {', '.join(resultat.get('etapes_completees', []))}")

        # Données extraites
        print("\n" + "-" * 70)
        print("1️⃣  DONNÉES EXTRAITES")
        print("-" * 70)
        donnees = resultat.get("donnees_extraites", {})
        if isinstance(donnees, dict):
            documents = donnees.get("documents", [])
            print(f"Nombre de documents traités: {len(documents)}")
            for i, doc in enumerate(documents, 1):
                print(f"\nDocument {i}: {doc.get('nom_fichier', 'N/A')}")
                print(f"  Texte: {len(doc.get('texte', ''))} caractères")
                print(f"  Montants: {len(doc.get('montants', []))}")
                print(f"  Dates: {len(doc.get('dates', []))}")
                print(f"  Noms: {len(doc.get('noms', []))}")
                print(f"  Adresses: {len(doc.get('adresses', []))}")
        else:
            print(json.dumps(donnees, indent=2, ensure_ascii=False)[:500])

        # Classification
        print("\n" + "-" * 70)
        print("2️⃣  CLASSIFICATION")
        print("-" * 70)
        classification = resultat.get("classification", {})
        print(f"Type de transaction: {classification.get('type_transaction', 'N/A')}")
        print(f"Type de propriété: {classification.get('type_propriete', 'N/A')}")
        print(f"Documents identifiés: {len(classification.get('documents_identifies', []))}")
        print(f"Documents manquants: {len(classification.get('documents_manquants', []))}")
        if classification.get('documents_manquants'):
            print("\nDocuments manquants:")
            for doc in classification['documents_manquants'][:5]:
                print(f"  - {doc}")

        # Vérification
        print("\n" + "-" * 70)
        print("3️⃣  VÉRIFICATION")
        print("-" * 70)
        verification = resultat.get("verification", {})
        print(f"Score de vérification: {verification.get('score_verification', 'N/A')}")
        print(f"Nombre d'alertes: {len(verification.get('alertes', []))}")
        if verification.get('alertes'):
            print("\nAlertes:")
            for alerte in verification['alertes'][:5]:
                print(f"  ⚠️  {alerte}")

        # Checklist
        print("\n" + "-" * 70)
        print("4️⃣  CHECKLIST GÉNÉRÉE")
        print("-" * 70)
        checklist = resultat.get("checklist", {})
        print(f"Items de checklist: {len(checklist.get('checklist', []))}")
        print(f"Points d'attention: {len(checklist.get('points_attention', []))}")
        print(f"Documents à obtenir: {len(checklist.get('documents_a_obtenir', []))}")
        print(f"Score de confiance: {checklist.get('score_confiance', 'N/A')}")

        if checklist.get('checklist'):
            print("\nChecklist (5 premiers items):")
            for item in checklist['checklist'][:5]:
                priorite = item.get('priorite', 'N/A')
                emoji = {"haute": "🔴", "moyenne": "🟡", "basse": "🟢"}.get(priorite, "⚪")
                print(f"  {emoji} [{priorite}] {item.get('item', 'N/A')}")

        if checklist.get('points_attention'):
            print("\nPoints d'attention:")
            for point in checklist['points_attention'][:5]:
                print(f"  🚨 {point}")

        # Score de confiance et validation humaine
        print("\n" + "-" * 70)
        print("📈 SCORE DE CONFIANCE")
        print("-" * 70)
        score = resultat.get("score_confiance", 0.0)
        requiert_validation = resultat.get("requiert_validation", True)
        print(f"Score: {score:.2%}")
        print(f"Validation humaine requise: {'OUI 🚨' if requiert_validation else 'NON ✅'}")

        # Sauvegarde JSON complète
        output_file = Path("data/test_pdfs/resultat_analyse.json")
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(resultat, f, indent=2, ensure_ascii=False)
        print(f"\n💾 Résultat complet sauvegardé dans: {output_file}")

        print("\n" + "=" * 70)
        print("✨ TEST TERMINÉ")
        print("=" * 70)
        return 0

    except Exception as e:
        print(f"\n❌ Erreur lors de l'exécution du workflow: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(asyncio.run(main()))
