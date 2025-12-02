#!/usr/bin/env python3
"""
Script de migration pour lier les fichiers dérivés existants à leurs fichiers sources.

Ce script identifie:
1. Les transcriptions (is_transcription=True) et les lie à leur audio source
2. Les fichiers TTS (is_tts=True) et les lie à leur document source
3. Les fichiers markdown issus de PDF (heuristique par nom de fichier)

Et ajoute les champs:
- source_document_id: ID du document parent
- is_derived: True
- derivation_type: "transcription", "pdf_extraction", ou "tts"
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.surreal_service import init_surreal_service, get_surreal_service
from config.settings import settings


async def migrate_transcriptions(service):
    """Migrer les transcriptions existantes."""
    print("\n=== Migration des transcriptions ===")

    # Récupérer toutes les transcriptions avec source_audio
    result = await service.query(
        "SELECT * FROM document WHERE is_transcription = true AND source_audio IS NOT NONE"
    )

    if not result or len(result) == 0:
        print("Aucune transcription trouvée")
        return 0

    items = result[0].get("result", result) if isinstance(result[0], dict) else result
    if not isinstance(items, list):
        items = []

    migrated = 0
    for trans in items:
        trans_id = str(trans.get("id", ""))
        source_filename = trans.get("source_audio")
        judgment_id = trans.get("judgment_id")

        if not source_filename or not judgment_id:
            print(f"  ⚠️  Transcription {trans_id}: source_audio ou judgment_id manquant")
            continue

        # Trouver le document audio source
        audio_result = await service.query(
            "SELECT * FROM document WHERE judgment_id = $judgment_id AND nom_fichier = $filename",
            {"judgment_id": judgment_id, "filename": source_filename}
        )

        if audio_result and len(audio_result) > 0:
            audio_items = audio_result[0].get("result", audio_result) if isinstance(audio_result[0], dict) else audio_result
            if isinstance(audio_items, list) and len(audio_items) > 0:
                audio_doc = audio_items[0]
                audio_doc_id = str(audio_doc.get("id", ""))

                if audio_doc_id:
                    # Mettre à jour la transcription
                    await service.merge(trans_id, {
                        "source_document_id": audio_doc_id,
                        "is_derived": True,
                        "derivation_type": "transcription"
                    })
                    migrated += 1
                    print(f"  ✓  {trans.get('nom_fichier', 'unknown')} → {source_filename}")
        else:
            print(f"  ⚠️  Audio source non trouvé pour: {trans.get('nom_fichier', 'unknown')}")

    print(f"\nTranscriptions migrées: {migrated}")
    return migrated


async def migrate_tts_files(service):
    """Migrer les fichiers TTS existants."""
    print("\n=== Migration des fichiers TTS ===")

    # Récupérer tous les fichiers TTS
    result = await service.query(
        "SELECT * FROM document WHERE is_tts = true"
    )

    if not result or len(result) == 0:
        print("Aucun fichier TTS trouvé")
        return 0

    items = result[0].get("result", result) if isinstance(result[0], dict) else result
    if not isinstance(items, list):
        items = []

    migrated = 0
    for tts in items:
        tts_id = str(tts.get("id", ""))

        # Les fichiers TTS ont déjà source_document (qui est l'ID)
        source_doc_id = tts.get("source_document")

        if source_doc_id:
            # Mettre à jour avec les nouveaux champs
            await service.merge(tts_id, {
                "source_document_id": source_doc_id,  # Copier source_document
                "is_derived": True,
                "derivation_type": "tts"
            })
            migrated += 1
            print(f"  ✓  {tts.get('nom_fichier', 'unknown')}")
        else:
            print(f"  ⚠️  TTS sans source_document: {tts.get('nom_fichier', 'unknown')}")

    print(f"\nFichiers TTS migrés: {migrated}")
    return migrated


async def migrate_pdf_extractions(service):
    """Migrer les extractions PDF existantes (heuristique par nom)."""
    print("\n=== Migration des extractions PDF ===")

    # Récupérer tous les fichiers markdown qui ne sont PAS des transcriptions
    result = await service.query(
        "SELECT * FROM document WHERE type_fichier = 'md' AND (is_transcription IS NULL OR is_transcription = false)"
    )

    if not result or len(result) == 0:
        print("Aucun fichier markdown (non-transcription) trouvé")
        return 0

    items = result[0].get("result", result) if isinstance(result[0], dict) else result
    if not isinstance(items, list):
        items = []

    migrated = 0
    for md in items:
        md_id = str(md.get("id", ""))
        md_filename = md.get("nom_fichier", "")
        judgment_id = md.get("judgment_id")

        if not md_filename or not judgment_id:
            continue

        # Heuristique: chercher un PDF avec le même nom de base
        # Ex: "rapport.md" → "rapport.pdf"
        base_name = md_filename.replace(".md", "").replace(".MD", "")
        pdf_filename = f"{base_name}.pdf"

        # Chercher le PDF source
        pdf_result = await service.query(
            "SELECT * FROM document WHERE judgment_id = $judgment_id AND nom_fichier = $filename",
            {"judgment_id": judgment_id, "filename": pdf_filename}
        )

        if pdf_result and len(pdf_result) > 0:
            pdf_items = pdf_result[0].get("result", pdf_result) if isinstance(pdf_result[0], dict) else pdf_result
            if isinstance(pdf_items, list) and len(pdf_items) > 0:
                pdf_doc = pdf_items[0]
                pdf_doc_id = str(pdf_doc.get("id", ""))

                if pdf_doc_id:
                    # Mettre à jour le markdown
                    await service.merge(md_id, {
                        "source_document_id": pdf_doc_id,
                        "is_derived": True,
                        "derivation_type": "pdf_extraction"
                    })
                    migrated += 1
                    print(f"  ✓  {md_filename} → {pdf_filename}")
        else:
            print(f"  ⚠️  PDF source non trouvé pour: {md_filename} (cherché: {pdf_filename})")

    print(f"\nExtractions PDF migrées: {migrated}")
    return migrated


async def main():
    """Point d'entrée principal."""
    print("=" * 60)
    print("Migration des fichiers dérivés")
    print("=" * 60)

    # Initialiser le service SurrealDB
    init_surreal_service(
        url=settings.surreal_url,
        namespace=settings.surreal_namespace,
        database=settings.surreal_database
    )
    service = get_surreal_service()

    try:
        # Connexion à SurrealDB
        print("\nConnexion à SurrealDB...")
        if not service.db:
            await service.connect()
        print("✓ Connecté")

        # Migration des transcriptions
        trans_count = await migrate_transcriptions(service)

        # Migration des fichiers TTS
        tts_count = await migrate_tts_files(service)

        # Migration des extractions PDF
        pdf_count = await migrate_pdf_extractions(service)

        # Résumé
        print("\n" + "=" * 60)
        print(f"RÉSUMÉ DE LA MIGRATION")
        print("=" * 60)
        print(f"Transcriptions migrées: {trans_count}")
        print(f"Fichiers TTS migrés: {tts_count}")
        print(f"Extractions PDF migrées: {pdf_count}")
        print(f"TOTAL: {trans_count + tts_count + pdf_count}")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ Erreur lors de la migration: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        # Déconnexion
        if service.db:
            await service.db.close()
            print("\n✓ Déconnecté de SurrealDB")


if __name__ == "__main__":
    asyncio.run(main())
