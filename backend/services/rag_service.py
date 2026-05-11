"""
RAG (Retrieval-Augmented Generation) service for PDF RAG Chatbot application.
Orchestrates document processing, retrieval, and AI response generation.
"""
import asyncio
import json
import threading
from typing import List, Dict, Any, Optional

from config.settings import Settings
from services.llm_service import GeminiLLMService
from services.embedding_service import EnhancedEmbeddingService
from services.vector_service import EnhancedVectorService
from services.pdf_service import EnhancedPDFService
from services.chunk_service import SemanticChunkingService
from database.repositories import DocumentRepository
from utils.logger import get_logger


logger = get_logger(__name__)


class RAGService:
    """
    Service for Retrieval-Augmented Generation.

    Orchestrates the complete RAG pipeline:
    1. Document processing (PDF extraction, chunking, embedding)
    2. Vector storage and retrieval
    3. Context-aware AI response generation
    """

    def __init__(
        self,
        llm_service: GeminiLLMService,
        embedding_service: EnhancedEmbeddingService,
        vector_service: EnhancedVectorService,
        pdf_service: EnhancedPDFService,
        chunk_service: SemanticChunkingService,
        document_repo: DocumentRepository,
        settings: Settings = None
    ):
        """
        Initialize the RAG service.

        Args:
            llm_service: Local LLM service
            embedding_service: Embedding service
            vector_service: Vector database service
            pdf_service: PDF processing service
            chunk_service: Text chunking service
            document_repo: Document repository
            settings: Application settings
        """
        self.llm_service = llm_service
        self.embedding_service = embedding_service
        self.vector_service = vector_service
        self.pdf_service = pdf_service
        self.chunk_service = chunk_service
        self.document_repo = document_repo
        self.settings = settings

        # Default RAG parameters
        self.default_top_k = settings.TOP_K_RETRIEVAL if settings else 5
        self.default_similarity_threshold = settings.SIMILARITY_THRESHOLD if settings else 0.7
        
        logger.info(f"RAGService initialized with top_k={self.default_top_k}, threshold={self.default_similarity_threshold}")
        self.default_chunk_size = settings.CHUNK_SIZE if settings else 500

        logger.info("RAGService initialized")

    async def process_document(
        self,
        file_path: Optional[str],
        document_id: str,
        filename: str,
        category: str = "general",
        chunk_size: Optional[int] = None,
        use_semantic: bool = True,
        content: Optional[bytes] = None
    ) -> Dict[str, Any]:
        """
        Process an uploaded PDF document and create vector embeddings.

        Args:
            file_path: Path to the PDF file (optional if content provided)
            document_id: Document identifier
            filename: Document filename
            category: Document category
            chunk_size: Target chunk size in words
            use_semantic: Use semantic chunking (True) or traditional (False)
            content: Binary PDF content (optional if file_path provided)

        Returns:
            Dictionary with processing results
        """
        try:
            logger.info(f"Processing document {document_id}: {filename}")

            # Use provided chunk size or default
            chunk_size = chunk_size or self.default_chunk_size

            # Step 1: Extract text from the uploaded document
            if content:
                logger.info(f"Extracting text from document binary content: {filename}")
                text = self.pdf_service.extract_text(content=content, filename=filename)
            else:
                logger.info(f"Extracting text from document: {file_path}")
                text = self.pdf_service.extract_text(pdf_path=file_path, filename=filename)

            if not text or len(text.strip()) < 100:
                raise Exception(f"Extracted text too short: {len(text)} characters")

            logger.info(f"Extracted {len(text)} characters from PDF")

            # Step 2: Chunk the text
            logger.info(f"Chunking text with size={chunk_size}, semantic={use_semantic}")
            chunks = self.chunk_service.chunk_text(
                text=text,
                chunk_size=chunk_size,
                chunk_overlap=chunk_size // 10,  # 10% overlap
                use_semantic=use_semantic,
                use_sentences=True
            )

            if not chunks:
                raise Exception("Failed to create text chunks")

            logger.info(f"Created {len(chunks)} chunks")

            # Step 3: Generate embeddings for chunks
            logger.info("Generating embeddings for chunks")
            embeddings = self.embedding_service.generate_embeddings(
                texts=chunks,
                show_progress=True
            )

            # Step 4: Create FAISS index
            embedding_dim = embeddings.shape[1]
            logger.info(f"Creating FAISS index with dimension {embedding_dim}")
            index = self.vector_service.create_index(
                embedding_dim=embedding_dim,
                index_type="flat"
            )

            # Step 5: Add embeddings to index
            success = self.vector_service.add_embeddings(
                index=index,
                embeddings=embeddings,
                document_id=document_id,
                chunks=chunks
            )

            if not success:
                raise Exception("Failed to add embeddings to index")

            # Step 6: Create metadata and serialize index
            document_metadata = self.vector_service.create_document_metadata(
                document_id=document_id,
                filename=filename,
                category=category,
                uploaded_at="now",  # Will be set by database
                chunks=chunks
            )

            # Serialize index for MongoDB storage
            index_data = self.vector_service.serialize_index(
                index=index,
                metadata=document_metadata
            )

            # Store serialized index in MongoDB
            success = await self.document_repo.store_vector_index(document_id, index_data)

            if not success:
                raise Exception("Failed to store vector index in MongoDB")

            # Step 7: Update document record in database
            await self.document_repo.update_chunk_count(document_id, len(chunks))
            await self.document_repo.update_vector_index(document_id, "mongodb_stored")

            logger.info(f"Successfully processed document {document_id} with {len(chunks)} chunks and stored in MongoDB")

            return {
                "document_id": document_id,
                "chunk_count": len(chunks),
                "embedding_dimension": embedding_dim,
                "processing_status": "completed",
                "index_size": f"{document_id}.faiss"
            }

        except Exception as e:
            logger.error(f"Failed to process document {document_id}: {e}")
            raise Exception(f"Document processing failed: {e}")

    async def query_documents(
        self,
        query: str,
        document_ids: List[str],
        top_k: Optional[int] = None,
        similarity_threshold: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Query documents and retrieve relevant chunks.

        Args:
            query: User query/question
            document_ids: List of document IDs to search
            top_k: Number of relevant chunks to retrieve
            similarity_threshold: Minimum similarity score

        Returns:
            Dictionary with retrieved chunks and metadata
        """
        try:
            logger.info(f"Querying {len(document_ids)} documents with: {query[:50]}...")

            # Use provided parameters or defaults
            top_k = top_k or self.default_top_k
            similarity_threshold = similarity_threshold or self.default_similarity_threshold

            # Step 1: Generate query embedding
            logger.info("Generating query embedding")
            query_embedding = self.embedding_service.generate_embedding(query)

            # Step 2: Load indices and metadata for documents from MongoDB
            indices = []
            metadata_list = []

            for doc_id in document_ids:
                # Retrieve index data from MongoDB
                index_data = await self.document_repo.get_vector_index(doc_id)
                
                if index_data:
                    try:
                        index, metadata = self.vector_service.deserialize_index(index_data)
                        indices.append(index)
                        metadata_list.append(metadata)
                    except Exception as e:
                        logger.error(f"Failed to deserialize index for {doc_id}: {e}")
                        continue
                else:
                    # Fallback to disk for legacy support (optional)
                    logger.warning(f"Index not found in MongoDB for {doc_id}, checking disk...")
                    index, metadata = self.vector_service.load_index(doc_id)
                    if index:
                        indices.append(index)
                        metadata_list.append(metadata)

            # Filter out None values (failed to load)
            valid_pairs = [(idx, meta) for idx, meta in zip(indices, metadata_list) if idx is not None and meta is not None]

            if not valid_pairs:
                logger.warning("No valid indices found for query")
                return {
                    "chunks": [],
                    "total_results": 0,
                    "query": query,
                    "documents_searched": len(document_ids),
                    "documents_found": 0
                }

            indices, metadata_list = zip(*valid_pairs)

            # Step 3: Search across all documents
            logger.info("Searching vector indices")
            results = self.vector_service.search(
                query_embedding=query_embedding,
                indices=list(indices),
                metadata_list=list(metadata_list),
                top_k=top_k,
                similarity_threshold=similarity_threshold
            )

            logger.info(f"Retrieved {len(results)} relevant chunks")

            return {
                "chunks": results,
                "total_results": len(results),
                "query": query,
                "documents_searched": len(document_ids),
                "documents_found": len(set(result['document_id'] for result in results)),
                "top_k": top_k,
                "similarity_threshold": similarity_threshold
            }

        except Exception as e:
            logger.error(f"Failed to query documents: {e}")
            raise Exception(f"Document query failed: {e}")

    async def generate_response(
        self,
        query: str,
        context_chunks: List[Dict[str, Any]],
        system_prompt: Optional[str] = None,
        max_length: Optional[int] = None,
        temperature: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Generate AI response using retrieved context.

        Args:
            query: Original user query
            context_chunks: Retrieved relevant chunks
            system_prompt: Optional system prompt
            max_length: Maximum response length
            temperature: Response temperature

        Returns:
            Dictionary with generated response and metadata
        """
        try:
            if not context_chunks:
                logger.warning("No context chunks provided for response generation; generating constrained document-mode fallback")
            else:
                logger.info(f"Generating response with {len(context_chunks)} context chunks")

            # Step 1: Format context from retrieved chunks
            context_text = self._format_context(context_chunks)

            # Step 2: Create prompt
            prompt = self._create_prompt(query, context_text, system_prompt)

            # Step 3: Generate response using LLM
            logger.info("Generating AI response")
            response = self.llm_service.generate_response(
                prompt=prompt,
                max_length=max_length,
                temperature=temperature
            )

            # Step 4: Calculate confidence based on chunk similarities
            avg_similarity = (
                sum(chunk['similarity'] for chunk in context_chunks) / len(context_chunks)
                if context_chunks else 0.0
            )

            logger.info(f"Generated response with confidence: {avg_similarity:.2f}")

            return {
                "answer": response,
                "confidence": float(avg_similarity),
                "sources_used": len(context_chunks),
                "context_available": bool(context_chunks),
                "chunk_similarities": [chunk['similarity'] for chunk in context_chunks]
            }

        except Exception as e:
            logger.error(f"Failed to generate response: {e}")
            raise Exception(f"Response generation failed: {e}")

    async def rag_query(
        self,
        query: str,
        document_ids: List[str],
        top_k: Optional[int] = None,
        similarity_threshold: Optional[float] = None,
        system_prompt: Optional[str] = None,
        max_length: Optional[int] = None,
        temperature: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Complete RAG query pipeline.

        Args:
            query: User query/question
            document_ids: List of document IDs to query
            top_k: Number of relevant chunks to retrieve
            similarity_threshold: Minimum similarity score
            system_prompt: Optional system prompt
            max_length: Maximum response length
            temperature: Response temperature

        Returns:
            Complete RAG response with answer, sources, and metadata
        """
        try:
            logger.info(f"Starting RAG query: {query[:50]}...")

            # Step 1: Retrieve relevant chunks
            retrieval_result = await self.query_documents(
                query=query,
                document_ids=document_ids,
                top_k=top_k,
                similarity_threshold=similarity_threshold
            )
            if not retrieval_result["chunks"]:
                logger.info("No relevant chunks found, retrying document retrieval with a wider search")
                retrieval_result = await self.query_documents(
                    query=query,
                    document_ids=document_ids,
                    top_k=max(top_k or self.default_top_k, 10),
                    similarity_threshold=0.0
                )
                
            generation_result = await self.generate_response(
                query=query,
                context_chunks=retrieval_result["chunks"],
                system_prompt=system_prompt,
                max_length=max_length,
                temperature=temperature
            )

            # Step 3: Format sources with chunk previews
            sources = [
                {
                    "document_id": chunk['document_id'],
                    "document_filename": chunk['document_metadata']['filename'],
                    "chunk_id": chunk['chunk_id'],
                    "content_preview": chunk['content'][:200] + '...' if len(chunk['content']) > 200 else chunk['content'],
                    "confidence": chunk['similarity'],
                    "metadata": chunk['metadata']
                }
                for chunk in retrieval_result["chunks"][:3]  # Top 3 sources
            ]

            logger.info(f"RAG query completed with {len(sources)} sources")

            return {
                "answer": generation_result["answer"],
                "sources": sources,
                "confidence": generation_result["confidence"],
                "chunks_found": retrieval_result["total_results"],
                "documents_searched": retrieval_result["documents_searched"],
                "documents_with_results": retrieval_result["documents_found"],
                "query": query
            }

        except Exception as e:
            logger.error(f"RAG query failed: {e}")
            raise Exception(f"RAG query failed: {e}")

    async def rag_query_streaming(
        self,
        query: str,
        document_ids: List[str],
        top_k: Optional[int] = None,
        similarity_threshold: Optional[float] = None,
        system_prompt: Optional[str] = None,
        max_length: Optional[int] = None,
        temperature: Optional[float] = None
    ):
        """
        Complete RAG query pipeline with streaming response.

        Yields:
            Chunks of the response (metadata first, then tokens)
        """
        try:
            logger.info(f"Starting streaming RAG query: {query[:50]}...")

            # Step 1: Retrieve relevant chunks
            retrieval_result = await self.query_documents(
                query=query,
                document_ids=document_ids,
                top_k=top_k,
                similarity_threshold=similarity_threshold
            )

            if not retrieval_result["chunks"]:
                logger.info("No relevant chunks found for streaming, retrying with a wider search")
                retrieval_result = await self.query_documents(
                    query=query,
                    document_ids=document_ids,
                    top_k=max(top_k or self.default_top_k, 10),
                    similarity_threshold=0.0
                )

            # Format sources
            sources = [
                {
                    "document_id": chunk['document_id'],
                    "document_filename": chunk['document_metadata']['filename'],
                    "chunk_id": chunk['chunk_id'],
                    "content_preview": chunk['content'][:200] + '...' if len(chunk['content']) > 200 else chunk['content'],
                    "confidence": chunk['similarity'],
                    "metadata": chunk['metadata']
                }
                for chunk in retrieval_result["chunks"][:3]
            ]

            # Yield metadata first (as JSON)
            import json
            yield json.dumps({
                "type": "metadata",
                "sources": sources,
                "confidence": sum(chunk['similarity'] for chunk in retrieval_result["chunks"]) / len(retrieval_result["chunks"]) if retrieval_result["chunks"] else 0.0,
                "chunks_found": retrieval_result["total_results"],
                "documents_searched": retrieval_result["documents_searched"]
            }) + "\n"

            # Step 2: Generate response using retrieved context
            if not retrieval_result["chunks"]:
                logger.info("No document chunks found after fallback retrieval")

            context_text = self._format_context(retrieval_result["chunks"])
            prompt = self._create_prompt(query, context_text, system_prompt)

            # Run blocking LLM generation in a thread, stream via asyncio.Queue
            logger.info("Starting LLM streaming (threaded)")
            loop = asyncio.get_event_loop()
            token_queue = asyncio.Queue()

            def _generate_in_thread():
                try:
                    for token in self.llm_service.generate_streaming(
                        prompt=prompt,
                        max_length=200, # Hard limit to prevent long regurgitation
                        temperature=0.3 # Lower temperature for more concise answers
                    ):
                        loop.call_soon_threadsafe(token_queue.put_nowait, token)
                except Exception as exc:
                    loop.call_soon_threadsafe(token_queue.put_nowait, exc)
                finally:
                    loop.call_soon_threadsafe(token_queue.put_nowait, None)  # sentinel

            import threading
            thread = threading.Thread(target=_generate_in_thread, daemon=True)
            thread.start()

            while True:
                token = await token_queue.get()
                if token is None:
                    break
                if isinstance(token, Exception):
                    raise token
                yield json.dumps({"type": "content", "text": token}) + "\n"

            logger.info("Streaming RAG query completed")

        except Exception as e:
            logger.error(f"Streaming RAG query failed: {e}")
            yield json.dumps({
                "type": "error",
                "message": str(e)
            }) + "\n"

    def _format_context(self, chunks: List[Dict[str, Any]]) -> str:
        """
        Format retrieved chunks into context string.

        Args:
            chunks: Retrieved chunks with metadata

        Returns:
            Formatted context string
        """
        context_parts = []

        for i, chunk in enumerate(chunks, 1):
            source_info = f"[Source {i}: {chunk['document_metadata']['filename']} (Confidence: {chunk['similarity']:.2f})]"
            content = chunk['content']
            context_parts.append(f"{source_info}\n{content}")

        return "\n\n".join(context_parts)

    def _create_prompt(
        self,
        query: str,
        context: str,
        system_prompt: Optional[str] = None
    ) -> str:
        """
        Create prompt for LLM with context and query.

        Args:
            query: User question
            context: Retrieved document context
            system_prompt: Optional system prompt

        Returns:
            Formatted prompt string
        """
        system_msg = (
            system_prompt
            if system_prompt
            else (
                "You are a helpful AI assistant that answers questions based on the provided "
                "context. Keep your answers concise: use a short paragraph (2-3 sentences) "
                "followed by clear bullet points where appropriate."
            )
        )

        prompt = f"{system_msg}\n\n"
        
        if context:
            prompt += f"Context from documents:\n{context}\n\n"
        else:
            prompt += (
                "System Note: No matching text chunks were retrieved for this question. "
                "Use only the active document inventory from the system prompt for metadata questions. "
                "For content questions, say that the answer was not found in the indexed document text and suggest a more specific query. "
                "Do not use general knowledge as if it came from the documents.\n\n"
            )
            
        prompt += f"Question: {query}\n\n"
        prompt += "Answer:"

        return prompt

    def get_system_prompt(self, prompt_type: str = "default") -> str:
        """
        Get system prompt for specific use case.

        Args:
            prompt_type: Type of prompt ("default", "summarization", "qa", etc.)

        Returns:
            System prompt string
        """
        prompts = {
            "default": "You are a helpful AI assistant. Use the provided context to answer the user's question. If the answer is not contained within the context, you may use your general knowledge to answer, but briefly mention that the information was not found in the provided documents.",
            "summarization": "You are a helpful AI assistant that summarizes information from the provided context. Focus on key points and main ideas.",
            "qa": "You are a helpful AI assistant. Answer the question accurately using the provided context. If the context doesn't contain the answer, use your general knowledge to provide a helpful response while noting the absence of specific document information.",
            "explanatory": "You are a helpful AI assistant that provides detailed explanations based on the provided context or general knowledge when context is unavailable."
        }

        return prompts.get(prompt_type, prompts["default"])

    async def get_document_info(self, document_id: str) -> Dict[str, Any]:
        """
        Get information about a processed document.

        Args:
            document_id: Document identifier

        Returns:
            Dictionary with document information
        """
        try:
            # Load vector index metadata
            index, metadata = self.vector_service.load_index(document_id)

            if not metadata:
                return {"error": "Document not found"}

            return {
                "document_id": document_id,
                "filename": metadata.get('filename', ''),
                "category": metadata.get('category', ''),
                "chunk_count": metadata.get('chunk_count', 0),
                "uploaded_at": metadata.get('uploaded_at', ''),
                "has_vector_index": True,
                "embedding_dimension": self.embedding_service.get_embedding_dimension() if self.embedding_service.is_loaded() else None
            }

        except Exception as e:
            logger.error(f"Failed to get document info: {e}")
            return {"error": str(e)}

    async def delete_document_vectors(self, document_id: str) -> bool:
        """
        Delete vector index for a document.

        Args:
            document_id: Document identifier

        Returns:
            True if deletion successful, False otherwise
        """
        try:
            logger.info(f"Deleting vectors for document {document_id}")

            # Delete vector index
            success = self.vector_service.delete_index(document_id)

            if success:
                # Clear from cache
                self.vector_service.clear_cache()

                # Update database record
                await self.document_repo.update_vector_index(document_id, None)
                await self.document_repo.update_chunk_count(document_id, 0)

                logger.info(f"Successfully deleted vectors for document {document_id}")

            return success

        except Exception as e:
            logger.error(f"Failed to delete document vectors: {e}")
            return False


# Convenience function to create RAG service
def create_rag_service(
    llm_service: GeminiLLMService,
    embedding_service: EnhancedEmbeddingService,
    vector_service: EnhancedVectorService,
    pdf_service: EnhancedPDFService,
    chunk_service: SemanticChunkingService,
    document_repo: DocumentRepository,
    settings: Settings = None
) -> RAGService:
    """
    Create a RAG service instance.

    Args:
        llm_service: Local LLM service
        embedding_service: Embedding service
        vector_service: Vector database service
        pdf_service: PDF processing service
        chunk_service: Text chunking service
        document_repo: Document repository
        settings: Application settings

    Returns:
        RAGService instance
    """
    return RAGService(
        llm_service=llm_service,
        embedding_service=embedding_service,
        vector_service=vector_service,
        pdf_service=pdf_service,
        chunk_service=chunk_service,
        document_repo=document_repo,
        settings=settings
    )
