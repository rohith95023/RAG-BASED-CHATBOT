FLASH MAN is a local PDF RAG chatbot built for document Q&A.

Core flow:

1. User uploads a document.
2. Backend extracts text from the file.
3. Text is chunked and embedded.
4. Chunks are indexed in FAISS.
5. User asks a question in chat.
6. The backend retrieves relevant chunks.
7. The model generates an answer with document grounding.
8. The frontend shows the answer, sources, history, and controls.

Important implementation ideas:

- Use local model files inside the project.
- Keep document and vector storage inside the repository folders.
- Use MongoDB Atlas for persistence.
- Use React Context for auth state.
- Use browser speech APIs for voice input and read-aloud.

The visible product name is FLASH MAN.
The internal chat mode key `gemini` is still used for compatibility.
