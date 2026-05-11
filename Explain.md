# FLASH MAN Explained

This file is written for a beginner-friendly explanation in plain English.
If someone asks, "What is this project and how does it work?", this is the version to read.

## 1. What This Project Is

FLASH MAN is a chatbot that can answer questions about PDF documents.

Think of it like this:

- You upload a PDF.
- The app reads the PDF.
- It breaks the PDF into smaller pieces.
- It turns those pieces into searchable math vectors.
- When you ask a question, it finds the most relevant pieces.
- It sends those pieces to the language model.
- The model writes back an answer using the document as context.

So the project is not just a chat app.
It is a document understanding system.

## 2. Why This Project Exists

Normal chatbots answer from general knowledge.
This project is different because it is meant to answer from your documents.

That matters when:

- you need grounded answers
- you want sources
- you want to search large PDFs fast
- you want a private local workflow

The goal is to make PDF questions easier and more reliable.

## 3. The Big Idea

The project is built around RAG.

RAG means Retrieval Augmented Generation.

In simple words:

- Retrieval means finding the right text from your documents.
- Generation means using an AI model to write the final answer.

So the app does two jobs:

1. Find the right information.
2. Turn that information into a useful answer.

## 4. Main Parts of the Project

### Frontend

The frontend is the part the user sees in the browser.

It is built with React and Vite.

This is where the user:

- uploads documents
- chats with FLASH MAN
- opens history
- changes settings
- reads help
- uses voice features

### Backend

The backend is the server side of the app.

It is built with FastAPI.

It handles:

- document upload
- text extraction
- chunking
- embeddings
- vector search
- chat sessions
- chat answers
- health and stats endpoints

### Database

The database is MongoDB Atlas.

It stores:

- users
- documents
- chat sessions
- chat messages
- user settings

This is the memory of the app.

### Vector Search

Vector search is handled by FAISS.

This is what makes document lookup fast.

It stores mathematical representations of text chunks, so the system can search by meaning instead of only exact words.

### Local Model Storage

The project stores model files inside the repository under `models/`.

That means:

- the models are local
- they can be reused
- they do not need to be downloaded every time

## 5. How the Information Flows

This is the most important part.

### Step 1: Upload

The user uploads a PDF or another supported file.

The frontend sends the file to the backend.

### Step 2: Extract Text

The backend reads the file using PyMuPDF.

PyMuPDF is a Python library that can extract text from PDFs.

If the PDF has text, the app pulls that text out.
If the file is scanned or weirdly formatted, extraction may be less perfect.

### Step 3: Chunk the Text

The extracted text is too big to send as one huge block.

So the app breaks it into chunks.

Why?

- smaller pieces are easier to search
- smaller pieces fit model limits better
- retrieval works better on chunks than on full documents

### Step 4: Create Embeddings

Each chunk is converted into an embedding.

An embedding is just a list of numbers that represents the meaning of text.

SentenceTransformers does this part.

The important idea:

- similar meanings produce similar vectors
- similar vectors are easier to search

### Step 5: Store in FAISS and MongoDB

The chunk vectors go into FAISS for similarity search.

Metadata goes into MongoDB.

Metadata means helpful details like:

- file name
- document ID
- category
- timestamps

### Step 6: Ask a Question

When the user asks a question, the backend searches the vector store.

It finds the chunks most related to the question.

### Step 7: Generate the Answer

The selected chunks are passed to the LLM.

The LLM is the text-generating model.

Its job is not to invent the answer from nowhere.
Its job is to write a useful answer using the retrieved context.

### Step 8: Show the Result

The frontend shows:

- the answer
- sources
- citations
- confidence-related context
- chat history

## 6. What Each Folder Means

### `frontend/`

All browser UI code.

This includes:

- `Chat.jsx`
- `Sidebar.jsx`
- `Upload.jsx`
- `HistoryView.jsx`
- `SettingsView.jsx`
- `HelpView.jsx`

### `backend/`

All server code.

This includes:

- API routes
- services
- database code
- models and schemas
- middleware

### `models/`

Local model storage.

This is where downloaded model files live.

### `data/`

Storage for app data and database-related working files.

### `logs/`

Application logs.

Logs are useful when debugging problems.

## 7. What the Backend Services Do

### PDF Service

This service reads PDFs and extracts text.

Why it matters:

- without text extraction, the app has nothing to search

### Chunk Service

This service breaks large text into smaller chunks.

Why it matters:

- AI models have input limits
- search works better on smaller units

