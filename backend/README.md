# Document OCR Backend API (Phase 5 - RAG Document Chat)

This is the backend API service for the Document OCR application built using **FastAPI**. It has been upgraded to support full **Retrieval-Augmented Generation (RAG) Document Chat** using **LangChain**, **ChromaDB**, and **Sentence Transformers**.

Users can query the contents of uploaded documents using natural language, and the system performs semantic search to retrieve the most relevant sections of text (chunks) and generate context-bound answers using the **Qwen2.5-VL-3B-Instruct** Vision Language Model.

---

## RAG Architecture Flow

```
User Question
    │
    ▼
Semantic Search (Similarity Query) ──► ChromaDB Vector Store
    │                                      ▲
    ▼                                      │
Top 5 Context Chunks ──────────────────────┘
    │
    ▼
Prompt Engineering (rag_qa Context Prompt)
    │
    ▼
LLM Inference (Qwen2.5-VL)
    │
    ▼
Strict Context-Bound Answer
```

1. **Document Upload & OCR**: Original files are saved securely. If RAG chat is initialized on an un-indexed document ID, the service runs OCR (page-by-page) to capture the text content.
2. **Page-by-page Chunking**: Splits text using LangChain's `RecursiveCharacterTextSplitter` configured with a chunk size of `1000` characters and `200` characters overlap. Metadata for the source page number and chunk sequence indexes are carried forward.
3. **Embeddings & Vector Store**: Embeds the chunks locally using the `sentence-transformers/all-MiniLM-L6-v2` model (dimension `384`) and registers them in a persistent **ChromaDB** collection under the document UUID.
4. **Caching**: Embeddings are cached per document. Re-indexing is skipped if the document ID is already present in ChromaDB.
5. **Context-Bound Prompt**: Semantic search queries the top 5 most similar chunks. The system constructs a strict QA prompt instructing the model to answer *only* from the retrieved context. If the answer is not present, it returns exactly: `"The uploaded document does not contain enough information to answer this question."`

---

## Project Structure

```
backend/
├── app/
│   ├── api/
│   │   └── routes/
│   │       ├── ocr.py
│   │       ├── pdf_routes.py
│   │       ├── document_routes.py
│   │       └── rag_routes.py     # [Phase 5] POST /document/chat, GET document lookups
│   ├── core/
│   │   └── config.py             # Configures chunk sizes, overlaps, and persistent paths
│   ├── exceptions/
│   │   └── handlers.py           # Maps HTTP 404 (DocumentNotFoundException)
│   ├── prompts/
│   │   ├── ...
│   │   └── rag_qa.txt            # [Phase 5] QA prompt template enforcing zero hallucination
│   ├── schemas/
│   │   ├── document_schemas.py
│   │   ├── pdf_schema.py
│   │   ├── rag_schema.py         # [Phase 5] Pydantic models for chat requests and statistics
│   │   └── vlm_schema.py
│   ├── services/
│   │   ├── chunk_service.py      # [Phase 5] LangChain page-by-page text splitter
│   │   ├── embedding_service.py  # [Phase 5] Local SentenceTransformers (all-MiniLM-L6-v2) wrapper
│   │   ├── vector_service.py     # [Phase 5] ChromaDB indexer and similarity search manager
│   │   ├── rag_service.py        # [Phase 5] RAG pipeline orchestrator
│   │   ├── pdf_service.py
│   │   ├── document_service.py
│   │   └── vlm_service.py
│   ├── utils/
│   │   └── helpers.py
│   └── main.py                   # Initialises Vector Store on lifespan startup
├── requirements.txt              # Standard package requirements
├── .env                          # Local configs (MOCK_VLM=True/False)
└── README.md                     # Running guide and API documentation
```

---

## API Endpoints

### 1. RAG Document Chat
- **URL**: `POST /document/chat`
- **Request Body**:
  ```json
  {
     "document_id": "8016f640-cc2a-4196-aeb2-87b7c9ea61f3",
     "question": "What is the total invoice amount?"
  }
  ```
- **Response (200 OK)**:
  ```json
  {
     "success": true,
     "question": "What is the total invoice amount?",
     "answer": "The total invoice amount is $1,350.00.",
     "sources": [
        {
           "page": 1,
           "chunk": 0
        }
     ],
     "processing_time": "0.14s"
  }
  ```

### 2. Get Document Metadata
- **URL**: `GET /document/{id}`
- **Response**:
  ```json
  {
     "document_id": "8016f640-cc2a-4196-aeb2-87b7c9ea61f3",
     "filename": "invoice.pdf",
     "file_type": "pdf",
     "size": "45.24 KB",
     "indexed": true,
     "chunk_count": 4
  }
  ```

### 3. Get Indexed Chunks
- **URL**: `GET /document/{id}/chunks`
- **Response**:
  ```json
  {
     "success": true,
     "document_id": "8016f640-cc2a-4196-aeb2-87b7c9ea61f3",
     "chunks": [
        {
           "page": 1,
           "chunk_index": 0,
           "text": "ACME Industrial Suppliers Inc. Invoice INV-2026-9941..."
        }
     ]
  }
  ```

### 4. Get Embeddings Info
- **URL**: `GET /document/{id}/embeddings`
- **Response**:
  ```json
  {
     "success": true,
     "document_id": "8016f640-cc2a-4196-aeb2-87b7c9ea61f3",
     "model": "sentence-transformers/all-MiniLM-L6-v2",
     "dimension": 384,
     "chunk_count": 4
  }
  ```

---

## Local Setup & Run

### 1. Prerequisites (Poppler Dependency)
Ensure Poppler is configured in your OS PATH (required to process PDFs page-by-page). See details inside the Phase 3 logs.

### 2. Startup Virtual Environment & Install Requirements
```bash
python -m venv venv
# Windows
.\venv\Scripts\Activate.ps1
# macOS/Linux
source venv/bin/activate

pip install -r requirements.txt
```

### 3. Launch Development Server
```bash
python -m app.main
```
The server will bind to **http://localhost:8000** and automatically create the Chroma database directory structure.

### 4. Mock Mode Toggle (`.env`)
To bypass downloading VLM weights (~6GB) and embeddings models (~100MB) during local API testing, make sure you configure your `.env`:
```env
MOCK_VLM=True
```
Set it to `False` to run local AI GPU/CPU inference.

---

## Interactive Swagger Dashboard

Start the server and visit [http://localhost:8000/docs](http://localhost:8000/docs) in your browser to test chat sessions and metadata lookups.
