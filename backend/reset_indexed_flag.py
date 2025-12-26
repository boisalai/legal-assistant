"""Script pour remettre indexed=false sur tous les documents d'un cours."""
import asyncio
import sys
from services.surreal_service import init_surreal_service, get_surreal_service
from config.settings import settings

async def reset_indexed_flag(course_id: str):
    """Remet indexed=false pour tous les documents d'un cours."""
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

    # Mettre à jour tous les documents
    query = """
        UPDATE document SET indexed = false
        WHERE course_id = $course_id
        AND source_type = 'linked'
        RETURN AFTER
    """
    result = await service.db.query(query, {"course_id": course_id})

    docs = result if result else []
    print(f"✅ Remis indexed=false sur {len(docs)} documents")

if __name__ == "__main__":
    course_id = sys.argv[1] if len(sys.argv) > 1 else "4de2c06d"
    asyncio.run(reset_indexed_flag(course_id))
