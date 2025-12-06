"""
Script de migration pour ajouter source_type aux documents existants.

Ce script met à jour tous les documents dans SurrealDB pour ajouter
le champ source_type basé sur leurs caractéristiques existantes.

Usage:
    uv run python migrate_source_types.py
"""

import asyncio
import logging
from services.surreal_service import SurrealDBService
from config.settings import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def migrate_source_types():
    """Ajoute source_type à tous les documents existants."""
    service = SurrealDBService(
        url=settings.surreal_url,
        namespace=settings.surreal_namespace,
        database=settings.surreal_database
    )

    try:
        await service.connect()

        logger.info("🔍 Récupération de tous les documents...")

        # Get all documents
        result = await service.query("SELECT * FROM document")

        if not result or len(result) == 0:
            logger.info("Aucun document trouvé")
            return

        # Parse result similar to debug_db.py
        documents = []
        if result and len(result) > 0:
            first_item = result[0]
            if isinstance(first_item, dict):
                if "result" in first_item:
                    documents = first_item["result"] if isinstance(first_item["result"], list) else []
                elif "id" in first_item or "nom_fichier" in first_item:
                    documents = result
            elif isinstance(first_item, list):
                documents = first_item

        if not documents:
            logger.info("Aucun document trouvé dans la base de données")
            return

        logger.info(f"✅ Trouvé {len(documents)} document(s)")

        updated_count = 0
        skipped_count = 0

        for doc in documents:
            doc_id = doc.get("id")
            current_source_type = doc.get("source_type")

            # Skip if already has source_type
            if current_source_type:
                logger.debug(f"  ⏭️  {doc_id} a déjà source_type={current_source_type}")
                skipped_count += 1
                continue

            # Determine source_type based on document characteristics
            source_type = None

            # Check for Docusaurus source
            if doc.get("docusaurus_source"):
                source_type = "docusaurus"
            # Check for linked source
            elif doc.get("linked_source"):
                source_type = "linked"
            # Check for YouTube source (legacy field)
            elif doc.get("source") == "youtube":
                source_type = "youtube"
            # Default to upload
            else:
                source_type = "upload"

            # Update document
            logger.info(f"  📝 {doc_id}: {doc.get('nom_fichier')} → source_type={source_type}")
            await service.merge(str(doc_id), {"source_type": source_type})
            updated_count += 1

        logger.info("")
        logger.info("=" * 60)
        logger.info(f"✅ Migration terminée !")
        logger.info(f"   Documents mis à jour: {updated_count}")
        logger.info(f"   Documents ignorés (déjà à jour): {skipped_count}")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"❌ Erreur lors de la migration: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    asyncio.run(migrate_source_types())
