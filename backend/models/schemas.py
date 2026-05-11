"""
Pydantic schemas for PDF RAG Chatbot application.
Provides data models for API requests, responses, and internal data structures.
"""
from pydantic import BaseModel, Field, EmailStr, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


# ==================== Enums ====================
class UserRole(str, Enum):
    USER = "user"
    ADMIN = "admin"


class DocumentCategory(str, Enum):
    GENERAL = "general"
    TECHNICAL = "technical"
    LEGAL = "legal"
    FINANCIAL = "financial"
    MEDICAL = "medical"
    OTHER = "other"


class MessageType(str, Enum):
    USER = "user"
    AI = "ai"
    SYSTEM = "system"


# ==================== Authentication Schemas ====================
class UserBase(BaseModel):
    """Base user model with common fields"""
    username: str = Field(..., min_length=3, max_length=20, description="Username (3-20 characters)")
    email: EmailStr = Field(..., description="User email address")


class UserCreate(UserBase):
    """Schema for user registration"""
    password: str = Field(..., min_length=8, max_length=128, description="Password (8-128 characters)")
    confirm_password: str = Field(..., description="Password confirmation")

    @validator('confirm_password')
    def passwords_match(cls, v, values):
        if 'password' in values and v != values['password']:
            raise ValueError('Passwords do not match')
        return v


class UserLogin(BaseModel):
    """Schema for user login"""
    username: str = Field(..., description="Username")
    password: str = Field(..., description="Password")


class UserResponse(UserBase):
    """Schema for user response (without password)"""
    id: str = Field(..., description="User ID")
    role: UserRole = Field(default=UserRole.USER, description="User role")
    is_active: bool = Field(default=True, description="Account active status")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Account creation time")
    last_login: Optional[datetime] = Field(None, description="Last login time")
    preferences: Dict[str, Any] = Field(default_factory=dict, description="User preferences")

    class Config:
        schema_extra = {
            "example": {
                "id": "507f1f77bcf86cd799439011",
                "username": "john_doe",
                "email": "john@example.com",
                "role": "user",
                "is_active": True,
                "created_at": "2024-01-01T00:00:00",
                "last_login": "2024-01-15T12:30:00",
                "preferences": {"theme": "dark", "language": "en"}
            }
        }


class UserUpdate(BaseModel):
    """Schema for user profile update"""
    email: Optional[EmailStr] = Field(None, description="New email address")
    preferences: Optional[Dict[str, Any]] = Field(None, description="User preferences")


class PasswordChange(BaseModel):
    """Schema for password change"""
    current_password: str = Field(..., description="Current password")
    new_password: str = Field(..., min_length=8, max_length=128, description="New password")
    confirm_password: str = Field(..., description="Confirm new password")

    @validator('confirm_password')
    def passwords_match(cls, v, values):
        if 'new_password' in values and v != values['new_password']:
            raise ValueError('Passwords do not match')
        return v


class Token(BaseModel):
    """Schema for JWT token response"""
    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiration time in seconds")

    class Config:
        schema_extra = {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "expires_in": 1800
            }
        }


class TokenRefresh(BaseModel):
    """Schema for token refresh"""
    refresh_token: str = Field(..., description="Refresh token")


# ==================== Document Schemas ====================
class DocumentBase(BaseModel):
    """Base document model"""
    filename: str = Field(..., description="Document filename")
    category: DocumentCategory = Field(default=DocumentCategory.GENERAL, description="Document category")


class DocumentCreate(DocumentBase):
    """Schema for document creation (internal use)"""
    original_filename: str = Field(..., description="Original uploaded filename")
    file_path: str = Field(..., description="File storage path")
    file_size: int = Field(..., description="File size in bytes")
    user_id: str = Field(..., description="Owner user ID")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class DocumentUpdate(BaseModel):
    """Schema for document update"""
    filename: Optional[str] = Field(None, min_length=1, max_length=255, description="New filename")
    category: Optional[DocumentCategory] = Field(None, description="New category")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Updated metadata")


