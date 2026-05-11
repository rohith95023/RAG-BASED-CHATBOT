"""
Enhanced embedding service for PDF RAG Chatbot application.
Provides local SentenceTransformer integration with model caching and batch processing.
"""
from sentence_transformers import SentenceTransformer
from typing import List, Optional, Dict, Any
from pathlib import Path
import numpy as np
from config.settings import Settings
from utils.logger import get_logger


logger = get_logger(__name__)


class EnhancedEmbeddingService:
    """
    Singleton service for managing SentenceTransformer embeddings.

    Implements lazy loading, local model caching, and batch processing
    for efficient embedding generation.
    """

    _instance = None
    _model = None
    _is_loaded = False

    def __new__(cls, settings: Settings):
        """Ensure singleton pattern"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize(settings)
        return cls._instance

    def _initialize(self, settings: Settings):
        """Initialize the embedding service"""
        try:
            self.settings = settings
            self.models_dir = settings.MODELS_DIR / "embeddings"
            self.models_dir.mkdir(parents=True, exist_ok=True)

            # Set batch size for efficient processing
            self.batch_size = settings.BATCH_SIZE_EMBEDDINGS

            # Device configuration (SentenceTransformers handles GPU automatically)
            self.device = "cuda" if self._is_cuda_available() else "cpu"

            logger.info(f"EnhancedEmbeddingService initialized with batch_size={self.batch_size}, device={self.device}")

        except Exception as e:
            logger.error(f"Failed to initialize EnhancedEmbeddingService: {e}")
            raise Exception(f"Embedding service initialization failed: {e}")

    @staticmethod
    def _is_cuda_available() -> bool:
        """Check if CUDA is available"""
        try:
            import torch
            return torch.cuda.is_available()
        except ImportError:
            return False

    @property
    def model(self):
        """Lazy load the embedding model"""
        if self._model is None:
            self._load_model()
        return self._model

    def _load_model(self):
        """Load the SentenceTransformer model with caching"""
        try:
            logger.info(f"Loading embedding model: {self.settings.EMBEDDING_MODEL_NAME}")

            self._model = SentenceTransformer(
                self.settings.EMBEDDING_MODEL_NAME,
                cache_folder=self.models_dir,
                device=self.device
            )

            self._is_loaded = True
            logger.info("Embedding model loaded successfully")

        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            raise Exception(f"Embedding model loading failed: {e}")

    def ensure_loaded(self):
        """Ensure the model is loaded"""
        if not self._is_loaded:
            logger.info("Loading embedding model on first use")
            _ = self.model

    def generate_embeddings(
        self,
        texts: List[str],
        batch_size: Optional[int] = None,
        show_progress: bool = False
    ) -> np.ndarray:
        """
        Generate embeddings for a list of texts with batching.

        Args:
            texts: List of text strings to embed
            batch_size: Override default batch size
            show_progress: Show progress bar during processing

        Returns:
            Numpy array of embeddings with shape (len(texts), embedding_dim)
        """
        try:
            if not texts:
                logger.warning("Empty text list provided for embedding")
                return np.array([])

            # Ensure model is loaded
            self.ensure_loaded()

            # Use provided batch size or default
            effective_batch_size = batch_size or self.batch_size

            logger.info(f"Generating embeddings for {len(texts)} texts with batch_size={effective_batch_size}")

            # Generate embeddings with batching
            embeddings = self.model.encode(
                texts,
                batch_size=effective_batch_size,
                show_progress_bar=show_progress,
                convert_to_numpy=True,
                normalize_embeddings=True  # Normalize for cosine similarity
            )

            logger.info(f"Successfully generated {len(embeddings)} embeddings")

            return embeddings

        except Exception as e:
            logger.error(f"Failed to generate embeddings: {e}")
            raise Exception(f"Embedding generation failed: {e}")

    def generate_embedding(self, text: str) -> np.ndarray:
        """
        Generate embedding for a single text.

        Args:
            text: Text string to embed

        Returns:
            Numpy array of embedding with shape (embedding_dim,)
        """
        try:
            if not text or not text.strip():
                logger.warning("Empty text provided for single embedding")
                # Return zero embedding of correct dimension
                return np.zeros(self.get_embedding_dimension())

            # Generate for single text
            embeddings = self.generate_embeddings([text])
            return embeddings[0]

        except Exception as e:
            logger.error(f"Failed to generate single embedding: {e}")
            raise Exception(f"Single embedding generation failed: {e}")

    def compute_similarity(
        self,
        query_embedding: np.ndarray,
        document_embeddings: np.ndarray
    ) -> np.ndarray:
        """
        Compute cosine similarity between query and document embeddings.

        Args:
            query_embedding: Query embedding vector
            document_embeddings: Document embeddings matrix

        Returns:
            Array of similarity scores
        """
        try:
            # Ensure embeddings are normalized (should already be from generation)
            query_norm = query_embedding / np.linalg.norm(query_embedding)
            doc_norms = document_embeddings / np.linalg.norm(document_embeddings, axis=1, keepdims=True)

            # Compute cosine similarity using dot product
            similarities = np.dot(doc_norms, query_norm)

            return similarities

        except Exception as e:
            logger.error(f"Failed to compute similarity: {e}")
            raise Exception(f"Similarity computation failed: {e}")

    def compute_similarities(
        self,
        query_embeddings: np.ndarray,
        document_embeddings: np.ndarray
    ) -> np.ndarray:
        """
        Compute cosine similarity matrix between multiple queries and documents.

        Args:
            query_embeddings: Query embeddings matrix
            document_embeddings: Document embeddings matrix

        Returns:
            Similarity matrix with shape (num_queries, num_documents)
        """
        try:
            # Normalize embeddings
            query_norms = query_embeddings / np.linalg.norm(query_embeddings, axis=1, keepdims=True)
            doc_norms = document_embeddings / np.linalg.norm(document_embeddings, axis=1, keepdims=True)

            # Compute similarity matrix
            similarities = np.dot(query_norms, doc_norms.T)

            return similarities

        except Exception as e:
            logger.error(f"Failed to compute similarity matrix: {e}")
            raise Exception(f"Similarity matrix computation failed: {e}")

    def get_embedding_dimension(self) -> int:
        """
        Get the dimension of the embedding vectors.

        Returns:
            Dimension of embedding vectors (e.g., 384 for all-MiniLM-L6-v2)
        """
        try:
            if not self._is_loaded:
                self.ensure_loaded()

            return self.model.get_sentence_embedding_dimension()

        except Exception as e:
            logger.error(f"Failed to get embedding dimension: {e}")
            # Return default dimension for common models
            return 384

    def get_model_info(self) -> Dict[str, Any]:
        """
        Get information about the loaded model.

        Returns:
            Dictionary with model information
        """
        try:
            return {
                "model_name": self.settings.EMBEDDING_MODEL_NAME,
                "device": self.device,
                "is_loaded": self._is_loaded,
                "models_directory": str(self.models_dir),
                "batch_size": self.batch_size,
                "embedding_dimension": self.get_embedding_dimension() if self._is_loaded else None
            }

        except Exception as e:
            logger.error(f"Failed to get model info: {e}")
            return {
                "model_name": self.settings.EMBEDDING_MODEL_NAME,
                "device": self.device,
                "is_loaded": self._is_loaded,
                "models_directory": str(self.models_dir),
                "batch_size": self.batch_size,
                "embedding_dimension": None
            }

    def is_loaded(self) -> bool:
        """
        Check if the model is loaded.

        Returns:
            True if model is loaded, False otherwise
        """
        return self._is_loaded

    def unload_model(self):
        """Unload the model from memory to free resources"""
        try:
            if self._model is not None:
                logger.info("Unloading embedding model from memory")
                del self._model
                self._model = None
                self._is_loaded = False

                # Clear CUDA cache if applicable
                if self.device == "cuda":
                    import torch
                    torch.cuda.empty_cache()

                logger.info("Embedding model unloaded successfully")

        except Exception as e:
            logger.error(f"Failed to unload embedding model: {e}")

    def reload_model(self):
        """Reload the model after unloading"""
        try:
            logger.info("Reloading embedding model")
            self._load_model()
            logger.info("Embedding model reloaded successfully")

        except Exception as e:
            logger.error(f"Failed to reload embedding model: {e}")
            raise Exception(f"Embedding model reload failed: {e}")

    def clear_cache(self):
        """Clear model cache and free memory"""
        try:
            logger.info("Clearing embedding model cache")

            if self.device == "cuda":
                import torch
                torch.cuda.empty_cache()

            logger.info("Embedding model cache cleared successfully")

        except Exception as e:
            logger.error(f"Failed to clear embedding model cache: {e}")

    def optimize_for_device(self):
        """Optimize model for current device"""
        try:
            if not self._is_loaded:
                return

            logger.info(f"Optimizing embedding model for device: {self.device}")

            # SentenceTransformers handles device optimization automatically
            # This method can be extended for specific optimizations

            if self.device == "cpu":
                # CPU optimizations
                import torch
                torch.set_num_threads(4)

            logger.info("Embedding model optimization completed")

        except Exception as e:
            logger.error(f"Failed to optimize embedding model: {e}")


# Convenience function to create embedding service instance
def create_embedding_service(settings: Settings) -> EnhancedEmbeddingService:
    """
    Create an enhanced embedding service instance.

    Args:
        settings: Application settings

    Returns:
        EnhancedEmbeddingService instance
    """
    return EnhancedEmbeddingService(settings)