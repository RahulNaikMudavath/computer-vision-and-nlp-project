import os
import logging
from contextlib import asynccontextmanager
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.routes.ocr import router as api_router
from app.api.routes.pdf_routes import router as pdf_router
from app.api.routes.document_routes import router as document_router
from app.api.routes.rag_routes import router as rag_router
from app.api.routes.auth import router as auth_router
from app.api.routes.admin import router as admin_router
from app.api.routes.websocket import router as websocket_router
from app.api.routes.monitoring import router as monitoring_router
from app.core.logging_middleware import StructuredLoggingMiddleware
from app.models.database import Base, engine
from app.services.vlm_service import vlm_service
from app.services.prompt_manager import prompt_manager
from app.services.vector_service import vector_service
from app.services.websocket_manager import websocket_manager
from app.exceptions.handlers import (
    ImageUploadException,
    InvalidFileExtensionException,
    FileTooLargeException,
    InvalidImageException,
    InvalidPDFException,
    DocumentNotFoundException,
    VLMInferenceException,
    VLMModelLoadingException,
    image_upload_exception_handler,
    invalid_file_extension_handler,
    file_too_large_handler,
    invalid_image_handler,
    invalid_pdf_handler,
    document_not_found_handler,
    vlm_inference_handler,
    vlm_model_loading_handler,
    cuda_oom_handler,
)

# Configure logging system
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("document_ocr")

# Define lifespan event handler for model loading and directory setup
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan events coordinator:
      1. Ensures the output upload directories exist.
      2. Loads the Qwen2.5-VL-3B-Instruct model once into memory on startup.
      3. Launches the background Redis Pub/Sub listener for WebSockets.
    """
    logger.info("Starting up FastAPI application...")
    
    # 1. Automatically create upload directories and database tables
    try:
        os.makedirs(settings.UPLOAD_IMAGES_DIR, exist_ok=True)
        logger.info(f"Verified upload directory: {settings.UPLOAD_IMAGES_DIR}")
        os.makedirs(settings.UPLOAD_PDFS_DIR, exist_ok=True)
        logger.info(f"Verified upload directory: {settings.UPLOAD_PDFS_DIR}")
        os.makedirs(settings.UPLOAD_CHROMA_DIR, exist_ok=True)
        logger.info(f"Verified vector db directory: {settings.UPLOAD_CHROMA_DIR}")
        
        # Create database tables (SQLite/PostgreSQL)
        logger.info("Verifying database schema. Standard schema creation active as fallback...")
        from sqlalchemy import text
        try:
            with engine.connect() as conn:
                res = conn.execute(text("PRAGMA table_info(chat_history);")).fetchall()
                if res:
                    for col in res:
                        if col[1] == "document_id" and col[3] == 1:
                            logger.info("Outdated schema detected: dropping chat_history to apply nullable=True column updates...")
                            conn.execute(text("DROP TABLE chat_history;"))
                            conn.commit()
                            break
        except Exception as e:
            logger.warning(f"Schema pre-check skipped: {str(e)}")
            
        Base.metadata.create_all(bind=engine)
        logger.info("Database initialized. (Note: Use Alembic migrations in production environment: 'alembic upgrade head')")
        
        # Initialize persistent ChromaDB vector store
        vector_service.initialize_store()
    except Exception as e:
        logger.error(f"Failed to create upload directories, database, or initialize VectorDB: {str(e)}")
    
    # 2. Load prompt templates and VLM model only when explicitly enabled.
    # This keeps local auth/login flows available even when the heavyweight model download or GPU setup fails.
    try:
        prompt_manager.load_prompts()
        if settings.MOCK_VLM:
            logger.info("MOCK_VLM is enabled. Skipping VLM model loading during startup.")
        else:
            vlm_service.load_model()
    except Exception as e:
        logger.warning(f"Startup skipped VLM model initialization because it failed: {str(e)}")

    # 3. Start Redis Pub/Sub WebSockets background task
    import asyncio
    listener_task = asyncio.create_task(websocket_manager.start_redis_listener())
    websocket_manager.listener_task = listener_task
    logger.info("WebSocket Redis Pub/Sub background listener started.")
        
    yield
    
    # Clean up background tasks on shutdown
    if websocket_manager.listener_task:
        websocket_manager.listener_task.cancel()
        logger.info("WebSocket Redis Pub/Sub background listener stopped.")
    logger.info("Shutting down FastAPI application...")

# Initialize FastAPI application
app = FastAPI(
    title="Document OCR & Image Upload API",
    description="FastAPI Backend for Document OCR Setup and Image Upload API with Size and Type Validations.",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS Middleware to allow requests from any origin (ideal for local development)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add JSON structured logging middleware
app.add_middleware(StructuredLoggingMiddleware)

# Register custom exception handlers for robust API error responses
app.add_exception_handler(InvalidFileExtensionException, invalid_file_extension_handler)
app.add_exception_handler(FileTooLargeException, file_too_large_handler)
app.add_exception_handler(InvalidImageException, invalid_image_handler)
app.add_exception_handler(InvalidPDFException, invalid_pdf_handler)
app.add_exception_handler(DocumentNotFoundException, document_not_found_handler)
app.add_exception_handler(VLMInferenceException, vlm_inference_handler)
app.add_exception_handler(VLMModelLoadingException, vlm_model_loading_handler)
app.add_exception_handler(ImageUploadException, image_upload_exception_handler)

# Register CUDA Out Of Memory exception handler if PyTorch is loaded
if cuda_oom_handler is not None:
    try:
        import torch
        app.add_exception_handler(torch.cuda.OutOfMemoryError, cuda_oom_handler)
        logger.info("Registered CUDA OutOfMemory exception handler.")
    except Exception as ex:
        logger.warning(f"Could not register CUDA OOM exception handler: {str(ex)}")

# Include modular routing definitions
app.include_router(monitoring_router)
app.include_router(websocket_router)
app.include_router(auth_router)
app.include_router(api_router)
app.include_router(pdf_router)
app.include_router(document_router)
app.include_router(rag_router)
app.include_router(admin_router)

# Run the FastAPI server directly if executed as the main script
if __name__ == "__main__":
    import uvicorn
    logger.info("Launching server via Uvicorn...")
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
