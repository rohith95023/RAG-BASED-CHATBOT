"""
FLASH MAN Backend - FastAPI Application
Main application with upload and chat endpoints.
"""
from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import logging

from services.pdf_service import pdf_service
from services.embedding_service import embedding_service
from services.vector_service import vector_service
from services.llm_service import llm_service
from utils.file_utils import save_uploaded_file, create_data_directories

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="FLASH MAN API",
    description="Backend for FLASH MAN with vector search and LLM integration",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request/Response models
class ChatRequest(BaseModel):
    question: str
    top_k: Optional[int] = 3

class ChatResponse(BaseModel):
    answer: str
    sources: List[str]

class UploadResponse(BaseModel):
    message: str
    filename: str
    category: str
    chunks_processed: int
    total_vectors: int

class HealthResponse(BaseModel):
    status: str
    embedding_model: str
    index_size: int
    ollama_available: bool

# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    logger.info("Starting FLASH MAN Backend...")

    # Create necessary directories
    create_data_directories()

    # Check embedding service
    if embedding_service.is_loaded():
        logger.info(f"Embedding model loaded: {embedding_service.model_name}")
    else:
        logger.error("Failed to load embedding model")

    # Check vector service
    logger.info(f"Vector database loaded. Size: {vector_service.get_index_size()} vectors")

    # Check Ollama
    if llm_service.check_ollama_available():
        logger.info("Ollama is available")
    else:
        logger.warning("Ollama is not available. Chat functionality will not work.")

    logger.info("FLASH MAN Backend started successfully")


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint.
    Returns status of all services.
    """
    try:
        return HealthResponse(
            status="healthy",
            embedding_model=embedding_service.model_name,
            index_size=vector_service.get_index_size(),
            ollama_available=llm_service.check_ollama_available()
        )
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Health check failed")


@app.post("/upload", response_model=UploadResponse)
async def upload_pdf(
    file: UploadFile = File(...),
    category: str = Form(...)
):
    """
    Upload and process a PDF file.

    Args:
        file: PDF file to upload
        category: Category to organize the file

    Returns:
        Upload response with processing details
    """
    try:
        logger.info(f"Uploading file: {file.name}, category: {category}")

        # Validate file type
        if not file.filename.endswith('.pdf'):
            raise HTTPException(status_code=400, detail="Only PDF files are allowed")

        # Read file content
        file_content = await file.read()

        # Save file locally
        file_path = save_uploaded_file(file_content, category, file.filename)
        logger.info(f"File saved to: {file_path}")

        # Process PDF - extract text and create chunks
        chunks = pdf_service.process_pdf(file_path)
        logger.info(f"Extracted {len(chunks)} text chunks")

        # Generate embeddings
        embeddings = embedding_service.generate_embeddings(chunks)
        logger.info(f"Generated embeddings: shape {embeddings.shape}")

        # Prepare metadata
        metadata = [{
            "filename": file.filename,
            "category": category
        } for _ in chunks]

        # Add to vector database
        vector_service.add_embeddings(embeddings, chunks, metadata)

        # Save index
        vector_service.save_index()
        logger.info(f"Vector database updated. Total vectors: {vector_service.get_index_size()}")

        return UploadResponse(
            message="File uploaded and processed successfully",
            filename=file.filename,
            category=category,
            chunks_processed=len(chunks),
            total_vectors=vector_service.get_index_size()
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upload failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Chat with the PDF documents.

    Args:
        request: Chat request with question and top_k parameter

    Returns:
        Chat response with answer and sources
    """
    try:
        logger.info(f"Chat request: {request.question}")

        # Check if vector database has any documents
        if vector_service.get_index_size() == 0:
            raise HTTPException(
                status_code=400,
                detail="No documents uploaded yet. Please upload a PDF first."
            )

        # Check Ollama availability
        if not llm_service.check_ollama_available():
            raise HTTPException(
                status_code=503,
                detail="Ollama service is not available. Please ensure Ollama is running."
            )

        # Generate embedding for question
        question_embedding = embedding_service.generate_single_embedding(request.question)

        # Search for relevant chunks
        results = vector_service.search(question_embedding, k=request.top_k)
        logger.info(f"Found {len(results)} relevant chunks")

        if not results:
            return ChatResponse(
                answer="No relevant information found in the uploaded documents.",
                sources=[]
            )

        # Extract text chunks for LLM
        relevant_chunks = [result[0] for result in results]
        sources = [result[2].get("filename", "Unknown") for result in results]

        # Generate response using LLM
        answer = llm_service.generate_response_with_chunks(request.question, relevant_chunks)
        logger.info(f"Generated answer: {answer[:100]}...")

        return ChatResponse(
            answer=answer,
            sources=list(set(sources))  # Remove duplicates
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Chat failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Chat failed: {str(e)}")


@app.delete("/vectors")
async def clear_vectors():
    """
    Clear all vectors from the database.
    """
    try:
        vector_service.clear_index()
        logger.info("Vector database cleared")
        return {"message": "Vector database cleared successfully"}
    except Exception as e:
        logger.error(f"Failed to clear vectors: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to clear vectors: {str(e)}")


@app.get("/stats")
async def get_stats():
    """
    Get statistics about the vector database.
    """
    try:
        return {
            "total_vectors": vector_service.get_index_size(),
            "embedding_dimension": vector_service.dimension,
            "embedding_model": embedding_service.model_name,
            "documents": list(set([meta.get("filename", "Unknown") for meta in vector_service.metadata]))
        }
    except Exception as e:
        logger.error(f"Failed to get stats: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
