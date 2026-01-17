"""
Routes for course document management.

Endpoints:
- GET /api/courses/{course_id}/documents - List documents
- POST /api/courses/{course_id}/documents - Upload a document
- GET /api/courses/{course_id}/documents/{doc_id} - Get document details
- DELETE /api/courses/{course_id}/documents/{doc_id} - Delete a document
- GET /api/courses/{course_id}/documents/{doc_id}/download - Download a document
"""

import logging
import uuid
import mimetypes
import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, List

from fastapi import APIRouter, HTTPException, status, UploadFile, File, Form, Depends
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel

from config.settings import settings
from services.surreal_service import get_surreal_service
from services.document_indexing_service import DocumentIndexingService
from utils.text_utils import remove_yaml_frontmatter
from models.document_models import DocumentResponse, DocumentListResponse, RegisterDocumentRequest
from services.document_service import get_document_service
from services.module_service import get_module_service
from models.transcription_models import ExtractionResponse
from models.tts_models import TTSVoice, TTSRequest, TTSResponse
from utils.file_utils import (
    LINKABLE_EXTENSIONS,
    MAX_FILE_SIZE,
    MAX_LINKED_FILES,
    FileValidationError,
    calculate_file_hash,
    get_file_extension,
    get_mime_type,
    is_allowed_file,
    scan_folder_for_files,
    validate_file_for_upload,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/courses", tags=["Documents"])

# Import auth helpers
from auth.helpers import require_auth, get_current_user_id


# ============================================================================
# Pydantic Models (Local to this route)
# ============================================================================
# Note: DocumentResponse, DocumentListResponse, RegisterDocumentRequest
#       are imported from models.document_models

class LinkPathRequest(BaseModel):
    """Request to link a file or folder."""
    path: str  # Absolute path to file or folder


class LinkPathResponse(BaseModel):
    """Response for link operation."""
    success: bool
    linked_count: int
    documents: List[DocumentResponse]
    warnings: Optional[List[str]] = None


# ============================================================================
# Endpoints
# ============================================================================
# Note: Helper functions (calculate_file_hash, get_file_extension, is_allowed_file,
#       is_linkable_file, scan_folder_for_files, get_mime_type) are imported from
#       utils.file_utils

@router.get("/{course_id}/documents", response_model=DocumentListResponse)
async def list_documents(
    course_id: str,
    verify_files: bool = True,
    auto_remove_missing: bool = True,
    auto_discover: bool = False,  # Disabled by default to avoid duplicates
    include_derived: bool = True,  # Include derived files by default (filtering done in frontend)
    user_id: Optional[str] = Depends(get_current_user_id)
):
    """
    List documents for a course.

    Args:
        course_id: Course ID
        verify_files: If True, verify that files exist on disk
        auto_remove_missing: If True, automatically remove documents whose files no longer exist
        auto_discover: If True, automatically discover and register orphaned files in /data/uploads/[id]/
        include_derived: If True, include derived files (transcriptions, extractions, TTS). Default False.
    """
    try:
        # Use document service for main listing logic
        doc_service = get_document_service()
        documents = await doc_service.list_documents(
            course_id=course_id,
            verify_files=verify_files,
            auto_remove_missing=auto_remove_missing,
            include_derived=include_derived
        )

        missing_files = []  # Track missing files (already handled by service if auto_remove_missing=True)

        # Auto-discover orphaned files in uploads directory (if requested)
        if auto_discover:
            # Normalize course ID
            if not course_id.startswith("course:"):
                course_id = f"course:{course_id}"

            # Track registered files to avoid duplicates
            registered_files = set()
            registered_filenames = set()
            for doc in documents:
                if doc.file_path:
                    try:
                        abs_path = Path(doc.file_path).resolve()
                        registered_files.add(abs_path)
                    except Exception:
                        registered_files.add(Path(doc.file_path))
                    registered_filenames.add(doc.filename)

            # Scan upload directory for orphaned files
            upload_dir = Path(settings.upload_dir) / course_id.replace("course:", "")
            if upload_dir.exists() and upload_dir.is_dir():
                surreal_service = get_surreal_service()
                if not surreal_service.db:
                    await surreal_service.connect()

                for file_path in upload_dir.iterdir():
                    if file_path.is_file():
                        # Check if already registered
                        is_registered = (
                            file_path.resolve() in registered_files or
                            file_path.name in registered_filenames
                        )

                        if not is_registered:
                            # Skip markdown files (derived files)
                            ext = get_file_extension(file_path.name).lower()
                            if ext in ['.md', '.markdown']:
                                logger.debug(f"Skipping auto-discovery of markdown file: {file_path.name}")
                                continue

                            # Auto-register if allowed file type
                            if is_allowed_file(file_path.name):
                                try:
                                    # Use document service to create
                                    doc_id = str(uuid.uuid4())[:8]
                                    ext = get_file_extension(file_path.name)
                                    file_size = file_path.stat().st_size
                                    relative_path = f"data/uploads/{course_id.replace('course:', '')}/{file_path.name}"

                                    # Create via service
                                    new_doc = await doc_service.create_document(
                                        course_id=course_id,
                                        filename=file_path.name,
                                        file_path=relative_path,
                                        file_size=file_size,
                                        file_type=ext.lstrip('.'),
                                        mime_type=get_mime_type(file_path.name),
                                        source_type="upload",
                                        is_derived=False
                                    )

                                    logger.info(f"Auto-discovered and registered file: {file_path.name}")
                                    documents.append(new_doc)

                                except Exception as e:
                                    logger.warning(f"Could not auto-register file {file_path.name}: {e}")

        # Sort documents by created_at descending
        documents.sort(key=lambda d: d.created_at, reverse=True)

        return DocumentListResponse(
            documents=documents,
            total=len(documents),
            missing_files=missing_files
        )

    except Exception as e:
        logger.error(f"Error listing documents: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/{course_id}/documents", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    course_id: str,
    file: UploadFile = File(...),
    module_id: Optional[str] = Form(None),
    user_id: str = Depends(require_auth)
):
    """
    Upload a document for a course.
    Accepts: PDF, Word, TXT, Markdown, Audio (MP3, WAV, M4A)

    PDFs are automatically processed with OCR to create a searchable markdown document.

    Args:
        module_id: If provided, directly assign the document to this module
    """
    # Read file content
    content = await file.read()

    # Validate file type and size
    try:
        validate_file_for_upload(file.filename or "", len(content), "upload")
    except FileValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=e.message)

    try:
        # Normalize course ID
        if not course_id.startswith("course:"):
            course_id = f"course:{course_id}"

        # Verify course exists
        service = get_surreal_service()
        if not service.db:
            await service.connect()

        clean_course_id = course_id.replace("course:", "")
        course_result = await service.query(
            "SELECT * FROM course WHERE id = type::thing('course', $course_id)",
            {"course_id": clean_course_id}
        )
        if not course_result or len(course_result) == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Course not found: {course_id}"
            )

        # Save file to disk
        doc_id = str(uuid.uuid4())[:8]
        ext = get_file_extension(file.filename)

        upload_dir = Path(settings.upload_dir) / course_id.replace("course:", "")
        upload_dir.mkdir(parents=True, exist_ok=True)

        file_path = str(upload_dir / f"{doc_id}{ext}")
        with open(file_path, "wb") as f:
            f.write(content)

        logger.info(f"Document saved: {file_path}")

        # Create document record using service
        doc_service = get_document_service()
        document = await doc_service.create_document(
            course_id=course_id,
            filename=file.filename,
            file_path=file_path,
            file_size=len(content),
            source_type="upload",
            module_id=module_id
        )

        logger.info(f"Document created: {document.id}")

        # For PDFs, automatically trigger OCR in background
        if ext.lower() == '.pdf':
            from services.document_ocr_task import run_ocr_for_document, update_ocr_status

            # Set initial OCR status to pending
            await update_ocr_status(document.id, "pending")
            logger.info(f"OCR scheduled for document: {document.id}")

            # Launch OCR task in background (non-blocking)
            asyncio.create_task(
                run_ocr_for_document(
                    document_id=document.id,
                    course_id=course_id,
                    pdf_path=file_path
                )
            )

        return document

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading document: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/{course_id}/documents/register", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def register_document(
    course_id: str,
    request: RegisterDocumentRequest,
    user_id: str = Depends(require_auth)
):
    """
    Register a document by its file path (without copying).

    The file remains at its original location on disk.
    The application only stores a reference to this file.
    Text is automatically extracted to enable AI analysis.
    """
    file_path = Path(request.file_path)

    # Verify file exists
    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File does not exist: {request.file_path}"
        )

    if not file_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Path is not a file: {request.file_path}"
        )

    # Validate file type and size
    filename = file_path.name
    file_size = file_path.stat().st_size
    try:
        validate_file_for_upload(filename, file_size, "upload")
    except FileValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=e.message)

    try:
        # Normalize course ID
        if not course_id.startswith("course:"):
            course_id = f"course:{course_id}"

        # Create document record using service (no file copy!)
        # NOTE: No automatic text extraction - user must trigger via UI/assistant
        doc_service = get_document_service()
        document = await doc_service.create_document(
            course_id=course_id,
            filename=filename,
            file_path=str(file_path.absolute()),  # Store absolute path
            file_size=file_size,
            source_type="upload"  # Could be "register" but keeping "upload" for consistency
        )

        logger.info(f"Document registered (no copy): {document.id} -> {file_path}")
        return document

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error registering document: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/{course_id}/documents/link", response_model=LinkPathResponse, status_code=status.HTTP_201_CREATED)
async def link_file_or_folder(
    course_id: str,
    request: LinkPathRequest,
    user_id: str = Depends(require_auth)
):
    """
    Link a file or directory without copying.

    - If path is a file: link this file only
    - If path is a directory: link all supported files in the directory (non-recursive)

    Files are referenced at their original location.
    A SHA-256 hash and mtime are stored to detect modifications.

    Supported types: .md, .mdx, .pdf, .txt, .docx
    Limit: 50 files maximum per directory
    """
    # Validate path is not empty
    if not request.path or not request.path.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Path cannot be empty"
        )

    path = Path(request.path)
    warnings = []
    linked_documents = []

    # Verify path exists
    if not path.exists():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Path does not exist: {request.path}"
        )

    try:
        # Get document service
        doc_service = get_document_service()

        # Get surreal service for indexing updates
        service = get_surreal_service()
        if not service.db:
            await service.connect()

        # Normalize course ID
        if not course_id.startswith("course:"):
            course_id = f"course:{course_id}"

        # Determine if path is file or folder
        files_to_link = []

        if path.is_file():
            # Single file - validate extension
            try:
                validate_file_for_upload(path.name, 0, "link")  # Size checked later
            except FileValidationError as e:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=e.message)
            files_to_link = [path]

        elif path.is_dir():
            # Folder - scan for files
            files_to_link = scan_folder_for_files(path, MAX_LINKED_FILES)

            if len(files_to_link) == 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"No supported files found in this directory. Allowed extensions: {', '.join(LINKABLE_EXTENSIONS)}"
                )

            if len(files_to_link) == MAX_LINKED_FILES:
                warnings.append(f"Limit of {MAX_LINKED_FILES} files reached. Some files were ignored.")

        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Path is neither a file nor a directory"
            )

        # Link each file
        now = datetime.utcnow().isoformat()

        for file_path in files_to_link:
            try:
                # Get file info
                file_stat = file_path.stat()
                file_size = file_stat.st_size
                ext = get_file_extension(file_path.name)

                # Check file size
                if file_size > MAX_FILE_SIZE:
                    warnings.append(f"File ignored (too large): {file_path.name}")
                    continue

                # Calculate hash and get mtime
                file_hash = calculate_file_hash(file_path)
                file_mtime = file_stat.st_mtime

                # Create linked source metadata
                linked_source = {
                    "absolute_path": str(file_path.absolute()),
                    "original_path": str(file_path.absolute()),  # Alias for test compatibility
                    "last_sync": now,
                    "source_hash": file_hash,
                    "file_hash": file_hash,  # Alias for test compatibility
                    "source_mtime": file_mtime,
                    "needs_reindex": False
                }

                # Read file content for text files
                texte_extrait = None
                if ext in {'.md', '.mdx', '.txt'}:
                    try:
                        texte_extrait = file_path.read_text(encoding='utf-8')
                        # Remove YAML frontmatter from markdown files
                        if ext in {'.md', '.mdx'}:
                            texte_extrait = remove_yaml_frontmatter(texte_extrait)
                    except Exception as e:
                        logger.warning(f"Could not read text from {file_path}: {e}")

                # Create document record using document service
                document = await doc_service.create_document(
                    course_id=course_id,
                    filename=file_path.name,
                    file_path=str(file_path.absolute()),
                    file_size=file_size,
                    file_type=ext.lstrip('.'),
                    mime_type=get_mime_type(file_path.name),
                    extracted_text=texte_extrait,
                    source_type="linked",
                    linked_source=linked_source
                )

                logger.info(f"Linked file: {file_path.name} -> {document.id}")

                # Index text content if available
                if texte_extrait:
                    try:
                        indexing_service = DocumentIndexingService()
                        result = await indexing_service.index_document(
                            document_id=document.id,
                            course_id=course_id,
                            text_content=texte_extrait
                        )

                        if result.get("success"):
                            await service.merge(document.id, {"indexed": True})
                            logger.info(f"Indexed {document.id} with {result.get('chunks_created', 0)} chunks")
                    except Exception as e:
                        logger.error(f"Error indexing {document.id}: {e}")

                # Add to response
                linked_documents.append(document)

            except Exception as e:
                logger.error(f"Error linking file {file_path}: {e}")
                warnings.append(f"Error linking {file_path.name}: {str(e)}")

        if len(linked_documents) == 0:
            detail = "No files could be linked."
            if warnings:
                detail += f" Warnings: {'; '.join(warnings)}"
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=detail
            )

        return LinkPathResponse(
            success=True,
            linked_count=len(linked_documents),
            documents=linked_documents,
            warnings=warnings if warnings else None
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error linking path: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


# ============================================================================
# DIAGNOSTIC ENDPOINT (Must be before /{doc_id} routes)
# ============================================================================

class DiagnosticResult(BaseModel):
    """Result of file/database consistency diagnostic."""
    total_documents: int
    missing_files: list[dict]
    orphan_records: list[dict]
    ok_count: int


@router.get("/{course_id}/documents/diagnostic", response_model=DiagnosticResult)
async def diagnose_documents(
    course_id: str,
    user_id: str = Depends(get_current_user_id)
):
    """
    Diagnostic of consistency between database and filesystem.

    Identifies:
    - Database records without physical files (orphans)
    - Physical files without database records (missing)
    """
    # Get all documents using document service (without auto-removal)
    doc_service = get_document_service()
    documents = await doc_service.list_documents(
        course_id=course_id,
        verify_files=False,  # Don't auto-remove missing files
        auto_remove_missing=False
    )

    missing_files = []
    ok_count = 0

    # Verify each document
    for doc in documents:
        if not doc.file_path:
            missing_files.append({
                "id": doc.id,
                "filename": doc.filename,
                "reason": "No file path registered"
            })
            continue

        if not Path(doc.file_path).exists():
            missing_files.append({
                "id": doc.id,
                "filename": doc.filename,
                "path": doc.file_path,
                "reason": "Physical file missing"
            })
        else:
            ok_count += 1

    return DiagnosticResult(
        total_documents=len(documents),
        missing_files=missing_files,
        orphan_records=missing_files,  # Alias for clarity
        ok_count=ok_count
    )


# ============================================================================
# Unassigned Documents (Must be before /{doc_id} routes)
# ============================================================================

@router.get("/{course_id}/documents/unassigned", summary="Unassigned documents")
async def get_unassigned_documents(
    course_id: str,
    user_id: Optional[str] = Depends(get_current_user_id)
):
    """
    Retrieve course documents that are not assigned to any module.

    Useful for identifying documents to organize.
    """
    module_service = get_module_service()
    documents = await module_service.get_unassigned_documents(course_id)

    return {
        "documents": documents,
        "total": len(documents)
    }


# ============================================================================
# ENDPOINTS WITH /{doc_id} PARAMETER (Must be after specific routes)
# ============================================================================

@router.get("/{course_id}/documents/{doc_id}/derived")
async def get_derived_documents(
    course_id: str,
    doc_id: str,
    user_id: Optional[str] = Depends(get_current_user_id)
):
    """
    Retrieve all derived files from a source document.

    Returns transcriptions, PDF extractions, TTS files, etc.
    created from the specified document.
    """
    try:
        # Get derived documents using document service
        doc_service = get_document_service()
        derived = await doc_service.get_derived_documents(doc_id)

        return {"derived": derived, "total": len(derived)}

    except Exception as e:
        logger.error(f"Error getting derived documents: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/{course_id}/documents/{doc_id}", response_model=DocumentResponse)
async def get_document(
    course_id: str,
    doc_id: str,
    user_id: Optional[str] = Depends(get_current_user_id)
):
    """
    Retrieve document details.
    """
    try:
        # Use document service
        doc_service = get_document_service()
        document = await doc_service.get_document(doc_id)

        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document non trouve"
            )

        return document

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting document: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.delete("/{course_id}/documents/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    course_id: str,
    doc_id: str,
    filename: Optional[str] = None,
    file_path: Optional[str] = None,
    user_id: str = Depends(require_auth)
):
    """
    Delete a document.

    Args:
        filename: Optional - filename to delete (used if document is not in database)
        file_path: Optional - full path of the file to delete (used if document is not in database)
    """
    try:
        # Normalize IDs
        if not course_id.startswith("course:"):
            course_id = f"course:{course_id}"
        if not doc_id.startswith("document:"):
            doc_id = f"document:{doc_id}"

        # Get document service
        doc_service = get_document_service()
        document = await doc_service.get_document(doc_id)

        # If document exists in database, handle deletion
        if document:
            logger.info(f"Found document to delete: {document.filename}")

            # Special handling for transcription documents
            if document.source_document_id and document.derivation_type == "transcription":
                # Clear texte_extrait from the source audio document
                service = get_surreal_service()
                if not service.db:
                    await service.connect()

                try:
                    await service.merge(document.source_document_id, {"texte_extrait": None})
                    logger.info(f"Cleared texte_extrait from source document: {document.source_document_id}")
                except Exception as e:
                    logger.warning(f"Could not clear texte_extrait from source: {e}")

            # Delete using service (handles file, DB, and embeddings)
            # Only delete file if it's in uploads directory (not linked files)
            delete_file = (
                document.file_path and
                ("data/uploads/" in document.file_path or str(settings.upload_dir) in document.file_path)
            )

            await doc_service.delete_document(doc_id, delete_file=delete_file)
            logger.info(f"Document deleted: {doc_id}")
        else:
            # Document not in database
            # If no file_path or filename provided, this is a real 404 error
            if not file_path and not filename:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Document non trouvé"
                )

            # Try to delete orphaned file if file_path or filename was provided
            logger.warning(f"Document not found in database (may have been auto-removed): {doc_id}")

            # Try to delete orphaned file using provided file_path or filename
            if file_path:
                # Use provided file_path directly
                file_path_obj = Path(file_path)
                if file_path_obj.exists():
                    # Check if file is in uploads directory
                    if "data/uploads/" in str(file_path_obj) or str(settings.upload_dir) in str(file_path_obj):
                        try:
                            file_path_obj.unlink()
                            logger.info(f"Deleted orphaned file from disk using file_path: {file_path}")
                        except Exception as e:
                            logger.warning(f"Could not delete orphaned file: {e}")
                    else:
                        logger.info(f"Orphaned file is external (not deleting): {file_path}")
                else:
                    logger.warning(f"Orphaned file does not exist: {file_path}")
            elif filename:
                # Use filename to find file in uploads directory
                upload_dir = Path(settings.upload_dir) / course_id.replace("course:", "")
                if upload_dir.exists():
                    file_path_obj = upload_dir / filename
                    if file_path_obj.exists():
                        try:
                            file_path_obj.unlink()
                            logger.info(f"Deleted orphaned file from disk using filename: {filename}")
                        except Exception as e:
                            logger.warning(f"Could not delete orphaned file: {e}")
                    else:
                        logger.warning(f"Orphaned file does not exist: {file_path_obj}")
            else:
                # Fallback: try to find file with matching ID in name (old behavior)
                upload_dir = Path(settings.upload_dir) / course_id.replace("course:", "")
                if upload_dir.exists():
                    # Look for file with matching ID in name
                    clean_id_short = clean_id[:8] if len(clean_id) > 8 else clean_id
                    found_any = False
                    for orphan_file in upload_dir.glob(f"{clean_id_short}*"):
                        try:
                            orphan_file.unlink()
                            logger.info(f"Deleted orphaned file from disk: {orphan_file}")
                            found_any = True
                        except Exception as e:
                            logger.warning(f"Could not delete orphaned file: {e}")
                    if not found_any:
                        logger.warning(f"No orphaned files found with ID pattern: {clean_id_short}*")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting document: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/{course_id}/documents/{doc_id}/download")