class DocumentResponse(DocumentBase):
    """Schema for document response"""
    id: str = Field(..., description="Document ID")
    original_filename: str = Field(..., description="Original filename")
    file_size: int = Field(..., description="File size in bytes")
    user_id: str = Field(..., description="Owner user ID")
    chunk_count: int = Field(default=0, description="Number of text chunks")
    uploaded_at: datetime = Field(default_factory=datetime.utcnow, description="Upload timestamp")
    vector_index_path: Optional[str] = Field(None, description="Vector index file path")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Document metadata")
    is_deleted: bool = Field(default=False, description="Deletion status")
    processing_status: str = Field(default="completed", description="RAG processing status: completed or failed")
    processing_error: Optional[str] = Field(None, description="Error message if processing failed")

    class Config:
        schema_extra = {
            "example": {
                "id": "507f1f77bcf86cd799439012",
                "filename": "research_paper_2024.pdf",
                "original_filename": "research_paper.pdf",
                "category": "technical",
                "file_size": 524288,
                "user_id": "507f1f77bcf86cd799439011",
                "chunk_count": 45,
                "uploaded_at": "2024-01-10T14:30:00",
                "vector_index_path": "507f1f77bcf86cd799439012.faiss",
                "metadata": {"author": "John Doe", "pages": 12},
                "is_deleted": False
            }
        }


class DocumentListResponse(BaseModel):
    """Schema for paginated document list"""
    documents: List[DocumentResponse] = Field(..., description="List of documents")
    total: int = Field(..., description="Total number of documents")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Number of documents per page")
    total_pages: int = Field(..., description="Total number of pages")


# ==================== Chat Schemas ====================
class ChatSessionBase(BaseModel):
    """Base chat session model"""
    title: str = Field(..., min_length=1, max_length=100, description="Session title")


class ChatSessionCreate(ChatSessionBase):
    """Schema for chat session creation"""
    document_ids: List[str] = Field(default_factory=list, description="Associated document IDs")


class ChatSessionUpdate(BaseModel):
    """Schema for chat session update"""
    title: Optional[str] = Field(None, min_length=1, max_length=100, description="New session title")
    document_ids: Optional[List[str]] = Field(None, description="Updated document IDs")
    is_active: Optional[bool] = Field(None, description="Session active status")


class ChatSessionResponse(ChatSessionBase):
    """Schema for chat session response"""
    id: str = Field(..., description="Session ID")
    user_id: str = Field(..., description="Owner user ID")
    document_ids: List[str] = Field(default_factory=list, description="Associated document IDs")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp")
    is_active: bool = Field(default=True, description="Session active status")
    context_window: Dict[str, Any] = Field(default_factory=dict, description="Context window data")

    class Config:
        schema_extra = {
            "example": {
                "id": "507f1f77bcf86cd799439013",
                "user_id": "507f1f77bcf86cd799439011",
                "title": "Research on AI",
                "document_ids": ["507f1f77bcf86cd799439012"],
                "created_at": "2024-01-10T15:00:00",
                "updated_at": "2024-01-10T16:30:00",
                "is_active": True,
                "context_window": {"max_history": 10}
            }
        }


class ChatMessageBase(BaseModel):
    """Base chat message model"""
    content: str = Field(..., min_length=1, max_length=10000, description="Message content")
    is_user: bool = Field(..., description="Whether message is from user")


class ChatMessageCreate(ChatMessageBase):
    """Schema for chat message creation"""
    session_id: str = Field(..., description="Parent session ID")
    referenced_documents: List[str] = Field(default_factory=list, description="Referenced document IDs")


class ChatMessageResponse(ChatMessageBase):
    """Schema for chat message response"""
    id: str = Field(..., description="Message ID")
    session_id: str = Field(..., description="Parent session ID")
    user_id: str = Field(..., description="Sender user ID")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Message timestamp")
    referenced_documents: List[str] = Field(default_factory=list, description="Referenced document IDs")
    citations: List[Dict[str, Any]] = Field(default_factory=list, description="Source citations")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    class Config:
        schema_extra = {
            "example": {
                "id": "507f1f77bcf86cd799439014",
                "session_id": "507f1f77bcf86cd799439013",
                "user_id": "507f1f77bcf86cd799439011",
                "content": "What is the main topic of the document?",
                "is_user": True,
                "timestamp": "2024-01-10T15:05:00",
                "referenced_documents": [],
                "citations": [],
                "metadata": {}
            }
        }


