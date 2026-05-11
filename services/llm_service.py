"""
LLM service for generating responses using Ollama.
Integrates with local Ollama instance using mistral model.
"""
import requests
import json
from typing import List, Dict, Optional


class LLMService:
    """
    Service for interacting with Ollama LLM.
    """

    def __init__(self, base_url: str = "http://localhost:11434", model: str = "mistral"):
        """
        Initialize LLM service.

        Args:
            base_url: Ollama API base URL
            model: Model name to use (default: mistral)
        """
        self.base_url = base_url
        self.model = model
        self.api_url = f"{base_url}/api/generate"

    def generate_response(self, question: str, context: str, system_prompt: Optional[str] = None) -> str:
        """
        Generate response based on question and retrieved context.

        Args:
            question: User's question
            context: Retrieved context from document
            system_prompt: Optional custom system prompt

        Returns:
            Generated response from LLM
        """
        if system_prompt is None:
            system_prompt = "Answer only from the provided context. If not found, say 'Not in document'."

        # Create prompt with context and question
        prompt = f"""Context: {context}

Question: {question}

Provide a helpful answer based on the context above."""

        try:
            response = requests.post(
                self.api_url,
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "system": system_prompt
                },
                timeout=60
            )

            response.raise_for_status()
            result = response.json()
            return result.get("response", "").strip()

        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to get response from Ollama: {str(e)}")

    def generate_response_with_chunks(self, question: str, relevant_chunks: List[str]) -> str:
        """
        Generate response using multiple relevant chunks.

        Args:
            question: User's question
            relevant_chunks: List of relevant text chunks

        Returns:
            Generated response from LLM
        """
        # Combine chunks into context
        context = "\n\n---\n\n".join(relevant_chunks)

        return self.generate_response(question, context)

    def check_ollama_available(self) -> bool:
        """
        Check if Ollama is running and accessible.

        Returns:
            True if Ollama is available, False otherwise
        """
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            return response.status_code == 200
        except requests.exceptions.RequestException:
            return False

    def get_available_models(self) -> List[str]:
        """
        Get list of available models from Ollama.

        Returns:
            List of model names
        """
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            response.raise_for_status()
            result = response.json()
            return [model.get("name", "") for model in result.get("models", [])]
        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to get models from Ollama: {str(e)}")


# Global instance
llm_service = LLMService()