async def download_document(
    course_id: str,
    doc_id: str,
    inline: bool = False,
    user_id: Optional[str] = Depends(get_current_user_id)
):
    """
    Download a document or display it inline.

    Args:
        inline: If True, display the file in the browser (for iframe/preview)
                If False, force download
    """
    try:
        # Get document using document service
        doc_service = get_document_service()
        document = await doc_service.get_document(doc_id)

        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document non trouve"
            )

        if not document.file_path or not Path(document.file_path).exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Fichier non trouve sur le disque"
            )

        media_type = document.mime_type or "application/octet-stream"

        if inline:
            # For inline display (iframe/preview), don't set filename
            # This results in Content-Disposition: inline
            return FileResponse(
                path=document.file_path,
                media_type=media_type,
            )
        else:
            # For download, set filename which triggers attachment disposition
            return FileResponse(
                path=document.file_path,
                filename=document.filename or "document",
                media_type=media_type,
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading document: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


# Audio file extensions that can be transcribed
AUDIO_EXTENSIONS = {'.mp3', '.wav', '.m4a', '.ogg', '.webm', '.flac', '.aac'}


@router.post("/{course_id}/documents/{doc_id}/extract", response_model=ExtractionResponse)
async def extract_document_text(
    course_id: str,
    doc_id: str,
    user_id: str = Depends(require_auth)
):
    """
    Extract text from a document (PDF, Word, text, markdown).

    For audio files, use the /transcribe endpoint.
    """
    try:
        # Get document using document service
        doc_service = get_document_service()
        document = await doc_service.get_document(doc_id)

        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document non trouve"
            )

        # Validate file exists
        if not document.file_path:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Chemin du fichier non trouve"
            )

        if not Path(document.file_path).exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Fichier non trouve sur le disque"
            )

        # Check if it's an audio file (should use transcribe endpoint instead)
        ext = Path(document.file_path).suffix.lower()
        if ext in AUDIO_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Utilisez l'endpoint /transcribe pour les fichiers audio"
            )

        # Extract text
        from services.document_extraction_service import get_extraction_service

        extraction_service = get_extraction_service()
        extraction_result = await extraction_service.extract(document.file_path)

        if not extraction_result.success:
            logger.error(f"Extraction failed for {document.file_path}: {extraction_result.error}")
            return ExtractionResponse(
                success=False,
                error=extraction_result.error or "Erreur d'extraction inconnue"
            )

        # Update document with extracted text and metadata
        service = get_surreal_service()
        if not service.db:
            await service.connect()

        # Normalize document ID
        normalized_doc_id = doc_id if doc_id.startswith("document:") else f"document:{doc_id}"

        now = datetime.utcnow().isoformat()
        await service.merge(normalized_doc_id, {
            "texte_extrait": extraction_result.text,
            "extraction_method": extraction_result.extraction_method,
            "updated_at": now,
        })

        logger.info(f"Text extracted for {normalized_doc_id}: {len(extraction_result.text)} chars via {extraction_result.extraction_method}")

        return ExtractionResponse(
            success=True,
            text=extraction_result.text[:500] + "..." if len(extraction_result.text) > 500 else extraction_result.text,
            method=extraction_result.extraction_method
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error extracting document: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.delete("/{course_id}/documents/{doc_id}/text")
async def clear_document_text(
    course_id: str,
    doc_id: str,
    user_id: str = Depends(require_auth)
):
    """
    Clear the extracted text from a document.

    Removes the texte_extrait field from the document in the database.
    """
    try:
        # Verify document exists using document service
        doc_service = get_document_service()
        document = await doc_service.get_document(doc_id)

        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document non trouvé"
            )

        # Clear texte_extrait
        service = get_surreal_service()
        if not service.db:
            await service.connect()

        # Normalize document ID
        normalized_doc_id = doc_id if doc_id.startswith("document:") else f"document:{doc_id}"

        now = datetime.utcnow().isoformat()
        await service.merge(normalized_doc_id, {
            "texte_extrait": None,
            "extraction_method": None,
            "updated_at": now,
        })

        logger.info(f"Cleared texte_extrait for {normalized_doc_id}")

        return {"success": True, "message": "Texte extrait supprimé"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error clearing document text: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

# ============================================================================
# PDF Extraction to Markdown
# ============================================================================

@router.post("/{course_id}/documents/{doc_id}/extract-to-markdown")
async def extract_pdf_to_markdown(
    course_id: str,
    doc_id: str,
    force_reextract: bool = False,
    user_id: str = Depends(require_auth)
):
    """
    Extract text from a PDF and format it as markdown with LLM-detected sections.

    Args:
        force_reextract: If True, delete existing markdown file before re-extracting

    Returns an SSE stream with progress events:
    - progress: {step, message, percentage}
    - step_start: {step}
    - step_complete: {step, success}
    - complete: {result}
    - error: {message}
    """
    try:
        # Normalize course ID
        if not course_id.startswith("course:"):
            course_id = f"course:{course_id}"

        # Get document using document service
        doc_service = get_document_service()
        document = await doc_service.get_document(doc_id)

        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document non trouve"
            )

        if not document.file_path:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Chemin du fichier non trouve"
            )

        # Check if it's a PDF file
        ext = Path(document.file_path).suffix.lower()
        if ext != '.pdf':
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Ce n'est pas un fichier PDF. Extension: {ext}"
            )

        if not Path(document.file_path).exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Fichier PDF non trouve sur le disque"
            )

        # Get surreal service for later queries
        service = get_surreal_service()
        if not service.db:
            await service.connect()

        # Create SSE generator
        async def event_generator():
            import asyncio
            import json
            progress_queue = asyncio.Queue()

            async def run_extraction():
                try:
                    # Check if a markdown already exists for this PDF
                    original_filename = document.filename or "document.pdf"
                    markdown_filename = Path(original_filename).stem + ".md"

                    # Get judgment directory
                    judgment_dir = Path(settings.upload_dir) / course_id.replace("course:", "")
                    markdown_path = judgment_dir / markdown_filename

                    # Check existing documents in database
                    docs_result = await service.query(
                        "SELECT * FROM document WHERE course_id = $course_id AND nom_fichier = $filename",
                        {"course_id": course_id, "filename": markdown_filename}
                    )

                    existing_docs = []
                    if docs_result and len(docs_result) > 0:
                        # Parse result
                        first_item = docs_result[0]
                        if isinstance(first_item, dict):
                            if "result" in first_item:
                                existing_docs = first_item["result"] if isinstance(first_item["result"], list) else []
                            elif "id" in first_item:
                                existing_docs = docs_result
                        elif isinstance(first_item, list):
                            existing_docs = first_item

                    # Handle existing markdown
                    if markdown_path.exists() or (existing_docs and len(existing_docs) > 0):
                        if not force_reextract:
                            # Send "complete" event with error instead of "error" event
                            # This ensures the frontend receives a proper completion signal
                            await progress_queue.put({
                                "type": "complete",
                                "data": {
                                    "success": False,
                                    "error": f"Un fichier markdown '{markdown_filename}' existe déjà pour ce PDF."
                                }
                            })
                            return

                        # Delete existing file and database records if force_reextract=True
                        await progress_queue.put({
                            "type": "progress",
                            "data": {"step": "cleanup", "message": "Suppression du markdown existant...", "percentage": 10}
                        })

                        # Delete file from disk
                        if markdown_path.exists():
                            try:
                                markdown_path.unlink()
                                logger.info(f"Deleted existing markdown file: {markdown_path}")
                            except Exception as e:
                                logger.warning(f"Failed to delete markdown file: {e}")

                        # Delete database records
                        if existing_docs and len(existing_docs) > 0:
                            for existing_doc in existing_docs:
                                try:
                                    doc_id_str = str(existing_doc["id"])

                                    # Delete embedding chunks first
                                    await service.query(
                                        "DELETE FROM embedding_chunk WHERE document_id = $doc_id",
                                        {"doc_id": doc_id_str}
                                    )

                                    # Delete document record
                                    await service.delete(doc_id_str)
                                    logger.info(f"Deleted existing document record: {doc_id_str}")
                                except Exception as e:
                                    logger.warning(f"Failed to delete document record: {e}")

                    # Step 1: Extract text with MarkItDown
                    await progress_queue.put({
                        "type": "progress",
                        "data": {"step": "extract", "message": "Extraction du texte avec MarkItDown...", "percentage": 20}
                    })

                    from services.document_extraction_service import get_extraction_service
                    extraction_service = get_extraction_service()

                    extraction_result = await extraction_service.extract(
                        file_path=document.file_path,
                        content_type="application/pdf"
                    )

                    if not extraction_result.success:
                        await progress_queue.put({
                            "type": "error",
                            "data": {"message": extraction_result.error or "Échec de l'extraction"}
                        })
                        return

                    await progress_queue.put({
                        "type": "progress",
                        "data": {"step": "extract", "message": "Texte extrait avec succès", "percentage": 60}
                    })

                    # Step 2: Save as markdown file
                    await progress_queue.put({
                        "type": "progress",
                        "data": {"step": "save", "message": "Création du fichier markdown...", "percentage": 70}
                    })

                    # Ensure judgment directory exists (judgment_dir and markdown_path already defined at the beginning)
                    judgment_dir.mkdir(parents=True, exist_ok=True)

                    # Write markdown file
                    with open(markdown_path, "w", encoding="utf-8") as f:
                        f.write(extraction_result.text)

                    # Step 3: Create document record in SurrealDB
                    await progress_queue.put({
                        "type": "progress",
                        "data": {"step": "save", "message": "Enregistrement dans la base de données...", "percentage": 85}
                    })

                    # Generate document ID (remove hyphens for SurrealDB compatibility)
                    new_doc_id = uuid.uuid4().hex[:16]
                    doc_record = {
                        # ❌ DO NOT include "id" in doc_record as CREATE will add it automatically
                        "course_id": course_id,
                        "nom_fichier": markdown_filename,
                        "type_fichier": "md",
                        "type_mime": "text/markdown",
                        "taille": len(extraction_result.text.encode('utf-8')),
                        "file_path": str(markdown_path),
                        "texte_extrait": extraction_result.text,  # Store for indexing
                        "is_transcription": False,
                        "source_document_id": doc_id,  # Link to source PDF
                        "is_derived": True,
                        "derivation_type": "pdf_extraction",
                        "source_type": "upload",
                        "created_at": datetime.utcnow().isoformat(),
                        "updated_at": datetime.utcnow().isoformat(),
                    }

                    # Use service.create() with record_id to ensure correct format
                    await service.create("document", doc_record, record_id=new_doc_id)

                    # Index the document for semantic search
                    try:
                        from services.document_indexing_service import get_document_indexing_service

                        await progress_queue.put({
                            "type": "progress",
                            "data": {"step": "save", "message": "Indexation pour recherche sémantique...", "percentage": 90}
                        })

                        indexing_service = get_document_indexing_service()
                        index_result = await indexing_service.index_document(
                            document_id=f"document:{new_doc_id}",
                            course_id=course_id,
                            text_content=extraction_result.text,
                            force_reindex=False
                        )

                        if index_result.get("success"):
                            logger.info(f"Document indexed: {index_result.get('chunks_created', 0)} chunks")
                        else:
                            logger.warning(f"Indexing failed: {index_result.get('error', 'Unknown error')}")
                    except Exception as e:
                        # Don't block if indexing fails
                        logger.warning(f"Could not index document: {e}")

                    await progress_queue.put({
                        "type": "complete",
                        "data": {
                            "success": True,
                            "document_id": f"document:{new_doc_id}",
                            "document_path": str(markdown_path),
                            "page_count": extraction_result.metadata.get("num_pages", 0)
                        }
                    })

                except Exception as e:
                    logger.error(f"Extraction error: {e}", exc_info=True)
                    await progress_queue.put({
                        "type": "error",
                        "data": {"message": str(e)}
                    })
                finally:
                    await progress_queue.put(None)  # Signal end

            # Start extraction
            task = asyncio.create_task(run_extraction())

            try:
                while True:
                    event = await progress_queue.get()
                    if event is None:
                        break

                    yield f"event: {event['type']}\n"
                    yield f"data: {json.dumps(event['data'], ensure_ascii=False)}\n\n"

            except asyncio.CancelledError:
                task.cancel()
                raise

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting PDF extraction workflow: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