class ChatRequest(BaseModel):
    """Schema for RAG chat request"""
    question: str = Field(..., min_length=1, max_length=1000, description="User question")
    session_id: Optional[str] = Field(None, description="Chat session ID")
    document_ids: Optional[List[str]] = Field(default_factory=list, description="Document IDs to query (if empty, searches all documents)")
    top_k: int = Field(default=5, ge=1, le=20, description="Number of relevant chunks to retrieve")
    similarity_threshold: float = Field(default=0.7, ge=0.0, le=1.0, description="Similarity threshold for retrieval")
    stream: bool = Field(default=False, description="Enable streaming response")
    mode: str = Field(default="gemini", description="Chat mode: 'gemini' for standalone LLM, 'document' for RAG with documents")
    image: Optional[str] = Field(None, description="Base64 encoded image data")
    mime_type: Optional[str] = Field(None, description="MIME type for image (e.g., 'image/jpeg')")

    class Config:
        schema_extra = {
            "example": {
                "question": "What is the main topic of the document?",
                "session_id": "507f1f77bcf86cd799439013",
                "document_ids": ["507f1f77bcf86cd799439012"],
                "top_k": 5,
                "similarity_threshold": 0.7,
                "stream": False
            }
        }


class ChatResponse(BaseModel):
    """Schema for RAG chat response"""
    answer: str = Field(..., description="AI generated answer")
    sources: List[Dict[str, Any]] = Field(default_factory=list, description="Source information")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Response confidence score")
    session_id: str = Field(..., description="Chat session ID")
    message_id: str = Field(..., description="Generated message ID")

    class Config:
        schema_extra = {
            "example": {
                "answer": "The document discusses artificial intelligence research, focusing on machine learning algorithms...",
                "sources": [
                    {
                        "document_id": "507f1f77bcf86cd799439012",
                        "chunk_id": 3,
                        "content": "Artificial intelligence (AI) is intelligence demonstrated by machines...",
                        "confidence": 0.85
                    }
                ],
                "confidence": 0.82,
                "session_id": "507f1f77bcf86cd799439013",
                "message_id": "507f1f77bcf86cd799439014"
            }
        }


# ==================== System Schemas ====================
class HealthCheck(BaseModel):
    """Schema for health check response"""
    status: str = Field(..., description="Service status")
    version: str = Field(..., description="Application version")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Check timestamp")
    dependencies: Dict[str, str] = Field(default_factory=dict, description="Dependency statuses")


class SystemStats(BaseModel):
    """Schema for system statistics"""
    documents_count: int = Field(..., description="Total documents")
    users_count: int = Field(..., description="Total users")
    sessions_count: int = Field(..., description="Total chat sessions")
    messages_count: int = Field(..., description="Total messages")
    storage_used: int = Field(..., description="Storage used in bytes")
    models_loaded: List[str] = Field(default_factory=list, description="Loaded AI models")


class ErrorResponse(BaseModel):
    """Schema for error response"""
    error: bool = Field(default=True, description="Error indicator")
    type: str = Field(..., description="Error type")
    detail: str = Field(..., description="Error description")
    status_code: int = Field(..., description="HTTP status code")

    class Config:
        schema_extra = {
            "example": {
                "error": True,
                "type": "validation_error",
                "detail": "Invalid email format",
                "status_code": 422
            }
        }


# ==================== Settings Schemas ====================
class UserSettingsResponse(BaseModel):
    """Schema for user settings response"""
    id: str = Field(..., description="Settings ID")
    user_id: str = Field(..., description="Associated user ID")
    theme: str = Field(default="light", description="UI theme")
    language: str = Field(default="en", description="Interface language")
    notifications_enabled: bool = Field(default=True, description="Notification preferences")
    default_chunk_size: int = Field(default=500, description="Default chunk size")
    default_top_k: int = Field(default=5, description="Default top-k retrieval")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Settings creation time")

    class Config:
        schema_extra = {
            "example": {
                "id": "507f1f77bcf86cd799439015",
                "user_id": "507f1f77bcf86cd799439011",
                "theme": "dark",
                "language": "en",
                "notifications_enabled": True,
                "default_chunk_size": 500,
                "default_top_k": 5,
                "created_at": "2024-01-01T00:00:00"
            }
        }


class UserSettingsUpdate(BaseModel):
    """Schema for user settings update"""
    theme: Optional[str] = Field(None, description="New UI theme")
    language: Optional[str] = Field(None, description="New interface language")
    notifications_enabled: Optional[bool] = Field(None, description="New notification preference")
    default_chunk_size: Optional[int] = Field(None, ge=100, le=2000, description="New default chunk size")
    default_top_k: Optional[int] = Field(None, ge=1, le=20, description="New default top-k retrieval")
