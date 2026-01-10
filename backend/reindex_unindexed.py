"""Script pour réindexer tous les documents avec indexed=false."""
import asyncio
import sys
from services.surreal_service import init_surreal_service, get_surreal_service
from services.document_indexing_service import DocumentIndexingService
from config.settings import settings

async def reindex_unindexed_documents(course_id: str):
    """Réindexe tous les documents avec indexed=false pour un cours."""
    # Initialiser le service SurrealDB
    init_surreal_service(
        url=settings.surreal_url,
        namespace=settings.surreal_namespace,
        database=settings.surreal_database
    )
    service = get_surreal_service()
    if not service.db:
        await service.connect()

    # Normaliser l'ID du cours
    if not course_id.startswith("course:"):
        course_id = f"course:{course_id}"

    # Récupérer tous les documents non indexés
    query = """
        SELECT * FROM document
        WHERE course_id = $course_id
        AND indexed = false
        AND texte_extrait IS NOT NONE
    """
    result = await service.db.query(query, {"course_id": course_id})
    docs = result if result else []

    if not docs:
        print(f"Aucun document non indexé trouvé pour {course_id}")
        return

    print(f"Trouvé {len(docs)} documents non indexés")
    indexing_service = DocumentIndexingService()

    indexed_count = 0
    failed_count = 0

    for doc in docs:
        doc_id = str(doc["id"])  # Convert RecordID to string
        texte_extrait = doc.get("texte_extrait")
        nom_fichier = doc.get("nom_fichier", "unknown")

        if not texte_extrait or not texte_extrait.strip():
            print(f"⚠️  {nom_fichier} - Pas de texte extrait, skip")
            continue

        print(f"📄 Indexation de {nom_fichier}...")

        try:
            result = await indexing_service.index_document(
                document_id=doc_id,
                course_id=course_id,
                text_content=texte_extrait
            )

            if result.get("success"):
                # Mettre à jour indexed=True
                await service.merge(doc_id, {"indexed": True})
                indexed_count += 1
                chunks = result.get("chunks_created", 0)
                print(f"   ✅ Indexé ({chunks} chunks)")
            else:
                failed_count += 1
                error = result.get("error", "Unknown error")
                print(f"   ❌ Échec: {error}")

        except Exception as e:
            failed_count += 1
            print(f"   ❌ Erreur: {e}")

    print(f"\n📊 Résumé:")
    print(f"   - Indexés: {indexed_count}")
    print(f"   - Échecs: {failed_count}")
    print(f"   - Total: {len(docs)}")

if __name__ == "__main__":
    course_id = sys.argv[1] if len(sys.argv) > 1 else "4de2c06d"
    asyncio.run(reindex_unindexed_documents(course_id))
