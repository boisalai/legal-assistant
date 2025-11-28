"""
Routes API pour la gestion des dossiers notariaux.

Endpoints:
- POST   /api/dossiers              - Créer un dossier
- GET    /api/dossiers              - Lister les dossiers
- GET    /api/dossiers/{id}         - Récupérer un dossier
- PUT    /api/dossiers/{id}         - Mettre à jour un dossier
- DELETE /api/dossiers/{id}         - Supprimer un dossier
- POST   /api/dossiers/{id}/upload  - Uploader un document (PDF, Word, texte, audio)
- POST   /api/dossiers/{id}/audio   - Sauvegarder un enregistrement audio
- GET    /api/dossiers/{id}/documents - Lister les documents
- GET    /api/dossiers/{id}/documents/{doc_id}/download - Télécharger un document
- GET    /api/dossiers/{id}/documents/{doc_id}/preview - Prévisualiser un document
- DELETE /api/dossiers/{id}/documents/{doc_id} - Supprimer un document
- GET    /api/dossiers/{id}/checklist - Récupérer la checklist
- POST   /api/dossiers/{id}/analyser - Lancer l'analyse
"""

import logging
import asyncio
from pathlib import Path
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, File, UploadFile, Form, BackgroundTasks, Query
from fastapi.responses import JSONResponse, StreamingResponse
from sse_starlette.sse import EventSourceResponse

from models import (
    Dossier,
    DossierCreate,
    DossierUpdate,
    Document,
    Checklist,
)
from services.dossier_service import DossierService
from services.surreal_service import SurrealDBService, get_db_connection
from config import settings
from exceptions import (
    ResourceNotFoundError,
    FileUploadError,
    ValidationError as NotaryValidationError,
)
from services.progress_service import get_progress_manager, ProgressEvent, ProgressEventType

logger = logging.getLogger(__name__)

# Créer le router
router = APIRouter()


# ============================================================================
# DEPENDENCIES
# ============================================================================

async def get_dossier_service():
    """
    Dependency pour obtenir une instance du DossierService.

    Architecture hybride (Sprint 1 - Migration SurrealDB):
    - Utilise SurrealDBService pour CRUD des tables métier
    - Utilise AgnoDBService pour persistance automatique des workflows

    Utilise la connexion SurrealDB globale (singleton) avec lazy initialization.
    La connexion est établie à la première requête pour éviter les problèmes
    avec l'event loop d'Uvicorn en mode reload.

    AVANT (problématique):
    - Requête 1: Nouvelle connexion → CREATE → Disconnect
    - Requête 2: Nouvelle connexion → SELECT → Pas trouvé! (bug)

    APRÈS (corrigé):
    - Première requête: Connexion globale établie (lazy)
    - Requêtes suivantes: Réutilisent la même connexion
    - Shutdown: Connexion fermée proprement
    """
    from services.surreal_service import get_surreal_service
    from services.agno_db_service import get_agno_db_service

    # Récupérer la connexion SurrealDB globale (singleton)
    db = get_surreal_service()

    # Lazy initialization: connecter si pas encore connecté
    if db.db is None:
        logger.info("🔌 First request - connecting to SurrealDB...")
        await db.connect()
        logger.info("✅ SurrealDB connection established")

    # Récupérer AgnoDBService (singleton) pour persistance workflow
    agno_db_service = get_agno_db_service()

    # Créer le service avec les deux connexions
    service = DossierService(
        db,
        upload_dir=settings.upload_dir,
        agno_db_service=agno_db_service  # ✅ Persistance automatique Agno
    )

    return service


DossierServiceDep = Annotated[DossierService, Depends(get_dossier_service)]


# ============================================================================
# ROUTES - CRUD Dossiers
# ============================================================================

@router.post("", response_model=Dossier, status_code=201)
async def create_dossier(
    dossier: DossierCreate,
    service: DossierServiceDep,
):
    """
    Crée un nouveau dossier notarial.

    Args:
        dossier: Données du dossier à créer

    Returns:
        Le dossier créé
    """
    return await service.create_dossier(
        nom_dossier=dossier.nom_dossier,
        user_id=dossier.user_id,
        type_transaction=dossier.type_transaction,
    )


