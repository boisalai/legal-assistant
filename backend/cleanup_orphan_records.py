#!/usr/bin/env python3
"""
Script de nettoyage des enregistrements orphelins.

Ce script identifie et supprime les enregistrements de documents en base de données
qui n'ont plus de fichier physique correspondant sur le disque.

Usage:
    python cleanup_orphan_records.py [--dry-run] [--judgment-id ID]

Options:
    --dry-run       Affiche ce qui serait supprimé sans effectuer de suppression
    --judgment-id   Limite le nettoyage à un dossier spécifique
"""

import asyncio
import argparse
import logging
from pathlib import Path
from typing import List, Dict

from services.surreal_service import get_surreal_service, init_surreal_service

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def init_service():
    """Initialise le service SurrealDB."""
    from config.settings import settings
    init_surreal_service(
        url=settings.surreal_url,
        database=settings.surreal_database,
        namespace=settings.surreal_namespace,
        username=settings.surreal_username,
        password=settings.surreal_password
    )


async def find_orphan_records(judgment_id: str = None) -> List[Dict]:
    """
    Trouve tous les enregistrements orphelins.

    Args:
        judgment_id: Si spécifié, limite la recherche à ce dossier

    Returns:
        Liste des documents orphelins
    """
    service = get_surreal_service()
    if not service.db:
        await service.connect()

    # Récupérer tous les documents
    if judgment_id:
        if not judgment_id.startswith("judgment:"):
            judgment_id = f"judgment:{judgment_id}"
        docs_result = await service.query(
            "SELECT * FROM document WHERE judgment_id = $judgment_id",
            {"judgment_id": judgment_id}
        )
    else:
        docs_result = await service.query("SELECT * FROM document")

    # Parser les résultats
    documents = []
    if docs_result and len(docs_result) > 0:
        first_item = docs_result[0]
        if isinstance(first_item, dict):
            if "result" in first_item:
                documents = first_item["result"] if isinstance(first_item["result"], list) else []
            elif "id" in first_item:
                documents = docs_result
        elif isinstance(first_item, list):
            documents = first_item

    # Identifier les orphelins
    orphans = []
    for doc in documents:
        doc_id = doc.get("id", "")
        doc_name = doc.get("nom_fichier", "")
        file_path = doc.get("file_path", "")

        if not file_path:
            orphans.append({
                "id": doc_id,
                "filename": doc_name,
                "judgment_id": doc.get("judgment_id", ""),
                "reason": "Aucun chemin de fichier"
            })
            continue

        if not Path(file_path).exists():
            orphans.append({
                "id": doc_id,
                "filename": doc_name,
                "judgment_id": doc.get("judgment_id", ""),
                "file_path": file_path,
                "reason": "Fichier physique manquant"
            })

    return orphans


async def delete_orphan_records(orphans: List[Dict], dry_run: bool = True):
    """
    Supprime les enregistrements orphelins.

    Args:
        orphans: Liste des orphelins à supprimer
        dry_run: Si True, n'effectue pas la suppression
    """
    if not orphans:
        logger.info("Aucun enregistrement orphelin trouvé.")
        return

    logger.info(f"Trouvé {len(orphans)} enregistrement(s) orphelin(s):")
    for orphan in orphans:
        logger.info(f"  - {orphan['id']}: {orphan['filename']} ({orphan['reason']})")

    if dry_run:
        logger.info("\n[DRY RUN] Aucune suppression effectuée.")
        logger.info(f"Pour supprimer ces {len(orphans)} enregistrements, exécutez sans --dry-run")
        return

    # Confirmer avec l'utilisateur
    print(f"\nVoulez-vous vraiment supprimer ces {len(orphans)} enregistrements orphelins? (y/N): ", end="")
    confirmation = input().strip().lower()

    if confirmation != 'y':
        logger.info("Suppression annulée.")
        return

    # Supprimer les enregistrements
    service = get_surreal_service()
    if not service.db:
        await service.connect()

    deleted_count = 0
    for orphan in orphans:
        try:
            doc_id = orphan["id"]
            await service.delete(doc_id)
            logger.info(f"✓ Supprimé: {orphan['filename']}")
            deleted_count += 1
        except Exception as e:
            logger.error(f"✗ Erreur lors de la suppression de {orphan['filename']}: {e}")

    logger.info(f"\n{deleted_count}/{len(orphans)} enregistrements supprimés avec succès.")


async def main():
    parser = argparse.ArgumentParser(
        description="Nettoie les enregistrements orphelins en base de données"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Affiche ce qui serait supprimé sans effectuer de suppression"
    )
    parser.add_argument(
        "--judgment-id",
        type=str,
        help="Limite le nettoyage à un dossier spécifique"
    )

    args = parser.parse_args()

    # Initialiser le service SurrealDB
    logger.info("Initialisation de la connexion à SurrealDB...")
    init_service()

    logger.info("Recherche des enregistrements orphelins...")
    orphans = await find_orphan_records(judgment_id=args.judgment_id)

    await delete_orphan_records(orphans, dry_run=args.dry_run)


if __name__ == "__main__":
    asyncio.run(main())
