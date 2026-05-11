"""
Logging middleware for PDF RAG Chatbot application.
Provides request/response logging and monitoring.
"""
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from time import time
import json
from utils.logger import get_logger


logger = get_logger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for logging HTTP requests and responses"""

    async def dispatch(self, request: Request, call_next):
        """Process request and log information"""
        start_time = time()

        # Get request information
        method = request.method
        url = str(request.url)
        client_host = request.client.host if request.client else "unknown"

        # Log request
        logger.info(f"Incoming request: {method} {url} from {client_host}")

        try:
            # Process request
            response = await call_next(request)

            # Calculate processing time
            process_time = (time() - start_time) * 1000  # Convert to milliseconds

            # Get response information
            status_code = response.status_code

            # Log response
            if status_code >= 500:
                logger.error(f"Request failed: {method} {url} - {status_code} - {process_time:.2f}ms")
            elif status_code >= 400:
                logger.warning(f"Request error: {method} {url} - {status_code} - {process_time:.2f}ms")
            else:
                logger.info(f"Request completed: {method} {url} - {status_code} - {process_time:.2f}ms")

            # Add processing time to response headers
            response.headers["X-Process-Time"] = str(process_time)

            return response

        except Exception as e:
            # Log exception
            process_time = (time() - start_time) * 1000
            logger.error(f"Request exception: {method} {url} - {str(e)} - {process_time:.2f}ms")

            # Re-raise exception
            raise