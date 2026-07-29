import logging
from typing import List
from app.core.config import settings

logger = logging.getLogger("document_ocr.embedding_service")

class MockEmbeddings:
    """
    Mock embeddings class to bypass loading SentenceTransformers model during local mock-mode development.
    Produces vectors of size 384 (dimension of all-MiniLM-L6-v2).
    """
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        # Generate dummy 384-dimension vector for each text chunk
        return [[0.1 * i for i in range(384)] for _ in texts]

    def embed_query(self, text: str) -> List[float]:
        # Generate dummy 384-dimension vector for the search query
        return [0.1 * i for i in range(384)]

class EmbeddingService:
    """
    Service responsible for loading the sentence embedding model and encoding texts.
    """
    def __init__(self) -> None:
        self._embeddings = None

    def get_embeddings(self):
        """
        Instantiates or retrieves the cached embeddings generator.
        """
        if self._embeddings is not None:
            return self._embeddings
            
        if settings.MOCK_VLM:
            logger.info("MOCK_VLM is enabled. Initializing MockEmbeddings.")
            self._embeddings = MockEmbeddings()
            return self._embeddings

        logger.info(f"Loading Embedding Model: {settings.EMBEDDING_MODEL_ID} via LangChain...")
        try:
            from langchain_community.embeddings import HuggingFaceEmbeddings
            self._embeddings = HuggingFaceEmbeddings(
                model_name=settings.EMBEDDING_MODEL_ID,
                model_kwargs={'device': 'cpu'}  # Keep embedding CPU-based for portability
            )
            logger.info("Successfully loaded HuggingFaceEmbeddings model.")
        except Exception as e:
            logger.error(f"Failed to load HuggingFaceEmbeddings: {str(e)}. Falling back to MockEmbeddings.")
            self._embeddings = MockEmbeddings()
            
        return self._embeddings

    @property
    def model_name(self) -> str:
        if settings.MOCK_VLM:
            return "Mock-all-MiniLM-L6-v2"
        return settings.EMBEDDING_MODEL_ID

    @property
    def dimension(self) -> int:
        return 384

# Instantiate EmbeddingService singleton
embedding_service = EmbeddingService()
