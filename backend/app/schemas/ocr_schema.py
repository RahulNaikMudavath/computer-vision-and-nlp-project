from pydantic import BaseModel
from typing import List, Optional

class PageResult(BaseModel):
    page_num: int
    text: str
    image_url: Optional[str] = None

class OCRResponse(BaseModel):
    file_id: str
    filename: str
    status: str
    text: str
    pages: List[PageResult]
    message: Optional[str] = None

class AskQuestionRequest(BaseModel):
    question: str
    file_id: Optional[str] = None
    text: Optional[str] = None

class AskQuestionResponse(BaseModel):
    answer: str
