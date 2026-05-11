"""
Enhanced vector service for PDF RAG Chatbot application.
Provides FAISS vector database management with metadata-aware retrieval.
"""
import faiss
import pickle
import numpy as np
from pathlib import Path
from typing import List, Tuple, Optional, Dict, Any
from collections import defaultdict
from utils.logger import get_logger
from utils.file_utils import format_file_size, get_directory_size


logger = get_logger(__name__)


class EnhancedVectorService:
    """
    Service for managing FAISS vector indices with metadata support.

    Provides vector indexing, storage, retrieval, and document lifecycle management.
    """

    def __init__(self, vector_store_dir: Path):
        """
        Initialize the vector service.

        Args:
            vector_store_dir: Directory to store vector indices
        """
        self.vector_store_dir = Path(vector_store_dir)
        self.vector_store_dir.mkdir(parents=True, exist_ok=True)

        # Index cache for performance
        self._index_cache: Dict[str, Tuple[faiss.Index, Dict[str, Any]]] = {}

        logger.info(f"EnhancedVectorService initialized with directory: {self.vector_store_dir}")

    def create_index(self, embedding_dim: int, index_type: str = "flat") -> faiss.Index:
        """
        Create a new FAISS index.

        Args:
            embedding_dim: Dimension of embedding vectors
            index_type: Type of index ("flat" or "ivf")

        Returns:
            FAISS index object
        """
        try:
            if index_type == "flat":
                # Flat index - exact search, good for small-medium datasets
                index = faiss.IndexFlatIP(embedding_dim)  # Inner product for cosine similarity
                logger.info(f"Created flat index with dimension {embedding_dim}")
            elif index_type == "ivf":
                # IVF (Inverted File) index - approximate search, faster for large datasets
                quantizer = faiss.IndexFlatIP(embedding_dim)
                nlist = min(100, max(1, embedding_dim // 4))  # Adaptive cluster count
                index = faiss.IndexIVFFlat(quantizer, embedding_dim, nlist)
                logger.info(f"Created IVF index with dimension {embedding_dim}, nlist={nlist}")
            else:
                raise ValueError(f"Unknown index type: {index_type}")

            return index

        except Exception as e:
            logger.error(f"Failed to create index: {e}")
            raise Exception(f"Index creation failed: {e}")

    def serialize_index(self, index: faiss.Index, metadata: Dict[str, Any]) -> bytes:
        """
        Serialize FAISS index and metadata to a byte array.
        """
        try:
            # Serialize FAISS index
            index_bytes = faiss.serialize_index(index)
            
            # Combine with metadata using pickle
            data = {
                'index': index_bytes,
                'metadata': metadata
            }
            return pickle.dumps(data)
        except Exception as e:
            logger.error(f"Failed to serialize index: {e}")
            raise Exception(f"Serialization failed: {e}")

    def deserialize_index(self, data_bytes: bytes) -> Tuple[faiss.Index, Dict[str, Any]]:
        """
        Deserialize FAISS index and metadata from a byte array.
        """
        try:
            # Load from pickle
            data = pickle.loads(data_bytes)
            
            # Deserialize FAISS index
            index = faiss.deserialize_index(data['index'])
            metadata = data['metadata']
            
            return index, metadata
        except Exception as e:
            logger.error(f"Failed to deserialize index: {e}")
            raise Exception(f"Deserialization failed: {e}")

    def save_index(
        self,
        index: faiss.Index,
        document_id: str,
        metadata: Dict[str, Any],
        index_type: str = "flat"
    ) -> bool:
        """
        Save FAISS index and metadata to disk (Legacy - use serialize_index for MongoDB).
        """
        try:
            # Prepare file paths
            index_path = self.vector_store_dir / f"{document_id}.faiss"
            metadata_path = self.vector_store_dir / f"{document_id}_metadata.pkl"

            # Ensure index is trained if needed (for IVF)
            if index_type == "ivf" and not index.is_trained:
                logger.warning(f"IVF index for {document_id} is not trained, skipping save")
                return False

            # Save FAISS index
            faiss.write_index(index, str(index_path))

            # Save metadata
            with open(metadata_path, 'wb') as f:
                pickle.dump(metadata, f)

            logger.info(f"Saved index for document {document_id} to disk")
            return True

        except Exception as e:
            logger.error(f"Failed to save index for document {document_id}: {e}")
            return False

    def load_index(self, document_id: str, use_cache: bool = True) -> Tuple[Optional[faiss.Index], Optional[Dict[str, Any]]]:
        """
        Load FAISS index and metadata from disk.

        Args:
            document_id: Document identifier
            use_cache: Use cached index if available

        Returns:
            Tuple of (index, metadata) or (None, None) if not found
        """
        try:
            # Check cache first
            if use_cache and document_id in self._index_cache:
                logger.info(f"Loading index for {document_id} from cache")
                return self._index_cache[document_id]

            # Prepare file paths
            index_path = self.vector_store_dir / f"{document_id}.faiss"
            metadata_path = self.vector_store_dir / f"{document_id}_metadata.pkl"

            # Check if files exist
            if not index_path.exists():
                logger.warning(f"Index file not found for document {document_id}")
                return None, None

            # Load FAISS index
            index = faiss.read_index(str(index_path))

            # Load metadata
            with open(metadata_path, 'rb') as f:
                metadata = pickle.load(f)

            # Cache the loaded index
            self._index_cache[document_id] = (index, metadata)

            logger.info(f"Loaded index for document {document_id}: {format_file_size(index_path.stat().st_size)}")
            return index, metadata

        except Exception as e:
            logger.error(f"Failed to load index for document {document_id}: {e}")
            return None, None

    def delete_index(self, document_id: str) -> bool:
        """
        Delete FAISS index and metadata for a document.

        Args:
            document_id: Document identifier

        Returns:
            True if deletion successful, False otherwise
        """
        try:
            # Remove from cache
            if document_id in self._index_cache:
                del self._index_cache[document_id]

            # Prepare file paths
            index_path = self.vector_store_dir / f"{document_id}.faiss"
            metadata_path = self.vector_store_dir / f"{document_id}_metadata.pkl"

            # Delete files
            deleted = False

            if index_path.exists():
                index_path.unlink()
                deleted = True
                logger.info(f"Deleted index file for document {document_id}")

            if metadata_path.exists():
                metadata_path.unlink()
                deleted = True
                logger.info(f"Deleted metadata file for document {document_id}")

            return deleted

        except Exception as e:
            logger.error(f"Failed to delete index for document {document_id}: {e}")
            return False

    def search(
        self,
        query_embedding: np.ndarray,
        indices: List[faiss.Index],
        metadata_list: List[Dict[str, Any]],
        top_k: int = 5,
        similarity_threshold: float = 0.7
    ) -> List[Dict[str, Any]]:
        """
        Search across multiple indices with metadata filtering.

        Args:
            query_embedding: Query embedding vector
            indices: List of FAISS indices to search
            metadata_list: List of metadata corresponding to indices
            top_k: Number of results to return per document
            similarity_threshold: Minimum similarity score for results

        Returns:
            List of search results with metadata
        """
        try:
            all_results = []

            # Normalize query embedding for cosine similarity
            query_norm = query_embedding / np.linalg.norm(query_embedding)

            # Search each index
            for index, metadata in zip(indices, metadata_list):
                if index is None or metadata is None:
                    continue

                try:
                    # Normalize query shape for FAISS
                    query_vector = query_norm.reshape(1, -1).astype('float32')

                    # Perform search
                    similarities, indices_found = index.search(query_vector, top_k)
                    
                    logger.info(f"Search results for {metadata.get('document_id')}: similarities={similarities[0]}, threshold={similarity_threshold}")

                    # Process results
                    for sim, idx in zip(similarities[0], indices_found[0]):
                        # Filter by similarity threshold
                        if sim < similarity_threshold or idx == -1:
                            continue

                        # Get chunk data from metadata
                        chunks = metadata.get('chunks', [])
                        if idx >= len(chunks):
                            continue

                        chunk_data = chunks[idx]

                        all_results.append({
                            'similarity': float(sim),
                            'chunk_id': int(idx),
                            'document_id': metadata.get('document_id', 'unknown'),
                            'content': chunk_data.get('content', ''),
                            'metadata': chunk_data.get('metadata', {}),
                            'document_metadata': {
                                'filename': metadata.get('filename', ''),
                                'category': metadata.get('category', ''),
                                'uploaded_at': metadata.get('uploaded_at', '')
                            }
                        })

                except Exception as e:
                    logger.error(f"Failed to search index for document {metadata.get('document_id', 'unknown')}: {e}")
                    continue

            # Sort by similarity and return top results
            all_results.sort(key=lambda x: x['similarity'], reverse=True)

            return all_results[:top_k]

        except Exception as e:
            logger.error(f"Failed to perform vector search: {e}")
            return []

    def add_embeddings(
        self,
        index: faiss.Index,
        embeddings: np.ndarray,
        document_id: str,
        chunks: List[str],
        metadata: Dict[str, Any] = None
    ) -> bool:
        """
        Add embeddings to an existing index.

        Args:
            index: FAISS index to add to
            embeddings: Embedding vectors to add
            document_id: Document identifier
            chunks: Text chunks corresponding to embeddings
            metadata: Additional metadata

        Returns:
            True if addition successful, False otherwise
        """
        try:
            # Ensure embeddings are normalized for cosine similarity
            if embeddings.ndim == 1:
                embeddings = embeddings.reshape(1, -1)

            normalized_embeddings = embeddings / np.linalg.norm(embeddings, axis=1, keepdims=True)

            # Add to index
            index.add(normalized_embeddings.astype('float32'))

            logger.info(f"Added {len(embeddings)} embeddings to index for document {document_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to add embeddings to index for document {document_id}: {e}")
            return False

    def create_document_metadata(
        self,
        document_id: str,
        filename: str,
        category: str,
        uploaded_at: str,
        chunks: List[str]
    ) -> Dict[str, Any]:
        """
        Create metadata structure for a document.

        Args:
            document_id: Document identifier
            filename: Document filename
            category: Document category
            uploaded_at: Upload timestamp
            chunks: Text chunks

        Returns:
            Metadata dictionary
        """
        # Create chunk metadata
        chunk_metadata = []
        for i, chunk in enumerate(chunks):
            chunk_metadata.append({
                'content': chunk,
                'metadata': {
                    'chunk_id': i,
                    'length': len(chunk.split()),
                    'character_count': len(chunk)
                }
            })

        # Create document metadata
        document_metadata = {
            'document_id': document_id,
            'filename': filename,
            'category': category,
            'uploaded_at': uploaded_at,
            'chunk_count': len(chunks),
            'chunks': chunk_metadata
        }

        return document_metadata

    def get_storage_stats(self) -> Dict[str, Any]:
        """
        Get statistics about vector storage.

        Returns:
            Dictionary with storage statistics
        """
        try:
            # Count index files
            index_files = list(self.vector_store_dir.glob("*.faiss"))
            metadata_files = list(self.vector_store_dir.glob("*_metadata.pkl"))

            # Calculate total storage
            total_size = get_directory_size(self.vector_store_dir)

            # Get index sizes
            index_sizes = [f.stat().st_size for f in index_files]
            total_index_size = sum(index_sizes)

            return {
                'total_documents': len(index_files),
                'total_storage_bytes': total_size,
                'total_storage_formatted': format_file_size(total_size),
                'total_index_size_bytes': total_index_size,
                'total_index_size_formatted': format_file_size(total_index_size),
                'vector_store_directory': str(self.vector_store_dir),
                'average_index_size_bytes': total_index_size // len(index_files) if index_files else 0,
                'average_index_size_formatted': format_file_size(total_index_size // len(index_files)) if index_files else "0 B"
            }

        except Exception as e:
            logger.error(f"Failed to get storage stats: {e}")
            return {
                'total_documents': 0,
                'total_storage_bytes': 0,
                'total_storage_formatted': "0 B",
                'total_index_size_bytes': 0,
                'total_index_size_formatted': "0 B",
                'vector_store_directory': str(self.vector_store_dir),
                'average_index_size_bytes': 0,
                'average_index_size_formatted': "0 B"
            }

    def clear_cache(self):
        """Clear the index cache to free memory"""
        try:
            cache_size = len(self._index_cache)
            self._index_cache.clear()
            logger.info(f"Cleared vector index cache (freed {cache_size} indices)")

        except Exception as e:
            logger.error(f"Failed to clear vector cache: {e}")

    def cleanup_orphaned_files(self) -> int:
        """
        Remove orphaned metadata or index files.

        Returns:
            Number of files removed
        """
        try:
            removed_count = 0

            # Get all index and metadata files
            index_files = {f.stem: f for f in self.vector_store_dir.glob("*.faiss")}
            metadata_files = {f.stem.replace('_metadata', ''): f for f in self.vector_store_dir.glob("*_metadata.pkl")}

            # Find orphaned files
            orphaned_indexes = index_files.keys() - metadata_files.keys()
            orphaned_metadata = metadata_files.keys() - index_files.keys()

            # Remove orphaned files
            for doc_id in orphaned_indexes:
                try:
                    index_files[doc_id].unlink()
                    removed_count += 1
                    logger.info(f"Removed orphaned index file: {doc_id}")
                except Exception as e:
                    logger.warning(f"Failed to remove orphaned index {doc_id}: {e}")

            for doc_id in orphaned_metadata:
                try:
                    metadata_files[doc_id].unlink()
                    removed_count += 1
                    logger.info(f"Removed orphaned metadata file: {doc_id}")
                except Exception as e:
                    logger.warning(f"Failed to remove orphaned metadata {doc_id}: {e}")

            if removed_count > 0:
                logger.info(f"Cleaned up {removed_count} orphaned files")
            else:
                logger.info("No orphaned files found")

            return removed_count

        except Exception as e:
            logger.error(f"Failed to cleanup orphaned files: {e}")
            return 0


# Convenience function to create vector service
def create_vector_service(vector_store_dir: Path) -> EnhancedVectorService:
    """
    Create an enhanced vector service instance.

    Args:
        vector_store_dir: Directory to store vector indices

    Returns:
        EnhancedVectorService instance
    """
    return EnhancedVectorService(vector_store_dir)