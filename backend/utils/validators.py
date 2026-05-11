"""
Input validators for PDF RAG Chatbot application.
Provides validation functions for common input types.
"""
import re
from typing import List, Optional
from pathlib import Path
from datetime import datetime


def validate_email(email: str) -> bool:
    """
    Validate email format.
    """
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def validate_username(username: str) -> bool:
    """
    Validate username format.
    Username should be 3-20 characters, alphanumeric with underscores.
    """
    pattern = r'^[a-zA-Z0-9_]{3,20}$'
    return re.match(pattern, username) is not None


def validate_password(password: str) -> tuple[bool, Optional[str]]:
    """
    Validate password strength.
    Returns (is_valid, error_message)
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    if len(password) > 128:
        return False, "Password must be less than 128 characters"
    if not re.search(r'[A-Z]', password):
        return False, "Password must contain at least one uppercase letter"
    if not re.search(r'[a-z]', password):
        return False, "Password must contain at least one lowercase letter"
    if not re.search(r'\d', password):
        return False, "Password must contain at least one digit"
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        return False, "Password must contain at least one special character"
    return True, None


def validate_file_type(filename: str, allowed_extensions: List[str] = None) -> bool:
    """
    Validate file type based on extension.
    """
    if allowed_extensions is None:
        allowed_extensions = [
            '.pdf',
            '.docx', '.doc',
            '.xlsx', '.xlsm', '.xls',
            '.pptx',
            '.txt', '.md', '.markdown',
            '.csv', '.tsv',
            '.json', '.xml', '.html', '.htm',
            '.rtf',
            '.odt', '.ods', '.odp',
        ]

    path = Path(filename)
    return path.suffix.lower() in [ext.lower() for ext in allowed_extensions]


def validate_file_size(file_size: int, max_size: int) -> bool:
    """
    Validate file size.
    """
    return file_size <= max_size


def validate_document_category(category: str) -> bool:
    """
    Validate document category.
    """
    valid_categories = ['general', 'technical', 'legal', 'financial', 'medical', 'other']
    return category.lower() in valid_categories


def validate_chunk_size(size: int) -> bool:
    """
    Validate chunk size for document processing.
    """
    return 100 <= size <= 2000


def validate_similarity_threshold(threshold: float) -> bool:
    """
    Validate similarity threshold (0.0 to 1.0).
    """
    return 0.0 <= threshold <= 1.0


def validate_top_k(top_k: int) -> bool:
    """
    Validate top-k retrieval parameter.
    """
    return 1 <= top_k <= 20


def validate_temperature(temperature: float) -> bool:
    """
    Validate temperature for model generation.
    """
    return 0.0 <= temperature <= 2.0


def validate_max_length(max_length: int) -> bool:
    """
    Validate max length for model generation.
    """
    return 1 <= max_length <= 4096


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename by removing dangerous characters.
    """
    # Remove path traversal and dangerous characters
    filename = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '', filename)
    # Remove leading/trailing spaces and dots
    filename = filename.strip('. ')
    # Limit length
    if len(filename) > 255:
        name, ext = Path(filename).stem, Path(filename).suffix
        filename = name[:255-len(ext)] + ext
    return filename if filename else "unnamed_file"


def validate_mongodb_id(mongodb_id: str) -> bool:
    """
    Validate MongoDB ObjectId format.
    """
    pattern = r'^[0-9a-fA-F]{24}$'
    return re.match(pattern, mongodb_id) is not None


def validate_url(url: str) -> bool:
    """
    Validate URL format.
    """
    pattern = r'^https?://[^\s/$.?#].[^\s]*$'
    return re.match(pattern, url) is not None


def validate_date_string(date_string: str, date_format: str = "%Y-%m-%d") -> bool:
    """
    Validate date string format.
    """
    try:
        datetime.strptime(date_string, date_format)
        return True
    except ValueError:
        return False


def validate_search_query(query: str) -> tuple[bool, Optional[str]]:
    """
    Validate search query.
    Returns (is_valid, error_message)
    """
    if not query or not query.strip():
        return False, "Search query cannot be empty"
    if len(query) > 500:
        return False, "Search query is too long (max 500 characters)"
    # Check for potential SQL injection patterns
    dangerous_patterns = ['--', ';', 'drop ', 'delete ', 'update ', 'insert ']
    query_lower = query.lower()
    for pattern in dangerous_patterns:
        if pattern in query_lower:
            return False, "Search query contains invalid characters"
    return True, None


def validate_pagination_params(page: int, page_size: int, max_page_size: int = 100) -> tuple[bool, Optional[str]]:
    """
    Validate pagination parameters.
    Returns (is_valid, error_message)
    """
    if page < 1:
        return False, "Page number must be at least 1"
    if page_size < 1:
        return False, "Page size must be at least 1"
    if page_size > max_page_size:
        return False, f"Page size cannot exceed {max_page_size}"
    return True, None


class ValidationError(Exception):
    """Custom validation exception"""
    def __init__(self, message: str, field: str = None):
        self.message = message
        self.field = field
        super().__init__(self.message)

    def to_dict(self) -> dict:
        """Convert to dictionary format"""
        result = {"message": self.message}
        if self.field:
            result["field"] = self.field
        return result


def validate_user_registration(username: str, email: str, password: str) -> List[ValidationError]:
    """
    Validate user registration data.
    Returns list of validation errors.
    """
    errors = []

    if not validate_username(username):
        errors.append(ValidationError("Invalid username format", "username"))

    if not validate_email(email):
        errors.append(ValidationError("Invalid email format", "email"))

    is_valid, error_message = validate_password(password)
    if not is_valid:
        errors.append(ValidationError(error_message, "password"))

    return errors


def validate_document_upload(filename: str, file_size: int, category: str,
                          max_size: int = 100 * 1024 * 1024) -> List[ValidationError]:
    """
    Validate document upload data.
    Returns list of validation errors.
    """
    errors = []

    if not validate_file_type(filename):
        errors.append(ValidationError("Unsupported document file type", "file"))

    if not validate_file_size(file_size, max_size):
        errors.append(ValidationError(f"File size exceeds maximum of {max_size} bytes", "file"))

    if not validate_document_category(category):
        errors.append(ValidationError("Invalid document category", "category"))

    return errors


def validate_rag_query(query: str, top_k: int, similarity_threshold: float) -> List[ValidationError]:
    """
    Validate RAG query parameters.
    Returns list of validation errors.
    """
    errors = []

    is_valid, error_message = validate_search_query(query)
    if not is_valid:
        errors.append(ValidationError(error_message, "query"))

    if not validate_top_k(top_k):
        errors.append(ValidationError("Invalid top_k parameter (must be 1-20)", "top_k"))

    if not validate_similarity_threshold(similarity_threshold):
        errors.append(ValidationError("Invalid similarity_threshold (must be 0.0-1.0)", "similarity_threshold"))

    return errors
