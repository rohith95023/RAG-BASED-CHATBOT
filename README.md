# FLASH MAN

FLASH MAN is a local-first PDF RAG chatbot. It lets you upload documents, search them with semantic retrieval, chat with source-backed answers, and use voice or image input in the chat UI.

## What It Uses

- Frontend: React 19 + Vite
- Backend: FastAPI
- Database: MongoDB Atlas
- Vector search: FAISS
- PDF parsing: PyMuPDF
- Embeddings: SentenceTransformers
- LLM: HuggingFace Transformers
- Storage: Local project folders for uploads, vectors, logs, and models

## Main Capabilities

- Upload and manage PDF documents
- Chunk and embed document text
- Retrieve relevant context with similarity search
- Generate answers with citations and confidence scoring
- Keep chat sessions and message history
- Support image questions and voice input in the browser

## Project Structure

```text
project/
├── backend/
├── frontend/
├── models/
├── data/
└── logs/
```

## Current UI Pages

- Chat
- Documents
- History
- Settings
- Help

## Local Setup

1. Install backend dependencies.
2. Install frontend dependencies with `npm install` in `frontend/`.
3. Configure `.env`.
4. Start the backend.
5. Start the frontend.

## Notes

- The app is branded as FLASH MAN in the UI.
- The chat still uses the internal `gemini` mode key in a few places for compatibility with existing backend routing.
- All model files and generated project artifacts are kept inside the repository folders.
