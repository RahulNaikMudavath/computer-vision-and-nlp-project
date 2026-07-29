import os
import uuid
from fastapi import UploadFile
from app.core.config import settings
from app.exceptions.handlers import (
    InvalidFileExtensionException,
    FileTooLargeException,
)

# Supported image configurations
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png"}
ALLOWED_MIME_TYPES = {"image/jpeg", "image/png"}

def format_size(bytes_size: int) -> str:
    """Format the file size into a human-readable string."""
    for unit in ['bytes', 'KB', 'MB', 'GB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.2f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.2f} TB"

def validate_image_upload(file: UploadFile) -> None:
    """
    Validate extension and content type.
    """
    filename = file.filename or ""
    _, ext = os.path.splitext(filename.lower())
    
    # 1. Validate file extension
    if ext not in ALLOWED_EXTENSIONS:
        raise InvalidFileExtensionException(
            message=f"File extension '{ext}' is not allowed. Supported extensions are: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
        )
        
    # 2. Validate MIME type
    if file.content_type not in ALLOWED_MIME_TYPES:
        raise InvalidFileExtensionException(
            message=f"MIME type '{file.content_type}' is not allowed. Supported types are: {', '.join(sorted(ALLOWED_MIME_TYPES))}"
        )

async def read_and_validate_image_file(file: UploadFile) -> bytes:
    """
    Read the uploaded file in chunks directly in-memory.
    Validates extension, MIME type, and checks if file size is within the max limit (20MB).
    Returns the raw bytes if validation passes.
    Raises:
        - InvalidFileExtensionException: for bad formats/types
        - FileTooLargeException: if size exceeds 20MB
    """
    # 1. Validate file extension and MIME type
    validate_image_upload(file)
    
    # 2. Read in chunks to validate size
    total_bytes = 0
    chunks = []
    chunk_size = 1024 * 1024  # 1MB chunks
    
    while True:
        chunk = await file.read(chunk_size)
        if not chunk:
            break
        total_bytes += len(chunk)
        if total_bytes > settings.MAX_FILE_SIZE_BYTES:
            raise FileTooLargeException(
                message=f"File size exceeds the limit of {format_size(settings.MAX_FILE_SIZE_BYTES)} (Actual size: >{format_size(total_bytes)})",
                max_size_bytes=settings.MAX_FILE_SIZE_BYTES
            )
        chunks.append(chunk)
        
    return b"".join(chunks)

async def save_image_securely(file: UploadFile, destination_dir: str) -> dict:
    """
    Validate and save an uploaded image file securely to a destination directory.
    Reads and writes in chunks to prevent high-memory usage.
    If the size exceeds 20MB, it raises FileTooLargeException and deletes the partial file.
    
    Returns a dictionary containing:
        - filename: unique generated filename
        - filepath: absolute local path
        - size: human-readable size
        - content_type: file MIME type
    """
    # Create directory if it doesn't exist
    os.makedirs(destination_dir, exist_ok=True)
    
    # Validate extension and MIME type
    validate_image_upload(file)
    
    # Generate unique UUID filename
    _, ext = os.path.splitext(file.filename.lower())
    unique_filename = f"{uuid.uuid4()}{ext}"
    dest_path = os.path.join(destination_dir, unique_filename)
    
    total_bytes = 0
    chunk_size = 1024 * 1024  # 1MB chunks
    
    limit_exceeded = False
    try:
        # Open destination file for writing binary
        with open(dest_path, "wb") as buffer:
            while True:
                # Read a chunk asynchronously
                chunk = await file.read(chunk_size)
                if not chunk:
                    break
                
                total_bytes += len(chunk)
                if total_bytes > settings.MAX_FILE_SIZE_BYTES:
                    limit_exceeded = True
                    break
                
                buffer.write(chunk)
                
        if limit_exceeded:
            if os.path.exists(dest_path):
                os.remove(dest_path)
            raise FileTooLargeException(
                message=f"File size exceeds the limit of {format_size(settings.MAX_FILE_SIZE_BYTES)} (Actual size: >{format_size(total_bytes)})",
                max_size_bytes=settings.MAX_FILE_SIZE_BYTES
            )
                
    except Exception as e:
        # Ensure file cleanup on other errors
        if os.path.exists(dest_path):
            try:
                os.remove(dest_path)
            except OSError:
                pass
        raise e
        
    return {
        "filename": unique_filename,
        "filepath": os.path.abspath(dest_path),
        "size": format_size(total_bytes),
        "content_type": file.content_type
    }

def validate_pdf_upload(file: UploadFile) -> None:
    """
    Validate that the uploaded file is indeed a PDF based on extension and MIME type.
    """
    filename = file.filename or ""
    _, ext = os.path.splitext(filename.lower())
    
    # 1. Validate file extension
    if ext != ".pdf":
        raise InvalidFileExtensionException(
            message=f"File extension '{ext}' is not allowed. Supported extension for documents is: .pdf"
        )
        
    # 2. Validate MIME type
    if file.content_type != "application/pdf":
        raise InvalidFileExtensionException(
            message=f"MIME type '{file.content_type}' is not allowed. Supported document type is: application/pdf"
        )

async def save_pdf_securely(file: UploadFile, destination_dir: str) -> str:
    """
    Validate and save an uploaded PDF file securely to a destination directory.
    Reads and writes in chunks directly to disk to prevent RAM exhaustion.
    If the size exceeds 50MB, raises FileTooLargeException and deletes the partial file.
    
    Returns the absolute path to the saved PDF file.
    """
    # Create directory if it doesn't exist
    os.makedirs(destination_dir, exist_ok=True)
    
    # Validate format and MIME
    validate_pdf_upload(file)
    
    # Generate unique UUID filename
    unique_filename = f"{uuid.uuid4()}.pdf"
    dest_path = os.path.join(destination_dir, unique_filename)
    
    max_pdf_size = 50 * 1024 * 1024  # 50 MB
    total_bytes = 0
    chunk_size = 1024 * 1024  # 1MB chunks
    
    limit_exceeded = False
    try:
        # Write PDF to disk in chunks
        with open(dest_path, "wb") as buffer:
            while True:
                chunk = await file.read(chunk_size)
                if not chunk:
                    break
                
                total_bytes += len(chunk)
                if total_bytes > max_pdf_size:
                    limit_exceeded = True
                    break
                
                buffer.write(chunk)
                
        if limit_exceeded:
            if os.path.exists(dest_path):
                os.remove(dest_path)
            raise FileTooLargeException(
                message=f"PDF size exceeds the limit of {format_size(max_pdf_size)} (Actual size: >{format_size(total_bytes)})",
                max_size_bytes=max_pdf_size
            )
                
    except Exception as e:
        # Cleanup file on errors
        if os.path.exists(dest_path):
            try:
                os.remove(dest_path)
            except OSError:
                pass
        raise e
        
    return os.path.abspath(dest_path)

def validate_document_upload(file: UploadFile) -> None:
    """
    Validate that the uploaded file is either a PDF or an allowed image (JPG, JPEG, PNG).
    """
    filename = file.filename or ""
    _, ext = os.path.splitext(filename.lower())
    
    if ext == ".pdf":
        validate_pdf_upload(file)
    elif ext in ALLOWED_EXTENSIONS:
        validate_image_upload(file)
    else:
        raise InvalidFileExtensionException(
            message=f"File extension '{ext}' is not allowed. Supported formats are: PDF, PNG, JPG, JPEG"
        )

async def save_document_securely(file: UploadFile) -> tuple[str, str]:
    """
    Saves an uploaded PDF or image file securely checking the respective size limits:
    - PDF: 50 MB
    - Image: 20 MB
    
    Returns:
        tuple[str, str]: (absolute_file_path, file_type) where file_type is 'pdf' or 'image'
    """
    filename = file.filename or ""
    _, ext = os.path.splitext(filename.lower())
    
    if ext == ".pdf":
        path = await save_pdf_securely(file, settings.UPLOAD_PDFS_DIR)
        return path, "pdf"
    elif ext in ALLOWED_EXTENSIONS:
        img_details = await save_image_securely(file, settings.UPLOAD_IMAGES_DIR)
        return img_details["filepath"], "image"
    else:
        raise InvalidFileExtensionException(
            message=f"File extension '{ext}' is not allowed. Supported formats are: PDF, PNG, JPG, JPEG"
        )
