import time
import logging
from fastapi import APIRouter, UploadFile, File
from app.core.config import settings
from app.utils.helpers import save_pdf_securely
from app.services.pdf_service import pdf_service
from app.schemas.pdf_schema import PDFOCRResponse

logger = logging.getLogger("document_ocr.api.pdf_routes")

# Initialize modular pdf router
router = APIRouter()

@router.post(
    "/ocr/pdf",
    response_model=PDFOCRResponse,
    summary="Perform OCR on PDF Document",
    description=(
        "Upload a PDF document (up to 50 MB) via multipart/form-data. "
        "The endpoint validates the document format, saves it, converts it page-by-page "
        "at 300 DPI, and runs the Qwen2.5-VL VLM model sequentially on each page to extract all text."
    )
)
async def ocr_pdf(file: UploadFile = File(..., description="The PDF document file to process.")) -> dict:
    """
    Receives a PDF, validates its mime type and file size, saves it locally under uploads/pdfs/,
    splits it into pages, transcribes each page with Qwen2.5-VL, and combines the text.
    """
    logger.info(f"Received PDF OCR request. Filename: '{file.filename}', Content Type: '{file.content_type}'")
    
    # 1. Save and validate the PDF file (max 50MB, application/pdf only)
    saved_pdf_path = await save_pdf_securely(file, settings.UPLOAD_PDFS_DIR)
    logger.info(f"PDF saved securely to disk path: {saved_pdf_path}")
    
    # 2. Run PDF-to-images & VLM OCR pipeline
    start_time = time.time()
    logger.info("Initializing PDF OCR processing pipeline...")
    
    process_result = await pdf_service.process_pdf_ocr(saved_pdf_path)
    
    processing_time_sec = time.time() - start_time
    logger.info(f"Successfully finished PDF processing for file '{file.filename}' in {processing_time_sec:.2f} seconds.")
    
    # 3. Formulate and return structured API response
    return {
        "success": True,
        "filename": file.filename,
        "pages": process_result["pages"],
        "processing_time": f"{processing_time_sec:.2f}s",
        "model": "Qwen2.5-VL-3B-Instruct",
        "results": process_result["results"],
        "full_text": process_result["full_text"]
    }
