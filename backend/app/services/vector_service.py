import os
import logging
from typing import List, Dict, Any
from app.core.config import settings
from app.services.embedding_service import embedding_service

logger = logging.getLogger("document_ocr.vector_service")

class MockVectorStore:
    """
    In-memory mock vector database replacing ChromaDB for mock-mode testing.
    """
    def __init__(self) -> None:
        # Structure: { document_id: [ {"text": str, "metadata": dict} ] }
        self._db: Dict[str, List[Dict[str, Any]]] = {}

    def add_chunks(self, document_id: str, chunks: List[Dict[str, Any]]) -> None:
        if document_id not in self._db:
            self._db[document_id] = []
        self._db[document_id].extend(chunks)
        logger.info(f"MockVectorStore: Indexed {len(chunks)} chunks for document: {document_id}")

    def get_chunks(self, document_id: str) -> List[Dict[str, Any]]:
        return self._db.get(document_id, [])

    def similarity_search(self, document_id: str, query: str, k: int = 5) -> List[Dict[str, Any]]:
        chunks = self.get_chunks(document_id)
        # Ensure we enrich chunk copy with document_id
        retrieved = []
        for c in chunks[:k]:
            retrieved.append({
                "text": c["text"],
                "metadata": {
                    "page": c["metadata"].get("page", 1),
                    "chunk_index": c["metadata"].get("chunk_index", 0),
                    "document_id": document_id
                }
            })
        return retrieved

    def similarity_search_multiple(self, document_ids: List[str], query: str, k: int = 5) -> List[Dict[str, Any]]:
        aggregated = []
        for doc_id in document_ids:
            chunks = self.get_chunks(doc_id)
            for c in chunks:
                aggregated.append({
                    "text": c["text"],
                    "metadata": {
                        "page": c["metadata"].get("page", 1),
                        "chunk_index": c["metadata"].get("chunk_index", 0),
                        "document_id": doc_id
                    }
                })
        return aggregated[:k]

    def has_document(self, document_id: str) -> bool:
        return document_id in self._db


