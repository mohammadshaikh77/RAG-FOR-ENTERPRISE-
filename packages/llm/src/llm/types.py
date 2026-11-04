"""Data models and type definitions for LLM requests, responses, and tool calls."""

import json
from typing import Any, Literal

from pydantic import BaseModel, Field


class FunctionCall(BaseModel):
    """Represents a function name and arguments requested by an LLM."""

    name: str
    arguments: str  # JSON-encoded arguments string


class ToolCall(BaseModel):
    """Represents a tool call initiated by an LLM."""

    id: str
    type: Literal["function"] = "function"
    function: FunctionCall

    def get_parsed_arguments(self) -> dict[str, Any]:
        """Safely parses arguments JSON into a dictionary."""
        try:
            return json.loads(self.function.arguments)  # type: ignore[no-any-return]
        except Exception:
            return {}


class ChatMessage(BaseModel):
    """Represents a chat message compatible with OpenAI/Groq/Gemini specifications."""

    role: Literal["system", "user", "assistant", "tool"]
    content: str | None = None
    name: str | None = None
    tool_call_id: str | None = None
    tool_calls: list[ToolCall] | None = None

    def to_api_dict(self) -> dict[str, Any]:
        """Converts message into standard JSON format expected by OpenAI-compatible endpoints."""
        d: dict[str, Any] = {"role": self.role}
        if self.content is not None:
            d["content"] = self.content
        if self.name is not None:
            d["name"] = self.name
        if self.tool_call_id is not None:
            d["tool_call_id"] = self.tool_call_id
        if self.tool_calls is not None:
            d["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": tc.type,
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                }
                for tc in self.tool_calls
            ]
        return d


class FunctionDefinition(BaseModel):
    """JSON Schema definition for an individual callable tool function."""

    name: str
    description: str
    parameters: dict[str, Any] = Field(default_factory=dict)


class ToolDefinition(BaseModel):
    """Standard OpenAI/Groq-compatible tool specification."""

    type: Literal["function"] = "function"
    function: FunctionDefinition

    def to_api_dict(self) -> dict[str, Any]:
        return {
            "type": self.type,
            "function": {
                "name": self.function.name,
                "description": self.function.description,
                "parameters": self.function.parameters,
            },
        }


class TokenUsage(BaseModel):
    """Token consumption statistics."""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class LLMResponse(BaseModel):
    """Normalized response from any LLM provider."""

    content: str | None = None
    tool_calls: list[ToolCall] = Field(default_factory=list)
    provider: str
    model: str
    usage: TokenUsage = Field(default_factory=TokenUsage)
    finish_reason: str = "stop"
    raw_response: dict[str, Any] | None = None
