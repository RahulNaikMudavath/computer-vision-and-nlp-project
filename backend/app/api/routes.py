import os
import json
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse
from app.utils.helpers import is_allowed_file, save_upload_file
from app.services.ocr import perform_ocr, ask_question_about_document
from app.schemas.ocr_schema import OCRResponse, AskQuestionRequest, AskQuestionResponse

router = APIRouter(prefix="/api/ocr", tags=["OCR"])

UPLOAD_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../uploads"))

@router.post("/upload", response_model=OCRResponse)
async def upload_file(
    file: UploadFile = File(...),
    force_ai: bool = Form(False)
):
    """
    Upload a document (PDF or Image) and perform OCR on it.
    If force_ai is true and GEMINI_API_KEY is configured, it will use Gemini AI OCR.
    """
    if not is_allowed_file(file.filename):
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format. Supported formats: PDF, PNG, JPG, JPEG, TIFF, BMP"
        )
        
    try:
        # Save the uploaded file
        saved_path = save_upload_file(file, UPLOAD_DIR)
        file_id, _ = os.path.splitext(os.path.basename(saved_path))
        
        # Run OCR
        result = perform_ocr(saved_path, file.filename, force_ai=force_ai)
        
        if result["status"] == "error":
            raise HTTPException(status_code=500, detail=result["message"])
            
        # Cache text and complete result JSON to disk
        text_path = os.path.join(UPLOAD_DIR, f"{file_id}.txt")
        json_path = os.path.join(UPLOAD_DIR, f"{file_id}.json")
        
        with open(text_path, "w", encoding="utf-8") as f:
            f.write(result["text"])
            
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
            
        return OCRResponse(
            file_id=file_id,
            filename=file.filename,
            status=result["status"],
            text=result["text"],
            pages=result["pages"],
            message=result["message"]
        )
        
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"File upload and processing failed: {str(e)}")

@router.post("/qa", response_model=AskQuestionResponse)
async def ask_question(request: AskQuestionRequest):
    """
    Ask a question about a processed document using Gemini AI.
    Provide either a file_id to load cached text or pass raw text directly.
    """
    document_text = ""
    
    if request.file_id:
        text_path = os.path.join(UPLOAD_DIR, f"{request.file_id}.txt")
        if not os.path.exists(text_path):
            raise HTTPException(status_code=404, detail="Processed document not found.")
            
        with open(text_path, "r", encoding="utf-8") as f:
            document_text = f.read()
    elif request.text:
        document_text = request.text
    else:
        raise HTTPException(
            status_code=400,
            detail="Either file_id or text must be provided to perform Q&A."
        )
        
    if not document_text.strip():
        raise HTTPException(status_code=400, detail="Document text is empty.")
        
    answer = ask_question_about_document(document_text, request.question)
    return AskQuestionResponse(answer=answer)

@router.get("/download/{file_id}")
async def download_extracted_text(file_id: str):
    """Download the extracted plain text file."""
    text_path = os.path.join(UPLOAD_DIR, f"{file_id}.txt")
    if not os.path.exists(text_path):
        raise HTTPException(status_code=404, detail="Extracted text file not found.")
        
    # Find original filename if JSON metadata exists
    json_path = os.path.join(UPLOAD_DIR, f"{file_id}.json")
    original_name = f"{file_id}.txt"
    if os.path.exists(json_path):
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                metadata = json.load(f)
                orig_filename = metadata.get("filename", "")
                if orig_filename:
                    name_base, _ = os.path.splitext(orig_filename)
                    original_name = f"{name_base}_ocr.txt"
        except Exception:
            pass
            
    return FileResponse(
        path=text_path,
        media_type="text/plain",
        filename=original_name
    )

@router.get("/health")
async def health_check():
    """Endpoint to check API status and feature support."""
    has_gemini = os.getenv("GEMINI_API_KEY") is not None
    return {
        "status": "healthy",
        "features": {
            "gemini_ai_ocr": has_gemini,
            "gemini_document_qa": has_gemini,
            "local_tesseract_ocr": True
        }
    }
