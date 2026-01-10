"""Script temporaire pour réindexer tous les documents d'un cours."""
import asyncio
import sys
from services.surreal_service import init_surreal_service, get_surreal_service
from services.document_indexing_service import get_document_indexing_service
from config.settings import settings

async def reindex_course_documents(course_id: str):
    """Réindexe tous les documents d'un cours."""

    # Normaliser course_id
    if not course_id.startswith("course:"):
        course_id = f"course:{course_id}"

    print(f"📚 Réindexation des documents pour {course_id}")

    # Initialiser le service SurrealDB
    init_surreal_service(
        url=settings.surreal_url,
        namespace=settings.surreal_namespace,
        database=settings.surreal_database,
        username=settings.surreal_username,
        password=settings.surreal_password
    )

    # Connexion
    surreal_service = get_surreal_service()
    if not surreal_service.db:
        await surreal_service.connect()
    
    # Récupérer tous les documents avec texte
    result = await surreal_service.query(
        """
        SELECT * FROM document
        WHERE course_id = $course_id
        AND texte_extrait IS NOT NONE
        AND texte_extrait != ''
        ORDER BY created_at DESC
        """,
        {"course_id": course_id}
    )
    
    documents = []
    if result and len(result) > 0:
        first_item = result[0]
        if isinstance(first_item, dict) and "result" in first_item:
            documents = first_item["result"] if isinstance(first_item["result"], list) else []
        elif isinstance(first_item, list):
            documents = first_item
        elif isinstance(first_item, dict):
            documents = result
    
    print(f"📄 Trouvé {len(documents)} documents avec texte extrait")
    
    # Indexer chaque document
    indexing_service = get_document_indexing_service()
    success_count = 0
    error_count = 0
    
    for idx, doc in enumerate(documents, 1):
        doc_id = str(doc.get("id", ""))
        nom_fichier = doc.get("nom_fichier", "Unknown")
        texte_extrait = doc.get("texte_extrait", "")
        
        print(f"\n[{idx}/{len(documents)}] 🔄 Indexation de {nom_fichier}...")
        print(f"  📝 Longueur du texte: {len(texte_extrait)} chars")
        
        try:
            result = await indexing_service.index_document(
                document_id=doc_id,
                course_id=course_id,
                text_content=texte_extrait,
                force_reindex=True
            )
            
            if result.get("success"):
                chunks_created = result.get("chunks_created", 0)
                print(f"  ✅ Succès: {chunks_created} chunks créés")
                
                # Mettre à jour indexed=True
                await surreal_service.merge(doc_id, {"indexed": True})
                success_count += 1
            else:
                error_msg = result.get("error", "Unknown error")
                print(f"  ❌ Échec: {error_msg}")
                error_count += 1
                
        except Exception as e:
            print(f"  ❌ Exception: {e}")
            error_count += 1
    
    print(f"\n{'='*60}")
    print(f"✅ Réindexation terminée:")
    print(f"  - Succès: {success_count}")
    print(f"  - Échecs: {error_count}")
    print(f"{'='*60}")

if __name__ == "__main__":
    course_id = sys.argv[1] if len(sys.argv) > 1 else "938c0203"
    asyncio.run(reindex_course_documents(course_id))
