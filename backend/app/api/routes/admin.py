import logging
from fastapi import APIRouter, Depends, HTTPException, status, Path, Query
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy.orm import Session

from app.models.database import get_db, User, Document, ChatHistory
from app.core.security import get_admin_user
from app.utils.helpers import format_size

logger = logging.getLogger("document_ocr.api.admin")

# Initialize router
router = APIRouter(prefix="/admin", tags=["Administrative Control"])

# =====================================================================
# Response Schemas
# =====================================================================

class PlatformAnalytics(BaseModel):
    total_users: int
    total_documents: int
    total_chats: int
    total_storage_bytes: int
    storage_used_formatted: str


class AdminUserResponse(BaseModel):
    id: int
    email: str
    full_name: Optional[str]
    role: str
    is_active: bool
    created_at: str
    document_count: int


class LogLineResponse(BaseModel):
    timestamp: str
    level: str
    message: str

# =====================================================================
# Endpoints
# =====================================================================

@router.get(
    "/analytics",
    response_model=PlatformAnalytics,
    summary="Get platform metrics (Admin only)",
    description="Calculates system-wide analytics including users count, document counts, and VRAM/disk storage size."
)
async def get_analytics(
    db: Session = Depends(get_db),
    admin: User = Depends(get_admin_user)
) -> dict:
    total_users = db.query(User).count()
    total_docs = db.query(Document).count()
    total_chats = db.query(ChatHistory).count()
    
    # Calculate storage size
    size_sum = db.query(Document).with_entities(Document.size_bytes).all()
    total_bytes = sum([s[0] for s in size_sum]) if size_sum else 0
    
    logger.info(f"Admin '{admin.email}' requested platform analytics.")
    return {
        "total_users": total_users,
        "total_documents": total_docs,
        "total_chats": total_chats,
        "total_storage_bytes": total_bytes,
        "storage_used_formatted": format_size(total_bytes)
    }


@router.get(
    "/users",
    response_model=List[AdminUserResponse],
    summary="List all users (Admin only)",
    description="Retrieves a complete list of users, their document counts, and statuses."
)
async def list_users(
    db: Session = Depends(get_db),
    admin: User = Depends(get_admin_user)
) -> list:
    users = db.query(User).all()
    results = []
    
    for u in users:
        doc_count = db.query(Document).filter(Document.uploaded_by == u.id).count()
        results.append({
            "id": u.id,
            "email": u.email,
            "full_name": u.full_name,
            "role": u.role,
            "is_active": u.is_active,
            "created_at": u.created_at.isoformat(),
            "document_count": doc_count
        })
        
    logger.info(f"Admin '{admin.email}' retrieved users list.")
    return results


@router.post(
    "/users/{id}/toggle-status",
    summary="Toggle user active status (Admin only)",
    description="Deactivates or reactivates a user account, blocking login sessions if deactivated."
)
async def toggle_user_status(
    id: int = Path(..., description="User ID key."),
    db: Session = Depends(get_db),
    admin: User = Depends(get_admin_user)
) -> dict:
    if id == admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot toggle your own administrative account active status."
        )
        
    user = db.query(User).filter(User.id == id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found."
        )
        
    user.is_active = not user.is_active
    db.commit()
    db.refresh(user)
    
    logger.info(f"Admin '{admin.email}' toggled user {user.email} status to: is_active={user.is_active}")
    return {
        "success": True,
        "message": f"Successfully toggled user {user.email} status.",
        "is_active": user.is_active
    }


@router.get(
    "/logs",
    response_model=List[LogLineResponse],
    summary="Get system logs (Admin only)",
    description="Retrieves a list of simulated server logs to inspect active platform threads."
)
async def get_logs(
    admin: User = Depends(get_admin_user)
) -> list:
    logger.info(f"Admin '{admin.email}' accessed server logs.")
    # Return simulated system logs to provide clear platform inspectability in the UI
    import datetime
    now = datetime.datetime.now()
    return [
        {
            "timestamp": (now - datetime.timedelta(minutes=15)).strftime("%Y-%m-%d %H:%M:%S"),
            "level": "INFO",
            "message": "Uvicorn server running on http://127.0.0.1:8000 (Press CTRL+C to quit)"
        },
        {
            "timestamp": (now - datetime.timedelta(minutes=14)).strftime("%Y-%m-%d %H:%M:%S"),
            "level": "INFO",
            "message": "Persistent ChromaDB vector store loaded at uploads/chroma_db/"
        },
        {
            "timestamp": (now - datetime.timedelta(minutes=10)).strftime("%Y-%m-%d %H:%M:%S"),
            "level": "INFO",
            "message": "Prompt templates loaded and cached. PromptManager cache count: 12"
        },
        {
            "timestamp": (now - datetime.timedelta(minutes=5)).strftime("%Y-%m-%d %H:%M:%S"),
            "level": "INFO",
            "message": "VLMService loaded Qwen2.5-VL-3B-Instruct model weights successfully on VRAM."
        },
        {
            "timestamp": now.strftime("%Y-%m-%d %H:%M:%S"),
            "level": "INFO",
            "message": f"Admin session authenticated for user: {admin.email} (Role: {admin.role})"
        }
    ]


@router.delete(
    "/document/{id}",
    summary="Purge abusive document (Admin only)",
    description="Deletes any document index and associated physical files from disk, bypassing normal user boundaries."
)
async def purge_document(
    id: str = Path(..., description="Document UUID string."),
    db: Session = Depends(get_db),
    admin: User = Depends(get_admin_user)
) -> dict:
    doc = db.query(Document).filter(Document.id == id).first()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found."
        )
        
    # Delete from relational database (cascades chunks, chats, embeddings)
    db.delete(doc)
    db.commit()
    
    # Try deleting physical files if present
    import glob
    from app.core.config import settings
    # PDFs
    pdf_pattern = os.path.join(settings.UPLOAD_PDFS_DIR, f"{id}.pdf")
    for f in glob.glob(pdf_pattern):
        try:
            os.remove(f)
        except OSError:
            pass
    # Images
    for ext in [".png", ".jpg", ".jpeg"]:
        img_pattern = os.path.join(settings.UPLOAD_IMAGES_DIR, f"{id}{ext}")
        for f in glob.glob(img_pattern):
            try:
                os.remove(f)
            except OSError:
                pass
                
    logger.warning(f"Admin '{admin.email}' purged document {id} (Filename: {doc.filename}) from platform database and disk.")
    return {
        "success": True,
        "message": f"Purged document '{doc.filename}' successfully."
    }
