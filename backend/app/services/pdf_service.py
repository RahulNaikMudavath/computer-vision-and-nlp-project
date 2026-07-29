import os
import time
import logging
import tempfile
from PIL import Image
from pdf2image import convert_from_path
from pdf2image.exceptions import PDFInfoNotInstalledError, PDFPageCountError, PDFSyntaxError
from app.core.config import settings
from app.services.vlm_service import vlm_service
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
            except PDFInfoNotInstalledError:
                logger.error("Poppler is not installed on the system or is missing from System PATH.")
                raise VLMInferenceException(
                    "Poppler dependency (system PDF converter) is missing. "
                    "Please ensure poppler is installed and configured in System PATH."
                )
            except (PDFPageCountError, PDFSyntaxError) as count_err:
                logger.error(f"Failed to read PDF pages: {str(count_err)}")
                if "encrypted" in str(count_err).lower() or "password" in str(count_err).lower():
                    raise InvalidPDFException("The uploaded PDF is encrypted/password-protected and cannot be processed.")
                else:
                    raise InvalidPDFException("The uploaded PDF is corrupted or invalid.")
            except Exception as ex:
                logger.error(f"Failed during PDF to image conversion: {str(ex)}")
                raise InvalidPDFException(f"Failed to convert PDF pages: {str(ex)}")
                
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
                        page_text = await vlm_service.perform_ocr(pil_image)
                        logger.info(f"Inference completed on page {page_num}.")
                        
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
                    logger.warning(f"Could not remove temporary directory '{temp_dir}': {str(dir_err)}")

# Instantiate PDFService singleton
pdf_service = PDFService()
