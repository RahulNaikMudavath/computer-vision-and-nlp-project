import os
import time
import logging
import tempfile
import fitz  # PyMuPDF
from PIL import Image
from pdf2image import convert_from_path
from pdf2image.exceptions import PDFInfoNotInstalledError, PDFPageCountError, PDFSyntaxError
from app.core.config import settings
from app.services.vlm_service import vlm_service
from app.services.ocr import extract_text_from_pdf_scanned, extract_text_from_image_local
from app.exceptions.handlers import InvalidPDFException, VLMInferenceException

logger = logging.getLogger("document_ocr.pdf_service")

class PDFService:
    """
    Service managing PDF loading, Poppler page conversion at 300 DPI,
    sequential Vision OCR, and instant temp files cleanup.
    """
    async def process_pdf_ocr(self, pdf_path: str) -> dict:
        """
        Loads a PDF from the disk, splits it into high-resolution 300 DPI page images,
        iteratively transcribes the pages via VLM, and aggregates results.
        
        Returns:
            dict: {
                "pages": int (total page count),
                "results": list (page results list),
                "full_text": str (concatenated document text)
            }
        """
        # Create a temp folder within uploads/ to host intermediate PNG pages
        temp_dir = tempfile.mkdtemp(dir=settings.UPLOAD_DIR)
        logger.info(f"Temporary output directory created for PDF pages: {temp_dir}")
        
        try:
            start_time = time.time()
            logger.info(f"Converting PDF '{pdf_path}' to images at 300 DPI (Disk-safe stream mode)...")
            
            # Run pdf2image conversion. 
            # paths_only=True writes images to disk and returns file paths, avoiding RAM spikes.
            try:
                image_paths = convert_from_path(
                    pdf_path,
                    dpi=300,
                    output_folder=temp_dir,
                    fmt="png",
                    paths_only=True
                )
            except PDFInfoNotInstalledError as poppler_err:
                logger.warning(
                    "Poppler is not installed or not available in PATH. Falling back to PyMuPDF/VLM PDF OCR."
                )
                return await self._process_pdf_with_fitz_fallback(pdf_path)
            except (PDFPageCountError, PDFSyntaxError) as count_err:
                logger.error(f"Failed to read PDF pages: {str(count_err)}")
                if "encrypted" in str(count_err).lower() or "password" in str(count_err).lower():
                    raise InvalidPDFException("The uploaded PDF is encrypted/password-protected and cannot be processed.")
                else:
                    logger.warning(
                        "PDF conversion failed, falling back to PyMuPDF/VLM PDF OCR."
                    )
                    return await self._process_pdf_with_fitz_fallback(pdf_path)
            except Exception as ex:
                logger.warning(
                    "Failed during PDF to image conversion: %s. Falling back to PyMuPDF/VLM PDF OCR.",
                    str(ex)
                )
                return await self._process_pdf_with_fitz_fallback(pdf_path)
                
            total_pages = len(image_paths)
            logger.info(f"PDF split complete. Total pages: {total_pages}")
            
            if total_pages == 0:
                raise InvalidPDFException("The uploaded PDF document contains no readable pages.")
            
            results = []
            full_text_parts = []
            
            # Loop sequentially through the page paths
            # Sequential design allows adding parallel threads/queues easily later.
            for i, img_path in enumerate(image_paths):
                page_num = i + 1
                logger.info(f"Processing page {page_num} of {total_pages}...")
                
                try:
                    # Load image file from disk and execute VLM character scanner
                    with Image.open(img_path) as pil_image:
                        logger.info(f"Inference started on page {page_num}...")
                        try:
                            page_text = await vlm_service.perform_ocr(pil_image)
                        except Exception as ocr_err:
                            logger.warning(
                                "VLM OCR failed for PDF page %d. Falling back to local text extraction: %s",
                                page_num,
                                str(ocr_err)
                            )
                            if pil_image.mode != "RGB":
                                pil_image = pil_image.convert("RGB")
                            page_text = extract_text_from_image_local(pil_image)
                        
                        results.append({
                            "page": page_num,
                            "text": page_text
                        })
                        full_text_parts.append(page_text)
                finally:
                    # Clean up individual page image immediately to free local disk space
                    if os.path.exists(img_path):
                        try:
                            os.remove(img_path)
                            logger.info(f"Deleted temporary page file: {img_path}")
                        except OSError as io_err:
                            logger.warning(f"Could not delete temporary page image '{img_path}': {str(io_err)}")
            
            full_text = "\n\n--- Page Break ---\n\n".join(full_text_parts)
            elapsed_time = time.time() - start_time
            logger.info(f"Processed PDF document OCR in {elapsed_time:.2f} seconds.")
            
            return {
                "pages": total_pages,
                "results": results,
                "full_text": full_text
            }
        finally:
            # Clear out the temporary subdirectory after parsing is complete
            if os.path.exists(temp_dir):
                try:
                    os.rmdir(temp_dir)
                    logger.info(f"Removed temporary directory: {temp_dir}")
                except OSError as dir_err:
                    logger.warning(f"Could not remove temporary directory '%s': %s", temp_dir, str(dir_err))
        
    async def _process_pdf_with_fitz_fallback(self, pdf_path: str) -> dict:
        """
        Fall back to PyMuPDF page rendering and VLM OCR when pdf2image / Poppler is unavailable.
        """
        logger.info("Starting PDF OCR fallback via PyMuPDF and VLM OCR.")
        results = []
        full_text_parts = []
        try:
            doc = fitz.open(pdf_path)
            for i, page in enumerate(doc):
                page_num = i + 1
                # Render page to a pixmap (image)
                pix = page.get_pixmap(dpi=150)
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                
                try:
                    page_text = await vlm_service.perform_ocr(img)
                except Exception as ocr_err:
                    logger.warning(
                        "VLM OCR fallback failed for page %d. Falling back to local Tesseract OCR: %s",
                        page_num,
                        str(ocr_err)
                    )
                    page_text = extract_text_from_image_local(img)
                
                results.append({
                    "page": page_num,
                    "text": page_text
                })
                full_text_parts.append(page_text)
            doc.close()
        except Exception as e:
            logger.error(f"Error in fitz fallback PDF extraction: {e}")
            raise InvalidPDFException(
                f"PDF OCR fallback failed: {str(e)}"
            )

        full_text = "\n\n".join([
            f"--- Page {page_num} ---\n{text}" for page_num, text in zip(range(1, len(results) + 1), full_text_parts)
        ])

        return {
            "pages": len(results),
            "results": results,
            "full_text": full_text
        }

# Instantiate PDFService singleton
pdf_service = PDFService()