@router.get("", response_model=list[Dossier])
async def list_dossiers(
    service: DossierServiceDep,
    user_id: Optional[str] = None,
    limit: int = 50,
):
    """
    Liste les dossiers, optionnellement filtrés par utilisateur.

    Args:
        user_id: ID de l'utilisateur (optionnel)
        limit: Nombre max de résultats (défaut: 50)

    Returns:
        Liste de dossiers
    """
    return await service.list_dossiers(user_id=user_id, limit=limit)


@router.get("/{dossier_id}", response_model=Dossier)
async def get_dossier(
    dossier_id: str,
    service: DossierServiceDep,
):
    """
    Récupère un dossier par son ID.

    Args:
        dossier_id: ID du dossier

    Returns:
        Le dossier
    """
    dossier = await service.get_dossier(dossier_id)

    if not dossier:
        raise ResourceNotFoundError(resource_type="Dossier", resource_id=dossier_id)

    return dossier


@router.put("/{dossier_id}", response_model=Dossier)
async def update_dossier(
    dossier_id: str,
    updates: DossierUpdate,
    service: DossierServiceDep,
):
    """
    Met à jour un dossier.

    Args:
        dossier_id: ID du dossier
        updates: Données à mettre à jour

    Returns:
        Le dossier mis à jour
    """
    dossier = await service.update_dossier(dossier_id, updates)

    if not dossier:
        raise ResourceNotFoundError(resource_type="Dossier", resource_id=dossier_id)

    return dossier


@router.patch("/{dossier_id}/pin", response_model=Dossier)
async def toggle_pin_dossier(
    dossier_id: str,
    service: DossierServiceDep,
):
    """
    Épingle ou dé-épingle un dossier.

    Args:
        dossier_id: ID du dossier

    Returns:
        Le dossier mis à jour avec le nouveau statut pinned
    """
    dossier = await service.toggle_pin_dossier(dossier_id)

    if not dossier:
        raise ResourceNotFoundError(resource_type="Dossier", resource_id=dossier_id)

    return dossier


@router.delete("/{dossier_id}", status_code=204)
async def delete_dossier(
    dossier_id: str,
    service: DossierServiceDep,
):
    """
    Supprime un dossier (et ses documents).

    Args:
        dossier_id: ID du dossier
    """
    success = await service.delete_dossier(dossier_id)

    if not success:
        raise ResourceNotFoundError(resource_type="Dossier", resource_id=dossier_id)

    return None


# ============================================================================
# ROUTES - Documents
# ============================================================================

# Types de fichiers supportés
SUPPORTED_MIME_TYPES = {
    # Documents PDF
    "application/pdf": "pdf",
    # Documents Word
    "application/msword": "doc",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
    # Documents texte
    "text/plain": "txt",
    "text/rtf": "rtf",
    "application/rtf": "rtf",
    "text/markdown": "md",
    "text/x-markdown": "md",
    # Images
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/gif": "gif",
    "image/webp": "webp",
    "image/tiff": "tiff",
    # Audio
    "audio/mpeg": "mp3",
    "audio/mp3": "mp3",
    "audio/mp4": "m4a",
    "audio/x-m4a": "m4a",
    "audio/wav": "wav",
    "audio/x-wav": "wav",
    "audio/webm": "webm",
    "audio/ogg": "ogg",
    "audio/flac": "flac",
    "audio/aac": "aac",
    "audio/opus": "opus",
    "video/mp4": "mp4",
    "video/webm": "webm",
}


