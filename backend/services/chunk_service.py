"""
Advanced semantic chunking service for PDF RAG Chatbot application.
Provides intelligent text chunking using embeddings and clustering.
"""
from typing import List, Optional, Dict, Any
import re
import numpy as np
from sklearn.cluster import KMeans
from config.settings import Settings
from utils.logger import get_logger


logger = get_logger(__name__)


class SemanticChunkingService:
    """
    Service for advanced text chunking using semantic analysis.

    Provides both traditional word-based chunking and semantic chunking
    that uses embeddings to group related content.
    """

    def __init__(self, embedding_service, settings: Settings = None):
        """
        Initialize the chunking service.

        Args:
            embedding_service: EmbeddingService instance for semantic analysis
            settings: Application settings for default parameters
        """
        self.embedding_service = embedding_service
        self.settings = settings

        # Default chunking parameters
        self.default_chunk_size = settings.CHUNK_SIZE if settings else 500
        self.default_chunk_overlap = settings.CHUNK_OVERLAP if settings else 50

        logger.info("SemanticChunkingService initialized")

    def chunk_text(
        self,
        text: str,
        chunk_size: Optional[int] = None,
        chunk_overlap: Optional[int] = None,
        use_semantic: bool = True,
        use_sentences: bool = True
    ) -> List[str]:
        """
        Chunk text into smaller pieces using specified method.

        Args:
            text: Input text to chunk
            chunk_size: Target chunk size in words
            chunk_overlap: Overlap between chunks in words
            use_semantic: Use semantic chunking (True) or traditional (False)
            use_sentences: Respect sentence boundaries (True) or word boundaries (False)

        Returns:
            List of text chunks
        """
        try:
            if not text or not text.strip():
                logger.warning("Empty text provided for chunking")
                return []

            # Use provided parameters or defaults
            chunk_size = chunk_size or self.default_chunk_size
            chunk_overlap = chunk_overlap or self.default_chunk_overlap

            logger.info(f"Chunking text of length {len(text)} with method={'semantic' if use_semantic else 'traditional'}")

            # Choose chunking method
            if use_semantic:
                chunks = self.semantic_chunking(
                    text=text,
                    chunk_size=chunk_size,
                    overlap=chunk_overlap,
                    use_sentences=use_sentences
                )
            else:
                chunks = self.traditional_chunking(
                    text=text,
                    chunk_size=chunk_size,
                    overlap=chunk_overlap,
                    use_sentences=use_sentences
                )

            logger.info(f"Generated {len(chunks)} chunks")

            return chunks

        except Exception as e:
            logger.error(f"Text chunking failed: {e}")
            raise Exception(f"Text chunking failed: {e}")

    def semantic_chunking(
        self,
        text: str,
        chunk_size: int,
        overlap: int,
        use_sentences: bool = True,
        min_cluster_size: int = 2
    ) -> List[str]:
        """
        Advanced semantic chunking using embeddings and clustering.

        Args:
            text: Input text to chunk
            chunk_size: Target chunk size in words
            overlap: Overlap between chunks in words
            use_sentences: Respect sentence boundaries
            min_cluster_size: Minimum number of sentences per cluster

        Returns:
            List of semantically related text chunks
        """
        try:
            # Split into sentences
            sentences = self._split_sentences(text) if use_sentences else self._split_into_word_groups(text, chunk_size // 5)

            if len(sentences) <= 1:
                return [text] if text else []

            logger.info(f"Semantic chunking: {len(sentences)} sentences")

            # Generate embeddings for sentences
            sentence_embeddings = self.embedding_service.generate_embeddings(sentences)

            # Determine optimal number of clusters
            n_clusters = self._determine_optimal_clusters(
                len(sentences),
                chunk_size,
                min_cluster_size
            )

            # Cluster sentences
            if n_clusters > 1:
                clusters = self._cluster_sentences(sentence_embeddings, n_clusters)
            else:
                # If only one cluster, put all sentences in one group
                clusters = [0] * len(sentences)

            # Group sentences by clusters and create chunks
            chunks = self._create_chunks_from_clusters(
                sentences,
                clusters,
                chunk_size,
                overlap
            )

            return chunks

        except Exception as e:
            logger.error(f"Semantic chunking failed, falling back to traditional: {e}")
            # Fallback to traditional chunking
            return self.traditional_chunking(text, chunk_size, overlap, use_sentences)

    def traditional_chunking(
        self,
        text: str,
        chunk_size: int,
        overlap: int,
        use_sentences: bool = True
    ) -> List[str]:
        """
        Traditional text chunking based on word/sentence count.

        Args:
            text: Input text to chunk
            chunk_size: Target chunk size in words
            overlap: Overlap between chunks in words
            use_sentences: Respect sentence boundaries

        Returns:
            List of text chunks
        """
        try:
            if use_sentences:
                # Sentence-based chunking with word count limits
                return self._sentence_based_chunking(text, chunk_size, overlap)
            else:
                # Word-based chunking
                return self._word_based_chunking(text, chunk_size, overlap)

        except Exception as e:
            logger.error(f"Traditional chunking failed: {e}")
            raise Exception(f"Traditional chunking failed: {e}")

    def _split_sentences(self, text: str) -> List[str]:
        """
        Split text into sentences using regex.

        Args:
            text: Input text

        Returns:
            List of sentences
        """
        # Clean and normalize internal whitespace but preserve existing sentence structure
        text = re.sub(r'[ \t]+', ' ', text.strip())

        # Split on sentence boundaries
        # This regex handles common sentence endings: . ! ?
        sentence_endings = r'(?<=[.!?])\s+(?=[A-Z])'
        sentences = re.split(sentence_endings, text)

        # Clean up empty sentences
        sentences = [s.strip() for s in sentences if s.strip()]

        return sentences

    def _split_into_word_groups(self, text: str, group_size: int) -> List[str]:
        """
        Split text into word groups of specified size.

        Args:
            text: Input text
            group_size: Number of words per group

        Returns:
            List of word groups
        """
        words = text.split()
        groups = []
        for i in range(0, len(words), group_size):
            group = ' '.join(words[i:i + group_size])
            groups.append(group)
        return groups

    def _determine_optimal_clusters(self, num_sentences: int, chunk_size: int, min_cluster_size: int) -> int:
        """
        Determine optimal number of clusters for semantic chunking.

        Args:
            num_sentences: Number of sentences to cluster
            chunk_size: Target chunk size in words
            min_cluster_size: Minimum sentences per cluster

        Returns:
            Optimal number of clusters
        """
        # Estimate average sentence length (words)
        # Assume average of 15 words per sentence if not available
        avg_words_per_sentence = 15

        # Calculate how many sentences fit in target chunk size
        sentences_per_chunk = chunk_size / avg_words_per_sentence

        # Calculate number of clusters needed
        n_clusters = max(2, min(num_sentences // int(sentences_per_chunk), num_sentences // min_cluster_size))

        # Ensure we don't have more clusters than sentences
        n_clusters = min(n_clusters, num_sentences)

        logger.info(f"Determined {n_clusters} clusters for {num_sentences} sentences")
        return n_clusters

    def _cluster_sentences(self, embeddings: np.ndarray, n_clusters: int) -> List[int]:
        """
        Cluster sentences using K-means clustering.

        Args:
            embeddings: Sentence embeddings matrix
            n_clusters: Number of clusters

        Returns:
            List of cluster assignments
        """
        try:
            kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
            clusters = kmeans.fit_predict(embeddings)
            return clusters.tolist()

        except Exception as e:
            logger.error(f"Clustering failed: {e}")
            # Fallback: return sequential clusters
            return list(range(len(embeddings)))

    def _create_chunks_from_clusters(
        self,
        sentences: List[str],
        clusters: List[int],
        chunk_size: int,
        overlap: int
    ) -> List[str]:
        """
        Create text chunks from clustered sentences.

        Args:
            sentences: List of sentences
            clusters: Cluster assignments for each sentence
            chunk_size: Target chunk size in words
            overlap: Overlap between chunks

        Returns:
            List of text chunks
        """
        try:
            # Group sentences by cluster
            cluster_dict = {}
            for sentence, cluster in zip(sentences, clusters):
                if cluster not in cluster_dict:
                    cluster_dict[cluster] = []
                cluster_dict[cluster].append(sentence)

            # Sort clusters by their first sentence position (maintain order)
            sorted_clusters = sorted(cluster_dict.items(),
                                   key=lambda x: sentences.index(x[1][0]) if x[1] else 0)

            # Create chunks from cluster groups
            chunks = []
            for cluster_id, cluster_sentences in sorted_clusters:
                if not cluster_sentences:
                    continue

                # Join sentences in cluster
                chunk_text = ' '.join(cluster_sentences)

                # Split if chunk is too long
                chunk_words = chunk_text.split()
                if len(chunk_words) > chunk_size * 1.5:  # Allow 50% flexibility
                    # Split long chunks
                    sub_chunks = self._split_long_chunk(chunk_text, chunk_size)
                    chunks.extend(sub_chunks)
                else:
                    chunks.append(chunk_text)

            return chunks

        except Exception as e:
            logger.error(f"Failed to create chunks from clusters: {e}")
            # Fallback: join all sentences
            return [' '.join(sentences)]

    def _split_long_chunk(self, text: str, chunk_size: int) -> List[str]:
        """
        Split a long text chunk into smaller pieces.

        Args:
            text: Long text chunk
            chunk_size: Target size in words

        Returns:
            List of smaller chunks
        """
        words = text.split()
        chunks = []
        current_chunk = []
        current_size = 0

        for word in words:
            current_size += 1
            current_chunk.append(word)

            if current_size >= chunk_size:
                chunks.append(' '.join(current_chunk))
                current_chunk = []
                current_size = 0

        if current_chunk:
            chunks.append(' '.join(current_chunk))

        return chunks

    def _sentence_based_chunking(self, text: str, chunk_size: int, overlap: int) -> List[str]:
        """
        Chunk text while respecting sentence boundaries.

        Args:
            text: Input text
            chunk_size: Target chunk size in words
            overlap: Overlap between chunks in words

        Returns:
            List of text chunks
        """
        sentences = self._split_sentences(text)
        chunks = []
        current_chunk = []
        current_size = 0

        for sentence in sentences:
            sentence_words = len(sentence.split())

            # Start new chunk if size exceeded
            if current_size + sentence_words > chunk_size and current_chunk:
                chunks.append(' '.join(current_chunk))

                # Keep overlap sentences
                overlap_sentences = []
                overlap_size = 0
                for sent in reversed(current_chunk):
                    sent_words = len(sent.split())
                    if overlap_size + sent_words <= overlap:
                        overlap_sentences.insert(0, sent)
                        overlap_size += sent_words
                    else:
                        break

                current_chunk = overlap_sentences
                current_size = overlap_size

            current_chunk.append(sentence)
            current_size += sentence_words

        if current_chunk:
            chunks.append(' '.join(current_chunk))

        return chunks

    def _word_based_chunking(self, text: str, chunk_size: int, overlap: int) -> List[str]:
        """
        Chunk text based on word count without considering sentences.

        Args:
            text: Input text
            chunk_size: Target chunk size in words
            overlap: Overlap between chunks in words

        Returns:
            List of text chunks
        """
        words = text.split()
        chunks = []

        for i in range(0, len(words), chunk_size - overlap):
            chunk = ' '.join(words[i:i + chunk_size])
            chunks.append(chunk)

        return chunks

    def get_chunk_statistics(self, chunks: List[str]) -> Dict[str, Any]:
        """
        Calculate statistics about generated chunks.

        Args:
            chunks: List of text chunks

        Returns:
            Dictionary with chunk statistics
        """
        if not chunks:
            return {
                "count": 0,
                "total_words": 0,
                "avg_words": 0,
                "min_words": 0,
                "max_words": 0
            }

        word_counts = [len(chunk.split()) for chunk in chunks]

        return {
            "count": len(chunks),
            "total_words": sum(word_counts),
            "avg_words": sum(word_counts) / len(word_counts),
            "min_words": min(word_counts),
            "max_words": max(word_counts),
            "total_chars": sum(len(chunk) for chunk in chunks)
        }


# Convenience function to create chunking service
def create_chunking_service(embedding_service, settings: Settings) -> SemanticChunkingService:
    """
    Create a chunking service instance.

    Args:
        embedding_service: EmbeddingService instance
        settings: Application settings

    Returns:
        SemanticChunkingService instance
    """
    return SemanticChunkingService(embedding_service, settings)