"""
PDF processing service using PyMuPDF.
Handles PDF text extraction and chunking for embedding generation.
"""
import fitz  # PyMuPDF
from typing import List, Tuple
import re


class PDFService:
    """
    Service for processing PDF files and extracting text.
    """

    def __init__(self, min_chunk_words: int = 500, max_chunk_words: int = 1000):
        """
        Initialize PDF service.

        Args:
            min_chunk_words: Minimum words per chunk
            max_chunk_words: Maximum words per chunk
        """
        self.min_chunk_words = min_chunk_words
        self.max_chunk_words = max_chunk_words

    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """
        Extract all text from a PDF file.

        Args:
            pdf_path: Path to the PDF file

        Returns:
            Extracted text as string
        """
        text = ""
        try:
            doc = fitz.open(pdf_path)
            for page in doc:
                text += page.get_text()
            doc.close()
        except Exception as e:
            raise Exception(f"Failed to extract text from PDF: {str(e)}")

        return text

    def chunk_text(self, text: str) -> List[str]:
        """
        Split text into chunks of specified word count range.

        Args:
            text: Text to chunk

        Returns:
            List of text chunks
        """
        # Clean text - remove excessive whitespace
        text = re.sub(r'\s+', ' ', text).strip()

        # Split into words
        words = text.split()

        chunks = []
        current_chunk = []

        for word in words:
            current_chunk.append(word)

            # Check if chunk reached max size
            if len(current_chunk) >= self.max_chunk_words:
                chunks.append(' '.join(current_chunk))
                current_chunk = []

        # Add remaining words as last chunk if it meets minimum size
        if current_chunk and len(current_chunk) >= self.min_chunk_words:
            chunks.append(' '.join(current_chunk))

        return chunks

    def process_pdf(self, pdf_path: str) -> List[str]:
        """
        Process PDF: extract text and return chunks.

        Args:
            pdf_path: Path to PDF file

        Returns:
            List of text chunks
        """
        # Extract text
        text = self.extract_text_from_pdf(pdf_path)

        # Check if we got any text
        if not text or len(text.strip()) < 50:
            raise Exception("PDF contains too little text to process")

        # Chunk text
        chunks = self.chunk_text(text)

        if not chunks:
            raise Exception("Failed to create chunks from PDF text")

        return chunks

    def get_pdf_info(self, pdf_path: str) -> dict:
        """
        Get basic information about a PDF file.

        Args:
            pdf_path: Path to PDF file

        Returns:
            Dictionary with PDF metadata
        """
        try:
            doc = fitz.open(pdf_path)
            info = {
                "page_count": len(doc),
                "metadata": doc.metadata,
                "file_size": len(doc.read())
            }
            doc.close()
            return info
        except Exception as e:
            raise Exception(f"Failed to get PDF info: {str(e)}")


# Global instance
pdf_service = PDFService()