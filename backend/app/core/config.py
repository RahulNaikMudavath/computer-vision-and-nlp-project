import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Settings:
    PROJECT_NAME: str = "Document OCR using Vision Language Model"
    VERSION: str = "1.0.0"
    
    # Model config - using Qwen2.5-VL 3B Instruct
    MODEL_ID: str = os.getenv("MODEL_ID", "Qwen/Qwen2.5-VL-3B-Instruct")
    
    # Toggle mock mode to skip downloading/loading the 6GB VLM model during local development
    MOCK_VLM: bool = os.getenv("MOCK_VLM", "False").lower() in ("true", "1", "yes")
    
    # Upload directories
    UPLOAD_DIR: str = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "../../../uploads")
    )
    UPLOAD_IMAGES_DIR: str = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "../../../uploads/images")
    )
    UPLOAD_PDFS_DIR: str = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "../../../uploads/pdfs")
    )
    UPLOAD_CHROMA_DIR: str = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "../../../uploads/chroma_db")
    )
    
    # RAG parameters
    CHUNK_SIZE: int = int(os.getenv("CHUNK_SIZE", "1000"))
    CHUNK_OVERLAP: int = int(os.getenv("CHUNK_OVERLAP", "200"))
    EMBEDDING_MODEL_ID: str = os.getenv("EMBEDDING_MODEL_ID", "sentence-transformers/all-MiniLM-L6-v2")
    
    # Database Configuration
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        f"sqlite:///{os.path.join(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../uploads')), 'document_ocr.db')}"
    )
    
    # JWT Security Configuration
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "7b92f7c001cfd74ba1e3d646b9a8fcf22c366ab21ef9a8d904b8df28331fa24e")
    JWT_REFRESH_SECRET_KEY: str = os.getenv("JWT_REFRESH_SECRET_KEY", "b39dc1d91e60058b871c4c1a2e38c924c568acb21ef0a8df0b4cf288331fa19f")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # Maximum size: 20 MB (20 * 1024 * 1024 bytes)
    MAX_FILE_SIZE_BYTES: int = 20 * 1024 * 1024
    
    # Redis Configuration
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    RATE_LIMIT_RPM: int = int(os.getenv("RATE_LIMIT_RPM", "30"))

settings = Settings()
