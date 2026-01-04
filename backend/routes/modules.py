"""
Routes for study module management.

Endpoints:
- POST /api/courses/{course_id}/modules - Create a module
- GET /api/courses/{course_id}/modules - List course modules
- POST /api/courses/{course_id}/modules/bulk - Create multiple modules
- GET /api/modules/{module_id} - Module details
- PATCH /api/modules/{module_id} - Update a module
- DELETE /api/modules/{module_id} - Delete a module
- GET /api/modules/{module_id}/documents - Module documents
- POST /api/modules/{module_id}/documents - Assign documents
- POST /api/modules/{module_id}/documents/upload - Direct upload to module
- DELETE /api/modules/{module_id}/documents - Unassign documents

Note: GET /api/courses/{course_id}/documents/unassigned is in documents.py
"""

import logging
import uuid
from pathlib import Path

from fastapi import APIRouter, HTTPException, status, UploadFile, File, Form, Depends

from config.settings import settings
from services.document_service import get_document_service
from utils.file_utils import is_allowed_file, get_file_extension, ALLOWED_EXTENSIONS, MAX_FILE_SIZE
from auth.helpers import require_auth
from models.document_models import DocumentResponse

from services.module_service import get_module_service
from models.module_models import (
    ModuleCreate,
    ModuleUpdate,
    ModuleResponse,
    ModuleListResponse,
    AssignDocumentsRequest,
    AssignDocumentsResponse,
    ModuleBulkCreateRequest,
    ModuleBulkCreateResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Modules"])


# ============================================================================
# Course-scoped Module Endpoints
# ============================================================================

@router.post(
    "/api/courses/{course_id}/modules",
    response_model=ModuleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a module"
)
async def create_module(course_id: str, request: ModuleCreate):
    """
    Create a new module for a course.

    A module allows grouping documents by theme/chapter
    and tracking learning progress.
    """
    service = get_module_service()

    try:
        module = await service.create_module(course_id, request)
        return module
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error creating module: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la création du module: {str(e)}"
        )


@router.get(
    "/api/courses/{course_id}/modules",
    response_model=ModuleListResponse,
    summary="List course modules"
)
async def list_modules(course_id: str):
    """List all modules for a course, ordered by order_index."""
    service = get_module_service()

    modules, total = await service.list_modules(course_id)

    return ModuleListResponse(modules=modules, total=total)


@router.post(
    "/api/courses/{course_id}/modules/bulk",
    response_model=ModuleBulkCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create multiple modules"
)
async def bulk_create_modules(course_id: str, request: ModuleBulkCreateRequest):
    """
    Create multiple modules in a single request.

    Useful for quickly setting up a course structure.
    """
    service = get_module_service()

    created = []
    for item in request.modules:
        module_data = ModuleCreate(
            name=item.name,
            order_index=item.order_index,
            exam_weight=item.exam_weight
        )
        try:
            module = await service.create_module(course_id, module_data)
            created.append(module)
        except Exception as e:
            logger.error(f"Error creating module {item.name}: {e}")

    return ModuleBulkCreateResponse(
        created_count=len(created),
        modules=created
    )


# ============================================================================
# Module-specific Endpoints
# ============================================================================

@router.get(
    "/api/modules/{module_id}",
    response_model=ModuleResponse,
    summary="Module details"
)
async def get_module(module_id: str):
    """Retrieve module details."""
    service = get_module_service()

    module = await service.get_module(module_id)
    if not module:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Module non trouvé: {module_id}"
        )

    return module


@router.patch(
    "/api/modules/{module_id}",
    response_model=ModuleResponse,
    summary="Update a module"
)
async def update_module(module_id: str, request: ModuleUpdate):
    """Update module properties."""
    service = get_module_service()

    module = await service.update_module(module_id, request)
    if not module:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Module non trouvé: {module_id}"
        )

    return module


@router.delete(
    "/api/modules/{module_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a module"
)
async def delete_module(module_id: str):
    """
    Delete a module.

    Assigned documents are not deleted, they are simply unassigned.
    """
    service = get_module_service()

    deleted = await service.delete_module(module_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Module non trouvé: {module_id}"
        )

    return None


# ============================================================================
# Document Assignment Endpoints
# ============================================================================

