from pydantic import BaseModel, Field

class VLMOCRResponse(BaseModel):
    success: bool = Field(
        default=True,
        description="Indicates whether OCR processing was successful."
    )
    text: str = Field(
        ...,
        description="The extracted text from the document image."
    )
    processing_time: str = Field(
        ...,
        description="The time taken to run the validation, load the image, and perform inference."
    )
    model: str = Field(
        default="Qwen2.5-VL-3B-Instruct",
        description="The name of the Vision Language Model used for OCR."
    )
