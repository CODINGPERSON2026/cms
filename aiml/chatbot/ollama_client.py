"""
Ollama Client Module for CMS AI Assistant.
Provides a unified interface for interacting with Ollama (Llama 3.2),
handling streaming responses, structured JSON requests, and offline fallbacks.
"""

import json
import os
from typing import Generator, Dict, Any, List, Optional
import ollama
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
        Raises Exception if Ollama call fails.
        """
        model = model_name or cls.get_model_name()
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        stream = ollama.chat(
            model=model,
            messages=messages,
            stream=True,
            options={
                "num_predict": min(max_tokens, 200),
                "temperature": temperature,
                "top_p": 0.7,
                "repeat_penalty": 1.1,
                "num_ctx": 1024,
            }
        )

        for chunk in stream:
            token = chunk.get("message", {}).get("content", "")
            if token:
                yield token

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
        Returns complete response text string.
        """
        model = model_name or cls.get_model_name()
        response = ollama.chat(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            options={
                "num_predict": 200,
                "temperature": temperature,
                "top_p": 0.7,
                "num_ctx": 1024,
            }
        )
        return response.get("message", {}).get("content", "").strip()

