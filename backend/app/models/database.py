import datetime
from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, Float, ForeignKey, Text
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from app.core.config import settings

# Create engine
# If using SQLite, we configure check_same_thread to False for async safety
is_sqlite = settings.DATABASE_URL.startswith("sqlite")
connect_args = {"check_same_thread": False} if is_sqlite else {}

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Dependency to inject DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# =====================================================================
# Database Table Models
# =====================================================================

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)
    role = Column(String(50), default="Standard User", nullable=False) # "Admin" or "Standard User"
    avatar_url = Column(String(500), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None), nullable=False)

    # Relationships
    settings = relationship("UserSettings", back_populates="user", uselist=False, cascade="all, delete-orphan")
    documents = relationship("Document", back_populates="owner", cascade="all, delete-orphan")
    chats = relationship("ChatHistory", back_populates="user", cascade="all, delete-orphan")


class UserSettings(Base):
    __tablename__ = "user_settings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    theme = Column(String(50), default="light", nullable=False) # "light" or "dark"
    language = Column(String(50), default="en", nullable=False)
    default_ocr_language = Column(String(50), default="en", nullable=False)
    email_notifications = Column(Boolean, default=True, nullable=False)

    # Relationships
    user = relationship("User", back_populates="settings")


class Document(Base):
    __tablename__ = "documents"

    id = Column(String(100), primary_key=True, index=True)  # UUID string
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    file_type = Column(String(50), nullable=False) # "pdf", "png", "jpg", "jpeg"
    size_bytes = Column(Integer, nullable=False)
    ocr_status = Column(String(50), default="PENDING", nullable=False) # "PENDING", "COMPLETED", "FAILED"
    processing_status = Column(String(50), default="IDLE", nullable=False) # "IDLE", "PROCESSING", "COMPLETED", "FAILED"
    document_type = Column(String(100), default="Generic Document", nullable=False)
    confidence_score = Column(Float, default=1.0, nullable=False)
    ocr_text = Column(Text, nullable=True)
    uploaded_by = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None), nullable=False)

    # Relationships
    owner = relationship("User", back_populates="documents")
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")
    chats = relationship("ChatHistory", back_populates="document", cascade="all, delete-orphan")
    embeddings = relationship("EmbeddingMetadata", back_populates="document", uselist=False, cascade="all, delete-orphan")


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(String(100), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    page_number = Column(Integer, nullable=False)
    chunk_index = Column(Integer, nullable=False)
    text_content = Column(Text, nullable=False)

    # Relationships
    document = relationship("Document", back_populates="chunks")


class ChatHistory(Base):
    __tablename__ = "chat_history"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(String(100), ForeignKey("documents.id", ondelete="CASCADE"), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    sources = Column(Text, nullable=True)  # JSON-serialized source array
    created_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None), nullable=False)

    # Relationships
    document = relationship("Document", back_populates="chats")
    user = relationship("User", back_populates="chats")


class EmbeddingMetadata(Base):
    __tablename__ = "embedding_metadata"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(String(100), ForeignKey("documents.id", ondelete="CASCADE"), unique=True, nullable=False)
    model_name = Column(String(255), nullable=False)
    dimensions = Column(Integer, nullable=False)
    chunk_count = Column(Integer, nullable=False)

    # Relationships
    document = relationship("Document", back_populates="embeddings")
