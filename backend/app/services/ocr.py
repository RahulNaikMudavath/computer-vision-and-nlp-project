import os
import logging
from typing import List, Dict, Any, Tuple
import fitz  # PyMuPDF
from PIL import Image
import pytesseract
import google.generativeai as genai

logger = logging.getLogger(__name__)

# Configure Gemini API if available
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    logger.info("Gemini API configured for enhanced OCR and Q&A.")
else:
    logger.warning("GEMINI_API_KEY not found in environment. Fallback OCR will be used.")

def extract_text_from_pdf_digital(file_path: str) -> List[Tuple[int, str]]:
    """Extract text from digital PDF pages using PyMuPDF."""
    pages_text = []
    try:
        doc = fitz.open(file_path)
        for i, page in enumerate(doc):
            text = page.get_text()
            pages_text.append((i + 1, text.strip()))
        doc.close()
    except Exception as e:
        logger.error(f"Error in digital PDF extraction: {e}")
    return pages_text

def extract_text_from_image_local(image: Image.Image) -> str:
    """Extract text from a PIL Image using Tesseract OCR, with graceful fallback."""
    try:
        return pytesseract.image_to_string(image).strip()
    except pytesseract.TesseractNotFoundError:
        logger.warning("Tesseract binary not found on this system. Local image OCR skipped.")
        return "[Error: Tesseract OCR is not installed on the system host. Please set a GEMINI_API_KEY in the backend .env to use cloud-based AI OCR, or install Tesseract-OCR locally.]"
    except Exception as e:
        logger.error(f"Tesseract OCR error: {e}")
        return f"[Error processing image: {str(e)}]"

def extract_text_from_pdf_scanned(file_path: str) -> List[Tuple[int, str]]:
    """Convert PDF pages to images and run local Tesseract OCR on them."""
    pages_text = []
    try:
        doc = fitz.open(file_path)
        for i, page in enumerate(doc):
            # Render page to a pixmap (image)
            pix = page.get_pixmap(dpi=150)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            text = extract_text_from_image_local(img)
            pages_text.append((i + 1, text))
        doc.close()
    except Exception as e:
        logger.error(f"Error in scanned PDF extraction: {e}")
        pages_text.append((1, f"[Error processing PDF pages: {str(e)}]"))
    return pages_text

def extract_text_gemini(file_path: str, mime_type: str) -> List[Tuple[int, str]]:
    """Use Gemini Multimodal Model to perform high-accuracy OCR."""
    if not GEMINI_API_KEY:
        raise ValueError("Gemini API key is not configured.")
        
    pages_text = []
    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        
        # If it's a PDF, we can upload it or convert pages to images
        if mime_type == "application/pdf":
            doc = fitz.open(file_path)
            for i, page in enumerate(doc):
                pix = page.get_pixmap(dpi=150)
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                
                # Ask Gemini to transcribe the image
                response = model.generate_content([
                    "You are an expert OCR engine. Transcribe all text from this page image exactly as it appears. Do not summarize, do not add commentary.",
                    img
                ])
                pages_text.append((i + 1, response.text.strip()))
            doc.close()
        else:
            # It's an image
            img = Image.open(file_path)
            response = model.generate_content([
                "You are an expert OCR engine. Transcribe all text from this document image exactly as it appears. Do not summarize, do not add commentary.",
                img
            ])
            pages_text.append((1, response.text.strip()))
            
    except Exception as e:
        logger.error(f"Gemini OCR extraction failed: {e}")
        raise e
        
    return pages_text

def perform_ocr(file_path: str, filename: str, force_ai: bool = False) -> Dict[str, Any]:
    """
    Orchestrate OCR processing:
    1. For PDFs: Try digital extraction first. If it yields very little/no text, do scanned OCR.
    2. For Images: Run image OCR.
    If GEMINI_API_KEY is available and force_ai is True, use Gemini OCR.
    """
    _, ext = os.path.splitext(filename.lower())
    mime_type = "application/pdf" if ext == ".pdf" else "image/png"  # general fallback
    
    pages = []
    use_ai = force_ai and GEMINI_API_KEY
    
    try:
        if use_ai:
            logger.info("Using AI OCR (Gemini)")
            pages = extract_text_gemini(file_path, mime_type)
        else:
            if ext == ".pdf":
                # Digital extraction
                pages = extract_text_from_pdf_digital(file_path)
                
                # Check if we got any real text. If empty, fall back to Tesseract OCR
                total_text_length = sum(len(txt) for _, txt in pages)
                if total_text_length < 50:
                    logger.info("Digital PDF text extraction yielded very little content. Falling back to scanned OCR.")
                    pages = extract_text_from_pdf_scanned(file_path)
            else:
                # Image
                img = Image.open(file_path)
                text = extract_text_from_image_local(img)
                pages = [(1, text)]
                
        # Format the response
        page_results = [{"page_num": p[0], "text": p[1]} for p in pages]
        full_text = "\n\n--- Page {} ---\n\n".join([p[1] for p in pages]) # format string
        # Actually join them cleanly
        full_text = "\n\n".join([f"--- Page {p[0]} ---\n{p[1]}" for p in pages])
        
        return {
            "status": "success",
            "text": full_text,
            "pages": page_results,
            "message": "OCR Completed successfully." + (" (AI-Powered)" if use_ai else " (Local engine)")
        }
    except Exception as e:
        logger.error(f"OCR orchestration failed: {e}")
        return {
            "status": "error",
            "text": "",
            "pages": [],
            "message": f"Failed to perform OCR: {str(e)}"
        }

def ask_question_about_document(document_text: str, question: str) -> str:
    """Answer a user query about the extracted document text using Gemini."""
    if not GEMINI_API_KEY:
        return "Gemini API key is not configured on the backend. Please add GEMINI_API_KEY to your .env file to enable document Q&A."
        
    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        prompt = f"""
You are a helpful document assistant. Answer the user's question based strictly on the provided document text. 
If the answer cannot be found in the document, reply: "I couldn't find the answer in the document."

Document Text:
---
{document_text}
---

User Question: {question}
"""
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        logger.error(f"Gemini Q&A failed: {e}")
        return f"Error answering question: {str(e)}"