class VectorService:
    """
    Service managing vector store connections, index updates, and semantic context search.
    """
    def __init__(self) -> None:
        self._db = None
        self._mock_db = MockVectorStore()

    def initialize_store(self) -> None:
        """
        Setup vector database directories and test local database connection.
        """
        if settings.MOCK_VLM:
            logger.info("MOCK_VLM is active. ChromaDB initialization bypassed.")
            return

        logger.info("Initializing persistent ChromaDB vector store...")
        try:
            # Create Chroma directory if missing
            os.makedirs(settings.UPLOAD_CHROMA_DIR, exist_ok=True)
            
            from langchain_community.vectorstores import Chroma
            
            # Load persistent vector collection
            self._db = Chroma(
                persist_directory=settings.UPLOAD_CHROMA_DIR,
                embedding_function=embedding_service.get_embeddings(),
                collection_name="document_ocr_rag"
            )
            logger.info(f"ChromaDB persistent store loaded at: {settings.UPLOAD_CHROMA_DIR}")
        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB: {str(e)}. Falling back to in-memory MockVectorStore.")
            self._db = None

    def add_document_chunks(self, document_id: str, chunks: List[Dict[str, Any]]) -> None:
        """
        Adds text chunks with metadata to the vector collection.
        """
        if settings.MOCK_VLM or self._db is None:
            self._mock_db.add_chunks(document_id, chunks)
            return

        logger.info(f"Indexing {len(chunks)} chunks into ChromaDB for document {document_id}...")
        try:
            from langchain.docstore.document import Document
            
            docs = [
                Document(
                    page_content=chunk["text"],
                    metadata={
                        "document_id": document_id,
                        "page": chunk["metadata"]["page"],
                        "chunk": chunk["metadata"]["chunk_index"]
                    }
                )
                for chunk in chunks
            ]
            self._db.add_documents(docs)
            logger.info(f"Successfully added document {document_id} chunks to ChromaDB.")
        except Exception as e:
            logger.error(f"Error writing to ChromaDB: {str(e)}")
            raise RuntimeError(f"Failed to index chunks into vector database: {str(e)}")

    def get_document_chunks(self, document_id: str) -> List[Dict[str, Any]]:
        """
        Retrieves all chunks matching the document ID.
        """
        if settings.MOCK_VLM or self._db is None:
            return self._mock_db.get_chunks(document_id)

        try:
            # Chroma db get query
            results = self._db.get(where={"document_id": document_id})
            
            chunks = []
            documents = results.get("documents", [])
            metadatas = results.get("metadatas", [])
            
            for doc_text, meta in zip(documents, metadatas):
                chunks.append({
                    "text": doc_text,
                    "metadata": {
                        "page": meta.get("page", 1),
                        "chunk_index": meta.get("chunk", 0)
                    }
                })
            # Sort by chunk_index
            chunks.sort(key=lambda x: x["metadata"]["chunk_index"])
            return chunks
        except Exception as e:
            logger.error(f"Failed to query ChromaDB document chunks: {str(e)}")
            return []

    def similarity_search(self, document_id: str, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """
        Runs similarity search on vector collection matching document_id.
        
        Returns:
            List[Dict[str, Any]]: List of chunks with 'text' and 'metadata'.
        """
        if settings.MOCK_VLM or self._db is None:
            return self._mock_db.similarity_search(document_id, query, k)

        logger.info(f"Performing similarity search for document {document_id} (K={k})...")
        try:
            results = self._db.similarity_search(
                query=query,
                k=k,
                filter={"document_id": document_id}
            )
            
            retrieved = []
            for doc in results:
                retrieved.append({
                    "text": doc.page_content,
                    "metadata": {
                        "page": doc.metadata.get("page", 1),
                        "chunk_index": doc.metadata.get("chunk", 0),
                        "document_id": doc.metadata.get("document_id", document_id)
                    }
                })
            logger.info(f"Retrieved {len(retrieved)} relevant context chunks.")
            return retrieved
        except Exception as e:
            logger.error(f"ChromaDB similarity search failed: {str(e)}")
            return []

    def similarity_search_multiple(self, document_ids: List[str], query: str, k: int = 5) -> List[Dict[str, Any]]:
        """
        Runs similarity search on vector collection across multiple document_ids.
        """
        if settings.MOCK_VLM or self._db is None:
            return self._mock_db.similarity_search_multiple(document_ids, query, k)

        logger.info(f"Performing similarity search for documents {document_ids} (K={k})...")
        try:
            results = self._db.similarity_search(
                query=query,
                k=k,
                filter={"document_id": {"$in": document_ids}}
            )
            
            retrieved = []
            for doc in results:
                retrieved.append({
                    "text": doc.page_content,
                    "metadata": {
                        "page": doc.metadata.get("page", 1),
                        "chunk_index": doc.metadata.get("chunk", 0),
                        "document_id": doc.metadata.get("document_id")
                    }
                })
            logger.info(f"Retrieved {len(retrieved)} relevant context chunks across multiple documents.")
            return retrieved
        except Exception as e:
            logger.error(f"ChromaDB multi similarity search failed: {str(e)}")
            return []

    def is_document_indexed(self, document_id: str) -> bool:
        """
        Checks if the vector store already has chunks for this document ID.
        """
        if settings.MOCK_VLM or self._db is None:
            return self._mock_db.has_document(document_id)

        try:
            # Query chroma collection matching document_id
            results = self._db.get(where={"document_id": document_id}, limit=1)
            return len(results.get("ids", [])) > 0
        except Exception as e:
            logger.error(f"Failed checking document indexing state: {str(e)}")
            return False

# Instantiate VectorService singleton
vector_service = VectorService()
