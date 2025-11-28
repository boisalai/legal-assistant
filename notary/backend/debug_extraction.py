#!/usr/bin/env python3
"""
Debug de l'extraction de données avec l'agent Claude.

Ce script teste juste l'agent extracteur pour comprendre pourquoi
il ne retourne pas de données.
"""

import asyncio
import json
from pathlib import Path

from workflows.analyse_dossier import agent_extracteur


async def main():
    """Fonction principale."""
    print("=" * 70)
    print("🐛 DEBUG: Agent Extracteur")
    print("=" * 70)
    print()

    # Fichier PDF de test
    pdf_path = "data/test_pdfs/promesse_achat_vente.pdf"

    if not Path(pdf_path).exists():
        print(f"❌ PDF non trouvé: {pdf_path}")
        return 1

    print(f"📄 Test avec: {pdf_path}")
    print()

    # Prompt pour l'agent
    prompt = f"""
    Extrais toutes les informations du document suivant.

    Fichier à analyser: {pdf_path}

    Utilise les tools disponibles pour extraire:
    - Le texte complet (extraire_texte_pdf)
    - Les montants (extraire_montants)
    - Les dates (extraire_dates)
    - Les noms (extraire_noms)
    - Les adresses (extraire_adresses)

    Retourne un JSON avec la structure DonneesExtraites contenant
    une liste "documents" avec un objet DocumentExtrait.
    """

    print("📤 Prompt envoyé à l'agent:")
    print(prompt)
    print()

    print("⏳ Appel de l'agent extracteur...")
    print()

    try:
        # Appeler l'agent
        response = await agent_extracteur.arun(prompt)

        print("=" * 70)
        print("📥 RÉPONSE DE L'AGENT")
        print("=" * 70)
        print()

        # Afficher le type de réponse
        print(f"Type de réponse: {type(response)}")
        print()

        # Afficher le contenu
        if hasattr(response, 'content'):
            print("Contenu (.content):")
            print(response.content)
            print()

        # Afficher les messages
        if hasattr(response, 'messages'):
            print(f"Nombre de messages: {len(response.messages)}")
            for i, msg in enumerate(response.messages, 1):
                print(f"\nMessage {i}:")
                print(f"  Role: {msg.role if hasattr(msg, 'role') else 'N/A'}")
                if hasattr(msg, 'content'):
                    content = msg.content
                    if isinstance(content, str):
                        print(f"  Content: {content[:200]}...")
                    else:
                        print(f"  Content type: {type(content)}")
            print()

        # Essayer de parser comme JSON si c'est une string
        if hasattr(response, 'content') and isinstance(response.content, str):
            try:
                parsed = json.loads(response.content)
                print("✅ Réponse parsée comme JSON:")
                print(json.dumps(parsed, indent=2, ensure_ascii=False)[:500])
            except json.JSONDecodeError as e:
                print(f"❌ Impossible de parser comme JSON: {e}")

        # Afficher les attributs disponibles
        print("\nAttributs de l'objet response:")
        for attr in dir(response):
            if not attr.startswith('_'):
                print(f"  - {attr}")

        return 0

    except Exception as e:
        print(f"❌ Erreur lors de l'appel de l'agent: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(asyncio.run(main()))
