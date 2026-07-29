import os
import io
import time
import logging
from fastapi import APIRouter, UploadFile, File
from PIL import Image, UnidentifiedImageError
from app.core.config import settings
from app.utils.helpers import save_image_securely, read_and_validate_image_file
from app.services.vlm_service import vlm_service
from app.exceptions.handlers import InvalidImageException
from app.schemas.vlm_schema import VLMOCRResponse
from pydantic import BaseModel, Field

logger = logging.getLogger("document_ocr.api.ocr")

# Setup routing
router = APIRouter()

# Schema definitions for Swagger UI/OpenAPI
class ProjectStatusResponse(BaseModel):
    project: str = Field(
        default="Document OCR using Vision Language Model",
        description="The name of the project."
    )
    version: str = Field(
        default="1.0.0",
        description="The semantic version of the application."
    )
    status: str = Field(
        default="Running",
        description="The current operational status of the server."
    )

class ImageUploadSuccessResponse(BaseModel):
    success: bool = Field(
        default=True,
        description="Indicates whether the upload process was successful."
    )
    message: str = Field(
        default="Image uploaded successfully",
        description="A confirmation message."
    )
    filename: str = Field(
        ...,
        description="The unique, UUID-generated filename of the saved image."
    )
    filepath: str = Field(
        ...,
        description="The absolute local file path where the image is stored."
    )
    size: str = Field(
        ...,
        description="The human-readable size of the saved image file."
    )
    content_type: str = Field(
        ...,
        description="The validated MIME content-type of the image."
    )


@router.get(
    "/",
    response_model=ProjectStatusResponse,
    summary="Get Project Status",
    description="Retrieve status details about the Document OCR application."
)
async def get_project_status() -> dict:
    """
    Returns baseline project info in the format:
    {
        "project": "Document OCR using Vision Language Model",
        "version": "1.0.0",
        "status": "Running"
    }
    """
    return {
        "project": "Document OCR using Vision Language Model",
        "version": "1.0.0",
        "status": "Running"
    }


@router.post(
    "/upload/image",
    response_model=ImageUploadSuccessResponse,
    summary="Upload Image File",
    description=(
        "Upload an image file (JPG, JPEG, PNG) up to a maximum size of 20 MB. "
        "The uploaded file is validated and saved locally under uploads/images/ with a unique UUID filename."
    )
)
async def upload_image(file: UploadFile = File(..., description="The image file to upload.")) -> dict:
    """
    Accepts, validates, and saves an image file to the local directory uploads/images/.
    If the file type is unsupported or size exceeds 20MB, custom exceptions are raised.
    """
    save_result = await save_image_securely(file, settings.UPLOAD_IMAGES_DIR)
    
    return {
        "success": True,
        "message": "Image uploaded successfully",
        "filename": save_result["filename"],
        "filepath": save_result["filepath"],
        "size": save_result["size"],
        "content_type": save_result["content_type"]
    }


@router.post(
    "/ocr/image",
    response_model=VLMOCRResponse,
    summary="Perform OCR using Qwen2.5-VL",
    description=(
        "Accepts an image file (JPG, JPEG, PNG) up to a maximum size of 20 MB via multipart/form-data. "
        "The file is processed in memory and sent to the Qwen2.5-VL-3B-Instruct model for text extraction."
    )
)
async def ocr_image(image: UploadFile = File(..., description="The image file to perform OCR on.")) -> dict:
    """
    Receives, validates, and decodes an image, then runs it through the Qwen2.5-VL VLM model.
    Returns the extracted text, model identifier, and processing time duration.
    """
    logger.info(f"Image received. Filename: '{image.filename}', Content Type: '{image.content_type}'")
    
    # 1. Validate size and type, and read file bytes in-memory
    image_bytes = await read_and_validate_image_file(image)
    
    # 2. Decode file bytes to a Pillow Image and verify validity
    try:
        pil_image = Image.open(io.BytesIO(image_bytes))
        pil_image.verify()  # Perform structural check
        
        # Re-open stream since verify() invalidates the open state
        pil_image = Image.open(io.BytesIO(image_bytes))
        # Trigger an actual pixel load to catch decompression bomb/format issues
        pil_image.load()
    except (UnidentifiedImageError, SyntaxError, ValueError, OSError) as e:
        logger.error(f"Image load error: Corrupted image or invalid format. Details: {str(e)}")
        raise InvalidImageException("The uploaded file is corrupted or not a valid image format.")
    
    # 3. Perform text extraction inference using the loaded VLM model
    start_time = time.time()
    logger.info(f"Inference started for file: '{image.filename}'")
    
    extracted_text = await vlm_service.perform_ocr(pil_image)
    
    processing_time_sec = time.time() - start_time
    logger.info(f"Inference completed in {processing_time_sec:.2f} seconds.")
    
    return {
        "success": True,
        "text": extracted_text,
        "processing_time": f"{processing_time_sec:.2f}s",
        "model": "Qwen2.5-VL-3B-Instruct"
    }
