"""
FastAPI dependency injection for authentication and services.
Provides reusable dependencies for route handlers.
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from typing import Optional
from config.settings import settings
from database.connection import db_manager
from services.auth_service import AuthService
from services.llm_service import GeminiLLMService
from services.embedding_service import EnhancedEmbeddingService as EmbeddingService
from services.vector_service import EnhancedVectorService
from services.pdf_service import EnhancedPDFService as PDFService
from services.chunk_service import SemanticChunkingService as ChunkService
from services.rag_service import RAGService
from database.repositories import UserRepository, DocumentRepository, ChatRepository, UserSettingsRepository
from utils.logger import get_logger

logger = get_logger(__name__)


# OAuth2 scheme for JWT authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


# Service instances (singleton pattern)
_auth_service: Optional[AuthService] = None
_llm_service: Optional[GeminiLLMService] = None
_embedding_service: Optional[EmbeddingService] = None
_vector_service: Optional[EnhancedVectorService] = None
_pdf_service: Optional[PDFService] = None
_chunk_service: Optional[ChunkService] = None
_rag_service: Optional[RAGService] = None
_user_repo: Optional[UserRepository] = None
_document_repo: Optional[DocumentRepository] = None
_chat_repo: Optional[ChatRepository] = None
_settings_repo: Optional[UserSettingsRepository] = None


def get_settings():
    """Get application settings"""
    return settings


def get_database():
    """Get MongoDB database instance"""
    return db_manager.get_database(settings)


# Service dependencies
def get_auth_service() -> AuthService:
    """Get authentication service instance"""
    global _auth_service
    if _auth_service is None:
        _auth_service = AuthService(settings)
    return _auth_service


def get_llm_service() -> GeminiLLMService:
    """Get Gemini LLM service instance"""
    global _llm_service
    if _llm_service is None:
        _llm_service = GeminiLLMService(settings)
    return _llm_service


def get_embedding_service() -> EmbeddingService:
    """Get embedding service instance (lazy loaded)"""
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService(settings)
    return _embedding_service


def get_vector_service() -> EnhancedVectorService:
    """Get vector service instance"""
    global _vector_service
    if _vector_service is None:
        _vector_service = EnhancedVectorService(settings.VECTOR_STORE_DIR)
    return _vector_service


def get_pdf_service() -> PDFService:
    """Get PDF service instance"""
    global _pdf_service
    if _pdf_service is None:
        _pdf_service = PDFService()
    return _pdf_service


def get_chunk_service() -> ChunkService:
    """Get chunk service instance"""
    global _chunk_service
    if _chunk_service is None:
        embedding_service = get_embedding_service()
        _chunk_service = ChunkService(embedding_service)
    return _chunk_service


def get_rag_service() -> RAGService:
    """Get RAG service instance (orchestrates all services)"""
    global _rag_service
    if _rag_service is None:
        logger.info(f"Creating RAGService with settings: {settings}")
        _rag_service = RAGService(
            llm_service=get_llm_service(),
            embedding_service=get_embedding_service(),
            vector_service=get_vector_service(),
            pdf_service=get_pdf_service(),
            chunk_service=get_chunk_service(),
            document_repo=get_document_repository(),
            settings=settings
        )
    return _rag_service


# Repository dependencies
def get_user_repository() -> UserRepository:
    """Get user repository instance"""
    global _user_repo
    if _user_repo is None:
        _user_repo = UserRepository(get_database())
    return _user_repo


def get_document_repository() -> DocumentRepository:
    """Get document repository instance"""
    global _document_repo
    if _document_repo is None:
        _document_repo = DocumentRepository(get_database())
    return _document_repo


def get_chat_repository() -> ChatRepository:
    """Get chat repository instance"""
    global _chat_repo
    if _chat_repo is None:
        _chat_repo = ChatRepository(get_database())
    return _chat_repo


def get_user_settings_repository() -> UserSettingsRepository:
    """Get user settings repository instance"""
    global _settings_repo
    if _settings_repo is None:
        _settings_repo = UserSettingsRepository(get_database())
    return _settings_repo


# Authentication dependencies
async def get_current_user() -> dict:
    """
    Mock authenticated user.
    Bypasses authentication to allow open access.
    """
    return {
        "_id": "000000000000000000000000",
        "username": "local_dev",
        "email": "local@example.com",
        "is_active": True,
        "role": "admin"
    }


async def get_current_active_user(
    current_user: dict = Depends(get_current_user)
) -> dict:
    """
    Get current active user.
    Raises HTTPException if user is not active.
    """
    if not current_user.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled"
        )
    return current_user


async def get_current_admin_user(
    current_user: dict = Depends(get_current_user)
) -> dict:
    """
    Get current admin user.
    Raises HTTPException if user is not an admin.
    """
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    return current_user


# Optional dependencies
async def get_optional_current_user() -> Optional[dict]:
    """
    Mock authenticated user.
    Useful for routes that work with or without authentication.
    """
    return await get_current_user()