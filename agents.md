# FLASH MAN Project Context

## Overview

FLASH MAN is a production-style local PDF RAG chatbot. It combines a React frontend with a FastAPI backend, MongoDB Atlas for persistence, FAISS for vector search, and local HuggingFace-based model services.

## Current Architecture

```text
backend/   FastAPI app, services, routes, database, middleware
frontend/  React app with chat, documents, history, settings, help
models/    Local model cache for LLMs and embeddings
data/      App data and working storage
logs/      Application logs
```

## Major Backend Pieces

- `backend/main.py`: primary FastAPI app entrypoint
- `backend/routes/chat.py`: chat/session endpoints
- `backend/routes/documents.py`: document upload and management
- `backend/routes/auth.py`: auth endpoints
- `backend/services/llm_service.py`: local Gemini-branded model service layer
- `backend/services/embedding_service.py`: SentenceTransformers embeddings
- `backend/services/pdf_service.py`: PDF extraction
- `backend/services/vector_service.py`: FAISS retrieval

## Major Frontend Pieces

- `frontend/src/components/Chat.jsx`: chat interface, speech, voice input, image input
- `frontend/src/components/Documents/*`: document manager UI
- `frontend/src/components/Pages/*`: History, Settings, Help pages
- `frontend/src/contexts/AuthContext.jsx`: auth state and helpers
- `frontend/src/services/api.js`: backend API client

## Important Behavior

- Authentication is currently bypassed for local development in the active backend flow.
- The UI brand is FLASH MAN.
- The internal chat mode key `gemini` remains in the API contract for compatibility.
- Speech playback is explicitly canceled on page load, navigation, and unload.

## Useful Endpoints

- `GET /health`
- `GET /stats`
- `POST /documents/upload`
- `GET /documents/`
- `POST /chat/query`
- `GET /chat/sessions`
- `GET /chat/stats/overview`

## Meeting Summary

If you need to explain the project quickly:

1. A user uploads PDFs.
2. The backend extracts text and chunks it.
3. Chunks are embedded and indexed in FAISS.
4. The user asks a question in chat.
5. The backend retrieves relevant chunks and generates a grounded answer.
6. The UI shows sources, supports voice, and stores history/settings locally and in MongoDB.
