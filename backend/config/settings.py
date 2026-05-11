"""
Configuration settings for PDF RAG Chatbot application.
Uses Pydantic for type-safe configuration management with environment variable support.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from pathlib import Path
from typing import Optional


class Settings(BaseSettings):
    """Application settings with validation and defaults"""

    # Application Info
    APP_NAME: str = "FLASH MAN"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True

    # Server Configuration
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # MongoDB Configuration
    MONGODB_URL: str = "mongodb+srv://thepgmanager:Pgmanager2026@cluster0.jnxvlh8.mongodb.net/PG_MANAGER?retryWrites=true&w=majority&appName=PDFChatbot"
    MONGODB_DATABASE: str = "pdf_chatbot"

    # JWT Authentication
    JWT_SECRET_KEY: str = Field(..., env="JWT_SECRET_KEY")
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Gemini API Configuration (cloud LLM — replaces local model)
    GEMINI_API_KEY: str = Field(..., env="GEMINI_API_KEY")
    GEMINI_MODEL_NAME: str = Field(default="gemini-2.5-flash-lite", env="GEMINI_MODEL_NAME")

    # Embedding Model Configuration (local SentenceTransformers — kept)
    EMBEDDING_MODEL_NAME: str = "sentence-transformers/all-MiniLM-L6-v2"
    MODELS_DIR: Path = Field(default=Path("./models"), env="MODELS_DIR")

    # RAG Pipeline Settings
    CHUNK_SIZE: int = 500
    CHUNK_OVERLAP: int = 50
    TOP_K_RETRIEVAL: int = 5
    SIMILARITY_THRESHOLD: float = 0.3

    # Storage Paths
    UPLOAD_DIR: Path = Field(default=Path("./backend/uploads"), env="UPLOAD_DIR")
    VECTOR_STORE_DIR: Path = Field(default=Path("./backend/vector_store"), env="VECTOR_STORE_DIR")
    LOGS_DIR: Path = Field(default=Path("./backend/logs"), env="LOGS_DIR")

    # Performance Settings
    MAX_UPLOAD_SIZE: int = 100 * 1024 * 1024  # 100MB
    BATCH_SIZE_EMBEDDINGS: int = 32
    MAX_CONCURRENT_PROCESSES: int = 4

    # Model Generation Settings
    DEFAULT_MAX_LENGTH: int = 512
    DEFAULT_TEMPERATURE: float = 0.7
    DEFAULT_TOP_P: float = 0.9

    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = False
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_PERIOD: int = 60  # seconds

    # CORS Settings
    CORS_ORIGINS: list = ["*"]
    CORS_CREDENTIALS: bool = True
    CORS_METHODS: list = ["*"]
    CORS_HEADERS: list = ["*"]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Create necessary directories
        self.MODELS_DIR.mkdir(parents=True, exist_ok=True)
        self.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        self.VECTOR_STORE_DIR.mkdir(parents=True, exist_ok=True)
        self.LOGS_DIR.mkdir(parents=True, exist_ok=True)

        # Create model subdirectory for embeddings only (no local LLM)
        (self.MODELS_DIR / "embeddings").mkdir(parents=True, exist_ok=True)

    @property
    def embedding_model_path(self) -> Path:
        """Get embedding model storage path"""
        return self.MODELS_DIR / "embeddings"


# Global settings instance
settings = Settings()
