"""
Script de diagnostic pour vérifier les relations entre documents.
"""

import asyncio
import sys
from services.surreal_service import get_db_connection


async def diagnose_documents(judgment_id: str):
    """Diagnose document relationships."""

    print(f"\n{'='*80}")
    print(f"DIAGNOSTIC DES DOCUMENTS - Dossier: {judgment_id}")
    print(f"{'='*80}\n")

    # Normalize judgment_id
    if not judgment_id.startswith("judgment:"):
        judgment_id = f"judgment:{judgment_id}"

    async with get_db_connection() as service:
        # Get all documents
        docs_result = await service.query(
            "SELECT * FROM document WHERE judgment_id = $judgment_id ORDER BY created_at DESC",
            {"judgment_id": judgment_id}
        )

        documents = []
        if docs_result and len(docs_result) > 0:
            first_item = docs_result[0]
            if isinstance(first_item, dict):
                if "result" in first_item:
                    documents = first_item["result"] if isinstance(first_item["result"], list) else []
                elif "id" in first_item or "nom_fichier" in first_item:
                    documents = docs_result
            elif isinstance(first_item, list):
                documents = first_item

        print(f"📄 Nombre total de documents: {len(documents)}\n")

        # Build relationship maps
        audio_transcription_map = {}

        for doc in documents:
            nom_fichier = doc.get("nom_fichier", "Unknown")
            doc_type = doc.get("type_fichier", "").upper()
            is_transcription = doc.get("is_transcription", False)
            source_audio = doc.get("source_audio", "")
            texte_extrait = doc.get("texte_extrait", "")

            print(f"📌 {nom_fichier} ({doc_type})")
            print(f"   - is_transcription: {is_transcription}")
            print(f"   - source_audio: '{source_audio}'")
            print(f"   - texte_extrait présent: {bool(texte_extrait)} ({len(texte_extrait)} chars)")

            if is_transcription and source_audio:
                audio_transcription_map[source_audio] = nom_fichier
                print(f"   ✅ Relation détectée: {source_audio} → {nom_fichier}")

            print()

        print(f"\n{'='*80}")
        print("RÉSUMÉ DES RELATIONS DÉTECTÉES")
        print(f"{'='*80}\n")

        if audio_transcription_map:
            print("🔗 Relations audio → transcription:")
            for audio_file, transcription_file in audio_transcription_map.items():
                print(f"   {audio_file} → {transcription_file}")
        else:
            print("❌ Aucune relation audio → transcription détectée")
            print("\n⚠️  PROBLÈME POTENTIEL:")
            print("   - Vérifiez que le champ 'source_audio' est bien rempli dans les documents de transcription")
            print("   - Vérifiez que le champ 'is_transcription' est à True pour les transcriptions")

        print(f"\n{'='*80}\n")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python diagnostic_documents.py <judgment_id>")
        print("Exemple: python diagnostic_documents.py 1f9fc70e")
        sys.exit(1)

    judgment_id = sys.argv[1]
    asyncio.run(diagnose_documents(judgment_id))