# ============================================================================
# TEXT-TO-SPEECH ENDPOINTS
# ============================================================================

@router.get("/tts/voices", response_model=list[TTSVoice])
async def list_tts_voices(
    user_id: Optional[str] = Depends(get_current_user_id)
):
    """
    List all available TTS voices.

    Returns the list of supported voices for text-to-speech synthesis.
    """
    try:
        from services.tts_service import get_tts_service, EDGE_TTS_AVAILABLE

        if not EDGE_TTS_AVAILABLE:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Service TTS non disponible. Installer edge-tts: uv add edge-tts"
            )

        tts_service = get_tts_service()
        voices = tts_service.get_available_voices()

        return [TTSVoice(**voice) for voice in voices]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing TTS voices: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/{course_id}/documents/{doc_id}/tts", response_model=TTSResponse)
async def generate_tts(
    course_id: str,
    doc_id: str,
    request: TTSRequest = TTSRequest(),
    user_id: str = Depends(require_auth)
):
    """
    Generate a TTS audio file from the extracted text of a document.

    The audio file is generated in MP3 format and saved in the case directory.
    Returns the URL to download/stream the audio.
    """
    try:
        from services.tts_service import get_tts_service, EDGE_TTS_AVAILABLE

        if not EDGE_TTS_AVAILABLE:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Service TTS non disponible. Installer edge-tts: uv add edge-tts"
            )

        # Normalize course ID
        if not course_id.startswith("course:"):
            course_id = f"course:{course_id}"

        # Get document using document service
        doc_service = get_document_service()
        document = await doc_service.get_document(doc_id)

        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document non trouvé"
            )

        # Get text content - try extracted_text first, then read from file for markdown
        text_content = document.extracted_text

        if not text_content:
            # For markdown files, try to read directly from file
            file_path = document.file_path
            if not file_path and document.linked_source:
                file_path = document.linked_source.get("absolute_path")

            if file_path and Path(file_path).exists():
                ext = Path(file_path).suffix.lower()
                if ext in [".md", ".markdown", ".txt"]:
                    try:
                        text_content = Path(file_path).read_text(encoding="utf-8")
                        logger.info(f"Read content from file: {file_path} ({len(text_content)} chars)")
                    except Exception as e:
                        logger.error(f"Error reading file {file_path}: {e}")

        if not text_content:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ce document n'a pas de texte extrait. Utilisez d'abord l'extraction ou la transcription."
            )

        # Generate TTS
        tts_service = get_tts_service()

        # Create output path
        judgment_dir = Path(settings.upload_dir) / course_id.replace("course:", "")
        judgment_dir.mkdir(parents=True, exist_ok=True)

        # Generate filename based on document name
        original_filename = document.filename or "document"
        audio_filename = f"{Path(original_filename).stem}_tts.mp3"
        audio_path = judgment_dir / audio_filename

        logger.info(f"Generating TTS for document {document.id}: {len(text_content)} chars")

        # Generate audio
        tts_result = await tts_service.text_to_speech(
            text=text_content,
            output_path=str(audio_path),
            language=request.language,
            voice=request.voice if request.voice else tts_service.get_voice_for_language(
                request.language,
                request.gender
            ),
            rate=request.rate,
            volume=request.volume
        )

        if not tts_result.success:
            logger.error(f"TTS generation failed: {tts_result.error}")
            return TTSResponse(
                success=False,
                error=tts_result.error or "Erreur de génération TTS inconnue"
            )

        # Create document record for the TTS audio
        tts_document = await doc_service.create_document(
            course_id=course_id,
            filename=audio_filename,
            file_path=tts_result.audio_path,
            file_size=Path(tts_result.audio_path).stat().st_size,
            file_type="mp3",
            mime_type="audio/mpeg",
            source_type="tts_audio",
            source_document_id=doc_id,
            is_derived=False,  # Show in documents list for download
            derivation_type="tts"
        )
        logger.info(f"TTS audio saved as document: {tts_document.id}")

        # Return URL for downloading/streaming
        clean_course_id = course_id.replace("course:", "")
        # tts_document.id already includes the "document:" prefix
        audio_url = f"/api/courses/{clean_course_id}/documents/{tts_document.id}/download?inline=true"

        return TTSResponse(
            success=True,
            audio_url=audio_url,
            duration=tts_result.duration,
            voice=tts_result.voice
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating TTS: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


# ============================================================================
# DIAGNOSTIC ENDPOINT
# Diagnostic endpoint moved before /{doc_id} routes for correct routing