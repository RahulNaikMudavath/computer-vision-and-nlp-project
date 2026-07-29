import os
import time
import glob
import logging
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, status, Path, Query, Body
from fastapi.responses import Response, JSONResponse, FileResponse
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from PIL import Image, UnidentifiedImageError

from app.core.config import settings
from app.models.database import get_db, User, Document, DocumentChunk, ChatHistory, UserSettings
from app.core.security import get_current_user
from app.utils.helpers import save_document_securely, format_size
from app.services.pdf_service import pdf_service
from app.services.vlm_service import vlm_service
from app.services.document_service import document_service
from app.services.chunk_service import chunk_service
from app.services.vector_service import vector_service
from app.exceptions.handlers import InvalidImageException

logger = logging.getLogger("document_ocr.api.document_routes")

# Initialize router
router = APIRouter(tags=["Document Management"])

# =====================================================================
# Request & Response DTOs
# =====================================================================

class DocumentResponse(BaseModel):
    id: str
    filename: str
    original_filename: str
    file_type: str
    size_formatted: str
    ocr_status: str
    processing_status: str
    document_type: str
    confidence_score: float
    created_at: str


class DocumentDetailResponse(BaseModel):
    id: str
    filename: str
    original_filename: str
    file_type: str
    size_formatted: str
    ocr_status: str
    processing_status: str
    document_type: str
    confidence_score: float
    ocr_text: Optional[str] = None
    created_at: str


class DocumentAnalyzeResponse(BaseModel):
    success: bool
    document_id: str
    document_type: Optional[str] = None
    confidence: Optional[float] = None
    data: Optional[Dict[str, Any]] = None
    processing_time: Optional[str] = None
    message: Optional[str] = None


class RenameRequest(BaseModel):
    filename: str


class ProfileUpdateRequest(BaseModel):
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
    new_password: Optional[str] = Field(None, min_length=6)


class SettingsUpdateRequest(BaseModel):
    theme: Optional[str] = None
    language: Optional[str] = None
    default_ocr_language: Optional[str] = None
    email_notifications: Optional[bool] = None


class RecentActivity(BaseModel):
    activity_type: str  # "upload" or "chat"
    message: str
    timestamp: str


class DashboardStats(BaseModel):
    documents_processed: int
    pages_processed: int
    total_chats: int
    storage_used_formatted: str
    storage_used_bytes: int
    recent_uploads: List[DocumentResponse]
    recent_activities: List[RecentActivity]

# =====================================================================
# Document Library & Analyze Endpoints
# =====================================================================

