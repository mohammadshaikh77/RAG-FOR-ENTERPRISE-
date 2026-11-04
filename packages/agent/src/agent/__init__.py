"""Agent package providing bounded tool-calling reasoning, citations, and trace persistence."""

from agent.citations import Citation, extract_citations, is_refusal
from agent.loop import AgentLoop, AgentResponse, AgentStep
from agent.tools import (
    BaseTool,
    CalculatorTool,
    CompareDocumentsTool,
    GetSectionTool,
    QueryStructuredDataTool,
    SearchDocumentsTool,
    ToolResult,
)

__all__ = [
    "AgentLoop",
    "AgentResponse",
    "AgentStep",
    "Citation",
    "extract_citations",
    "is_refusal",
    "BaseTool",
    "ToolResult",
    "SearchDocumentsTool",
    "GetSectionTool",
    "CompareDocumentsTool",
    "QueryStructuredDataTool",
    "CalculatorTool",
]