@router.post("/{dossier_id}/upload", response_model=Document, status_code=201)
async def upload_document(
    dossier_id: str,
    service: DossierServiceDep,
    file: UploadFile = File(...),
    use_ocr: bool = Form(False),
    document_type: Optional[str] = Form(None),
    language: str = Form("fr"),
):
    """
    Upload un document dans un dossier.

    Types supportés:
    - PDF (.pdf)
    - Word (.doc, .docx)
    - Texte (.txt, .rtf, .md)
    - Images (.jpg, .png, .gif, .webp, .tiff)
    - Audio (.mp3, .mp4, .m4a, .wav, .webm, .ogg, .opus, .flac, .aac)

    Args:
        dossier_id: ID du dossier
        file: Fichier à uploader
        use_ocr: Activer l'OCR pour les PDFs scannés
        document_type: Type de document (pièce d'identité, certificat, etc.)
        language: Langue pour la transcription audio (fr, en, etc.)

    Returns:
        Le document créé
    """
    # Vérifier que le dossier existe
    dossier = await service.get_dossier(dossier_id)
    if not dossier:
        raise ResourceNotFoundError(resource_type="Dossier", resource_id=dossier_id)

    # Vérifier le type de fichier
    content_type = file.content_type or ""
    filename = file.filename or "document"

    # Vérifier par type MIME ou extension
    file_ext = Path(filename).suffix.lower() if filename else ""
    is_supported = content_type in SUPPORTED_MIME_TYPES or file_ext in [
        ".pdf", ".doc", ".docx", ".txt", ".rtf", ".md",
        ".jpg", ".jpeg", ".png", ".gif", ".webp", ".tiff", ".tif",
        ".mp3", ".mp4", ".m4a", ".wav", ".webm", ".ogg", ".opus", ".flac", ".aac", ".mp2", ".pcm",
    ]

    if not is_supported:
        raise FileUploadError(
            message=f"Type de fichier non supporté: {content_type or file_ext}. "
                    f"Types acceptés: PDF, Word, texte, images, audio.",
            filename=filename,
        )

    # Lire le contenu du fichier
    file_content = await file.read()

    # Vérifier la taille (max 100MB pour les fichiers audio)
    max_size = 100 * 1024 * 1024  # 100MB
    if len(file_content) > max_size:
        raise FileUploadError(
            message=f"Fichier trop volumineux: {len(file_content)} octets (max: {max_size})",
            filename=filename,
        )

    # Déterminer le type de fichier pour le stockage
    file_type = SUPPORTED_MIME_TYPES.get(content_type) or file_ext.lstrip(".") or "unknown"

    # Ajouter le document
    document = await service.add_document(
        dossier_id=dossier_id,
        file_content=file_content,
        filename=filename,
        content_type=content_type,
        file_type=file_type,
        use_ocr=use_ocr,
        document_type=document_type,
        language=language,
    )

    return document


@router.post("/{dossier_id}/audio", response_model=Document, status_code=201)
async def save_audio_recording(
    dossier_id: str,
    service: DossierServiceDep,
    file: UploadFile = File(...),
    name: str = Form(...),
    language: str = Form("fr"),
    identify_speakers: bool = Form(False),
):
    """
    Sauvegarde un enregistrement audio dans un dossier.

    L'enregistrement sera automatiquement transcrit en texte.

    Args:
        dossier_id: ID du dossier
        file: Fichier audio (WebM, WAV, MP3, etc.)
        name: Nom de l'enregistrement
        language: Langue de l'audio (fr, en, etc.)
        identify_speakers: Identifier les différents interlocuteurs

    Returns:
        Le document créé avec la transcription
    """
    # Vérifier que le dossier existe
    dossier = await service.get_dossier(dossier_id)
    if not dossier:
        raise ResourceNotFoundError(resource_type="Dossier", resource_id=dossier_id)

    # Vérifier que c'est bien un fichier audio
    content_type = file.content_type or ""
    if not content_type.startswith("audio/") and not content_type.startswith("video/"):
        raise FileUploadError(
            message=f"Type de fichier non supporté: {content_type}. Un fichier audio est requis.",
            filename=file.filename,
        )

    # Lire le contenu du fichier
    file_content = await file.read()

    # Vérifier la taille (max 200MB pour les enregistrements)
    max_size = 200 * 1024 * 1024  # 200MB
    if len(file_content) > max_size:
        raise FileUploadError(
            message=f"Fichier trop volumineux: {len(file_content)} octets (max: {max_size})",
            filename=file.filename,
        )

    # Déterminer l'extension
    file_ext = Path(file.filename or "recording.webm").suffix.lower()
    if not file_ext:
        file_ext = ".webm"  # Format par défaut pour les enregistrements navigateur

    # Créer le nom de fichier
    filename = f"{name}{file_ext}"

    # Ajouter le document
    document = await service.add_document(
        dossier_id=dossier_id,
        file_content=file_content,
        filename=filename,
        content_type=content_type,
        file_type="audio",
        is_recording=True,
        language=language,
        identify_speakers=identify_speakers,
    )

    return document


@router.get("/{dossier_id}/documents", response_model=list[Document])
async def list_documents(
    dossier_id: str,
    service: DossierServiceDep,
):
    """
    Liste les documents d'un dossier.

    Args:
        dossier_id: ID du dossier

    Returns:
        Liste de documents
    """
    # Vérifier que le dossier existe
    dossier = await service.get_dossier(dossier_id)
    if not dossier:
        raise ResourceNotFoundError(resource_type="Dossier", resource_id=dossier_id)

    return await service.list_documents(dossier_id)


