"""
MongoDB document models for PDF RAG Chatbot application.
Defines document structures and helper methods for database entities.
"""
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum
from bson import ObjectId


# ==================== Helper Functions ====================
def str_object_id() -> str:
    """Generate a new ObjectId as string"""
    return str(ObjectId())


def current_time() -> datetime:
    """Get current UTC datetime"""
    return datetime.utcnow()


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


# ==================== User Document ====================
class UserDocument(BaseModel):
    """MongoDB document structure for users"""
    id: Optional[str] = Field(None, alias="_id")
    username: str = Field(..., description="Unique username")
    email: str = Field(..., description="User email")
    hashed_password: str = Field(..., description="Bcrypt hashed password")
    role: UserRole = Field(default=UserRole.USER, description="User role")
    is_active: bool = Field(default=True, description="Account active status")
    created_at: datetime = Field(default_factory=current_time, description="Account creation time")
    last_login: Optional[datetime] = Field(None, description="Last login timestamp")
    preferences: Dict[str, Any] = Field(default_factory=dict, description="User preferences")

    model_config = ConfigDict(populate_by_name=True)

    def to_dict(self, include_password: bool = False) -> Dict[str, Any]:
        """Convert to dictionary, optionally excluding sensitive fields"""
        doc = self.model_dump(by_alias=True)
        if not include_password:
            doc.pop('hashed_password', None)
        return doc

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UserDocument":
        """Create UserDocument from dictionary"""
        if '_id' in data and isinstance(data['_id'], ObjectId):
            data['_id'] = str(data['_id'])
        return cls(**data)


# ==================== Document Document ====================
class DocumentDocument(BaseModel):
    """MongoDB document structure for documents"""
    id: Optional[str] = Field(None, alias="_id")
    filename: str = Field(..., description="Document filename")
    original_filename: str = Field(..., description="Original uploaded filename")
    file_path: str = Field(..., description="File storage path")
    file_size: int = Field(..., description="File size in bytes")
    category: DocumentCategory = Field(default=DocumentCategory.GENERAL, description="Document category")
    user_id: str = Field(..., description="Owner user ID")
    chunk_count: int = Field(default=0, description="Number of text chunks")
    uploaded_at: datetime = Field(default_factory=current_time, description="Upload timestamp")
    vector_index_path: Optional[str] = Field(None, description="Vector index file path")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Document metadata")
    is_deleted: bool = Field(default=False, description="Soft deletion flag")

    model_config = ConfigDict(populate_by_name=True)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return self.model_dump(by_alias=True)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DocumentDocument":
        """Create DocumentDocument from dictionary"""
        if '_id' in data and isinstance(data['_id'], ObjectId):
            data['_id'] = str(data['_id'])
        return cls(**data)


# ==================== Chat Session Document ====================
class ChatSessionDocument(BaseModel):
    """MongoDB document structure for chat sessions"""
    id: Optional[str] = Field(None, alias="_id")
    user_id: str = Field(..., description="Owner user ID")
    title: str = Field(..., description="Session title")
    document_ids: List[str] = Field(default_factory=list, description="Associated document IDs")
    created_at: datetime = Field(default_factory=current_time, description="Creation timestamp")
    updated_at: datetime = Field(default_factory=current_time, description="Last update timestamp")
    is_active: bool = Field(default=True, description="Session active status")
    context_window: Dict[str, Any] = Field(default_factory=dict, description="Context window data")

    model_config = ConfigDict(populate_by_name=True)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return self.model_dump(by_alias=True)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ChatSessionDocument":
        """Create ChatSessionDocument from dictionary"""
        if '_id' in data and isinstance(data['_id'], ObjectId):
            data['_id'] = str(data['_id'])
        return cls(**data)


