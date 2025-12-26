"""
Test du mapping des rubriques CAIJ
Valide que la fonction infer_rubrique retourne les bonnes catégories.
"""

import sys
sys.path.insert(0, '/Users/alain/Workspace/GitHub/legal-assistant/backend')

from models.caij_models import infer_rubrique


def test_rubrique_mapping():
    """Test des différents mappings de rubriques."""
    print("=" * 80)
    print("TEST DU MAPPING DES RUBRIQUES CAIJ")
    print("=" * 80)
    print()

    # Cas de test (document_type, source, url, rubrique_attendue)
    test_cases = [
        # Dictionnaires
        (
            "Terme juridique défini",
            "Dictionnaire de droit québécois et canadien",
            "https://app.caij.qc.ca/fr/dictionnaires/dictionnaire-reid-6/Mariage",
            "Dictionnaires"
        ),
        (
            "Terme juridique défini",
            "Dictionnaire de droit privé et lexiques bilingues",
            "https://app.caij.qc.ca/fr/dictionnaires/dictionnaire-prive/Contrat",
            "Dictionnaires"
        ),

        # Doctrine en ligne
        (
            "Périodiques et revues",
            "Revue du notariat",
            "https://app.caij.qc.ca/doctrine/publications/revue-du-notariat",
            "Doctrine en ligne"
        ),
        (
            "Congrès et conférences",
            "Cours de perfectionnement du notariat",
            "https://app.caij.qc.ca/doctrine/congres",
            "Doctrine en ligne"
        ),

        # Catalogue de bibliothèque
        (
            "Livres",
            "Répertoire de droit / Nouvelle série",
            "https://app.caij.qc.ca/catalogue/livre/123",
            "Catalogue de bibliothèque"
        ),
        (
            "Livres",
            "Corporation sans but lucratif",
            "https://app.caij.qc.ca/catalogue",
            "Catalogue de bibliothèque"
        ),

        # Jurisprudence
        (
            "Jugement",
            "Cour d'appel du Québec",
            "https://app.caij.qc.ca/jurisprudence/cour-appel",
            "Jurisprudence"
        ),
        (
            "Décision",
            "Tribunal administratif du Québec",
            "https://app.caij.qc.ca/jurisprudence/taq",
            "Jurisprudence"
        ),

        # Législation
        (
            "Loi",
            "Code civil du Québec",
            "https://app.caij.qc.ca/legislation/code-civil",
            "Législation"
        ),
        (
            "Règlement",
            "Gazette officielle du Québec",
            "https://app.caij.qc.ca/lois/reglement",
            "Législation"
        ),

        # Lois annotées
        (
            "Loi annotée",
            "Code civil annoté",
            "https://app.caij.qc.ca/lois-annotees/ccq",
            "Lois annotées"
        ),

        # Modèles et formulaires
        (
            "Formulaire",
            "Modèles et formulaires",
            "https://app.caij.qc.ca/formulaires/contrat",
            "Modèles et formulaires"
        ),

        # Questions de recherche documentées
        (
            "Question de recherche",
            "Recherches documentées",
            "https://app.caij.qc.ca/questions-recherche/123",
            "Questions de recherche documentées"
        ),
    ]

    passed = 0
    failed = 0

    for doc_type, source, url, expected_rubrique in test_cases:
        result = infer_rubrique(doc_type, source, url)

        status = "✅ PASS" if result == expected_rubrique else "❌ FAIL"

        if result == expected_rubrique:
            passed += 1
        else:
            failed += 1

        print(f"{status}")
        print(f"  Type: {doc_type}")
        print(f"  Source: {source[:50]}...")
        print(f"  Attendu: {expected_rubrique}")
        print(f"  Obtenu:  {result}")
        print()

    # Résumé
    print("=" * 80)
    print(f"Résultats: {passed}/{len(test_cases)} tests passés ({passed/len(test_cases)*100:.1f}%)")

    if failed > 0:
        print(f"❌ {failed} tests échoués")
    else:
        print("✅ Tous les tests passent!")

    print("=" * 80)


if __name__ == "__main__":
    test_rubrique_mapping()
