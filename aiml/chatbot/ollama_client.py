"""
Ollama Client Module for CMS AI Assistant.
Provides a unified interface for interacting with Ollama (Llama 3.2),
handling streaming responses, structured JSON requests, and offline fallbacks.
"""

import json
import os
from typing import Generator, Dict, Any, List, Optional
try:
    import ollama
except ImportError:
    ollama = None
from dotenv import load_dotenv

load_dotenv()

DEFAULT_MODEL = os.getenv("MODEL_NAME", "llama3.2:latest")


class OllamaClient:
    """Wrapper for Ollama API communication with streaming and fallback support."""

    @staticmethod
    def get_model_name() -> str:
        return os.getenv("MODEL_NAME", DEFAULT_MODEL)

    @classmethod
    def generate_stream(
        cls,
        system_prompt: str,
        user_prompt: str,
        model_name: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 300
    ) -> Generator[str, None, None]:
        """
        Stream tokens from Ollama model. Yields individual token strings.
        Commented out for offline mode when no model is installed.
        """
        # if ollama is None:
        #     return
        # model = model_name or cls.get_model_name()
        # messages = [
        #     {"role": "system", "content": system_prompt},
        #     {"role": "user", "content": user_prompt}
        # ]
        # stream = ollama.chat(...)
        return
        yield ""

    @classmethod
    def generate_response(
        cls,
        system_prompt: str,
        user_prompt: str,
        model_name: Optional[str] = None,
        temperature: float = 0.1
    ) -> str:
        """
        Synchronous non-streaming call to Ollama model.
        Commented out for offline mode without Ollama.
        """
        # if ollama is None:
        #     return ""
        # model = model_name or cls.get_model_name()
        # response = ollama.chat(...)
        return ""

