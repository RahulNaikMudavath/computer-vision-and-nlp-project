import logging
import json
from fastapi import APIRouter, Depends, Path, HTTPException, status
from sqlalchemy.orm import Session

from app.models.database import get_db, User, Document, ChatHistory
from app.exceptions.handlers import DocumentNotFoundException
from app.core.security import get_current_user
from app.services.rag_service import rag_service
from app.services.vector_service import vector_service
from app.services.embedding_service import embedding_service
from app.schemas.rag_schema import (
    DocumentChatRequest,
    DocumentChatResponse,
    MultiDocumentChatRequest,
    DocumentMetadataResponse,
    ChunksListResponse,
    ChunkMetadataResponse,
    EmbeddingMetadataResponse
)

logger = logging.getLogger("document_ocr.api.rag_routes")

# Initialize modular RAG router
router = APIRouter(tags=["Document Chat & RAG"])

@router.post(
    "/document/chat",
    response_model=DocumentChatResponse,
    summary="Chat with Uploaded Document (RAG)",
    description=(
        "Ask natural language questions about the uploaded document based on its UUID. "
        "The system performs semantic search, fetches relevant context chunks, constructs "
        "a strict QA prompt, and uses the VLM model to answer based ONLY on the document context. Owner only."
    )
)
async def chat_with_document(
    request: DocumentChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> dict:
    logger.info(f"User '{current_user.email}' requested RAG chat for document '{request.document_id}'.")
    
    # 1. Enforce document ownership boundaries
    doc = db.query(Document).filter(
        Document.id == request.document_id,
        Document.uploaded_by == current_user.id
    ).first()
    if not doc:
        raise DocumentNotFoundException("Document not found or access denied.")
        
    # 2. Run chat pipeline
    chat_result = await rag_service.chat_with_document(
        document_id=request.document_id,
        question=request.question
    )
    
    # 3. Log Chat history in relational database
    try:
        chat_log = ChatHistory(
            document_id=request.document_id,
            user_id=current_user.id,
            question=request.question,
            answer=chat_result["answer"],
            sources=json.dumps(chat_result["sources"])
        )
        db.add(chat_log)
        db.commit()
    except Exception as ex:
        logger.warning(f"Failed to record relational RAG chat history: {str(ex)}")
        
    return chat_result


@router.post(
    "/documents/chat",
    response_model=DocumentChatResponse,
    summary="Chat with Multiple Uploaded Documents (Multi-RAG)",
    description=(
        "Ask natural language questions about multiple uploaded documents based on their UUID list. "
        "The system performs semantic search, fetches relevant context chunks, constructs "
        "a strict QA prompt, and uses the VLM model to answer. Owner only for all documents."
    )
)
async def chat_with_multiple_documents(
    request: MultiDocumentChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> dict:
    logger.info(f"User '{current_user.email}' requested Multi-RAG chat for documents {request.document_ids}.")
    
    # 1. Enforce document ownership boundaries for all documents
    docs = db.query(Document).filter(
        Document.id.in_(request.document_ids),
        Document.uploaded_by == current_user.id
    ).all()
    
    if len(docs) != len(request.document_ids):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. One or more documents do not belong to you or do not exist."
        )
        
    # 2. Run multi-chat pipeline
    chat_result = await rag_service.chat_with_multiple_documents(
        db=db,
        document_ids=request.document_ids,
        question=request.question
    )
    
    # 3. Log Chat history in relational database (leaving document_id as None/Null)
    try:
        chat_log = ChatHistory(
            document_id=None,
            user_id=current_user.id,
            question=request.question,
            answer=chat_result["answer"],
            sources=json.dumps(chat_result["sources"])
        )
        db.add(chat_log)
        db.commit()
    except Exception as ex:
        logger.warning(f"Failed to record relational RAG multi-chat history: {str(ex)}")
        
    return chat_result



@router.get(
    "/document/{id}",
    response_model=DocumentMetadataResponse,
    summary="Get Document Metadata & Index Status",
    description="Locates the uploaded document by UUID and returns file info, format, size, and whether it has been indexed. Owner only."
)
async def get_document_metadata(
    id: str = Path(..., description="The unique UUID of the uploaded document."),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> dict:
    logger.info(f"Metadata lookup requested by '{current_user.email}' for document ID: '{id}'")
    
    # Enforce ownership boundaries
    doc = db.query(Document).filter(
        Document.id == id,
        Document.uploaded_by == current_user.id
    ).first()
    if not doc:
        raise DocumentNotFoundException("Document not found or access denied.")
        
    # Check if indexed in Vector store
    is_indexed = vector_service.is_document_indexed(id)
    chunk_count = 0
    if is_indexed:
        chunks = vector_service.get_document_chunks(id)
        chunk_count = len(chunks)
        
    from app.utils.helpers import format_size
    return {
        "document_id": id,
        "filename": doc.original_filename,
        "file_type": doc.file_type,
        "size": format_size(doc.size_bytes),
        "indexed": is_indexed,
        "chunk_count": chunk_count
    }


@router.get(
    "/document/{id}/chunks",
    response_model=ChunksListResponse,
    summary="Retrieve Indexed Document Chunks",
    description="Returns a list of all raw text chunks and corresponding page numbers indexed for the specified document ID. Owner only."
)
async def get_document_chunks(
    id: str = Path(..., description="The unique UUID of the uploaded document."),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> dict:
    logger.info(f"Chunks list requested by '{current_user.email}' for document ID: '{id}'")
    
    # Enforce ownership boundaries
    doc = db.query(Document).filter(
        Document.id == id,
        Document.uploaded_by == current_user.id
    ).first()
    if not doc:
        raise DocumentNotFoundException("Document not found or access denied.")
        
    # Retrieve indexed chunks from database
    chunks = vector_service.get_document_chunks(id)
    
    formatted_chunks = [
        ChunkMetadataResponse(
            page=c["metadata"]["page"],
            chunk_index=c["metadata"]["chunk_index"],
            text=c["text"]
        )
        for c in chunks
    ]
    
    return {
        "success": True,
        "document_id": id,
        "chunks": formatted_chunks
    }


@router.get(
    "/document/{id}/embeddings",
    response_model=EmbeddingMetadataResponse,
    summary="Get Document Embeddings Info",
    description="Returns metadata about the embedding vectors generated for the document, including model name and output dimensions. Owner only."
)
async def get_document_embeddings_info(
    id: str = Path(..., description="The unique UUID of the uploaded document."),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> dict:
    logger.info(f"Embedding stats requested by '{current_user.email}' for document ID: '{id}'")
    
    # Enforce ownership boundaries
    doc = db.query(Document).filter(
        Document.id == id,
        Document.uploaded_by == current_user.id
    ).first()
    if not doc:
        raise DocumentNotFoundException("Document not found or access denied.")
        
    # Check indexing state
    is_indexed = vector_service.is_document_indexed(id)
    chunk_count = 0
    if is_indexed:
        chunks = vector_service.get_document_chunks(id)
        chunk_count = len(chunks)
        
    return {
        "success": True,
        "document_id": id,
        "model": embedding_service.model_name,
        "dimension": embedding_service.dimension,
        "chunk_count": chunk_count
    }
