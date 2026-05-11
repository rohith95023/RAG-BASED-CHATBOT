"""
Vector database service using FAISS.
Handles storage and retrieval of text embeddings.
"""
import faiss
import numpy as np
import pickle
import os
from typing import List, Tuple, Dict, Optional


class VectorService:
    """
    Service for managing vector database using FAISS.
    """

    def __init__(self, index_path: str = "./data/vectors", index_name: str = "document_index"):
        """
        Initialize vector service.

        Args:
            index_path: Directory to store FAISS index
            index_name: Name of the index file
        """
        self.index_path = index_path
        self.index_name = index_name
        self.index_file = os.path.join(index_path, f"{index_name}.faiss")
        self.metadata_file = os.path.join(index_path, f"{index_name}_metadata.pkl")

        self.index = None
        self.metadata = []  # Stores text chunks and source info
        self.dimension = None

        self._load_or_create_index()

    def _load_or_create_index(self) -> None:
        """
        Load existing index or create new one.
        """
        # Ensure directory exists
        os.makedirs(self.index_path, exist_ok=True)

        # Try to load existing index
        if os.path.exists(self.index_file) and os.path.exists(self.metadata_file):
            try:
                print(f"Loading existing index from {self.index_file}")
                self.index = faiss.read_index(self.index_file)

                with open(self.metadata_file, 'rb') as f:
                    self.metadata = pickle.load(f)

                self.dimension = self.index.d
                print(f"Index loaded successfully. Size: {self.index.ntotal} vectors")
            except Exception as e:
                print(f"Failed to load index: {str(e)}. Creating new index.")
                self._create_new_index()
        else:
            print("No existing index found. Creating new index.")
            self._create_new_index()

    def _create_new_index(self) -> None:
        """
        Create a new FAISS index.
        """
        # Default dimension (will be updated when first embeddings are added)
        self.dimension = 384  # Default for all-MiniLM-L6-v2
        self.index = faiss.IndexFlatL2(self.dimension)
        self.metadata = []

    def set_dimension(self, dimension: int) -> None:
        """
        Set the embedding dimension. Creates new index if needed.

        Args:
            dimension: Embedding dimension
        """
        if self.dimension != dimension:
            print(f"Creating new index with dimension: {dimension}")
            self.dimension = dimension
            self.index = faiss.IndexFlatL2(self.dimension)
            self.metadata = []

    def add_embeddings(self, embeddings: np.ndarray, texts: List[str], metadata: Optional[List[Dict]] = None) -> None:
        """
        Add embeddings to the index.

        Args:
            embeddings: Numpy array of embeddings
            texts: List of text chunks
            metadata: Optional list of metadata dicts for each chunk
        """
        if len(embeddings) != len(texts):
            raise ValueError("Number of embeddings must match number of texts")

        # Check dimension
        if self.index.d != embeddings.shape[1]:
            self.set_dimension(embeddings.shape[1])

        # Add embeddings to index
        self.index.add(embeddings.astype('float32'))

        # Store metadata
        for i, text in enumerate(texts):
            meta = {
                "text": text,
                "id": len(self.metadata)
            }
            if metadata and i < len(metadata):
                meta.update(metadata[i])
            self.metadata.append(meta)

    def search(self, query_embedding: np.ndarray, k: int = 5) -> List[Tuple[str, float, Dict]]:
        """
        Search for similar embeddings.

        Args:
            query_embedding: Query embedding vector
            k: Number of results to return

        Returns:
            List of tuples (text, score, metadata)
        """
        if self.index.ntotal == 0:
            return []

        # Ensure query is in correct format
        if query_embedding.ndim == 1:
            query_embedding = query_embedding.reshape(1, -1)

        # Search
        distances, indices = self.index.search(query_embedding.astype('float32'), k)

        # Gather results
        results = []
        for i in range(len(indices[0])):
            idx = indices[0][i]
            if idx < len(self.metadata) and idx >= 0:
                text = self.metadata[idx]["text"]
                score = float(distances[0][i])
                metadata = {k: v for k, v in self.metadata[idx].items() if k != "text"}
                results.append((text, score, metadata))

        return results

    def save_index(self) -> None:
        """
        Save index and metadata to disk.
        """
        try:
            # Save FAISS index
            faiss.write_index(self.index, self.index_file)

            # Save metadata
            with open(self.metadata_file, 'wb') as f:
                pickle.dump(self.metadata, f)

            print(f"Index saved to {self.index_file}")
        except Exception as e:
            raise Exception(f"Failed to save index: {str(e)}")

    def get_index_size(self) -> int:
        """
        Get the number of vectors in the index.

        Returns:
            Number of vectors
        """
        return self.index.ntotal

    def clear_index(self) -> None:
        """
        Clear all vectors from the index.
        """
        self._create_new_index()
        self.save_index()


# Global instance
vector_service = VectorService()