from pydantic import BaseModel, Field
from typing import List

class PDFPageResult(BaseModel):
    page: int = Field(
        ...,
        description="The page number in the PDF document (1-indexed)."
    )
    text: str = Field(
        ...,
        description="The raw OCR text extracted from this page."
    )

class PDFOCRResponse(BaseModel):
    success: bool = Field(
        default=True,
        description="Indicates whether the PDF OCR process completed successfully."
    )
    filename: str = Field(
        ...,
        description="The original filename of the uploaded PDF."
    )
    pages: int = Field(
        ...,
        description="The total number of pages in the PDF document."
    )
    processing_time: str = Field(
        ...,
        description="The total time elapsed to validate, parse, convert, and OCR all pages."
    )
    model: str = Field(
        default="Qwen2.5-VL-3B-Instruct",
        description="The name of the Vision Language Model used."
    )
    results: List[PDFPageResult] = Field(
        ...,
        description="List of OCR results containing page number and text for each page."
    )
    full_text: str = Field(
        ...,
        description="The combined transcription of all document pages separated by clean spacing."
    )
