# DocuMind - SaaS Document OCR & RAG Assistant (Phase 6)

DocuMind is a multi-user SaaS document understanding platform. It automates scanned PDF page conversion, extracts structured key-value schemas (Invoices, Receipts, PAN Cards, Passports, Driving Licenses, Resumes, Bank Statements, Utility Bills), and features a zero-hallucination document chat utilizing Retrieval-Augmented Generation (RAG).

---

## Entity-Relationship (ER) Diagram

```mermaid
erDiagram
    User ||--o{ UserSettings : "has settings (1-to-1)"
    User ||--o{ Document : "uploads (1-to-many)"
    User ||--o{ ChatHistory : "chats (1-to-many)"
    Document ||--o{ DocumentChunk : "splits into (1-to-many)"
    Document ||--o{ ChatHistory : "references (1-to-many)"
    Document ||--o| EmbeddingMetadata : "caches (1-to-1)"

    User {
        int id PK
        string email UK
        string hashed_password
        string full_name
        string role "Admin / Standard User"
        string avatar_url
        boolean is_active
        datetime created_at
    }

    UserSettings {
        int id PK
        int user_id FK
        string theme "light / dark"
        string language
        string default_ocr_language
        boolean email_notifications
    }

    Document {
        string id PK "UUID"
        string filename
        string original_filename
        string file_type
        int size_bytes
        string ocr_status "PENDING / COMPLETED / FAILED"
        string processing_status "IDLE / PROCESSING / COMPLETED / FAILED"
        string document_type "Invoice / Receipt / Passport / etc"
        float confidence_score
        string ocr_text
        int uploaded_by FK
        datetime created_at
    }

    DocumentChunk {
        int id PK
        string document_id FK
        int page_number
        int chunk_index
        string text_content
    }

    ChatHistory {
        int id PK
        string document_id FK
        int user_id FK
        string question
        string answer
        string sources "JSON array of page numbers"
        datetime created_at
    }

    EmbeddingMetadata {
        int id PK
        string document_id FK
        string model_name
        int dimensions
        int chunk_count
    }
```

---

## Authentication Flow

1. **Register (`POST /auth/register`)**: Standard registration creates account entries. The first registered account on the database automatically bootstraps with the `Admin` role.
2. **Login (`POST /auth/login`)**: Authenticates credentials and returns a JSON payload:
   - `access_token` (JWT payload with role, expires in 15 minutes)
   - `refresh_token` (expires in 7 days)
3. **Session Interceptor**: The React client stores the JWTs in `localStorage`. An Axios Interceptor automatically injects `Authorization: Bearer <access_token>` into the headers of all API requests.
4. **Token Refresh (`POST /auth/refresh`)**: When the access token expires, the client sends the `refresh_token` to receive new session tokens, maintaining seamless active sessions.
5. **Logout (`POST /auth/logout`)**: Clears credentials on both the client-side state and backend session registers.

---

## Role-Based Access Control (RBAC)

- **Standard Users**:
  - Upload documents and run OCR/Structured Extractions.
  - Review only their own document history library (strict multi-tenant isolation).
  - Interact with document text via the RAG Chat interface.
  - Edit personal profiles and default settings preferences.
- **Administrators**:
  - View platform-wide performance analytics metrics (Total Storage size, total documents parsed, total chats triggered).
  - List all user accounts and toggle active states (Suspend/Activate).
  - Stream live uvicorn application logs.
  - Purge documents from the platform.

---

## Getting Started

### 1. Backend Setup

Navigate to the `backend/` directory:

1. **Create and Activate a Virtual Environment:**
   ```bash
   python -m venv venv
   # Windows
   .\venv\Scripts\Activate.ps1
   # macOS / Linux
   source venv/bin/activate
   ```

2. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure Database Connection (`.env`):**
   By default, the application connects to a local SQLite database (`uploads/document_ocr.db`) for immediate offline testing. To connect to a production **PostgreSQL** instance, define the URL:
   ```env
   DATABASE_URL=postgresql://username:password@localhost:5432/document_ocr
   JWT_SECRET_KEY=generate_a_random_32_byte_hex_key
   JWT_REFRESH_SECRET_KEY=generate_another_random_32_byte_hex_key
   MOCK_VLM=True
   ```

4. **Launch the FastAPI Server:**
   ```bash
   python -m app.main
   ```
   The backend API will initialize database tables on boot and start at **http://localhost:8000**. Swagger UI interactive docs will be available at **http://localhost:8000/docs**.

### 2. Frontend Setup

Navigate to the `frontend/` directory:

1. **Install Packages:**
   ```bash
   npm install
   ```

2. **Launch Dev Mode:**
   ```bash
   npm run dev
   ```
   The Vite client will boot at **http://localhost:5173**.

---

## Verification Tests

Execute backend database and session tests:
```bash
venv/Scripts/python -m unittest scratch/test_auth_db.py
```
Execute mocked OCR/RAG pipeline tests:
```bash
venv/Scripts/python -m unittest scratch/test_api_mocked.py
```
