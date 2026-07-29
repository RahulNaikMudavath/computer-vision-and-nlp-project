import logging
from typing import List, Dict, Any
from langchain_text_splitters import RecursiveCharacterTextSplitter
from app.core.config import settings

logger = logging.getLogger("document_ocr.chunk_service")

class ChunkService:
    """
    Service handling text chunking using LangChain splitters.
    """
    def __init__(self) -> None:
        self.chunk_size = settings.CHUNK_SIZE
        self.chunk_overlap = settings.CHUNK_OVERLAP
        # Initialize LangChain splitter
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", " ", ""]
        )

    def split_pages(self, pages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Splits a list of document pages (dicts containing 'page' and 'text')
        into chunks, maintaining page metadata.
        
        Returns:
            List[Dict[str, Any]]: List of chunk dicts:
                {
                    "text": str,
                    "metadata": {
                        "page": int,
                        "chunk_index": int
                    }
                }
        """
        logger.info(f"Chunking document with size={self.chunk_size}, overlap={self.chunk_overlap}...")
        all_chunks = []
        global_chunk_idx = 0
        
        for p in pages:
            page_num = p.get("page", 1)
            text = p.get("text", "")
            
            if not text.strip():
                continue
                
            # Split text on this page
            split_texts = self.splitter.split_text(text)
            
            for i, chunk_text in enumerate(split_texts):
                all_chunks.append({
                    "text": chunk_text,
                    "metadata": {
                        "page": page_num,
                        "chunk_index": global_chunk_idx
                    }
                })
                global_chunk_idx += 1
                
        logger.info(f"Generated {len(all_chunks)} chunks from {len(pages)} pages.")
        return all_chunks

# Instantiate ChunkService singleton
chunk_service = ChunkService()
