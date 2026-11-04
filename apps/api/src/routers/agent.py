"""API router for agent execution and reasoning trace inspection."""

import json
import uuid
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from typing import Any

from agent.citations import Citation
from agent.loop import AgentLoop, AgentResponse
from agent.tools.calculator import CalculatorTool
from agent.tools.compare import CompareDocumentsTool
from agent.tools.search import SearchDocumentsTool
from agent.tools.section import GetSectionTool
from agent.tools.structured import QueryStructuredDataTool
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from llm.cache import LLMCache
from llm.gateway import LLMGateway
from llm.providers.base import BaseLLMProvider
from llm.providers.gemini import GeminiProvider
from llm.providers.groq import GroqProvider
from llm.providers.mock import MockLLMProvider
from llm.providers.ollama import OllamaProvider
from pydantic import BaseModel, Field
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.src.auth.deps import get_current_org, get_current_user
from apps.api.src.config import Settings, get_settings
from apps.api.src.db.session import async_session_maker, get_db
from apps.api.src.models.agent_trace import AgentTrace
from apps.api.src.models.user import User
from packages.rag.src.rag.embeddings import get_embedder
from packages.rag.src.rag.search import HybridRetriever

router = APIRouter(prefix="/agent", tags=["agent"])


class AgentQueryRequest(BaseModel):
    query: str = Field(
        ..., min_length=2, max_length=2000, description="User query or research question"
    )
    session_id: str | None = Field(
        None, max_length=100, description="Optional conversation session ID"
    )
    preferred_provider: str | None = Field(
        None, description="Preferred provider ('groq', 'gemini', 'ollama', 'mock')"
    )
    max_steps: int = Field(default=5, ge=1, le=10, description="Maximum reasoning steps")


class AgentQueryResponse(BaseModel):
    query: str
    final_answer: str
    refused: bool
    citations: list[Citation]
    trace_id: str
    steps_count: int
    tokens_total: int
    latency_ms: float
    provider: str
    model: str


class FeedbackRequest(BaseModel):
    trace_id: uuid.UUID
    rating: int = Field(..., ge=-1, le=1, description="1 for positive, -1 for negative")
    comment: str | None = Field(None, max_length=1000)


class AgentTraceSummary(BaseModel):
    id: uuid.UUID
    query: str
    final_answer: str
    refused: bool
    citations_count: int
    tool_calls_count: int
    tokens_total: int
    latency_ms: float
    provider: str
    model: str
    created_at: str


class AgentTraceDetail(BaseModel):
    id: uuid.UUID
    query: str
    final_answer: str
    refused: bool
    citations: list[dict[str, Any]]
    steps: list[dict[str, Any]]
    tool_calls_count: int
    retrieved_chunks_count: int
    tokens_prompt: int
    tokens_completion: int
    tokens_total: int
    latency_ms: float
    provider: str
    model: str
    error: str | None
    created_at: str


def build_agent_loop(settings: Settings) -> AgentLoop:
    """Constructs configured AgentLoop with all tools and prioritized LLM gateway."""
    # 1. Initialize providers
    providers: list[BaseLLMProvider] = []

    # Add providers based on settings order
    for p_name in settings.llm_provider_order:
        if p_name == "groq" and settings.groq_api_key:
            providers.append(
                GroqProvider(
                    api_key=settings.groq_api_key,
                    model=settings.groq_model,
                    rate_limit_rpm=settings.rate_limit_groq_rpm,
                )
            )
        elif p_name == "gemini" and settings.gemini_api_key:
            providers.append(
                GeminiProvider(
                    api_key=settings.gemini_api_key,
                    model=settings.gemini_model,
                    rate_limit_rpm=settings.rate_limit_gemini_rpm,
                )
            )
        elif p_name == "ollama":
            providers.append(
                OllamaProvider(
                    base_url=settings.ollama_base_url,
                    model=settings.ollama_model,
                )
            )
        elif p_name == "mock":
            providers.append(MockLLMProvider())

    # Ensure at least MockLLMProvider is available if no external API keys are configured
    if not providers:
        providers.append(MockLLMProvider())

    gateway = LLMGateway(providers=providers, cache=LLMCache(), enable_cache=True)

    # 2. Initialize Retriever and Tools
    embedder = get_embedder()
    retriever = HybridRetriever(embedder=embedder)

    tools = [
        SearchDocumentsTool(retriever=retriever, session_factory=async_session_maker),
        GetSectionTool(session_factory=async_session_maker),
        CompareDocumentsTool(session_factory=async_session_maker),
        QueryStructuredDataTool(session_factory=async_session_maker),
        CalculatorTool(),
    ]

    return AgentLoop(
        gateway=gateway,
        tools=tools,
        session_factory=async_session_maker,
        max_steps=5,
    )


