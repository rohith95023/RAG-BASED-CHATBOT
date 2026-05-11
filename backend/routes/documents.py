"""
Document management API routes for PDF RAG Chatbot application.
Provides endpoints for document CRUD operations with RAG integration.
"""
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from typing import List, Optional, Dict, Any
from pathlib import Path
import aiofiles
from config.settings import Settings
from models.schemas import (
    DocumentCreate, DocumentResponse, DocumentUpdate, DocumentListResponse
)
from services.rag_service import RAGService
from database.repositories import DocumentRepository
from api.dependencies import (
    get_settings, get_current_user, get_current_active_user,
    get_document_repository, get_rag_service
)
from utils.logger import get_logger
from utils.file_utils import (
    generate_unique_filename, ensure_directory, safe_delete_file,
    format_file_size
)
from utils.validators import validate_file_type


logger = get_logger(__name__)

# Create router
router = APIRouter(prefix="/documents", tags=["documents"])

SUPPORTED_DOCUMENT_EXTENSIONS = [
    ".pdf",
    ".docx", ".doc",
    ".xlsx", ".xlsm", ".xls",
    ".pptx",
    ".txt", ".md", ".markdown",
    ".csv", ".tsv",
    ".json", ".xml", ".html", ".htm",
    ".rtf",
    ".odt", ".ods", ".odp",
]


@router.post("/upload", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    category: str = Form(...),
    current_user: Dict[str, Any] = Depends(get_current_active_user),
    rag_service: RAGService = Depends(get_rag_service),
    document_repo: DocumentRepository = Depends(get_document_repository),
    settings: Settings = Depends(get_settings)
):
    """
    Upload and process a document.

    - **file**: Supported document file to upload (max 100MB)
    - **category**: Document category (general, technical, legal, financial, medical, other)
    - **Authorization**: Bearer token (required)

    Extracts text, creates embeddings, and builds vector index for search.
    """
    try:
        # Validate file type
        if not validate_file_type(file.filename, SUPPORTED_DOCUMENT_EXTENSIONS):
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail=f"Unsupported file type. Supported formats: {', '.join(SUPPORTED_DOCUMENT_EXTENSIONS)}"
            )

        # Validate category
        valid_categories = ['general', 'technical', 'legal', 'financial', 'medical', 'other']
        if category.lower() not in valid_categories:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid category. Must be one of: {', '.join(valid_categories)}"
            )

        logger.info(f"Document upload request: {file.filename} by {current_user.get('username')}")

        # Read file content
        content = await file.read()

        # Validate file size
        if len(content) > settings.MAX_UPLOAD_SIZE:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File size exceeds maximum of {format_file_size(settings.MAX_UPLOAD_SIZE)}"
            )

        # Create document record
        document_id = await document_repo.create_document(
            filename=file.filename,
            original_filename=file.filename,
            file_path="mongodb_stored",
            file_size=len(content),
            user_id=current_user["_id"],
            category=category.lower()
        )

        logger.info(f"Document record created: {document_id}")

        # Store file data in MongoDB
        await document_repo.store_file_data(document_id, content)

        # Process document with RAG pipeline
        processing_status = "completed"
        processing_error = None
        try:
            processing_result = await rag_service.process_document(
                file_path=None,
                document_id=document_id,
                filename=file.filename,
                category=category.lower(),
                chunk_size=settings.CHUNK_SIZE,
                use_semantic=True,
                content=content
            )

            logger.info(f"Document processing completed: {document_id}")

        except Exception as e:
            logger.error(f"Document processing failed: {e}")
            processing_status = "failed"
            processing_error = str(e)
            # Don't fail the upload — document record exists, user can re-process

        # Get the created document
        document = await document_repo.get_by_id(document_id)

        return DocumentResponse(
            id=document["_id"],
            filename=document["filename"],
            original_filename=document["original_filename"],
            category=document["category"],
            file_size=document["file_size"],
            user_id=document["user_id"],
            chunk_count=document.get("chunk_count", 0),
            uploaded_at=document["uploaded_at"],
            vector_index_path=document.get("vector_index_path"),
            metadata=document.get("metadata", {}),
            is_deleted=document.get("is_deleted", False),
            processing_status=processing_status,
            processing_error=processing_error
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Document upload failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Document upload failed"
        )


