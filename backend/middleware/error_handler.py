"""
Global exception handling middleware for PDF RAG Chatbot application.
Provides comprehensive error handling and logging.
"""
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
import traceback
from utils.logger import get_logger
from models.schemas import ErrorResponse


logger = get_logger(__name__)


class GlobalExceptionHandler:
    """Global exception handler for application-wide error management"""

    async def http_exception_handler(self, request: Request, exc: StarletteHTTPException):
        """Handle HTTP exceptions"""
        logger.error(f"HTTP error: {exc.status_code} - {exc.detail}")

        return JSONResponse(
            status_code=exc.status_code,
            content=ErrorResponse(
                error=True,
                type="http_error",
                detail=exc.detail,
                status_code=exc.status_code
            ).dict()
        )

    async def validation_exception_handler(self, request: Request, exc: RequestValidationError):
        """Handle validation errors"""
        logger.error(f"Validation error: {exc.errors()}")

        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=ErrorResponse(
                error=True,
                type="validation_error",
                detail="Validation failed",
                status_code=422
            ).dict()
        )

    async def general_exception_handler(self, request: Request, exc: Exception):
        """Handle all other exceptions"""
        logger.error(f"Unhandled exception: {str(exc)}\n{traceback.format_exc()}")

        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=ErrorResponse(
                error=True,
                type="internal_error",
                detail="Internal server error",
                status_code=500
            ).dict()
        )