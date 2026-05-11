# FLASH MAN Context

This repository contains FLASH MAN, a local PDF RAG chatbot.

## Stack

- React frontend
- FastAPI backend
- MongoDB Atlas
- FAISS
- PyMuPDF
- SentenceTransformers
- HuggingFace Transformers

## Current UI

- Upload
- Chat
- Documents
- History
- Settings
- Help

## Notes

- FLASH MAN is the visible product name.
- The chat API still uses `gemini` as an internal mode value.
- Speech playback is canceled on load and unload to avoid stuck narration.
- All project-specific docs should stay aligned with the actual codebase state.