@router.get("/{dossier_id}/documents/{document_id}/download")
async def download_document(
    dossier_id: str,
    document_id: str,
    service: DossierServiceDep,
):
    """
    Télécharge un document.

    Args:
        dossier_id: ID du dossier
        document_id: ID du document

    Returns:
        Le fichier en téléchargement
    """
    from fastapi.responses import FileResponse

    # Vérifier que le dossier existe
    dossier = await service.get_dossier(dossier_id)
    if not dossier:
        raise ResourceNotFoundError(resource_type="Dossier", resource_id=dossier_id)

    # Récupérer le document
    document = await service.get_document(document_id)
    if not document:
        raise ResourceNotFoundError(resource_type="Document", resource_id=document_id)

    # Vérifier que le fichier existe
    file_path = Path(document.chemin_fichier)
    if not file_path.exists():
        raise ResourceNotFoundError(
            resource_type="File",
            resource_id=document.chemin_fichier,
        )

    # Déterminer le type MIME
    content_type = document.type_mime or "application/octet-stream"

    return FileResponse(
        path=file_path,
        filename=document.nom_fichier,
        media_type=content_type,
        headers={
            "Content-Disposition": f'attachment; filename="{document.nom_fichier}"'
        },
    )


@router.get("/{dossier_id}/documents/{document_id}/preview")
async def preview_document(
    dossier_id: str,
    document_id: str,
    service: DossierServiceDep,
):
    """
    Prévisualise un document (affichage inline).

    Args:
        dossier_id: ID du dossier
        document_id: ID du document

    Returns:
        Le fichier pour affichage dans le navigateur
    """
    from fastapi.responses import FileResponse

    # Vérifier que le dossier existe
    dossier = await service.get_dossier(dossier_id)
    if not dossier:
        raise ResourceNotFoundError(resource_type="Dossier", resource_id=dossier_id)

    # Récupérer le document
    document = await service.get_document(document_id)
    if not document:
        raise ResourceNotFoundError(resource_type="Document", resource_id=document_id)

    # Vérifier que le fichier existe
    file_path = Path(document.chemin_fichier)
    if not file_path.exists():
        raise ResourceNotFoundError(
            resource_type="File",
            resource_id=document.chemin_fichier,
        )

    # Déterminer le type MIME
    content_type = document.type_mime or "application/octet-stream"

    return FileResponse(
        path=file_path,
        filename=document.nom_fichier,
        media_type=content_type,
        headers={
            "Content-Disposition": f'inline; filename="{document.nom_fichier}"'
        },
    )


@router.delete("/{dossier_id}/documents/{document_id}", status_code=204)
async def delete_document(
    dossier_id: str,
    document_id: str,
    service: DossierServiceDep,
):
    """
    Supprime un document.

    Args:
        dossier_id: ID du dossier
        document_id: ID du document
    """
    # Vérifier que le dossier existe
    dossier = await service.get_dossier(dossier_id)
    if not dossier:
        raise ResourceNotFoundError(resource_type="Dossier", resource_id=dossier_id)

    # Supprimer le document
    success = await service.delete_document(document_id)
    if not success:
        raise ResourceNotFoundError(resource_type="Document", resource_id=document_id)

    return None


@router.get("/{dossier_id}/checklist", response_model=Checklist)
async def get_checklist(
    dossier_id: str,
    service: DossierServiceDep,
):
    """
    Récupère la checklist d'un dossier.

    Args:
        dossier_id: ID du dossier

    Returns:
        La checklist ou 404 si pas trouvée
    """
    # Vérifier que le dossier existe
    dossier = await service.get_dossier(dossier_id)
    if not dossier:
        raise ResourceNotFoundError(resource_type="Dossier", resource_id=dossier_id)

    # Récupérer la checklist
    checklist = await service.get_checklist(dossier_id)
    if not checklist:
        raise ResourceNotFoundError(
            resource_type="Checklist",
            resource_id=f"dossier:{dossier_id}",
        )

    return checklist


# ============================================================================
# ROUTES - Analyse
# ============================================================================

