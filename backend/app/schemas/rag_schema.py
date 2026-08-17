from pydantic import BaseModel, Field
from typing import List, Optional

class DocumentChatRequest(BaseModel):
    document_id: str = Field(
        ...,
        description="The unique UUID of the uploaded document (image or PDF)."
    )
    question: str = Field(
        ...,
        description="The natural language question to ask the document."
    )

class SourceChunk(BaseModel):
    page: int = Field(
        ...,
        description="The 1-based page number of the source chunk."
    )
    chunk: int = Field(
        ...,
        description="The index of the chunk on the page or document."
    )
    document_id: Optional[str] = Field(
        None,
        description="The unique UUID of the source document."
    )
    filename: Optional[str] = Field(
        None,
        description="The filename of the source document."
    )

class MultiDocumentChatRequest(BaseModel):
    document_ids: List[str] = Field(
        ...,
        description="The list of unique UUIDs of the uploaded documents."
    )
    question: str = Field(
        ...,
        description="The natural language question to ask across the documents."
    )

class DocumentChatResponse(BaseModel):
    success: bool = Field(
        default=True,
        description="Indicates whether the RAG search and generation completed successfully."
    )
    question: str = Field(
        ...,
        description="The original question submitted."
    )
    answer: str = Field(
        ...,
        description="The synthesized natural language response based on the document context."
    )
    sources: List[SourceChunk] = Field(
        ...,
        description="The source chunks references retrieved during semantic search."
    )
    processing_time: str = Field(
        ...,
        description="The duration taken to retrieve context and generate response."
    )

class DocumentMetadataResponse(BaseModel):
    document_id: str = Field(..., description="Document identifier.")
    filename: str = Field(..., description="Original filename.")
    file_type: str = Field(..., description="Extension type ('pdf' or image extension).")
    size: str = Field(..., description="Human-readable file size.")
    indexed: bool = Field(..., description="True if document chunks are embedded in Vector DB.")
    chunk_count: int = Field(..., description="Number of text chunks indexed.")

class ChunkMetadataResponse(BaseModel):
    page: int = Field(..., description="The page number of the chunk.")
    chunk_index: int = Field(..., description="The sequence index of the chunk.")
    text: str = Field(..., description="The content of the chunk text.")

class ChunksListResponse(BaseModel):
    success: bool = Field(default=True)
    document_id: str = Field(..., description="Document identifier.")
    chunks: List[ChunkMetadataResponse] = Field(..., description="List of all chunk content and source pages.")

class EmbeddingMetadataResponse(BaseModel):
    success: bool = Field(default=True)
    document_id: str = Field(..., description="Document identifier.")
    model: str = Field(..., description="The model used to generate embeddings.")
    dimension: int = Field(..., description="Dimensions of embedding vectors.")
    chunk_count: int = Field(..., description="Number of embedded chunks.")
