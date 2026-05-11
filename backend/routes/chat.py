"""
Chat API routes for PDF RAG Chatbot application.
Provides endpoints for chat sessions, messages, and RAG queries.
"""
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from fastapi.responses import StreamingResponse
from typing import List, Optional, Dict, Any
import uuid
import json
import re
from models.schemas import (
    ChatRequest, ChatResponse, ChatSessionCreate, ChatSessionUpdate,
    ChatSessionResponse, ChatMessageResponse
)
from services.rag_service import RAGService
from services.llm_service import GeminiLLMService
from database.repositories import ChatRepository, DocumentRepository
from api.dependencies import (
    get_settings, get_current_user, get_current_active_user,
    get_rag_service, get_chat_repository, get_document_repository,
    get_llm_service
)
from utils.logger import get_logger


logger = get_logger(__name__)

# Create router
router = APIRouter(prefix="/chat", tags=["chat"])


def _normalize_question(question: str) -> str:
    """Normalize a user question for lightweight intent checks."""
    return re.sub(r"\s+", " ", (question or "").strip().lower())


def _document_id(doc: Dict[str, Any]) -> str:
    """Return a document id from Mongo-shaped documents."""
    value = doc.get("id") if isinstance(doc.get("id"), str) else doc.get("_id")
    return str(value) if value is not None else ""


def _is_document_metadata_request(question: str) -> bool:
    """Return true for document inventory/metadata questions that should not go through RAG."""
    normalized = _normalize_question(question)
    if not normalized:
        return False

    metadata_patterns = [
        r"\blist\b.*\bdocs?\b",
        r"\blist\b.*\bdocuments?\b",
        r"\bshow\b.*\bdocs?\b",
        r"\bshow\b.*\bdocuments?\b",
        r"\btitle(s)?\b.*\bdocs?\b",
        r"\btitle(s)?\b.*\bdocuments?\b",
        r"\bdoc(s)?\b.*\btitle(s)?\b",
        r"\bdocument(s)?\b.*\btitle(s)?\b",
        r"\bname(s)?\b.*\bdocs?\b",
        r"\bname(s)?\b.*\bdocuments?\b",
        r"\bfilename(s)?\b",
        r"\bfile name(s)?\b",
        r"\bcategory\b.*\bdocuments?\b",
        r"\bcategories\b.*\bdocuments?\b",
        r"\bstatus\b.*\bdocuments?\b",
        r"\bchunks?\b.*\bdocuments?\b",
        r"\bwhat\b.*\bdocuments?\b.*\b(uploaded|available|selected|active)\b",
        r"\bwhich\b.*\bdocuments?\b.*\b(uploaded|available|selected|active)\b",
        r"\bhow many\b.*\bdocuments?\b",
        r"\bcount\b.*\bdocuments?\b",
        r"\bdocument list\b",
        r"\buploaded documents?\b",
    ]
    return any(re.search(pattern, normalized) for pattern in metadata_patterns)


def _format_document_inventory(documents: List[Dict[str, Any]]) -> str:
    """Create a compact inventory block for prompts."""
    if not documents:
        return "No active documents."

    rows = []
    for index, doc in enumerate(documents, 1):
        filename = doc.get("filename") or doc.get("original_filename") or "Untitled document"
        original = doc.get("original_filename") or filename
        category = doc.get("category") or "general"
        chunks = doc.get("chunk_count", 0)
        status_text = doc.get("processing_status") or ("ready" if chunks else "uploaded")
        rows.append(
            f"{index}. id={_document_id(doc)}; filename={filename}; original={original}; "
            f"category={category}; chunks={chunks}; status={status_text}"
        )
    return "\n".join(rows)