@router.post("/{dossier_id}/analyser", response_model=Checklist)
async def analyser_dossier(
    dossier_id: str,
    service: DossierServiceDep,
):
    """
    Lance l'analyse d'un dossier via le workflow Agno.

    Cette endpoint:
    1. Vérifie que le dossier existe
    2. Vérifie qu'il y a au moins un document
    3. Lance le workflow d'analyse Agno
    4. Retourne la checklist générée

    Args:
        dossier_id: ID du dossier à analyser

    Returns:
        La checklist générée
    """
    # Vérifier que le dossier existe
    dossier = await service.get_dossier(dossier_id)
    if not dossier:
        raise ResourceNotFoundError(resource_type="Dossier", resource_id=dossier_id)

    # Vérifier qu'il y a des documents
    documents = await service.list_documents(dossier_id)
    if not documents:
        raise NotaryValidationError(
            message="Cannot analyze dossier: no documents uploaded",
            field="documents",
        )

    # Lancer l'analyse
    try:
        # Mettre à jour le statut du dossier
        await service.update_dossier(
            dossier_id,
            DossierUpdate(statut="en_analyse"),
        )

        # Lancer le workflow Agno
        checklist = await service.analyser_dossier(dossier_id)

        if not checklist:
            # Marquer comme erreur
            await service.update_dossier(
                dossier_id,
                DossierUpdate(statut="erreur"),
            )
            from exceptions import WorkflowError
            raise WorkflowError(
                message="Analysis failed - no checklist generated",
                workflow_name="analyse_dossier",
            )

        # Marquer comme complété
        await service.update_dossier(
            dossier_id,
            DossierUpdate(statut="complete"),
        )

        return checklist

    except (ResourceNotFoundError, NotaryValidationError, FileUploadError):
        # Re-raise les exceptions métier
        raise
    except Exception as e:
        logger.error(f"Error analyzing dossier: {e}")

        # Marquer comme erreur
        await service.update_dossier(
            dossier_id,
            DossierUpdate(statut="erreur"),
        )

        from exceptions import WorkflowError
        raise WorkflowError(
            message=f"Analysis failed: {str(e)}",
            workflow_name="analyse_dossier",
            details={"error": str(e)},
        )


# ============================================================================
# ROUTES - Analyse avec progression temps réel (SSE)
# ============================================================================

@router.get("/{dossier_id}/analyse-stream")
async def analyse_stream(
    dossier_id: str,
    service: DossierServiceDep,
):
    """
    Stream SSE pour suivre la progression de l'analyse en temps réel.

    Ce endpoint retourne un flux d'événements Server-Sent Events (SSE)
    qui permet au frontend de suivre la progression étape par étape.

    Événements émis:
    - connected: Connexion SSE établie
    - start: Début de l'analyse
    - step_start: Début d'une étape (1-4)
    - step_end: Fin d'une étape
    - complete: Analyse terminée avec succès
    - error: Erreur pendant l'analyse

    Args:
        dossier_id: ID du dossier à suivre

    Returns:
        EventSourceResponse avec les événements de progression
    """
    # Vérifier que le dossier existe
    dossier = await service.get_dossier(dossier_id)
    if not dossier:
        raise ResourceNotFoundError(resource_type="Dossier", resource_id=dossier_id)

    progress_manager = get_progress_manager()
    logger.info(f"SSE connection request for dossier {dossier_id}")

    async def event_generator():
        """Génère les événements SSE."""
        try:
            # Envoyer un événement initial pour confirmer la connexion
            connected_event = ProgressEvent(
                event_type=ProgressEventType.PROGRESS,
                step=0,
                step_name="Connexion",
                message="Connexion SSE établie. En attente des événements...",
                progress_percent=0.0,
            )
            logger.info(f"SSE sending connected event for {dossier_id}")
            # EventSourceResponse ajoute automatiquement "data: " et "\n\n"
            # On envoie donc juste le JSON, pas le format SSE complet
            yield connected_event.to_json()

            # Ensuite, suivre les vrais événements
            async for event in progress_manager.subscribe(dossier_id):
                logger.info(f"SSE sending event: {event.event_type.value} for {dossier_id}")
                yield event.to_json()

        except asyncio.CancelledError:
            logger.info(f"SSE connection closed for dossier {dossier_id}")
            raise
        except Exception as e:
            logger.error(f"SSE error for dossier {dossier_id}: {e}")
            raise

    return EventSourceResponse(
        event_generator(),
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # Désactive le buffering nginx/proxy
            "Connection": "keep-alive",
        }
    )


