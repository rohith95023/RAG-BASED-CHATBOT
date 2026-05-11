"""
Custom exceptions for PDF RAG Chatbot application.
Provides specific exception types for different error scenarios.
"""
from fastapi import HTTPException, status


class BaseApplicationError(HTTPException):
    """Base exception for application errors"""
    def __init__(self, detail: str, status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR):
        super().__init__(status_code=status_code, detail=detail)
        self.detail = detail
        self.status_code = status_code


class AuthenticationError(BaseApplicationError):
    """Authentication related errors"""
    def __init__(self, detail: str = "Authentication failed"):
        super().__init__(detail, status.HTTP_401_UNAUTHORIZED)


class AuthorizationError(BaseApplicationError):
    """Authorization related errors"""
    def __init__(self, detail: str = "Permission denied"):
        super().__init__(detail, status.HTTP_403_FORBIDDEN)


class NotFoundError(BaseApplicationError):
    """Resource not found errors"""
    def __init__(self, detail: str = "Resource not found"):
        super().__init__(detail, status.HTTP_404_NOT_FOUND)


class ValidationError(BaseApplicationError):
    """Validation errors"""
    def __init__(self, detail: str = "Validation failed"):
        super().__init__(detail, status.HTTP_422_UNPROCESSABLE_ENTITY)


class FileProcessingError(BaseApplicationError):
    """File processing errors"""
    def __init__(self, detail: str = "File processing failed"):
        super().__init__(detail, status.HTTP_422_UNPROCESSABLE_ENTITY)


class ModelLoadingError(BaseApplicationError):
    """AI model loading errors"""
    def __init__(self, detail: str = "Failed to load AI model"):
        super().__init__(detail, status.HTTP_500_INTERNAL_SERVER_ERROR)


class VectorDatabaseError(BaseApplicationError):
    """Vector database errors"""
    def __init__(self, detail: str = "Vector database error"):
        super().__init__(detail, status.HTTP_500_INTERNAL_SERVER_ERROR)


class DatabaseError(BaseApplicationError):
    """Database errors"""
    def __init__(self, detail: str = "Database error"):
        super().__init__(detail, status.HTTP_500_INTERNAL_SERVER_ERROR)


class RateLimitError(BaseApplicationError):
    """Rate limiting errors"""
    def __init__(self, detail: str = "Rate limit exceeded"):
        super().__init__(detail, status.HTTP_429_TOO_MANY_REQUESTS)


class ConfigurationError(BaseApplicationError):
    """Configuration errors"""
    def __init__(self, detail: str = "Configuration error"):
        super().__init__(detail, status.HTTP_500_INTERNAL_SERVER_ERROR)


class FileSizeExceededError(BaseApplicationError):
    """File size exceeded errors"""
    def __init__(self, detail: str = "File size exceeds maximum allowed"):
        super().__init__(detail, status.HTTP_413_REQUEST_ENTITY_TOO_LARGE)


class InvalidFileTypeError(BaseApplicationError):
    """Invalid file type errors"""
    def __init__(self, detail: str = "Invalid file type"):
        super().__init__(detail, status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)


class ModelGenerationError(BaseApplicationError):
    """AI model generation errors"""
    def __init__(self, detail: str = "Failed to generate response"):
        super().__init__(detail, status.HTTP_500_INTERNAL_SERVER_ERROR)


class EmbeddingGenerationError(BaseApplicationError):
    """Embedding generation errors"""
    def __init__(self, detail: str = "Failed to generate embeddings"):
        super().__init__(detail, status.HTTP_500_INTERNAL_SERVER_ERROR)


# Error response format
class ErrorResponse:
    """Standard error response format"""
    @staticmethod
    def create(error: BaseApplicationError, error_type: str = "error") -> dict:
        """Create standardized error response"""
        return {
            "error": True,
            "type": error_type,
            "detail": error.detail,
            "status_code": error.status_code
        }