def _format_document_metadata_answer(question: str, documents: List[Dict[str, Any]]) -> str:
    """Create a concise, deterministic list of active documents."""
    if not documents:
        return "No documents are available for this chat yet. Upload a PDF first, then switch to Documents mode."

    normalized = _normalize_question(question)
    wants_count_only = bool(re.search(r"\b(how many|count)\b", normalized)) and not re.search(r"\blist|show|title|name|file", normalized)
    if wants_count_only:
        return f"There {'is' if len(documents) == 1 else 'are'} {len(documents)} document{'s' if len(documents) != 1 else ''} available for this chat."

    lines = [f"I found {len(documents)} document{'s' if len(documents) != 1 else ''} available for this chat:"]
    for index, doc in enumerate(documents, 1):
        filename = doc.get("filename") or doc.get("original_filename") or "Untitled document"
        original = doc.get("original_filename") or filename
        category = doc.get("category") or "general"
        chunks = doc.get("chunk_count", 0)
        status_text = doc.get("processing_status") or ("ready" if chunks else "uploaded")

        if re.search(r"\btitle|name|filename|file name\b", normalized):
            lines.append(f"{index}. {filename}")
        else:
            lines.append(f"{index}. {filename} - original: {original} - category: {category} - {chunks} chunks - {status_text}")

    return "\n".join(lines)


def _document_mode_system_prompt(active_docs: List[Dict[str, Any]]) -> str:
    """System prompt for document mode, including the active corpus inventory."""
    inventory = _format_document_inventory(active_docs)
    return (
        "You are PDF Assistant in document mode. Answer using the active document corpus. "
        "Use retrieved document text as the primary evidence. The active document inventory below is also authoritative "
        "for filenames, titles, categories, counts, chunk counts, and processing status. "
        "If the retrieved text is incomplete, say exactly what could not be found and suggest a more specific question. "
        "Do not claim that no document context was provided when the inventory or retrieved chunks are present.\n\n"
        f"Active document inventory:\n{inventory}"
    )


@router.post("/query", response_model=ChatResponse)
async def query_documents(
    request: ChatRequest,
    background_tasks: BackgroundTasks,
    current_user: Dict[str, Any] = Depends(get_current_active_user),
    rag_service: RAGService = Depends(get_rag_service),
    llm_service: GeminiLLMService = Depends(get_llm_service),
    chat_repo: ChatRepository = Depends(get_chat_repository),
    document_repo: DocumentRepository = Depends(get_document_repository),
    settings = Depends(get_settings)
):
    """
    Execute chat query - either RAG mode or Gemini standalone mode.

    - **question**: User question
    - **mode**: 'gemini' for standalone LLM, 'document' for RAG with documents
    - **session_id**: Existing chat session ID (optional)
    - **document_ids**: List of document IDs to query (for document mode)
    - **top_k**: Number of relevant chunks to retrieve (default: 5)
    - **similarity_threshold**: Minimum similarity score (default: 0.7)
    - **stream**: Enable streaming response (default: false)
    - **image**: Base64 encoded image for vision queries
    - **Authorization**: Bearer token (required)

    Retrieves relevant document chunks and generates AI response (document mode),
    or generates standalone response using Gemini (gemini mode).
    """
    try:
        logger.info(f"Chat query request: {request.question[:50]}... by {current_user.get('username')}, mode: {request.mode}")

        # Determine mode - default to 'gemini' if not specified
        mode = request.mode or "gemini"

        # Create or use existing session
        if request.session_id:
            session = await chat_repo.get_session(request.session_id)
            if not session:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Chat session not found"
                )
            if session["user_id"] != current_user["_id"]:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You don't have permission to access this session"
                )
            session_id = request.session_id
        else:
            title = request.question[:50] + ("..." if len(request.question) > 50 else "")
            session_id = await chat_repo.create_session(
                user_id=current_user["_id"],
                title=title,
                document_ids=request.document_ids or []
            )
            logger.info(f"Created new chat session: {session_id}")

        # Save user message
        user_message_id = await chat_repo.create_message(
            session_id=session_id,
            user_id=current_user["_id"],
            content=request.question,
            is_user=True,
            referenced_documents=request.document_ids or [],
        )

        # Handle based on mode
        if mode == "gemini":
            # Standalone Gemini mode
            return await _handle_gemini_mode(
                request, llm_service, chat_repo, session_id, current_user["_id"],
                user_message_id, settings, background_tasks
            )
        else:
            # Document RAG mode
            return await _handle_document_mode(
                request, rag_service, chat_repo, document_repo,
                session_id, current_user, settings, background_tasks
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Chat query failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process query"
        )


