"""Base definitions and protocols for Agent tools."""

import uuid
from abc import ABC, abstractmethod
from typing import Any

from llm.types import FunctionDefinition, ToolDefinition
from pydantic import BaseModel


class ToolResult(BaseModel):
    """Normalized output from any executed tool."""

    tool_name: str
    success: bool
    data: Any
    error: str | None = None


class BaseTool(ABC):
    """Abstract base class for all tenant-scoped agent tools."""

    name: str
    description: str
    parameters: dict[str, Any]

    def to_tool_definition(self) -> ToolDefinition:
        """Converts tool into an OpenAI/Groq compatible ToolDefinition."""
        return ToolDefinition(
            function=FunctionDefinition(
                name=self.name,
                description=self.description,
                parameters=self.parameters,
            )
        )

    @abstractmethod
    async def execute(self, org_id: uuid.UUID, **kwargs: Any) -> ToolResult:
        """Executes the tool with strict tenant scoping."""
        pass
