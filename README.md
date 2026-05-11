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
│   ├── models/       # ML models (ignored in Git)
│   ├── data/         # Application data
│   ├── services/     # Logic & Services
│   └── ...
├── frontend/
└── logs/
```

## Current UI Pages

- Chat
- Documents
- History
- Settings
- Help

## Local Setup

### Backend
1. Navigate to the backend directory: `cd backend`
2. Create and activate a virtual environment.
3. Install dependencies: `pip install -r requirements.txt`
4. Configure your `.env` file based on `.env.example`.
5. Start the server: `uvicorn main:app --reload`
   > **Note:** The embedding model weight files (~86MB) will automatically download from HuggingFace on the first run and cache in `backend/models/embeddings/`.

### Frontend
1. Navigate to the frontend directory: `cd frontend`
2. Install dependencies: `npm install`
3. Start the dev server: `npm run dev`

## Notes

- The app is branded as FLASH MAN in the UI.
- The chat still uses the internal `gemini` mode key in a few places for compatibility with existing backend routing.
- All model files and generated project artifacts are kept inside the repository folders.