async def _handle_gemini_mode(
    request: ChatRequest,
    llm_service: GeminiLLMService,
    chat_repo: ChatRepository,
    session_id: str,
    user_id: str,
    user_message_id: str,
    settings,
    background_tasks
):
    """Handle standalone Gemini LLM mode (no document context)"""
    if request.stream:
        async def stream_generator():
            try:
                full_answer = ""
                for chunk in llm_service.generate_streaming(
                    prompt=request.question,
                    max_length=settings.DEFAULT_MAX_LENGTH,
                    temperature=settings.DEFAULT_TEMPERATURE,
                    image=request.image,
                    mime_type=request.mime_type,
                ):
                    full_answer += chunk
                    yield json.dumps({"type": "content", "text": chunk}) + "\n"
                
                # Save AI message in background
                background_tasks.add_task(
                    _save_ai_message_simple,
                    chat_repo, session_id, user_id, full_answer, user_message_id
                )
            except Exception as e:
                yield json.dumps({"type": "error", "message": str(e)}) + "\n"

        return StreamingResponse(
            stream_generator(),
            media_type="text/event-stream"
        )

    # Non-streaming response
    answer = llm_service.generate_chat_response(
        messages=[{"role": "user", "content": request.question}],
        max_length=settings.DEFAULT_MAX_LENGTH,
        temperature=settings.DEFAULT_TEMPERATURE,
        image=request.image,
        mime_type=request.mime_type,
    )

    ai_message_id = await chat_repo.create_message(
        session_id=session_id,
        user_id=user_id,
        content=answer,
        is_user=False,
        message_id=user_message_id,
    )

    return ChatResponse(
        answer=answer,
        sources=[],
        confidence=1.0,
        session_id=session_id,
        message_id=ai_message_id
    )


async def _handle_document_mode(
    request: ChatRequest,
    rag_service: RAGService,
    chat_repo: ChatRepository,
    document_repo: DocumentRepository,
    session_id: str,
    current_user: dict,
    settings,
    background_tasks
):
    """Handle document-based RAG mode"""
    # Handle document IDs - if none provided, use all available documents
    doc_ids = request.document_ids or []
    active_docs = []
    
    if not doc_ids:
        logger.info(f"No document IDs provided, fetching all documents for user {current_user.get('username')}")
        active_docs = await document_repo.get_user_documents(current_user["_id"], limit=1000)
        doc_ids = [_document_id(doc) for doc in active_docs if _document_id(doc)]
        
        if not doc_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No documents found in your account. Please upload a document first."
            )
        
        logger.info(f"Automatically selected {len(doc_ids)} documents for query")
    else:
        for doc_id in doc_ids:
            doc = await document_repo.get_by_id(doc_id)
            if not doc:
                continue
            if doc.get("user_id") != current_user["_id"]:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You don't have permission to access one or more selected documents"
                )
            active_docs.append(doc)

    if _is_document_metadata_request(request.question):
        answer = _format_document_metadata_answer(request.question, active_docs)

        if request.stream:
            message_id = str(uuid.uuid4())

            async def list_stream_generator():
                yield json.dumps({
                    "type": "metadata",
                    "sources": [],
                    "confidence": 1.0,
                    "chunks_found": 0,
                    "documents_searched": len(active_docs),
                    "message_id": message_id
                }) + "\n"
                yield json.dumps({"type": "content", "text": answer}) + "\n"
                background_tasks.add_task(
                    _save_ai_message,
                    chat_repo,
                    session_id,
                    current_user["_id"],
                    answer,
                    doc_ids,
                    [],
                    message_id
                )

            return StreamingResponse(
                list_stream_generator(),
                media_type="text/event-stream"
            )

        ai_message_id = await chat_repo.create_message(
            session_id=session_id,
            user_id=current_user["_id"],
            content=answer,
            is_user=False,
            referenced_documents=doc_ids,
            citations=[]
        )

        return ChatResponse(
            answer=answer,
            sources=[],
            confidence=1.0,
            session_id=session_id,
            message_id=ai_message_id
        )

    # If streaming is requested
    if request.stream:
        message_id = str(uuid.uuid4())
        
        async def stream_generator(msg_id):
            generator = rag_service.rag_query_streaming(
                query=request.question,
                document_ids=doc_ids,
                top_k=request.top_k,
                similarity_threshold=request.similarity_threshold,
                system_prompt=_document_mode_system_prompt(active_docs),
                max_length=settings.DEFAULT_MAX_LENGTH,
                temperature=settings.DEFAULT_TEMPERATURE
            )

            full_answer = ""
            sources = []
            
            async for chunk in generator:
                try:
                    data = json.loads(chunk.strip())
                    if data.get("type") == "metadata":
                        data["message_id"] = msg_id
                        sources = data.get("sources", [])
                        yield json.dumps(data) + "\n"
                        continue
                    elif data.get("type") == "content":
                        full_answer += data.get("text", "")
                except:
                    pass
                
                yield chunk

            # Save AI message to database in background after stream completes
            if full_answer:
                background_tasks.add_task(
                    _save_ai_message,
                    chat_repo,
                    session_id,
                    current_user["_id"],
                    full_answer,
                    doc_ids,
                    sources,
                    msg_id
                )

        return StreamingResponse(
            stream_generator(message_id),
            media_type="text/event-stream"
        )

    # Execute standard RAG query
    rag_result = await rag_service.rag_query(
        query=request.question,
        document_ids=doc_ids,
        top_k=request.top_k,
        similarity_threshold=request.similarity_threshold,
        system_prompt=_document_mode_system_prompt(active_docs),
        max_length=settings.DEFAULT_MAX_LENGTH,
        temperature=settings.DEFAULT_TEMPERATURE
    )

    # Save AI message
    ai_message_id = await chat_repo.create_message(
        session_id=session_id,
        user_id=current_user["_id"],
        content=rag_result["answer"],
        is_user=False,
        referenced_documents=[chunk["document_id"] for chunk in rag_result["sources"]],
        citations=rag_result["sources"]
    )

    logger.info(f"Saved AI message: {ai_message_id}")

    # Format sources for response
    formatted_sources = [
        {
            "document_id": source["document_id"],
            "document_filename": source["document_filename"],
            "chunk_id": source["chunk_id"],
            "content_preview": source["content_preview"],
            "confidence": source["confidence"]
        }
        for source in rag_result["sources"]
    ]

    return ChatResponse(
        answer=rag_result["answer"],
        sources=formatted_sources,
        confidence=rag_result["confidence"],
        session_id=session_id,
        message_id=ai_message_id
    )