@router.post("/batch", response_model=List[DocumentResponse])
async def get_documents_batch(
    document_ids: List[str],
    current_user: Dict[str, Any] = Depends(get_current_active_user),
    document_repo: DocumentRepository = Depends(get_document_repository)
):
    """
    Get multiple documents by their IDs.

    - **document_ids**: List of document IDs
    - **Authorization**: Bearer token (required)
    """
    try:
        logger.info(f"Batch document request for {len(document_ids)} IDs by {current_user.get('username')}")
        
        documents = await document_repo.get_documents_by_ids(document_ids)
        
        # Verify ownership for each document
        # In a real app, you'd filter out documents not owned by the user
        user_docs = [doc for doc in documents if doc["user_id"] == current_user["_id"]]
        
        return [
            DocumentResponse(
                id=doc["_id"],
                filename=doc["filename"],
                original_filename=doc["original_filename"],
                category=doc["category"],
                file_size=doc["file_size"],
                user_id=doc["user_id"],
                chunk_count=doc.get("chunk_count", 0),
                uploaded_at=doc["uploaded_at"],
                vector_index_path=doc.get("vector_index_path"),
                metadata=doc.get("metadata", {}),
                is_deleted=doc.get("is_deleted", False),
                processing_status="completed" if doc.get("chunk_count", 0) > 0 else "failed",
            )
            for doc in user_docs
        ]

    except Exception as e:
        logger.error(f"Batch document request failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve documents"
        )


@router.get("/", response_model=DocumentListResponse)
async def list_documents(
    category: Optional[str] = None,
    search: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    current_user: Dict[str, Any] = Depends(get_current_user),
    document_repo: DocumentRepository = Depends(get_document_repository)
):
    """
    List documents for the current user.

    - **category**: Filter by category (optional)
    - **search**: Search in filename and category (optional)
    - **page**: Page number (default: 1)
    - **page_size**: Items per page (default: 20)
    - **Authorization**: Bearer token (required)
    """
    try:
        logger.info(f"Document list request by {current_user.get('username')}")

        # Validate pagination parameters
        if page < 1:
            page = 1
        if page_size < 1 or page_size > 100:
            page_size = 20

        skip = (page - 1) * page_size

        # Get documents based on search/filter
        if search:
            documents = await document_repo.search_documents(
                user_id=current_user["_id"],
                search_term=search,
                skip=skip,
                limit=page_size
            )
        else:
            documents = await document_repo.get_user_documents(
                user_id=current_user["_id"],
                category=category.lower() if category else None,
                skip=skip,
                limit=page_size
            )

        # Get total count
        total = await document_repo.count({
            "user_id": current_user["_id"],
            "is_deleted": False
        })

        # Calculate total pages
        total_pages = (total + page_size - 1) // page_size

        logger.info(f"Retrieved {len(documents)} documents")

        return DocumentListResponse(
            documents=[
                DocumentResponse(
                    id=doc["_id"],
                    filename=doc["filename"],
                    original_filename=doc["original_filename"],
                    category=doc["category"],
                    file_size=doc["file_size"],
                    user_id=doc["user_id"],
                    chunk_count=doc.get("chunk_count", 0),
                    uploaded_at=doc["uploaded_at"],
                    vector_index_path=doc.get("vector_index_path"),
                    metadata=doc.get("metadata", {}),
                    is_deleted=doc.get("is_deleted", False),
                    processing_status="completed" if doc.get("chunk_count", 0) > 0 else "failed",
                )
                for doc in documents
            ],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )

    except Exception as e:
        logger.error(f"Document list failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve documents"
        )


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    document_repo: DocumentRepository = Depends(get_document_repository)
):
    """
    Get a specific document by ID.

    - **document_id**: Document identifier
    - **Authorization**: Bearer token (required)

    Returns document details if user owns it.
    """
    try:
        document = await document_repo.get_by_id(document_id)

        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )

        # Check ownership
        if document["user_id"] != current_user["_id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to access this document"
            )

        # Check if deleted
        if document.get("is_deleted", False):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document has been deleted"
            )

        return DocumentResponse(
            id=document["_id"],
            filename=document["filename"],
            original_filename=document["original_filename"],
            category=document["category"],
            file_size=document["file_size"],
            user_id=document["user_id"],
            chunk_count=document.get("chunk_count", 0),
            uploaded_at=document["uploaded_at"],
            vector_index_path=document.get("vector_index_path"),
            metadata=document.get("metadata", {}),
            is_deleted=document.get("is_deleted", False)
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Document retrieval failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve document"
        )


@router.put("/{document_id}", response_model=DocumentResponse)
async def update_document(
    document_id: str,
    document_update: DocumentUpdate,
    current_user: Dict[str, Any] = Depends(get_current_active_user),
    document_repo: DocumentRepository = Depends(get_document_repository)
):
    """
    Update document metadata.

    - **document_id**: Document identifier
    - **filename**: New filename (optional)
    - **category**: New category (optional)
    - **metadata**: Additional metadata (optional)
    - **Authorization**: Bearer token (required)

    Allows renaming and changing category of documents.
    """
    try:
        # Get document
        document = await document_repo.get_by_id(document_id)

        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )

        # Check ownership
        if document["user_id"] != current_user["_id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to update this document"
            )

        # Prepare update data
        update_data = {}
        if document_update.filename is not None:
            update_data["filename"] = document_update.filename
        if document_update.category is not None:
            update_data["category"] = document_update.category
        if document_update.metadata is not None:
            update_data["metadata"] = document_update.metadata

        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No fields to update"
            )

        # Update document
        success = await document_repo.update(document_id, update_data)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update document"
            )

        # Get updated document
        updated_document = await document_repo.get_by_id(document_id)

        logger.info(f"Document updated: {document_id} by {current_user.get('username')}")

        return DocumentResponse(
            id=updated_document["_id"],
            filename=updated_document["filename"],
            original_filename=updated_document["original_filename"],
            category=updated_document["category"],
            file_size=updated_document["file_size"],
            user_id=updated_document["user_id"],
            chunk_count=updated_document.get("chunk_count", 0),
            uploaded_at=updated_document["uploaded_at"],
            vector_index_path=updated_document.get("vector_index_path"),
            metadata=updated_document.get("metadata", {}),
            is_deleted=updated_document.get("is_deleted", False)
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Document update failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update document"
        )