### Embedding Service

This converts text into vectors.

Why it matters:

- vectors let the app search by meaning

### Vector Service

This stores and searches those vectors.

Why it matters:

- it returns the most relevant text chunks quickly

### RAG Service

This is the orchestrator.

It connects:

- document retrieval
- context preparation
- answer generation

So if someone asks, "What actually runs the whole pipeline?"
the answer is the RAG service.

### LLM Service

This is the model wrapper that generates text.

It takes the retrieved context and returns a response.

## 8. What the Frontend Pages Do

### Chat

The main place to talk to FLASH MAN.

It supports:

- text chat
- document chat
- image attachment
- voice input
- read-aloud speech
- stop speech button

### Documents

This page manages uploaded files.

You can:

- see documents
- search them
- select them
- delete them
- upload new ones

### History

This page shows past chat sessions.

It is useful for:

- seeing what was asked before
- continuing a previous thread
- checking active or archived sessions

### Settings

This page controls browser-side preferences.

Examples:

- stop speech on navigation
- show timestamps
- compact message layout
- default answer mode

### Help

This page explains how to use the app.

It is meant for quick guidance, keyboard hints, and FAQ-style support.

## 9. Why FAISS Is Used

FAISS is a fast similarity search library.

We use it because:

- it is fast
- it works well with embeddings
- it is good for semantic search

Without FAISS, the app would have to inspect every chunk manually.
That would be much slower.

## 10. Why MongoDB Is Used

MongoDB stores the structured data:

- users
- sessions
- messages
- documents
- settings

Why not put everything only in files?

- files are bad for structured querying
- databases make filtering and history easier
- MongoDB is flexible for document-style data

## 11. Why Local Models Are Used

The project is designed to run with local model files.

Benefits:

- less dependency on external AI services
- better privacy
- more control
- works well for a self-contained project

The current codebase still uses the internal `gemini` mode key in some places, but the visible branding is FLASH MAN.

## 12. Why Speech and Voice Input Exist

The app uses browser speech features for convenience.

### Speech synthesis

This reads assistant responses aloud.

### Speech recognition

This lets the user dictate input instead of typing.

Why include them?

- faster interaction
- accessibility
- a more polished user experience

There is also a stop button because speech can continue if not canceled.

## 13. Why the Stop Button Matters

Before the fix, speech could keep running after refresh.

Now the app cancels speech:

- on load
- on navigation
- on unload
- with a dedicated Stop Audio button

This makes the UI feel safer and more controlled.

## 14. What “Authentication Bypassed” Means

The repo mentions authentication being bypassed for local development.

That means:

- the auth system exists
- the auth code is still in the project
- but local development may skip strict login checks

In plain English:

The app still knows how auth should work, but the local setup is relaxed so development is easier.

## 15. How to Explain This in One Minute

If you only have one minute in the meeting, say this:

> FLASH MAN is a local PDF RAG chatbot. Users upload documents, the backend extracts and chunks the text, converts it into embeddings, stores the vectors in FAISS and the metadata in MongoDB, then retrieves the most relevant chunks when the user asks a question. The LLM uses those chunks to generate grounded answers. The frontend is built in React and includes chat, documents, history, settings, help, speech playback, and voice input.

## 16. What to Say If Asked “What Makes It Special?”

You can say:

- It answers from documents instead of only from general knowledge.
- It keeps the system local and self-contained.
- It supports history, voice, image input, and document management.
- It is organized like a production app rather than a demo.

## 17. What to Say If Asked “How Does Search Work?”

You can say:

- The document is split into chunks.
- Each chunk becomes an embedding.
- The question also becomes an embedding.
- FAISS compares the vectors.
- The closest chunks are sent to the model.

## 18. What to Say If Asked “Why Not Just Use a Normal Search?”

You can say:

- Normal search matches keywords only.
- Vector search understands meaning.
- That is better for natural language questions.

## 19. What to Say If Asked “What Is the Database Doing?”

You can say:

- MongoDB stores the app’s structured memory.
- It keeps documents, chats, messages, and settings.
- FAISS handles similarity search, MongoDB handles persistence.

## 20. Final Mental Model

Think of FLASH MAN like this:

- React = the face
- FastAPI = the brainstem and traffic controller
- PyMuPDF = the PDF reader
- SentenceTransformers = the meaning encoder
- FAISS = the search engine for meaning
- MongoDB = the long-term memory
- LLM = the writer of the final answer

That is the whole project in one picture.
