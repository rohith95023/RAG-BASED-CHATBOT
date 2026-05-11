"""
Main FastAPI application for PDF RAG Chatbot.
Entry point that integrates all routes, middleware, and services.
"""
from fastapi import FastAPI, Request, status, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import traceback

from config.settings import settings
from database.connection import db_manager
from api.dependencies import (
    get_settings, get_auth_service, get_llm_service,
    get_embedding_service, get_vector_service,
    get_pdf_service, get_chunk_service, get_rag_service
)
from models.schemas import HealthCheck, SystemStats, ErrorResponse
from routes import auth, documents, chat
from utils.logger import setup_logging


# Setup logging
logger = setup_logging(settings.APP_NAME)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    Handles startup and shutdown events.
    """
    # Startup
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info(f"Debug mode: {settings.DEBUG}")

    try:
        # Connect to database
        await db_manager.connect(settings)
        logger.info("Database connection established")

        # Initialize services (lazy loading)
        logger.info("Services initialized (lazy loading enabled)")

        logger.info("Application startup completed")

    except Exception as e:
        logger.error(f"Application startup failed: {e}")
        raise

    yield

    # Shutdown
    logger.info("Shutting down application...")

    try:
        # Disconnect from database
        await db_manager.disconnect()
        logger.info("Database connection closed")

        # Cleanup services if needed
        logger.info("Services cleaned up")

        logger.info("Application shutdown completed")

    except Exception as e:
        logger.error(f"Application shutdown failed: {e}")


# Create FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Production-grade FLASH MAN with local AI models",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
    debug=settings.DEBUG
)


# ==================== Middleware ====================

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=settings.CORS_CREDENTIALS,
    allow_methods=settings.CORS_METHODS,
    allow_headers=settings.CORS_HEADERS,
)


# ==================== Exception Handlers ====================


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle all unhandled exceptions"""
    logger.error(f"Unhandled exception: {exc}\n{traceback.format_exc()}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            error=True,
            type="internal_error",
            detail=str(exc),
            status_code=500
        ).dict()
    )


# ==================== Routes ====================

# Health check
@app.get("/", tags=["health"])
async def root():
    """Root endpoint with basic information"""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
        "message": "FLASH MAN API is running"
    }


@app.get("/health", response_model=HealthCheck, tags=["health"])
async def health_check():
    """
    Health check endpoint.

    Returns service status and dependency health.
    """
    try:
        # Check database health
        db_health = await db_manager.health_check()

        # Check service availability
        dependencies = {
            "database": db_health.get("status", "unknown"),
            "mongodb": "connected" if db_health.get("ping") else "disconnected"
        }

        return HealthCheck(
            status="healthy" if db_health.get("status") == "healthy" else "degraded",
            version=settings.APP_VERSION,
            timestamp=None,  # Will be set by model
            dependencies=dependencies
        )

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return HealthCheck(
            status="unhealthy",
            version=settings.APP_VERSION,
            timestamp=None,
            dependencies={"error": str(e)}
        )


@app.get("/stats", response_model=SystemStats, tags=["health"])
async def get_system_stats():
    """
    Get system statistics.

    Returns information about documents, users, and resource usage.
    """
    try:
        # Get database statistics
        from database.repositories import UserRepository, DocumentRepository, ChatRepository

        user_repo = UserRepository(db_manager.get_database(settings))
        document_repo = DocumentRepository(db_manager.get_database(settings))

        # Get counts
        documents_count = await document_repo.count()
        users_count = await user_repo.count()
        sessions_count = 0  # Placeholder
        messages_count = 0  # Placeholder

        # Get storage information
        from utils.file_utils import get_directory_size, format_file_size
        storage_used = get_directory_size(settings.UPLOAD_DIR)
        vector_storage = get_directory_size(settings.VECTOR_STORE_DIR)
        total_storage = storage_used + vector_storage

        # Check loaded models
        models_loaded = []
        try:
            llm_info = get_llm_service().get_model_info()
            models_loaded.append(f"LLM: {llm_info['model_name']} ({llm_info.get('provider', 'Gemini API')})")
        except:
            pass

        try:
            embedding_info = get_embedding_service().get_model_info()
            if embedding_info["is_loaded"]:
                models_loaded.append(f"Embedding: {embedding_info['model_name']}")
        except:
            pass

        return SystemStats(
            documents_count=documents_count,
            users_count=users_count,
            sessions_count=sessions_count,
            messages_count=messages_count,
            storage_used=total_storage,
            models_loaded=models_loaded
        )

    except Exception as e:
        logger.error(f"System stats failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve system statistics"
        )


# Include route modules
app.include_router(auth.router)
app.include_router(documents.router)
app.include_router(chat.router)


# ==================== Main Entry Point ====================

if __name__ == "__main__":
    import uvicorn

    # Run the application
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info" if not settings.DEBUG else "debug",
        access_log=True,
        workers=1  # Single worker for development
    )


# Export for testing
__all__ = ["app"]