@router.get(
    "/api/modules/{module_id}/documents",
    summary="Module documents"
)
async def get_module_documents(module_id: str):
    """Retrieve all documents assigned to a module."""
    service = get_module_service()

    # Verify module exists
    module = await service.get_module(module_id)
    if not module:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Module non trouvé: {module_id}"
        )

    documents = await service.get_module_documents(module_id)

    return {
        "module_id": module_id,
        "documents": documents,
        "total": len(documents)
    }


@router.post(
    "/api/modules/{module_id}/documents",
    response_model=AssignDocumentsResponse,
    summary="Assign documents"
)
async def assign_documents(module_id: str, request: AssignDocumentsRequest):
    """
    Assign documents to a module.

    Documents will be moved from their current module (if any)
    to this module.
    """
    service = get_module_service()

    try:
        count = await service.assign_documents(module_id, request.document_ids)
        return AssignDocumentsResponse(
            module_id=module_id,
            assigned_count=count,
            document_ids=request.document_ids
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.delete(
    "/api/modules/{module_id}/documents",
    summary="Unassign documents"
)
async def unassign_documents(module_id: str, request: AssignDocumentsRequest):
    """
    Remove documents from a module.

    Documents will no longer be associated with any module.
    """
    service = get_module_service()

    count = await service.unassign_documents(module_id, request.document_ids)

    return {
        "module_id": module_id,
        "unassigned_count": count,
        "document_ids": request.document_ids
    }


@router.post(
    "/api/modules/{module_id}/documents/upload",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Direct upload to module"
)
async def upload_document_to_module(
    module_id: str,
    file: UploadFile = File(...),
    auto_extract_markdown: bool = Form(False),
    user_id: str = Depends(require_auth)
):
    """
    Upload a document directly to a module.

    The document is created and automatically assigned to the specified module.
    Accepts: PDF, Word, TXT, Markdown, Audio (MP3, WAV, M4A)

    Args:
        module_id: Target module ID
        file: File to upload
        auto_extract_markdown: If True, automatically extract content to markdown (PDF only)
    """
    module_service = get_module_service()

    # Verify module exists and get its course_id
    module = await module_service.get_module(module_id)
    if not module:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Module non trouvé: {module_id}"
        )

    course_id = module.course_id

    # Validate file type
    if not file.filename or not is_allowed_file(file.filename):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Type de fichier non supporté. Extensions acceptées: {', '.join(ALLOWED_EXTENSIONS.keys())}"
        )

    # Read file content
    content = await file.read()

    # Check file size
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Fichier trop volumineux. Taille max: {MAX_FILE_SIZE // (1024*1024)} MB"
        )

    try:
        # Normalize IDs
        if not course_id.startswith("course:"):
            course_id = f"course:{course_id}"
        if not module_id.startswith("module:"):
            module_id = f"module:{module_id}"

        # Save file to disk
        doc_id = str(uuid.uuid4())[:8]
        ext = get_file_extension(file.filename)

        upload_dir = Path(settings.upload_dir) / course_id.replace("course:", "")
        upload_dir.mkdir(parents=True, exist_ok=True)

        file_path = str(upload_dir / f"{doc_id}{ext}")
        with open(file_path, "wb") as f:
            f.write(content)

        logger.info(f"Document saved to module {module_id}: {file_path}")

        # Create document record with module_id
        doc_service = get_document_service()
        document = await doc_service.create_document(
            course_id=course_id,
            filename=file.filename,
            file_path=file_path,
            file_size=len(content),
            source_type="upload",
            module_id=module_id
        )

        logger.info(f"Document {document.id} created and assigned to module {module_id}")

        # If auto_extract_markdown is enabled and file is PDF, trigger extraction in background
        if auto_extract_markdown and ext.lower() == '.pdf':
            import asyncio
            import httpx

            async def trigger_extraction():
                try:
                    async with httpx.AsyncClient(timeout=300.0) as client:
                        url = f"http://localhost:{settings.api_port}/api/courses/{course_id}/documents/{document.id}/extract-to-markdown"
                        await client.post(url, params={"force_reextract": False})
                        logger.info(f"Markdown extraction triggered for {document.id}")
                except Exception as e:
                    logger.warning(f"Auto-extraction failed for {document.id}: {e}")

            asyncio.create_task(trigger_extraction())

        return document

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading document to module: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