# ==================== Chat Message Document ====================
class ChatMessageDocument(BaseModel):
    """MongoDB document structure for chat messages"""
    id: Optional[str] = Field(None, alias="_id")
    session_id: str = Field(..., description="Parent session ID")
    user_id: str = Field(..., description="Sender user ID")
    content: str = Field(..., description="Message content")
    is_user: bool = Field(..., description="Whether message is from user")
    timestamp: datetime = Field(default_factory=current_time, description="Message timestamp")
    referenced_documents: List[str] = Field(default_factory=list, description="Referenced document IDs")
    citations: List[Dict[str, Any]] = Field(default_factory=list, description="Source citations")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    model_config = ConfigDict(populate_by_name=True)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return self.model_dump(by_alias=True)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ChatMessageDocument":
        """Create ChatMessageDocument from dictionary"""
        if '_id' in data and isinstance(data['_id'], ObjectId):
            data['_id'] = str(data['_id'])
        return cls(**data)


# ==================== User Settings Document ====================
class UserSettingsDocument(BaseModel):
    """MongoDB document structure for user settings"""
    id: Optional[str] = Field(None, alias="_id")
    user_id: str = Field(..., description="Associated user ID")
    theme: str = Field(default="light", description="UI theme preference")
    language: str = Field(default="en", description="Interface language")
    notifications_enabled: bool = Field(default=True, description="Notification preferences")
    default_chunk_size: int = Field(default=500, description="Default chunk size for document processing")
    default_top_k: int = Field(default=5, description="Default top-k retrieval")
    created_at: datetime = Field(default_factory=current_time, description="Settings creation time")
    updated_at: datetime = Field(default_factory=current_time, description="Last update timestamp")

    model_config = ConfigDict(populate_by_name=True)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return self.model_dump(by_alias=True)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UserSettingsDocument":
        """Create UserSettingsDocument from dictionary"""
        if '_id' in data and isinstance(data['_id'], ObjectId):
            data['_id'] = str(data['_id'])
        return cls(**data)


# ==================== Helper Functions ====================
def create_user_document(username: str, email: str, hashed_password: str, role: UserRole = UserRole.USER) -> Dict[str, Any]:
    """Create a new user document"""
    return UserDocument(
        id=str_object_id(),
        username=username,
        email=email,
        hashed_password=hashed_password,
        role=role,
        is_active=True,
        created_at=current_time(),
        preferences={}
    ).to_dict()


def create_document_document(filename: str, original_filename: str, file_path: str,
                          file_size: int, user_id: str, category: DocumentCategory) -> Dict[str, Any]:
    """Create a new document document"""
    return DocumentDocument(
        id=str_object_id(),
        filename=filename,
        original_filename=original_filename,
        file_path=file_path,
        file_size=file_size,
        user_id=user_id,
        category=category,
        chunk_count=0,
        uploaded_at=current_time(),
        metadata={}
    ).to_dict()


def create_chat_session_document(user_id: str, title: str, document_ids: List[str] = None) -> Dict[str, Any]:
    """Create a new chat session document"""
    return ChatSessionDocument(
        id=str_object_id(),
        user_id=user_id,
        title=title,
        document_ids=document_ids or [],
        created_at=current_time(),
        updated_at=current_time(),
        is_active=True,
        context_window={}
    ).to_dict()


def create_chat_message_document(session_id: str, user_id: str, content: str,
                              is_user: bool, referenced_documents: List[str] = None) -> Dict[str, Any]:
    """Create a new chat message document"""
    return ChatMessageDocument(
        id=str_object_id(),
        session_id=session_id,
        user_id=user_id,
        content=content,
        is_user=is_user,
        timestamp=current_time(),
        referenced_documents=referenced_documents or [],
        citations=[],
        metadata={}
    ).to_dict()


def create_user_settings_document(user_id: str) -> Dict[str, Any]:
    """Create default user settings document"""
    return UserSettingsDocument(
        id=str_object_id(),
        user_id=user_id,
        theme="light",
        language="en",
        notifications_enabled=True,
        default_chunk_size=500,
        default_top_k=5,
        created_at=current_time(),
        updated_at=current_time()
    ).to_dict()