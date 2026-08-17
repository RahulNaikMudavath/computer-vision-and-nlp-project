import os
import logging
from typing import List, Dict, Any, Tuple
import fitz  # PyMuPDF
from PIL import Image
import pytesseract

logger = logging.getLogger(__name__)

import warnings
try:
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=FutureWarning)
        import google.generativeai as genai
    _HAS_GEMINI_SDK = True
except ImportError:
    genai = None
    _HAS_GEMINI_SDK = False
    logger.warning("google-generativeai SDK not installed. Gemini OCR and Q&A are unavailable.")

# Configure Gemini API if available
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_API_KEY and _HAS_GEMINI_SDK:
    genai.configure(api_key=GEMINI_API_KEY)
    logger.info("Gemini API configured for enhanced OCR and Q&A.")
else:
    if GEMINI_API_KEY and not _HAS_GEMINI_SDK:
        logger.warning("Gemini API key is provided, but google-generativeai SDK is not installed.")
    else:
        logger.warning("GEMINI_API_KEY not found in environment or not configured. Fallback OCR will be used.")

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

def generate_content_sync_with_fallback(contents) -> Any:
    from google.api_core import exceptions as google_exceptions
    candidate_models = ["gemini-3.5-flash", "gemini-3.6-flash", "gemini-3.7-flash", "gemini-3.5-flash-lite"]
    last_error = None
    for model_name in candidate_models:
        try:
            logger.info(f"Attempting sync inference with Gemini model: {model_name}")
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(contents)
            return response
        except (google_exceptions.ResourceExhausted, google_exceptions.ClientError) as err:
            logger.warning(f"Gemini model {model_name} failed (error/quota): {str(err)}. Retrying with next candidate...")
            last_error = err
        except Exception as err:
            logger.warning(f"Gemini model {model_name} encountered error: {str(err)}. Retrying with next candidate...")
            last_error = err
    raise last_error

def extract_text_gemini(file_path: str, mime_type: str) -> List[Tuple[int, str]]:
    """Use Gemini Multimodal Model to perform high-accuracy OCR."""
    if not GEMINI_API_KEY:
        raise ValueError("Gemini API key is not configured.")
        
    pages_text = []
    try:
        # If it's a PDF, we can upload it or convert pages to images
        if mime_type == "application/pdf":
            doc = fitz.open(file_path)
            for i, page in enumerate(doc):
                pix = page.get_pixmap(dpi=150)
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                
                # Ask Gemini to transcribe the image
                response = generate_content_sync_with_fallback([
                    "You are an expert OCR engine. Transcribe all text from this page image exactly as it appears. Do not summarize, do not add commentary.",
                    img
                ])
                pages_text.append((i + 1, response.text.strip()))
            doc.close()
        else:
            # It's an image
            img = Image.open(file_path)
            response = generate_content_sync_with_fallback([
                "You are an expert OCR engine. Transcribe all text from this document image exactly as it appears. Do not summarize, do not add commentary.",
                img
            ])
            pages_text.append((1, response.text.strip()))
            
    except Exception as e:
        logger.error(f"Failed to perform Gemini OCR: {str(e)}")
        pages_text.append((1, f"[Error processing PDF pages: {str(e)}]"))
    return pages_text

def perform_ocr(file_path: str, mime_type: str) -> Dict[str, Any]:
    """
    Main entry point for standalone OCR. Runs Gemini OCR if API key is present,
    else falls back to local Tesseract OCR.
    """
    if GEMINI_API_KEY and _HAS_GEMINI_SDK:
        logger.info(f"Running high-accuracy Gemini OCR for file: {file_path}")
        pages = extract_text_gemini(file_path, mime_type)
        full_text = "\n\n".join([p[1] for p in pages])
        return {
            "success": True,
            "text": full_text,
            "pages": [{"page": p[0], "text": p[1]} for p in pages],
            "message": "OCR successfully completed using Gemini Multimodal API."
        }
    else:
        logger.info(f"Running local Tesseract OCR for file: {file_path}")
        try:
            if mime_type == "application/pdf":
                pages = extract_text_from_pdf_scanned(file_path)
            else:
                img = Image.open(file_path)
                text = extract_text_from_image_local(img)
                pages = [(1, text)]
            full_text = "\n\n".join([p[1] for p in pages])
            return {
                "success": True,
                "text": full_text,
                "pages": [{"page": p[0], "text": p[1]} for p in pages],
                "message": "OCR completed using local Tesseract engine."
            }
        except Exception as e:
            logger.error(f"Local Tesseract OCR failed: {str(e)}")
            return {
                "success": False,
                "text": "",
                "pages": [],
                "message": f"Failed to perform OCR: {str(e)}"
            }

def ask_question_about_document(document_text: str, question: str) -> str:
    """Answer a user query about the extracted document text using Gemini."""
    if not GEMINI_API_KEY:
        return "Gemini API key is not configured on the backend. Please add GEMINI_API_KEY to your .env file to enable document Q&A."
        
    try:
        prompt = f"""
You are a helpful document assistant. Answer the user's question using the provided document text and your general knowledge.
If the answer cannot be found explicitly in the document, make a reasonable inference or provide a helpful answer based on general knowledge.

Document Text:
---
{document_text}
---

User Question: {question}
"""
        response = generate_content_sync_with_fallback(prompt)
        return response.text.strip()
    except Exception as e:
        logger.error(f"Gemini Q&A failed: {e}")
        return f"Error answering question: {str(e)}"
