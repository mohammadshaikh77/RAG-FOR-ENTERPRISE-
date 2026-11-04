"""Abstract base class for all LLM providers."""

from abc import ABC, abstractmethod
from typing import Any

from llm.types import ChatMessage, LLMResponse, ToolDefinition


class BaseLLMProvider(ABC):
    """Abstract interface for LLM providers."""

    def __init__(self, name: str, model: str) -> None:
        self.name = name
        self.model = model

    @abstractmethod
    async def generate(
        self,
        messages: list[ChatMessage],
        temperature: float = 0.0,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> LLMResponse:
        """Generates a text completion from messages."""
        pass

    @abstractmethod
    async def generate_with_tools(
        self,
        messages: list[ChatMessage],
        tools: list[ToolDefinition],
        temperature: float = 0.0,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> LLMResponse:
        """Generates a completion that may choose to invoke one or more tools."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Returns True if the provider is configured and ready to receive requests."""
        pass