@router.post("/sessions", response_model=ChatSessionResponse, status_code=status.HTTP_201_CREATED)
async def create_chat_session(
    session_data: ChatSessionCreate,
    current_user: Dict[str, Any] = Depends(get_current_active_user),
    chat_repo: ChatRepository = Depends(get_chat_repository)
):
    """
    Create a new chat session.

    - **title**: Session title
    - **document_ids**: List of document IDs to associate
    - **Authorization**: Bearer token (required)

    Creates a new chat session for conversational context.
    """
    try:
        logger.info(f"Creating chat session by {current_user.get('username')}")

        session_id = await chat_repo.create_session(
            user_id=current_user["_id"],
            title=session_data.title,
            document_ids=session_data.document_ids
        )

        # Get created session
        session = await chat_repo.get_session(session_id)

        return ChatSessionResponse(
            id=session["_id"],
            user_id=session["user_id"],
            title=session["title"],
            document_ids=session.get("document_ids", []),
            created_at=session["created_at"],
            updated_at=session["updated_at"],
            is_active=session["is_active"],
            context_window=session.get("context_window", {})
        )

    except Exception as e:
        logger.error(f"Chat session creation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create chat session"
        )


@router.get("/sessions", response_model=List[ChatSessionResponse])
async def list_chat_sessions(
    is_active: Optional[bool] = None,
    page: int = 1,
    page_size: int = 20,
    current_user: Dict[str, Any] = Depends(get_current_user),
    chat_repo: ChatRepository = Depends(get_chat_repository)
):
    """
    List chat sessions for current user.

    - **is_active**: Filter by active status (optional)
    - **page**: Page number (default: 1)
    - **page_size**: Items per page (default: 20)
    - **Authorization**: Bearer token (required)

    Returns paginated list of chat sessions.
    """
    try:
        logger.info(f"Chat sessions list request by {current_user.get('username')}")

        # Validate pagination
        if page < 1:
            page = 1
        if page_size < 1 or page_size > 100:
            page_size = 20

        skip = (page - 1) * page_size

        # Get sessions
        sessions = await chat_repo.get_user_sessions(
            user_id=current_user["_id"],
            is_active=is_active,
            skip=skip,
            limit=page_size
        )

        logger.info(f"Retrieved {len(sessions)} chat sessions")

        return [
            ChatSessionResponse(
                id=session["_id"],
                user_id=session["user_id"],
                title=session["title"],
                document_ids=session.get("document_ids", []),
                created_at=session["created_at"],
                updated_at=session["updated_at"],
                is_active=session["is_active"],
                context_window=session.get("context_window", {})
            )
            for session in sessions
        ]

    except Exception as e:
        logger.error(f"Chat sessions list failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve chat sessions"
        )