@router.post("/query", response_model=AgentQueryResponse)
async def query_agent(
    payload: AgentQueryRequest,
    current_org_id: uuid.UUID = Depends(get_current_org),
    current_user: User = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> AgentResponse:
    """Executes the bounded tool-calling agent with grounded citations and trace recording."""
    agent_loop = build_agent_loop(settings)
    agent_loop.max_steps = payload.max_steps

    return await agent_loop.run(
        org_id=current_org_id,
        query=payload.query,
        user_id=current_user.id,
        session_id=payload.session_id,
        preferred_provider=payload.preferred_provider,
    )


@router.post("/query/stream")
async def query_agent_stream(
    payload: AgentQueryRequest,
    current_org_id: uuid.UUID = Depends(get_current_org),
    current_user: User = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> StreamingResponse:
    """Streams the agent reasoning progress, tool invocations, and response tokens via SSE."""
    agent_loop = build_agent_loop(settings)
    agent_loop.max_steps = payload.max_steps

    async def event_generator() -> AsyncGenerator[str, None]:
        try:
            async for chunk in agent_loop.run_stream(
                org_id=current_org_id,
                query=payload.query,
                user_id=current_user.id,
                session_id=payload.session_id,
                preferred_provider=payload.preferred_provider,
            ):
                event_name = chunk.get("event", "message")
                data_str = json.dumps(chunk.get("data", {}))
                yield f"event: {event_name}\ndata: {data_str}\n\n"
        except Exception as e:
            err_data = json.dumps({"error": str(e)})
            yield f"event: error\ndata: {err_data}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/feedback", status_code=status.HTTP_200_OK)
async def submit_feedback(
    payload: FeedbackRequest,
    current_org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Records user thumbs up/down and optional comment for a trace."""
    stmt = select(AgentTrace).where(
        AgentTrace.id == payload.trace_id,
        AgentTrace.org_id == current_org_id,
    )
    result = await db.execute(stmt)
    trace = result.scalar_one_or_none()

    if not trace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trace not found",
        )

    trace.feedback = {
        "rating": payload.rating,
        "comment": payload.comment,
        "submitted_at": datetime.now(UTC).isoformat(),
    }
    await db.commit()
    return {"status": "success", "message": "Feedback submitted successfully"}


@router.get("/traces", response_model=list[AgentTraceSummary])
async def list_agent_traces(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    session_id: str | None = None,
    current_org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
) -> list[AgentTraceSummary]:
    """Lists audit traces of past agent queries for the authenticated organization."""
    conditions = [AgentTrace.org_id == current_org_id]
    if session_id:
        conditions.append(AgentTrace.session_id == session_id)

    stmt = (
        select(AgentTrace)
        .where(*conditions)
        .order_by(desc(AgentTrace.created_at))
        .limit(limit)
        .offset(offset)
    )
    result = await db.execute(stmt)
    traces = result.scalars().all()

    return [
        AgentTraceSummary(
            id=t.id,
            query=t.query,
            final_answer=t.final_answer,
            refused=t.refused,
            citations_count=len(t.citations),
            tool_calls_count=t.tool_calls_count,
            tokens_total=t.tokens_total,
            latency_ms=t.latency_ms,
            provider=t.provider,
            model=t.model,
            created_at=t.created_at.isoformat(),
        )
        for t in traces
    ]


@router.get("/traces/{trace_id}", response_model=AgentTraceDetail)
async def get_agent_trace_detail(
    trace_id: uuid.UUID,
    current_org_id: uuid.UUID = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
) -> AgentTraceDetail:
    """Inspects detailed step-by-step reasoning and tool outputs for a specific trace."""
    stmt = select(AgentTrace).where(
        AgentTrace.id == trace_id,
        AgentTrace.org_id == current_org_id,
    )
    result = await db.execute(stmt)
    trace = result.scalar_one_or_none()

    if not trace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trace not found",
        )

    return AgentTraceDetail(
        id=trace.id,
        query=trace.query,
        final_answer=trace.final_answer,
        refused=trace.refused,
        citations=trace.citations,
        steps=trace.steps,
        tool_calls_count=trace.tool_calls_count,
        retrieved_chunks_count=trace.retrieved_chunks_count,
        tokens_prompt=trace.tokens_prompt,
        tokens_completion=trace.tokens_completion,
        tokens_total=trace.tokens_total,
        latency_ms=trace.latency_ms,
        provider=trace.provider,
        model=trace.model,
        error=trace.error,
        created_at=trace.created_at.isoformat(),
    )
