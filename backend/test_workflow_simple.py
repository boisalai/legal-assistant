#!/usr/bin/env python3
"""
Test simple du workflow de resume de jugement.

Ce script teste le workflow avec l'API Anthropic (Claude).
"""

import sys
import json
import logging

# Configurer le logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# Jugement de test simplifie
TEST_JUDGMENT = """
COUR SUPERIEURE DU QUEBEC

Dossier: 500-17-123456-234

DATE: 15 janvier 2024

JUGE: L'honorable Marie Tremblay, j.c.s.

ENTRE:
SOCIETE ABC INC.
Demanderesse

ET:
COMPAGNIE XYZ LTEE
Defenderesse

JUGEMENT

[1] La demanderesse reclame des dommages-interets de 150 000 $ pour
bris de contrat de services informatiques.

FAITS

[2] Le 1er mars 2023, les parties ont conclu un contrat de developpement
logiciel pour un systeme de gestion. Le prix convenu etait de 100 000 $.

[3] La defenderesse s'est engagee a livrer le systeme au plus tard
le 1er septembre 2023.

[4] La livraison a ete effectuee le 15 decembre 2023, soit avec plus
de trois mois de retard.

[5] Le systeme livre comportait de nombreux bogues qui le rendaient
inutilisable pour les fins prevues.

[6] La demanderesse a du faire appel a un autre fournisseur pour
corriger les problemes, au cout de 50 000 $.

QUESTIONS EN LITIGE

[7] La defenderesse a-t-elle manque a ses obligations contractuelles?

[8] Quels dommages la demanderesse peut-elle reclamer?

ANALYSE

[9] Selon l'article 1458 du Code civil du Quebec, toute personne a le
devoir d'honorer les engagements qu'elle a contractes.

[10] L'article 1590 C.c.Q. prevoit que le creancier peut demander des
dommages-interets en cas d'inexecution de l'obligation.

[11] La preuve demontre clairement que la defenderesse n'a pas respecte
le delai de livraison et que le produit livre etait defectueux.

[12] Le retard de trois mois a cause un prejudice important a la
demanderesse qui comptait sur ce systeme pour ses operations.

[13] Les couts de correction de 50 000 $ sont directement attribuables
aux defauts du systeme livre.

CONCLUSION

[14] POUR CES MOTIFS, LE TRIBUNAL:

[15] ACCUEILLE l'action de la demanderesse;

[16] CONDAMNE la defenderesse a payer a la demanderesse la somme de
75 000 $ avec interets au taux legal depuis l'assignation;

[17] CONDAMNE la defenderesse aux depens.

________________________________
Marie Tremblay, j.c.s.
"""


def test_workflow():
    """Test le workflow de resume de jugement avec Claude."""
    import os
    from services.model_factory import create_model
    from workflows.summarize_judgment import create_summarize_workflow

    print("=" * 70)
    print("TEST: Workflow de resume de jugement avec Claude")
    print("=" * 70)

    # Creer un modele Claude (utilise claude-sonnet-4-5-20250929 pour rapidite/cout)
    print("\n1. Creation du modele Claude...")
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("   ERREUR: ANTHROPIC_API_KEY non definie")
        return False

    try:
        model = create_model("anthropic:claude-sonnet-4-5-20250929", api_key=api_key)
        print("   OK - Modele Claude cree")
    except Exception as e:
        print(f"   ERREUR: {e}")
        return False

    # Creer le workflow
    print("\n2. Creation du workflow...")
    workflow = create_summarize_workflow(model=model)
    print("   OK - Workflow cree avec 4 agents")

    # Executer le workflow
    print("\n3. Execution du workflow sur le jugement de test...")
    print("   (Ceci peut prendre 30-60 secondes avec 4 agents)")

    try:
        result = workflow.run(TEST_JUDGMENT)
    except Exception as e:
        print(f"   ERREUR lors de l'execution: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Afficher les resultats
    print("\n" + "=" * 70)
    print("RESULTATS")
    print("=" * 70)

    if result.get("success"):
        print(f"\nSucces: OUI")
        print(f"Score de confiance: {result.get('confidence_score', 0):.0%}")
        print(f"\nA retenir: {result.get('key_takeaway', 'N/A')}")

        case_brief = result.get("case_brief", {})
        if case_brief:
            print("\n--- CASE BRIEF ---")
            print(json.dumps(case_brief, ensure_ascii=False, indent=2))
        else:
            print("\n(Pas de case brief genere)")

        return True
    else:
        print(f"\nSucces: NON")
        print(f"Erreur: {result.get('error', 'Inconnue')}")
        return False


if __name__ == "__main__":
    success = test_workflow()
    sys.exit(0 if success else 1)
