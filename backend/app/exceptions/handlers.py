from fastapi import Request
from fastapi.responses import JSONResponse

class ImageUploadException(Exception):
    """Base exception for all image upload related errors."""
    pass

class InvalidFileExtensionException(ImageUploadException):
    """Raised when the uploaded file extension or MIME type is not allowed."""
    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)

class FileTooLargeException(ImageUploadException):
    """Raised when the uploaded file size exceeds the allowed threshold."""
    def __init__(self, message: str, max_size_bytes: int):
        self.message = message
        self.max_size_bytes = max_size_bytes
        super().__init__(self.message)

class InvalidImageException(ImageUploadException):
    """Raised when the uploaded file is corrupted or not a valid image."""
    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)

class VLMInferenceException(Exception):
    """Raised when the VLM model fails during generation."""
    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)

class VLMModelLoadingException(Exception):
    """Raised when the VLM model fails to load during startup."""
    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)

class InvalidPDFException(Exception):
    """Raised when the uploaded PDF is corrupted, encrypted, or invalid."""
    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)

class DocumentNotFoundException(Exception):
    """Raised when the requested document ID does not match any uploaded file on disk."""
    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)



async def invalid_file_extension_handler(request: Request, exc: InvalidFileExtensionException) -> JSONResponse:
    """Handle invalid file extension exceptions (HTTP 400)."""
    return JSONResponse(
        status_code=400,
        content={
            "success": False,
            "message": exc.message,
            "error_type": "InvalidFileExtension"
        }
    )

async def file_too_large_handler(request: Request, exc: FileTooLargeException) -> JSONResponse:
    """Handle file size limits (HTTP 413)."""
    return JSONResponse(
        status_code=413,
        content={
            "success": False,
            "message": exc.message,
            "error_type": "FileTooLarge"
        }
    )

async def invalid_image_handler(request: Request, exc: InvalidImageException) -> JSONResponse:
    """Handle corrupted or invalid images (HTTP 400)."""
    return JSONResponse(
        status_code=400,
        content={
            "success": False,
            "message": exc.message,
            "error_type": "InvalidImage"
        }
    )

async def vlm_inference_handler(request: Request, exc: VLMInferenceException) -> JSONResponse:
    """Handle model inference failure (HTTP 500)."""
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "message": exc.message,
            "error_type": "VLMInferenceError"
        }
    )

async def vlm_model_loading_handler(request: Request, exc: VLMModelLoadingException) -> JSONResponse:
    """Handle model loading startup failure (HTTP 500)."""
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "message": exc.message,
            "error_type": "VLMModelLoadingError"
        }
    )

async def invalid_pdf_handler(request: Request, exc: InvalidPDFException) -> JSONResponse:
    """Handle corrupted or invalid PDFs (HTTP 400)."""
    return JSONResponse(
        status_code=400,
        content={
            "success": False,
            "message": exc.message,
            "error_type": "InvalidPDF"
        }
    )

async def image_upload_exception_handler(request: Request, exc: ImageUploadException) -> JSONResponse:
    """Generic fallback for image upload related exceptions (HTTP 400)."""
    return JSONResponse(
        status_code=400,
        content={
            "success": False,
            "message": str(exc),
            "error_type": "ImageUploadError"
        }
    )

# Try importing torch to catch GPU OOM. If torch is not installed yet, we skip defining the handler.
try:
    import torch
    async def cuda_oom_handler(request: Request, exc: torch.cuda.OutOfMemoryError) -> JSONResponse:
        """Handle GPU out-of-memory errors by returning a 503 Service Unavailable."""
        return JSONResponse(
            status_code=503,
            content={
                "success": False,
                "message": "GPU ran out of memory while processing the request. Please try again with a smaller image or wait for VRAM release.",
                "error_type": "CUDAOutOfMemory"
            }
        )
except ImportError:
    cuda_oom_handler = None

async def document_not_found_handler(request: Request, exc: DocumentNotFoundException) -> JSONResponse:
    """Handle document not found exceptions (HTTP 404)."""
    return JSONResponse(
        status_code=404,
        content={
            "success": False,
            "message": exc.message,
            "error_type": "DocumentNotFound"
        }
    )
