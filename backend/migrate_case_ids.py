"""
Script de migration pour mettre à jour case_id de "judgment:" vers "case:".

Ce script met à jour tous les documents et autres records dans SurrealDB
pour utiliser le nouveau format "case:" au lieu de "judgment:".

Usage:
    uv run python migrate_case_ids.py
"""

import asyncio
import logging
from services.surreal_service import get_surreal_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def migrate_case_ids():
    """Migrate all case_id from judgment: to case: format."""
    try:
        service = get_surreal_service()
        await service.connect()

        logger.info("Starting case_id migration from 'judgment:' to 'case:'...")

        # Update documents table
        logger.info("Updating document table...")
        result = await service.query(
            """
            UPDATE document SET case_id = string::replace(case_id, "judgment:", "case:")
            WHERE case_id CONTAINS "judgment:"
            RETURN BEFORE, AFTER
            """
        )

        if result and len(result) > 0:
            updated_docs = result[0].get("result", []) if isinstance(result[0], dict) else result
            logger.info(f"Updated {len(updated_docs)} documents")

            # Show first 3 examples
            for i, doc in enumerate(updated_docs[:3]):
                before_id = doc.get("BEFORE", {}).get("case_id", "N/A")
                after_id = doc.get("AFTER", {}).get("case_id", "N/A")
                logger.info(f"  Example {i+1}: {before_id} → {after_id}")
        else:
            logger.info("No documents needed updating")

        # Update conversation table
        logger.info("Updating conversation table...")
        result = await service.query(
            """
            UPDATE conversation SET case_id = string::replace(case_id, "judgment:", "case:")
            WHERE case_id CONTAINS "judgment:"
            RETURN BEFORE, AFTER
            """
        )

        if result and len(result) > 0:
            updated_convs = result[0].get("result", []) if isinstance(result[0], dict) else result
            logger.info(f"Updated {len(updated_convs)} conversations")
        else:
            logger.info("No conversations needed updating")

        # Update document_embedding table
        logger.info("Updating document_embedding table...")
        result = await service.query(
            """
            UPDATE document_embedding SET case_id = string::replace(case_id, "judgment:", "case:")
            WHERE case_id CONTAINS "judgment:"
            RETURN BEFORE, AFTER
            """
        )

        if result and len(result) > 0:
            updated_embs = result[0].get("result", []) if isinstance(result[0], dict) else result
            logger.info(f"Updated {len(updated_embs)} embeddings")
        else:
            logger.info("No embeddings needed updating")

        logger.info("✅ Migration completed successfully!")
        logger.info("You can now restart the backend to see all documents.")

    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        raise
    finally:
        if service.db:
            await service.close()


if __name__ == "__main__":
    asyncio.run(migrate_case_ids())