@router.post(
    "/document/analyze",
    response_model=DocumentAnalyzeResponse,
    summary="Intelligent Structured Document Understanding",
    description=(
        "Upload a PDF or Image (up to 50MB for PDFs, 20MB for images). "
        "The system indexes the upload inside the User SQL record, splits pages, transcribes OCR, "
        "runs classification, saves chunks to SQL/Chroma DB, and returns structured data."
    )
)
async def analyze_document(
    file: UploadFile = File(..., description="The document file (PDF or image) to analyze."),
    sync: bool = Query(False, description="Whether to run synchronously in-process (mainly for test suites)."),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> dict:
    logger.info(f"User '{current_user.email}' requested analyze. File: '{file.filename}'")
    
    # 1. Save locally with secure limits checking
    saved_path, doc_format = await save_document_securely(file)
    file_size = os.path.getsize(saved_path)
    document_id = os.path.splitext(os.path.basename(saved_path))[0]
    
    # 2. Register Document record in Postgres/SQLite database as PENDING
    db_doc = Document(
        id=document_id,
        filename=os.path.basename(saved_path),
        original_filename=file.filename,
        file_type=doc_format,
        size_bytes=file_size,
        ocr_status="PENDING",
        processing_status="PROCESSING",
        uploaded_by=current_user.id
    )
    db.add(db_doc)
    db.commit()
    
    is_test_env = "test" in settings.DATABASE_URL or settings.MOCK_VLM
    
    # 3. Trigger processing
    if sync or is_test_env:
        logger.info(f"Running synchronous extraction in-process for document ID '{document_id}'")
        start_time = time.time()
        ocr_text = ""
        pages = []
        
        try:
            if doc_format == "pdf":
                pdf_res = await pdf_service.process_pdf_ocr(saved_path)
                ocr_text = pdf_res["full_text"]
                for item in pdf_res.get("results", []):
                    pages.append({"page": item["page"], "text": item["text"]})
            else:
                try:
                    with Image.open(saved_path) as pil_image:
                        ocr_text = await vlm_service.perform_ocr(pil_image)
                        pages.append({"page": 1, "text": ocr_text})
                except (UnidentifiedImageError, OSError) as e:
                    logger.error(f"Image load failure: {str(e)}")
                    raise InvalidImageException("Uploaded file is corrupted or not a valid image.")
                    
            analysis_res = await document_service.analyze_document(ocr_text, file.filename)
            
            # Cache the extracted JSON data
            from app.services.cache_service import cache_service
            cache_service.set_json(f"doc:json:{document_id}", analysis_res["data"])
            
            chunks = chunk_service.split_pages(pages)
            for c in chunks:
                chunk_row = DocumentChunk(
                    document_id=document_id,
                    page_number=c["metadata"]["page"],
                    chunk_index=c["metadata"]["chunk_index"],
                    text_content=c["text"]
                )
                db.add(chunk_row)
                
            vector_service.add_document_chunks(document_id, chunks)
            
            db_doc.ocr_status = "COMPLETED"
            db_doc.processing_status = "COMPLETED"
            db_doc.ocr_text = ocr_text
            db_doc.document_type = analysis_res["document_type"]
            db_doc.confidence_score = analysis_res["confidence"]
            db.commit()
            
            elapsed = time.time() - start_time
            return {
                "success": True,
                "document_id": document_id,
                "document_type": db_doc.document_type,
                "confidence": db_doc.confidence_score,
                "data": analysis_res["data"],
                "processing_time": f"{elapsed:.2f}s",
                "message": "Processed synchronously."
            }
        except Exception as ex:
            db_doc.ocr_status = "FAILED"
            db_doc.processing_status = "FAILED"
            db.commit()
            logger.error(f"SaaS document analysis failed for ID '{document_id}': {str(ex)}")
            raise ex
    else:
        logger.info(f"Delegating asynchronous analysis pipeline for document ID '{document_id}' to Celery queue.")
        from app.tasks.worker import process_document_pipeline_task
        process_document_pipeline_task.delay(document_id, saved_path, file.filename, current_user.id)
        
        return {
            "success": True,
            "document_id": document_id,
            "message": "Document queued for asynchronous processing. Track status using WebSockets."
        }


@router.get(
    "/document/list",
    response_model=List[DocumentResponse],
    summary="List and filter user documents",
    description="Returns list of uploaded documents by current user with global search and sort parameters."
)
async def list_documents(
    search: Optional[str] = Query(None, description="Search term on filename, type, or OCR text."),
    doc_type: Optional[str] = Query(None, description="Filter by exact document type."),
    status: Optional[str] = Query(None, description="Filter by OCR status (PENDING/COMPLETED/FAILED)."),
    sort: str = Query("newest", description="Sort order: 'newest' or 'oldest'."),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> list:
    query = db.query(Document).filter(Document.uploaded_by == current_user.id)
    
    # Apply filters
    if status:
        query = query.filter(Document.ocr_status == status.upper())
    if doc_type:
        query = query.filter(Document.document_type == doc_type)
    if search:
        search_filter = f"%{search}%"
        query = query.filter(
            Document.original_filename.ilike(search_filter) |
            Document.document_type.ilike(search_filter) |
            Document.ocr_text.ilike(search_filter)
        )
        
    # Sort
    if sort == "oldest":
        query = query.order_by(Document.created_at.asc())
    else:
        query = query.order_by(Document.created_at.desc())
        
    documents = query.all()
    
    return [
        {
            "id": d.id,
            "filename": d.filename,
            "original_filename": d.original_filename,
            "file_type": d.file_type,
            "size_formatted": format_size(d.size_bytes),
            "ocr_status": d.ocr_status,
            "processing_status": d.processing_status,
            "document_type": d.document_type,
            "confidence_score": d.confidence_score,
            "created_at": d.created_at.isoformat()
        }
        for d in documents
    ]


@router.get(
    "/document/{id}",
    response_model=DocumentDetailResponse,
    summary="Get single document details",
    description="Locates the document by UUID and returns its metadata and plain OCR text. Owner only."
)
async def get_document_details(
    id: str = Path(..., description="The unique UUID of the uploaded document."),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> dict:
    doc = db.query(Document).filter(
        Document.id == id,
        Document.uploaded_by == current_user.id
    ).first()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found or access denied."
        )
        
    return {
        "id": doc.id,
        "filename": doc.filename,
        "original_filename": doc.original_filename,
        "file_type": doc.file_type,
        "size_formatted": format_size(doc.size_bytes),
        "ocr_status": doc.ocr_status,
        "processing_status": doc.processing_status,
        "document_type": doc.document_type,
        "confidence_score": doc.confidence_score,
        "ocr_text": doc.ocr_text,
        "created_at": doc.created_at.isoformat()
    }


@router.post(
    "/document/{id}/rename",
    summary="Rename document original filename",
    description="Renames the document's original filename. Restricted to document owner."
)
async def rename_document(
    id: str = Path(..., description="Document UUID string."),
    request: RenameRequest = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> dict:
    if not request or not request.filename.strip():
        raise HTTPException(status_code=400, detail="Filename cannot be empty.")
        
    doc = db.query(Document).filter(Document.id == id, Document.uploaded_by == current_user.id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found or access denied.")
        
    old_name = doc.original_filename
    doc.original_filename = request.filename.strip()
    db.commit()
    
    logger.info(f"User '{current_user.email}' renamed document '{id}' from '{old_name}' to '{doc.original_filename}'")
    return {"success": True, "message": "Document renamed successfully.", "original_filename": doc.original_filename}


@router.delete(
    "/document/{id}",
    summary="Delete uploaded document",
    description="Deletes document database records, chunks, chats, and purges physical files from disk. Owner only."
)
async def delete_document(
    id: str = Path(..., description="Document UUID string."),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> dict:
    doc = db.query(Document).filter(Document.id == id, Document.uploaded_by == current_user.id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found or access denied.")
        
    # Relational cascading deletes chunks, chat histories, embeddings
    db.delete(doc)
    db.commit()
    
    # Try deleting physical files
    import glob
    # PDF
    pdf_pattern = os.path.join(settings.UPLOAD_PDFS_DIR, f"{id}.pdf")
    for f in glob.glob(pdf_pattern):
        try: os.remove(f)
        except OSError: pass
    # Image
    for ext in [".png", ".jpg", ".jpeg"]:
        img_pattern = os.path.join(settings.UPLOAD_IMAGES_DIR, f"{id}{ext}")
        for f in glob.glob(img_pattern):
            try: os.remove(f)
            except OSError: pass
            
    logger.info(f"User '{current_user.email}' deleted document '{id}' ({doc.original_filename})")
    return {"success": True, "message": f"Successfully deleted document '{doc.original_filename}'."}


@router.get(
    "/document/{id}/download-text",
    summary="Download plain OCR text",
    description="Returns the parsed plain OCR text content as a text file download."
)
async def download_text(
    id: str = Path(..., description="Document UUID string."),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Response:
    doc = db.query(Document).filter(Document.id == id, Document.uploaded_by == current_user.id).first()
    if not doc or not doc.ocr_text:
        raise HTTPException(status_code=404, detail="Document OCR content not found.")
        
    headers = {
        "Content-Disposition": f"attachment; filename={doc.original_filename}.txt",
        "Content-Type": "text/plain; charset=utf-8"
    }
    return Response(content=doc.ocr_text, headers=headers)


@router.get(
    "/document/{id}/download-json",
    summary="Download structured extraction JSON data",
    description="Triggers direct download of the validated extraction schema details."
)
async def download_json(
    id: str = Path(..., description="Document UUID string."),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> JSONResponse:
    doc = db.query(Document).filter(Document.id == id, Document.uploaded_by == current_user.id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")
        
    # Check cache first
    from app.services.cache_service import cache_service
    cached_data = cache_service.get_json(f"doc:json:{id}")
    if cached_data:
        logger.info(f"Serving structured JSON from cache for document ID '{id}'")
        headers = {
            "Content-Disposition": f"attachment; filename={doc.original_filename}.json"
        }
        return JSONResponse(content=cached_data, headers=headers)
        
    # Analyze text to get JSON structure if not cached
    ocr_text = doc.ocr_text or ""
    analysis_res = await document_service.analyze_document(ocr_text, doc.original_filename)
    
    # Save cache
    cache_service.set_json(f"doc:json:{id}", analysis_res["data"])
    
    headers = {
        "Content-Disposition": f"attachment; filename={doc.original_filename}.json"
    }
    return JSONResponse(content=analysis_res["data"], headers=headers)

# =====================================================================
# Dashboard Stats & User Actions
# =====================================================================

@router.get(
    "/dashboard/stats",
    response_model=DashboardStats,
    summary="Get user dashboard stats",
    description="Retrieves storage used, document counts, pages, total chats, and recent history logs."
)
async def get_dashboard_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> dict:
    docs_processed = db.query(Document).filter(Document.uploaded_by == current_user.id, Document.ocr_status == "COMPLETED").count()
    chats_count = db.query(ChatHistory).filter(ChatHistory.user_id == current_user.id).count()
    
    # Calculate storage size
    size_sum = db.query(Document).filter(Document.uploaded_by == current_user.id).with_entities(Document.size_bytes).all()
    total_bytes = sum([s[0] for s in size_sum]) if size_sum else 0
    
    # Calculate page chunks count
    pages_processed = db.query(DocumentChunk).join(Document).filter(Document.uploaded_by == current_user.id).count()
    
    # Get 5 recent uploads
    recent_docs = db.query(Document).filter(Document.uploaded_by == current_user.id).order_by(Document.created_at.desc()).limit(5).all()
    formatted_docs = [
        {
            "id": d.id,
            "filename": d.filename,
            "original_filename": d.original_filename,
            "file_type": d.file_type,
            "size_formatted": format_size(d.size_bytes),
            "ocr_status": d.ocr_status,
            "processing_status": d.processing_status,
            "document_type": d.document_type,
            "confidence_score": d.confidence_score,
            "created_at": d.created_at.isoformat()
        }
        for d in recent_docs
    ]
    
    # Compile activities feed
    activities = []
    # 5 recent uploads
    for d in recent_docs[:3]:
        activities.append({
            "activity_type": "upload",
            "message": f"Uploaded document: '{d.original_filename}'",
            "timestamp": d.created_at.isoformat()
        })
    # 3 recent chats
    recent_chats = db.query(ChatHistory).filter(ChatHistory.user_id == current_user.id).order_by(ChatHistory.created_at.desc()).limit(3).all()
    for c in recent_chats:
        activities.append({
            "activity_type": "chat",
            "message": f"Asked: '{c.question}'",
            "timestamp": c.created_at.isoformat()
        })
    # Sort activities by timestamp descending
    activities.sort(key=lambda x: x["timestamp"], reverse=True)
    
    return {
        "documents_processed": docs_processed,
        "pages_processed": pages_processed,
        "total_chats": chats_count,
        "storage_used_bytes": total_bytes,
        "storage_used_formatted": format_size(total_bytes),
        "recent_uploads": formatted_docs,
        "recent_activities": activities[:5]
    }


@router.post(
    "/profile/update",
    summary="Update profile configurations",
    description="Updates user's name, avatar URL, or hashes a new account password."
)
async def update_profile(
    request: ProfileUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> dict:
    if request.full_name is not None:
        current_user.full_name = request.full_name
    if request.avatar_url is not None:
        current_user.avatar_url = request.avatar_url
    if request.new_password:
        from app.core.security import get_password_hash
        current_user.hashed_password = get_password_hash(request.new_password)
        
    db.commit()
    logger.info(f"User '{current_user.email}' updated profile.")
    return {"success": True, "message": "Successfully updated profile information."}


@router.post(
    "/settings/update",
    summary="Update settings theme/language",
    description="Changes themes, language indicators, OCR fallback language, or email parameters."
)
async def update_settings(
    request: SettingsUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> dict:
    settings_obj = db.query(UserSettings).filter(UserSettings.user_id == current_user.id).first()
    if not settings_obj:
        settings_obj = UserSettings(user_id=current_user.id)
        db.add(settings_obj)
        
    if request.theme is not None:
        settings_obj.theme = request.theme
    if request.language is not None:
        settings_obj.language = request.language
    if request.default_ocr_language is not None:
        settings_obj.default_ocr_language = request.default_ocr_language
    if request.email_notifications is not None:
        settings_obj.email_notifications = request.email_notifications
        
    db.commit()
    logger.info(f"User '{current_user.email}' updated settings parameters.")
    return {"success": True, "message": "Settings updated successfully."}


@router.delete(
    "/profile/delete-account",
    summary="Delete user account",
    description="Completely removes user, settings, all uploaded files and purging database histories. Owner only."
)
async def delete_account(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> dict:
    # Get user documents list to clean files on disk
    user_docs = db.query(Document).filter(Document.uploaded_by == current_user.id).all()
    doc_ids = [d.id for d in user_docs]
    
    # Delete User record (SQLAlchemy cascading triggers orphans cleanups)
    db.delete(current_user)
    db.commit()
    
    # Delete physical document files
    import glob
    for d_id in doc_ids:
        # PDF
        pdf_pattern = os.path.join(settings.UPLOAD_PDFS_DIR, f"{d_id}.pdf")
        for f in glob.glob(pdf_pattern):
            try: os.remove(f)
            except OSError: pass
        # Image
        for ext in [".png", ".jpg", ".jpeg"]:
            img_pattern = os.path.join(settings.UPLOAD_IMAGES_DIR, f"{d_id}{ext}")
            for f in glob.glob(img_pattern):
                try: os.remove(f)
                except OSError: pass
                
    logger.warning(f"SaaS User '{current_user.email}' self-deleted their account. All document data purged.")
    return {"success": True, "message": "Your account and all associated documents have been permanently deleted."}


@router.get(
    "/document/{id}/file",
    summary="Get raw document file content",
    description="Serves the raw PDF or image file content directly for inline viewing. Owner only."
)
async def get_document_file(
    id: str = Path(..., description="The unique UUID of the uploaded document."),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> FileResponse:
    doc = db.query(Document).filter(Document.id == id, Document.uploaded_by == current_user.id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found or access denied.")
        
    # Check PDFs folder
    pdf_path = os.path.join(settings.UPLOAD_PDFS_DIR, f"{id}.pdf")
    if os.path.exists(pdf_path):
        return FileResponse(pdf_path, media_type="application/pdf")
        
    # Check Images folder
    for ext in [".png", ".jpg", ".jpeg"]:
        img_path = os.path.join(settings.UPLOAD_IMAGES_DIR, f"{id}{ext}")
        if os.path.exists(img_path):
            media_type = f"image/{ext.replace('.', '')}" if ext != ".jpg" else "image/jpeg"
            return FileResponse(img_path, media_type=media_type)
            
    raise HTTPException(status_code=404, detail="Physical document file not found on disk.")


@router.post(
    "/document/{id}/update-json",
    summary="Save corrected structured JSON",
    description="Updates the cached/stored structured JSON data for the document. Owner only."
)
async def update_json_data(
    id: str = Path(..., description="Document UUID string."),
    payload: dict = Body(..., description="The edited structured JSON dictionary."),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> dict:
    doc = db.query(Document).filter(Document.id == id, Document.uploaded_by == current_user.id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found or access denied.")
        
    from app.services.cache_service import cache_service
    cache_service.set_json(f"doc:json:{id}", payload)
    
    logger.info(f"User '{current_user.email}' updated structured JSON cache for document '{id}'.")
    return {"success": True, "message": "Structured fields updated successfully."}
