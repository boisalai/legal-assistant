"""
Routes pour les migrations de base de données.
"""
import logging
from fastapi import APIRouter, Depends, HTTPException
from services.surreal_service import SurrealDBService, get_surreal_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/migration", tags=["migration"])


@router.post("/fix-statuts")
async def fix_statuts(
    db_service: SurrealDBService = Depends(get_surreal_service)
):
    """
    Migre tous les anciens statuts vers les nouveaux.

    Conversions:
    - complete → termine
    - erreur → en_erreur
    - valide → termine
    - analyse_complete → termine

    Returns:
        Rapport de migration avec nombre de dossiers mis à jour
    """
    try:
        logger.info("🔄 Début de la migration des statuts...")

        # Vérifier les statuts actuels
        current_statuts = await db_service.query(
            "SELECT statut, count() as total FROM dossier GROUP BY statut;"
        )
        logger.info(f"Statuts avant migration: {current_statuts}")

        migrations = [
            ("complete", "termine"),
            ("erreur", "en_erreur"),
            ("valide", "termine"),
            ("analyse_complete", "termine"),
        ]

        total_updated = 0
        details = []

        for old_status, new_status in migrations:
            # Exécuter la migration 3 fois pour être sûr
            status_updated = 0

            for attempt in range(3):
                query = f"UPDATE dossier SET statut = '{new_status}' WHERE statut = '{old_status}';"
                result = await db_service.query(query)

                if result and len(result) > 0 and isinstance(result[0], list):
                    count = len(result[0])
                    if count > 0:
                        logger.info(f"Migration '{old_status}' → '{new_status}': {count} dossier(s) (tentative {attempt + 1})")
                        status_updated += count

            if status_updated > 0:
                details.append({
                    "old_status": old_status,
                    "new_status": new_status,
                    "count": status_updated
                })
                total_updated += status_updated

        # Vérifier les statuts après migration
        final_statuts = await db_service.query(
            "SELECT statut, count() as total FROM dossier GROUP BY statut;"
        )
        logger.info(f"Statuts après migration: {final_statuts}")

        # Vérifier les statuts invalides restants
        invalid_query = """
        SELECT id, nom_dossier, statut
        FROM dossier
        WHERE statut NOT IN ['nouveau', 'en_analyse', 'termine', 'en_erreur', 'archive'];
        """
        invalid_result = await db_service.query(invalid_query)

        invalid_count = 0
        invalid_dossiers = []

        if invalid_result and len(invalid_result) > 0 and invalid_result[0]:
            invalid_count = len(invalid_result[0])
            for item in invalid_result[0]:
                invalid_dossiers.append({
                    "id": str(item.get("id")),
                    "nom_dossier": item.get("nom_dossier"),
                    "statut": item.get("statut")
                })

        logger.info(f"✅ Migration terminée! {total_updated} dossier(s) mis à jour, {invalid_count} invalides restants")

        return {
            "success": True,
            "total_updated": total_updated,
            "details": details,
            "invalid_count": invalid_count,
            "invalid_dossiers": invalid_dossiers,
            "statuts_before": current_statuts[0] if current_statuts else [],
            "statuts_after": final_statuts[0] if final_statuts else [],
        }

    except Exception as e:
        logger.error(f"❌ Erreur lors de la migration: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erreur lors de la migration: {str(e)}")


@router.get("/check-statuts")
async def check_statuts(
    db_service: SurrealDBService = Depends(get_surreal_service)
):
    """
    Vérifie les statuts actuels des dossiers et identifie les invalides.

    Returns:
        Distribution des statuts et liste des statuts invalides
    """
    try:
        # Distribution des statuts
        statuts_result = await db_service.query(
            "SELECT statut, count() as total FROM dossier GROUP BY statut;"
        )

        # Statuts invalides
        invalid_query = """
        SELECT id, nom_dossier, statut
        FROM dossier
        WHERE statut NOT IN ['nouveau', 'en_analyse', 'termine', 'en_erreur', 'archive'];
        """
        invalid_result = await db_service.query(invalid_query)

        invalid_dossiers = []
        if invalid_result and len(invalid_result) > 0 and invalid_result[0]:
            for item in invalid_result[0]:
                invalid_dossiers.append({
                    "id": str(item.get("id")),
                    "nom_dossier": item.get("nom_dossier"),
                    "statut": item.get("statut")
                })

        return {
            "statuts_distribution": statuts_result[0] if statuts_result else [],
            "invalid_count": len(invalid_dossiers),
            "invalid_dossiers": invalid_dossiers
        }

    except Exception as e:
        logger.error(f"❌ Erreur lors de la vérification: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erreur lors de la vérification: {str(e)}")