@router.post("/{dossier_id}/analyser-stream")
async def analyser_dossier_stream(
    dossier_id: str,
    service: DossierServiceDep,
    background_tasks: BackgroundTasks,
    model_id: Optional[str] = Query(default=None, description="ID du modèle LLM (ex: ollama:qwen2.5:7b)"),
    extraction_method: Optional[str] = Query(default="pypdf", description="Méthode d'extraction PDF"),
    use_ocr: Optional[bool] = Query(default=False, description="Activer l'OCR pour PDFs scannés"),
):
    """
    Lance l'analyse avec support de streaming de progression.

    Cette version:
    1. Lance l'analyse en tâche de fond
    2. Permet au client de suivre via GET /analyse-stream
    3. Retourne immédiatement un statut 202 Accepted

    Le client doit:
    1. Appeler POST /analyser-stream pour lancer l'analyse
    2. Se connecter à GET /analyse-stream pour suivre la progression
    3. Récupérer le résultat via GET /checklist une fois complete

    Args:
        dossier_id: ID du dossier à analyser
        model_id: ID du modèle LLM à utiliser (optionnel)
        extraction_method: Méthode d'extraction PDF (pypdf, docling-standard, docling-vlm)
        use_ocr: Activer l'OCR pour les PDFs scannés

    Returns:
        JSON avec statut et instructions
    """
    # Vérifier que le dossier existe
    dossier = await service.get_dossier(dossier_id)
    if not dossier:
        raise ResourceNotFoundError(resource_type="Dossier", resource_id=dossier_id)

    # Vérifier qu'il y a des documents
    documents = await service.list_documents(dossier_id)
    if not documents:
        raise NotaryValidationError(
            message="Cannot analyze dossier: no documents uploaded",
            field="documents",
        )

    # Vérifier si une analyse est déjà en cours
    if dossier.statut == "en_analyse":
        return JSONResponse(
            status_code=409,
            content={
                "message": "Analysis already in progress",
                "dossier_id": dossier_id,
                "stream_url": f"/api/dossiers/{dossier_id}/analyse-stream",
            },
        )

    # Mettre à jour le statut
    await service.update_dossier(
        dossier_id,
        DossierUpdate(statut="en_analyse"),
    )

    # Lancer l'analyse en background avec callback de progression
    progress_manager = get_progress_manager()
    progress_callback = progress_manager.create_callback(dossier_id)

    async def run_analysis():
        """Exécute l'analyse en arrière-plan."""
        try:
            # Émettre événement de démarrage
            await progress_callback(
                step=0,
                step_name="Initialisation",
                event_type="start",
                message="Démarrage de l'analyse...",
                progress_percent=0.0,
            )

            # Lancer le workflow avec callback et paramètres du modèle
            checklist = await service.analyser_dossier(
                dossier_id,
                progress_callback=progress_callback,
                model_id=model_id,
                extraction_method=extraction_method,
                use_ocr=use_ocr,
            )

            if checklist:
                # Mettre à jour le statut
                await service.update_dossier(
                    dossier_id,
                    DossierUpdate(statut="complete"),
                )

                # Émettre événement de fin
                # Note: checklist est un objet Pydantic, pas un dict
                score = getattr(checklist, "score_confiance", 0) if hasattr(checklist, "score_confiance") else 0
                await progress_callback(
                    step=4,
                    step_name="Terminé",
                    event_type="complete",
                    message="Analyse terminée avec succès!",
                    progress_percent=100.0,
                    data={"score_confiance": score},
                )
            else:
                await service.update_dossier(
                    dossier_id,
                    DossierUpdate(statut="erreur"),
                )
                await progress_callback(
                    step=0,
                    step_name="Erreur",
                    event_type="error",
                    message="Erreur: aucune checklist générée",
                    progress_percent=0.0,
                )

        except Exception as e:
            logger.error(f"Error in background analysis: {e}")
            await service.update_dossier(
                dossier_id,
                DossierUpdate(statut="erreur"),
            )
            await progress_callback(
                step=0,
                step_name="Erreur",
                event_type="error",
                message=f"Erreur: {str(e)}",
                progress_percent=0.0,
            )
        finally:
            # Nettoyer après un délai pour permettre aux clients de recevoir le dernier événement
            await asyncio.sleep(2)
            await progress_manager.clear(dossier_id)

    # Ajouter la tâche en arrière-plan
    background_tasks.add_task(run_analysis)

    return JSONResponse(
        status_code=202,
        content={
            "message": "Analysis started",
            "dossier_id": dossier_id,
            "stream_url": f"/api/dossiers/{dossier_id}/analyse-stream",
            "checklist_url": f"/api/dossiers/{dossier_id}/checklist",
        },
    )
