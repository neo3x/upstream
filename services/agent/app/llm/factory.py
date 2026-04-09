"""Factory for resolving the configured LLM provider."""
from .base import LLMProvider
from ..config import settings


def get_llm_provider(name: str | None = None) -> LLMProvider:
    """Resolve a provider by name or fall back to settings."""
    chosen = (name or settings.llm_provider).lower()

    if chosen == "claude":
        from .claude_provider import ClaudeProvider

        return ClaudeProvider()
    if chosen == "openai":
        from .openai_provider import OpenAIProvider

        return OpenAIProvider()
    if chosen == "ollama":
        from .ollama_provider import OllamaProvider

        return OllamaProvider()
    if chosen == "mock":
        from .mock_provider import MockProvider

        return MockProvider()

    raise ValueError(f"Unknown LLM provider: {chosen}")

