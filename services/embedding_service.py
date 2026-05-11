"""
Embedding service using SentenceTransformers.
Generates embeddings for text chunks and queries.
"""
from sentence_transformers import SentenceTransformer
import numpy as np
from typing import List, Union


class EmbeddingService:
    """
    Service for generating text embeddings using SentenceTransformers.
    """

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """
        Initialize embedding service.

        Args:
            model_name: Name of the SentenceTransformer model
        """
        self.model_name = model_name
        self.model = None
        self._load_model()

    def _load_model(self) -> None:
        """
        Load the SentenceTransformer model.
        """
        try:
            print(f"Loading embedding model: {self.model_name}")
            self.model = SentenceTransformer(self.model_name)
            print("Embedding model loaded successfully")
        except Exception as e:
            raise Exception(f"Failed to load embedding model: {str(e)}")

    def generate_embeddings(self, texts: List[str]) -> np.ndarray:
        """
        Generate embeddings for a list of texts.

        Args:
            texts: List of text strings

        Returns:
            Numpy array of embeddings
        """
        if not texts:
            return np.array([])

        try:
            embeddings = self.model.encode(texts, convert_to_numpy=True)
            return embeddings
        except Exception as e:
            raise Exception(f"Failed to generate embeddings: {str(e)}")

    def generate_single_embedding(self, text: str) -> np.ndarray:
        """
        Generate embedding for a single text.

        Args:
            text: Text string

        Returns:
            Numpy array of embedding
        """
        return self.generate_embeddings([text])[0]

    def get_embedding_dimension(self) -> int:
        """
        Get the dimension of the embedding vectors.

        Returns:
            Dimension of embedding vectors
        """
        if self.model is None:
            raise Exception("Model not loaded")
        return self.model.get_sentence_embedding_dimension()

    def is_loaded(self) -> bool:
        """
        Check if the model is loaded.

        Returns:
            True if model is loaded, False otherwise
        """
        return self.model is not None


# Global instance
embedding_service = EmbeddingService()