@router.delete("/{document_id}")
async def delete_document(
    document_id: str,
    current_user: Dict[str, Any] = Depends(get_current_active_user),
    rag_service: RAGService = Depends(get_rag_service),
    document_repo: DocumentRepository = Depends(get_document_repository)
):
    """
    Delete a document.

    - **document_id**: Document identifier
    - **Authorization**: Bearer token (required)

    Removes the file, metadata, and vector index.
    """
    try:
        # Get document
        document = await document_repo.get_by_id(document_id)

        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )

        # Check ownership
        if document["user_id"] != current_user["_id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to delete this document"
            )

        # Delete vector index
        await rag_service.delete_document_vectors(document_id)

        # Delete file
        file_path = Path(document["file_path"])
        if file_path.exists():
            safe_delete_file(file_path)
            logger.info(f"Deleted file: {file_path}")

        # Soft delete from database
        await document_repo.soft_delete(document_id)

        logger.info(f"Document deleted: {document_id} by {current_user.get('username')}")

        return {
            "message": "Document deleted successfully",
            "document_id": document_id
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Document deletion failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete document"
        )


@router.get("/categories/list")
async def list_categories(
    current_user: Dict[str, Any] = Depends(get_current_user),
    document_repo: DocumentRepository = Depends(get_document_repository)
):
    """
    Get list of document categories with counts.

    - **Authorization**: Bearer token (required)

    Returns categories and number of documents in each.
    """
    try:
        logger.info("Category list request")

        # Get all documents for user
        documents = await document_repo.get_user_documents(
            user_id=current_user["_id"],
            skip=0,
            limit=1000  # Get all for category counting
        )

        # Count by category
        category_counts = {}
        for doc in documents:
            category = doc.get("category", "general")
            category_counts[category] = category_counts.get(category, 0) + 1

        # Ensure all categories are represented
        all_categories = ['general', 'technical', 'legal', 'financial', 'medical', 'other']
        for category in all_categories:
            if category not in category_counts:
                category_counts[category] = 0

        return {
            "categories": [
                {"name": category, "count": category_counts.get(category, 0)}
                for category in all_categories
            ],
            "total_documents": len(documents)
        }

    except Exception as e:
        logger.error(f"Category list failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve categories"
        )


@router.get("/stats/overview")
async def get_document_stats(
    current_user: Dict[str, Any] = Depends(get_current_user),
    document_repo: DocumentRepository = Depends(get_document_repository)
):
    """
    Get document statistics for the current user.

    - **Authorization**: Bearer token (required)

    Returns summary statistics about user's documents.
    """
    try:
        logger.info(f"Document stats request by {current_user.get('username')}")

        # Get all documents for user
        documents = await document_repo.get_user_documents(
            user_id=current_user["_id"],
            skip=0,
            limit=1000
        )

        if not documents:
            return {
                "total_documents": 0,
                "total_size_bytes": 0,
                "total_size_formatted": "0 B",
                "total_chunks": 0,
                "categories": {},
                "recent_uploads": []
            }

        # Calculate statistics
        total_size = sum(doc["file_size"] for doc in documents)
        total_chunks = sum(doc.get("chunk_count", 0) for doc in documents)

        # Category breakdown
        categories = {}
        for doc in documents:
            category = doc.get("category", "general")
            categories[category] = categories.get(category, 0) + 1

        # Recent uploads (last 5)
        recent_documents = sorted(
            documents,
            key=lambda x: x["uploaded_at"],
            reverse=True
        )[:5]

        return {
            "total_documents": len(documents),
            "total_size_bytes": total_size,
            "total_size_formatted": format_file_size(total_size),
            "total_chunks": total_chunks,
            "categories": categories,
            "recent_uploads": [
                {
                    "id": doc["_id"],
                    "filename": doc["filename"],
                    "category": doc["category"],
                    "uploaded_at": doc["uploaded_at"]
                }
                for doc in recent_documents
            ]
        }

    except Exception as e:
        logger.error(f"Document stats failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve document statistics"
        )
