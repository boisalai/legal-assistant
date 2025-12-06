"""
Script pour retirer le frontmatter YAML des documents Docusaurus existants.

Ce script met à jour tous les documents Docusaurus dans SurrealDB pour
retirer les métadonnées YAML (frontmatter) du contenu.

Usage:
    uv run python clean_docusaurus_frontmatter.py
"""

import asyncio
import logging
from services.surreal_service import SurrealDBService
from config.settings import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def remove_frontmatter(content: str) -> str:
    """
    Retire le frontmatter YAML (métadonnées Docusaurus) du contenu Markdown.
    """
    lines = content.split('\n')

    # Vérifier si le fichier commence par ---
    if not lines or not lines[0].strip() == '---':
        return content

    # Trouver la fin du frontmatter (deuxième ---)
    for i in range(1, len(lines)):
        if lines[i].strip() == '---':
            # Retourner tout après le frontmatter
            remaining = '\n'.join(lines[i+1:])
            return remaining.lstrip('\n')

    # Si pas de deuxième ---, retourner le contenu original
    return content


async def clean_frontmatter():
    """Nettoie le frontmatter de tous les documents Docusaurus."""
    service = SurrealDBService(
        url=settings.surreal_url,
        namespace=settings.surreal_namespace,
        database=settings.surreal_database
    )

    try:
        await service.connect()
        logger.info("🔍 Recherche des documents Markdown...")

        # Récupérer tous les documents Markdown (md ou mdx)
        result = await service.query(
            "SELECT * FROM document WHERE type_fichier IN ['md', 'mdx']"
        )

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
            logger.info("Aucun document Markdown trouvé")
            return

        logger.info(f"✅ Trouvé {len(documents)} document(s) Markdown")

        updated_count = 0
        skipped_count = 0

        for doc in documents:
            doc_id = doc.get("id")
            content = doc.get("texte_extrait", "")

            if not content:
                logger.debug(f"  ⏭️  {doc_id} n'a pas de contenu")
                skipped_count += 1
                continue

            # Vérifier si le contenu commence par le frontmatter
            if not content.strip().startswith('---'):
                logger.debug(f"  ⏭️  {doc_id} n'a pas de frontmatter")
                skipped_count += 1
                continue

            # Nettoyer le frontmatter
            cleaned_content = remove_frontmatter(content)

            if cleaned_content == content:
                logger.debug(f"  ⏭️  {doc_id} déjà nettoyé")
                skipped_count += 1
                continue

            # Mettre à jour le document
            logger.info(f"  🧹 {doc_id}: {doc.get('nom_fichier')} - Nettoyage du frontmatter")
            await service.merge(str(doc_id), {"texte_extrait": cleaned_content})
            updated_count += 1

        logger.info("")
        logger.info("=" * 60)
        logger.info(f"✅ Nettoyage terminé !")
        logger.info(f"   Documents nettoyés: {updated_count}")
        logger.info(f"   Documents ignorés: {skipped_count}")
        logger.info("=" * 60)

        if updated_count > 0:
            logger.info("")
            logger.info("💡 Conseil: Rechargez la page dans le navigateur pour voir les changements")

    except Exception as e:
        logger.error(f"❌ Erreur: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    asyncio.run(clean_frontmatter())
