"""
Gemini LLM service for PDF RAG Chatbot application.
Uses the google-genai SDK (google.genai) for cloud-based response generation.
Replaces the local HuggingFace Transformers model entirely.
"""
import base64
from google import genai
from google.genai import types as genai_types
from typing import Optional, List, Dict, Any
from config.settings import Settings
from utils.logger import get_logger


logger = get_logger(__name__)


class GeminiLLMService:
    """
    Service for generating responses using the Google Gemini API.

    Uses the new google-genai SDK. Supports standard and streaming generation.
    No local model download required — fully cloud-based.
    """

    _instance = None

    def __new__(cls, settings: Settings):
        """Ensure singleton pattern"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize(settings)
        return cls._instance

    def _initialize(self, settings: Settings):
        """Initialize the Gemini LLM service"""
        try:
            self.settings = settings
            self.model_name = settings.GEMINI_MODEL_NAME
            self.api_key = settings.GEMINI_API_KEY

            # Create the authenticated client
            self._client = genai.Client(api_key=self.api_key)

            logger.info(f"GeminiLLMService initialized with model: {self.model_name}")

        except Exception as e:
            logger.error(f"Failed to initialize GeminiLLMService: {e}")
            raise Exception(f"Gemini LLM service initialization failed: {e}")

    # ------------------------------------------------------------------
    # Core generation methods
    # ------------------------------------------------------------------

    def generate_response(
        self,
        prompt: str,
        max_length: Optional[int] = None,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        top_k: Optional[int] = None,
        repetition_penalty: Optional[float] = None,
        stop_sequences: Optional[List[str]] = None,
        image: Optional[str] = None,
        mime_type: Optional[str] = None,
    ) -> str:
        """
        Generate a response from Gemini.

        Args:
            prompt: Input prompt for the model
            max_length: Maximum number of output tokens (default: from settings)
            temperature: Sampling temperature (default: from settings)
            top_p: Nucleus sampling parameter (default: from settings)
            top_k: Unused — kept for API compatibility
            repetition_penalty: Unused — kept for API compatibility
            stop_sequences: Sequences that stop generation
            image: Base64 encoded image data
            mime_type: MIME type for image

        Returns:
            Generated text response
        """
        try:
            max_tokens = max_length or self.settings.DEFAULT_MAX_LENGTH
            temp = temperature if temperature is not None else self.settings.DEFAULT_TEMPERATURE
            tp = top_p if top_p is not None else self.settings.DEFAULT_TOP_P

            config = genai_types.GenerateContentConfig(
                max_output_tokens=max_tokens,
                temperature=temp,
                top_p=tp,
                stop_sequences=stop_sequences or [],
            )

            # Build contents with optional image
            contents = prompt
            if image and mime_type:
                import base64
                image_bytes = base64.b64decode(image) if isinstance(image, str) else image
                contents = [
                    prompt,
                    genai_types.Part.from_bytes(
                        data=image_bytes,
                        mime_type=mime_type,
                    ),
                ]

            logger.info(
                f"Generating Gemini response (model={self.model_name}, "
                f"max_tokens={max_tokens}, temperature={temp})"
            )

            response = self._client.models.generate_content(
                model=self.model_name,
                contents=contents,
                config=config,
            )

            result = response.text.strip()
            logger.info(f"Gemini response generated ({len(result)} chars)")
            return result

        except Exception as e:
            logger.error(f"Gemini response generation failed: {e}")
            raise Exception(f"Failed to generate response from Gemini: {e}")

    def generate_chat_response(
        self,
        messages: List[Dict[str, str]],
        max_length: Optional[int] = None,
        temperature: Optional[float] = None,
        system_prompt: Optional[str] = None,
        image: Optional[str] = None,
        mime_type: Optional[str] = None,
    ) -> str:
        """
        Generate a response in chat format using Gemini.

        Args:
            messages: List of dicts with 'role' and 'content'
            max_length: Maximum number of output tokens
            temperature: Sampling temperature
            system_prompt: Optional system-level instruction
            image: Base64 encoded image data
            mime_type: MIME type for image

        Returns:
            Generated chat response string
        """
        try:
            prompt = self._format_chat_messages(messages, system_prompt)
            return self.generate_response(
                prompt=prompt,
                max_length=max_length,
                temperature=temperature,
                image=image,
                mime_type=mime_type,
            )
        except Exception as e:
            logger.error(f"Chat response generation failed: {e}")
            raise Exception(f"Failed to generate chat response: {e}")

    def generate_streaming(
        self,
        prompt: str,
        max_length: Optional[int] = None,
        temperature: Optional[float] = None,
        image: Optional[str] = None,
        mime_type: Optional[str] = None,
    ):
        """
        Generate response with streaming using Gemini's stream API.

        Args:
            prompt: Input prompt for the model
            max_length: Maximum number of output tokens
            temperature: Sampling temperature
            image: Base64 encoded image data
            mime_type: MIME type for image

        Yields:
            Generated text chunks (strings)
        """
        try:
            max_tokens = max_length or self.settings.DEFAULT_MAX_LENGTH
            temp = temperature if temperature is not None else self.settings.DEFAULT_TEMPERATURE

            config = genai_types.GenerateContentConfig(
                max_output_tokens=max_tokens,
                temperature=temp,
                top_p=self.settings.DEFAULT_TOP_P,
            )

            # Build contents with optional image
            contents = prompt
            if image and mime_type:
                # For streaming with image, we need to use bytes
                import base64
                image_bytes = base64.b64decode(image) if isinstance(image, str) else image
                contents = [
                    prompt,
                    genai_types.Part.from_bytes(
                        data=image_bytes,
                        mime_type=mime_type,
                    ),
                ]

            logger.info(
                f"Starting Gemini streaming generation "
                f"(model={self.model_name}, temperature={temp})"
            )

            for chunk in self._client.models.generate_content_stream(
                model=self.model_name,
                contents=contents,
                config=config,
            ):
                if chunk.text:
                    yield chunk.text

            logger.info("Gemini streaming generation completed")

        except Exception as e:
            logger.error(f"Gemini streaming generation failed: {e}")
            raise Exception(f"Failed to generate streaming response: {e}")

    # ------------------------------------------------------------------
    # Helper / compatibility methods
    # ------------------------------------------------------------------

    def _format_chat_messages(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
    ) -> str:
        """
        Format chat messages into a single prompt string for Gemini.

        Args:
            messages: List of message dicts with 'role' and 'content'
            system_prompt: Optional system instruction

        Returns:
            Formatted prompt string
        """
        prompt = ""

        if system_prompt:
            prompt += f"System: {system_prompt}\n\n"

        for message in messages:
            role = message.get("role", "user")
            content = message.get("content", "")

            if role == "user":
                prompt += f"User: {content}\n"
            elif role == "assistant":
                prompt += f"Assistant: {content}\n"
            elif role == "system":
                prompt += f"System: {content}\n"

        prompt += "Assistant:"
        return prompt

    def get_model_info(self) -> Dict[str, Any]:
        """
        Get information about the current Gemini configuration.

        Returns:
            Dictionary with model information
        """
        return {
            "model_name": self.model_name,
            "provider": "Google Gemini API",
            "is_loaded": True,  # Always ready — cloud-based, no local loading
            "device": "cloud",
            "max_length": self.settings.DEFAULT_MAX_LENGTH,
            "temperature": self.settings.DEFAULT_TEMPERATURE,
        }

    def ensure_loaded(self):
        """No-op: Gemini is always ready (cloud-based)."""
        pass

    def unload_model(self):
        """No-op: cloud model, nothing to unload locally."""
        logger.info("GeminiLLMService: unload_model called (no-op for cloud model)")

    def reload_model(self):
        """No-op: cloud model, nothing to reload locally."""
        logger.info("GeminiLLMService: reload_model called (no-op for cloud model)")

    def clear_cache(self):
        """No-op: no local cache to clear for the Gemini cloud model."""
        logger.info("GeminiLLMService: clear_cache called (no-op for cloud model)")