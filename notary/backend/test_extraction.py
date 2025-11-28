#!/usr/bin/env python3
"""
Teste l'extraction de données des PDFs de test.

Valide que nos tools (extraire_texte_pdf, extraire_montants, etc.)
fonctionnent correctement sur des documents réalistes.

Usage:
    uv run python test_extraction.py
"""

import json
from pathlib import Path
from workflows.tools import (
    extraire_texte_pdf,
    extraire_montants,
    extraire_dates,
    extraire_noms,
    extraire_adresses,
)


def test_pdf(pdf_path: str):
    """Teste l'extraction sur un PDF donné."""
    print(f"\n{'='*70}")
    print(f"📄 Test: {Path(pdf_path).name}")
    print(f"{'='*70}\n")

    # 1. Extraire le texte complet
    print("1️⃣  Extraction du texte...")
    try:
        texte = extraire_texte_pdf(pdf_path)
        print(f"✅ Texte extrait ({len(texte)} caractères)")
        print(f"Aperçu: {texte[:200]}...\n")
    except Exception as e:
        print(f"❌ Erreur: {e}\n")
        return

    # 2. Extraire les montants
    print("2️⃣  Extraction des montants...")
    try:
        montants = extraire_montants(texte)
        print(f"✅ {len(montants)} montants trouvés:")
        for montant in montants[:10]:  # Limiter à 10 pour affichage
            print(f"   - {montant}")
        if len(montants) > 10:
            print(f"   ... et {len(montants) - 10} autres")
        print()
    except Exception as e:
        print(f"❌ Erreur: {e}\n")

    # 3. Extraire les dates
    print("3️⃣  Extraction des dates...")
    try:
        dates = extraire_dates(texte)
        print(f"✅ {len(dates)} dates trouvées:")
        for date in dates[:10]:
            print(f"   - {date}")
        if len(dates) > 10:
            print(f"   ... et {len(dates) - 10} autres")
        print()
    except Exception as e:
        print(f"❌ Erreur: {e}\n")

    # 4. Extraire les noms
    print("4️⃣  Extraction des noms...")
    try:
        noms = extraire_noms(texte)
        print(f"✅ {len(noms)} noms trouvés:")
        for nom in noms[:10]:
            print(f"   - {nom}")
        if len(noms) > 10:
            print(f"   ... et {len(noms) - 10} autres")
        print()
    except Exception as e:
        print(f"❌ Erreur: {e}\n")

    # 5. Extraire les adresses
    print("5️⃣  Extraction des adresses...")
    try:
        adresses = extraire_adresses(texte)
        print(f"✅ {len(adresses)} adresses trouvées:")
        for adresse in adresses[:10]:
            print(f"   - {adresse}")
        if len(adresses) > 10:
            print(f"   ... et {len(adresses) - 10} autres")
        print()
    except Exception as e:
        print(f"❌ Erreur: {e}\n")

    # Résumé JSON
    print("📊 Résumé JSON:")
    summary = {
        "fichier": Path(pdf_path).name,
        "texte_caracteres": len(texte),
        "montants": montants,
        "dates": dates,
        "noms": noms,
        "adresses": adresses,
    }
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    print()


def main():
    """Fonction principale."""
    print("=" * 70)
    print("🧪 TEST D'EXTRACTION DE DONNÉES")
    print("=" * 70)

    # Chemins des PDFs de test
    test_dir = Path("data/test_pdfs")
    pdfs = [
        test_dir / "promesse_achat_vente.pdf",
        test_dir / "offre_achat.pdf",
        test_dir / "certificat_localisation.pdf",
    ]

    # Vérifier que les PDFs existent
    missing = [pdf for pdf in pdfs if not pdf.exists()]
    if missing:
        print("\n❌ PDFs manquants:")
        for pdf in missing:
            print(f"   - {pdf}")
        print("\n💡 Lancez d'abord: uv run python generate_test_pdfs.py")
        return 1

    # Tester chaque PDF
    for pdf in pdfs:
        test_pdf(str(pdf))

    # Résumé final
    print("=" * 70)
    print("✨ TESTS D'EXTRACTION TERMINÉS")
    print("=" * 70)
    print()
    print("✅ Prochaines étapes:")
    print("  1. Si les extractions sont correctes, lancer le workflow complet")
    print("  2. Si des patterns manquent, ajuster les regex dans workflows/tools.py")
    print("  3. Tester avec l'API: POST /api/dossiers/{id}/analyser")
    print()

    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
