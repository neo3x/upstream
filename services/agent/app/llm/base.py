"""Abstract LLM provider interface."""
from abc import ABC, abstractmethod
from typing import Optional, Type

from pydantic import BaseModel


class LLMProvider(ABC):
    """All providers implement this interface."""

    name: str
    supports_vision: bool

    @abstractmethod
    def complete_text(
        self,
        system: str,
        user: str,
        max_tokens: int = 1024,
        temperature: float = 0.2,
    ) -> str:
        """Plain text completion."""

    @abstractmethod
    def complete_multimodal(
        self,
        system: str,
        user_text: str,
        image_b64: Optional[str],
        max_tokens: int = 1024,
        temperature: float = 0.2,
    ) -> str:
        """Multimodal completion (text + optional image)."""

    @abstractmethod
    def complete_structured(
        self,
        system: str,
        user: str,
        schema: Type[BaseModel],
        image_b64: Optional[str] = None,
        max_tokens: int = 2048,
        temperature: float = 0.2,
    ) -> BaseModel:
        """Structured output forced into the given Pydantic schema."""