@router.get("/sessions/{session_id}", response_model=ChatSessionResponse)
async def get_chat_session(
    session_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    chat_repo: ChatRepository = Depends(get_chat_repository)
):
    """
    Get a specific chat session.

    - **session_id**: Session identifier
    - **Authorization**: Bearer token (required)

    Returns session details if user owns it.
    """
    try:
        session = await chat_repo.get_session(session_id)

        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chat session not found"
            )

        # Check ownership
        if session["user_id"] != current_user["_id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to access this session"
            )

        return ChatSessionResponse(
            id=session["_id"],
            user_id=session["user_id"],
            title=session["title"],
            document_ids=session.get("document_ids", []),
            created_at=session["created_at"],
            updated_at=session["updated_at"],
            is_active=session["is_active"],
            context_window=session.get("context_window", {})
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Chat session retrieval failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve chat session"
        )


@router.put("/sessions/{session_id}", response_model=ChatSessionResponse)
async def update_chat_session(
    session_id: str,
    session_update: ChatSessionUpdate,
    current_user: Dict[str, Any] = Depends(get_current_active_user),
    chat_repo: ChatRepository = Depends(get_chat_repository)
):
    """
    Update a chat session.

    - **session_id**: Session identifier
    - **title**: New session title (optional)
    - **document_ids**: New document IDs (optional)
    - **is_active**: New active status (optional)
    - **Authorization**: Bearer token (required)

    Allows renaming, changing associated documents, or archiving sessions.
    """
    try:
        # Get session
        session = await chat_repo.get_session(session_id)

        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chat session not found"
            )

        # Check ownership
        if session["user_id"] != current_user["_id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to update this session"
            )

        # Prepare update data
        update_data = {}
        if session_update.title is not None:
            update_data["title"] = session_update.title
        if session_update.document_ids is not None:
            update_data["document_ids"] = session_update.document_ids
        if session_update.is_active is not None:
            update_data["is_active"] = session_update.is_active

        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No fields to update"
            )

        # Update session
        success = await chat_repo.update_session(session_id, update_data)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update chat session"
            )

        # Get updated session
        updated_session = await chat_repo.get_session(session_id)

        logger.info(f"Chat session updated: {session_id} by {current_user.get('username')}")

        return ChatSessionResponse(
            id=updated_session["_id"],
            user_id=updated_session["user_id"],
            title=updated_session["title"],
            document_ids=updated_session.get("document_ids", []),
            created_at=updated_session["created_at"],
            updated_at=updated_session["updated_at"],
            is_active=updated_session["is_active"],
            context_window=updated_session.get("context_window", {})
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Chat session update failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update chat session"
        )


@router.delete("/sessions/{session_id}")
async def delete_chat_session(
    session_id: str,
    current_user: Dict[str, Any] = Depends(get_current_active_user),
    chat_repo: ChatRepository = Depends(get_chat_repository)
):
    """
    Delete a chat session and all its messages.

    - **session_id**: Session identifier
    - **Authorization**: Bearer token (required)

    Permanently removes the session and all associated messages.
    """
    try:
        # Get session
        session = await chat_repo.get_session(session_id)

        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chat session not found"
            )

        # Check ownership
        if session["user_id"] != current_user["_id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to delete this session"
            )

        # Delete session
        success = await chat_repo.delete_session(session_id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete chat session"
            )

        logger.info(f"Chat session deleted: {session_id} by {current_user.get('username')}")

        return {
            "message": "Chat session deleted successfully",
            "session_id": session_id
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Chat session deletion failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete chat session"
        )


