import os
import time
import logging
import asyncio
from PIL import Image, UnidentifiedImageError
from celery.utils.log import get_task_logger

from app.tasks.celery_app import celery_app
from app.models.database import SessionLocal, Document, DocumentChunk
from app.services.websocket_manager import websocket_manager
from app.services.pdf_service import pdf_service
from app.services.vlm_service import vlm_service
from app.services.document_service import document_service
from app.services.chunk_service import chunk_service
from app.services.vector_service import vector_service

logger = get_task_logger("document_ocr.celery_worker")

@celery_app.task(name="tasks.process_document_pipeline")
def process_document_pipeline_task(document_id: str, file_path: str, original_filename: str, user_id: int):
    """
    Celery task that executes the complete asynchronous pipeline:
    OCR Transcription -> Structured Field Extraction -> Text Chunking -> Vector Embeddings -> DB indexing.
    """
    logger.info(f"Celery task started: Analyzing Document ID: '{document_id}', Filename: '{original_filename}', User: {user_id}")
    
    # 1. Publish start status
    websocket_manager.publish_progress(
        user_id=user_id,
        document_id=document_id,
        status="UPLOAD_STARTED",
        progress=10,
        message="Document uploaded. Commencing asynchronous scanning pipeline..."
    )
    
    db = SessionLocal()
    try:
        db_doc = db.query(Document).filter(Document.id == document_id).first()
        if not db_doc:
            logger.error(f"Document ID '{document_id}' not found in database.")
            return False
            
        file_ext = os.path.splitext(file_path)[1].lower().replace(".", "")
        ocr_text = ""
        pages = []
        
        # 2. PDF Conversion & OCR phase
        if file_ext == "pdf":
            websocket_manager.publish_progress(
                user_id=user_id,
                document_id=document_id,
                status="PDF_CONVERSION",
                progress=30,
                message="Converting and processing PDF pages at 300 DPI..."
            )
            
            pdf_res = asyncio.run(pdf_service.process_pdf_ocr(file_path))
            ocr_text = pdf_res["full_text"]
            for item in pdf_res.get("results", []):
                pages.append({"page": item["page"], "text": item["text"]})
        else:
            websocket_manager.publish_progress(
                user_id=user_id,
                document_id=document_id,
                status="OCR_PROGRESS",
                progress=40,
                message="Transcribing image contents using Vision Language Model..."
            )
            try:
                with Image.open(file_path) as pil_image:
                    ocr_text = asyncio.run(vlm_service.perform_ocr(pil_image))
                    pages.append({"page": 1, "text": ocr_text})
            except (UnidentifiedImageError, OSError) as e:
                logger.error(f"Image load failure: {str(e)}")
                raise ValueError("Uploaded file is corrupted or not a valid image.")
                
        # 3. Structured Data Extraction
        websocket_manager.publish_progress(
            user_id=user_id,
            document_id=document_id,
            status="OCR_PROGRESS",
            progress=60,
            message="Classifying document type and running structured extraction..."
        )
        analysis_res = asyncio.run(document_service.analyze_document(ocr_text, original_filename))
        
        # Cache the extracted JSON data
        from app.services.cache_service import cache_service
        cache_service.set_json(f"doc:json:{document_id}", analysis_res["data"])
        
        # 4. Chunking & Embeddings generation
        websocket_manager.publish_progress(
            user_id=user_id,
            document_id=document_id,
            status="EMBEDDING_PROGRESS",
            progress=80,
            message="Splitting text into semantic chunks and generating vector embeddings..."
        )
        chunks = chunk_service.split_pages(pages)
        for c in chunks:
            chunk_row = DocumentChunk(
                document_id=document_id,
                page_number=c["metadata"]["page"],
                chunk_index=c["metadata"]["chunk_index"],
                text_content=c["text"]
            )
            db.add(chunk_row)
            
        # Index in vector store ChromaDB
        vector_service.add_document_chunks(document_id, chunks)
        
        # 5. DB Commit & Complete
        db_doc.ocr_status = "COMPLETED"
        db_doc.processing_status = "COMPLETED"
        db_doc.ocr_text = ocr_text
        db_doc.document_type = analysis_res["document_type"]
        db_doc.confidence_score = analysis_res["confidence"]
        db.commit()
        
        # 6. Broadcast completed state
        websocket_manager.publish_progress(
            user_id=user_id,
            document_id=document_id,
            status="COMPLETED",
            progress=100,
            message="Document indexing completed! Structured workspace is ready."
        )
        logger.info(f"Celery task success: Document ID '{document_id}' processed.")
        return True
        
    except Exception as ex:
        logger.error(f"Celery pipeline failure on Document '{document_id}': {str(ex)}")
        try:
            db_doc = db.query(Document).filter(Document.id == document_id).first()
            if db_doc:
                db_doc.ocr_status = "FAILED"
                db_doc.processing_status = "FAILED"
                db.commit()
        except Exception as db_ex:
            logger.error(f"Failed to record FAILED status on database: {str(db_ex)}")
            
        websocket_manager.publish_progress(
            user_id=user_id,
            document_id=document_id,
            status="FAILED",
            progress=100,
            message=f"Analysis pipeline crashed: {str(ex)}"
        )
        return False
    finally:
        db.close()
