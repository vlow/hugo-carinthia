"""LLM service factory and wrapper."""

from typing import Dict, Type
from interfaces.llm_interface import LLMInterface
from services.openai_service import OpenAIService
from services.claude_service import ClaudeService


class LLMService:
    """Factory class for creating LLM service instances."""

    _services: Dict[str, Type[LLMInterface]] = {
        'gpt-5': OpenAIService,  # GPT-5 with reasoning capabilities
        'claude': ClaudeService
    }

    @classmethod
    def create(cls, model: str) -> LLMInterface:
        """Create an LLM service instance for the specified model.

        Args:
            model: The model name ('gpt-5' or 'claude')

        Returns:
            LLM service instance

        Raises:
            ValueError: If model is not supported
        """
        if model not in cls._services:
            available_models = ', '.join(cls._services.keys())
            raise ValueError(f"Unsupported model: {model}. Available models: {available_models}")

        service_class = cls._services[model]
        return service_class()

    @classmethod
    def list_available_models(cls) -> list[str]:
        """Return list of available model names."""
        return list(cls._services.keys())