@router.get("/sessions/{session_id}/messages", response_model=List[ChatMessageResponse])
async def get_session_messages(
    session_id: str,
    skip: int = 0,
    limit: int = 100,
    current_user: Dict[str, Any] = Depends(get_current_user),
    chat_repo: ChatRepository = Depends(get_chat_repository)
):
    """
    Get messages from a chat session.

    - **session_id**: Session identifier
    - **skip**: Number of messages to skip (pagination)
    - **limit**: Maximum number of messages to return
    - **Authorization**: Bearer token (required)

    Returns paginated list of chat messages.
    """
    try:
        # Verify session ownership
        session = await chat_repo.get_session(session_id)

        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chat session not found"
            )

        if session["user_id"] != current_user["_id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to access this session"
            )

        # Get messages
        messages = await chat_repo.get_session_messages(
            session_id=session_id,
            skip=skip,
            limit=limit
        )

        logger.info(f"Retrieved {len(messages)} messages for session {session_id}")

        return [
            ChatMessageResponse(
                id=message["_id"],
                session_id=message["session_id"],
                user_id=message["user_id"],
                content=message["content"],
                is_user=message["is_user"],
                timestamp=message["timestamp"],
                referenced_documents=message.get("referenced_documents", []),
                citations=message.get("citations", []),
                metadata=message.get("metadata", {})
            )
            for message in messages
        ]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Session messages retrieval failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve session messages"
        )


@router.get("/stats/overview")
async def get_chat_stats(
    current_user: Dict[str, Any] = Depends(get_current_user),
    chat_repo: ChatRepository = Depends(get_chat_repository)
):
    """
    Get chat statistics for current user.

    - **Authorization**: Bearer token (required)

    Returns summary statistics about user's chat activity.
    """
    try:
        logger.info(f"Chat stats request by {current_user.get('username')}")

        # Get all sessions for user
        sessions = await chat_repo.get_user_sessions(
            user_id=current_user["_id"],
            skip=0,
            limit=1000  # Get all for statistics
        )

        if not sessions:
            return {
                "total_sessions": 0,
                "total_messages": 0,
                "active_sessions": 0,
                "recent_activity": []
            }

        # Calculate statistics
        total_sessions = len(sessions)
        active_sessions = sum(1 for s in sessions if s.get("is_active", True))

        # Get total messages (simplified estimate)
        total_messages = total_sessions * 10  # Estimate 10 messages per session

        # Recent activity (last 5 sessions)
        recent_sessions = sorted(
            sessions,
            key=lambda x: x["updated_at"],
            reverse=True
        )[:5]

        return {
            "total_sessions": total_sessions,
            "total_messages": total_messages,
            "active_sessions": active_sessions,
            "recent_activity": [
                {
                    "id": session["_id"],
                    "title": session["title"],
                    "updated_at": session["updated_at"],
                    "document_count": len(session.get("document_ids", []))
                }
                for session in recent_sessions
            ]
        }

    except Exception as e:
        logger.error(f"Chat stats failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve chat statistics"
        )


async def _save_ai_message(
    chat_repo: ChatRepository,
    session_id: str,
    user_id: str,
    answer: str,
    document_ids: List[str],
    sources: List[Dict[str, Any]],
    message_id: str
):
    """Internal helper to save AI message to database in background"""
    try:
        ai_message_id = await chat_repo.create_message(
            session_id=session_id,
            user_id=user_id,
            content=answer,
            is_user=False,
            referenced_documents=document_ids,
            citations=sources,
            message_id=message_id
        )
        
        logger.info(f"Background save completed for session {session_id}: {ai_message_id}")
    except Exception as e:
        logger.error(f"Failed to save AI message in background: {e}")


async def _save_ai_message_simple(
    chat_repo: ChatRepository,
    session_id: str,
    user_id: str,
    answer: str,
    message_id: str
):
    """Internal helper to save AI message for Gemini mode"""
    try:
        await chat_repo.create_message(
            session_id=session_id,
            user_id=user_id,
            content=answer,
            is_user=False,
            message_id=message_id
        )
        logger.info(f"Saved Gemini response for session {session_id}")
    except Exception as e:
        logger.error(f"Failed to save Gemini AI message: {e}")
