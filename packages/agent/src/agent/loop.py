"""Bounded ReAct agent execution loop with citations and trace recording."""

import json
import time
import uuid
from collections.abc import AsyncGenerator
from typing import Any

import structlog
from llm.gateway import LLMGateway
from llm.types import ChatMessage, ToolCall
from pydantic import BaseModel

from agent.citations import Citation, extract_citations, is_refusal
from agent.tools.base import BaseTool
from apps.api.src.models.agent_trace import AgentTrace

logger = structlog.get_logger(__name__)

SYSTEM_PROMPT = """You are "Cite", an AI document question-answering assistant.
Your goal is to provide accurate, readable, professional, and fully grounded answers using exclusively the evidence retrieved from uploaded documents.

You have access to 5 tools:
1. `search_documents(query, section_filter, top_k)`: Primary tool to retrieve relevant text passages from uploaded documents.
2. `get_section(document_id, section_name)`: Retrieves the text of a specific section (e.g., 'Boxed Warning', 'Contraindications', 'Dosage and Administration').
3. `compare_documents(doc_a_id, doc_b_id, topic)`: Pairs sections between two documents for comparison.
4. `query_structured_data(query_type, parameters)`: Retrieves metadata (document classes, routes, identifiers).
5. `calculator(expression)`: Safely evaluates arithmetic expressions (dosages, unit conversions).

RULES:
1. GROUNDING & EVIDENCE: Base every statement and claim strictly on evidence returned by your tools. Do not speculate, invent, or extrapolate beyond the retrieved text.
2. WRITING STYLE: Directly answer the question in clear, polished, natural English. Use bullet points or short paragraphs for readability. Do NOT append a separate "Sources" or bibliography section at the end of your response, as the system automatically extracts citations into an interactive panel.
3. INLINE CITATIONS: For each factual claim or key quote, append the citation immediately using the format:
   [Document: <Document Title> | Section: <Section Name> | "<verbatim quoted supporting text>"]
   The quoted text MUST be a direct, verbatim excerpt from the passage text provided.
4. NEGATIVE & REFUSAL INQUIRIES: If asked whether a document mentions something that is not present, or if asked whether a medicine cures a disease when the document only mentions managing symptoms or hypertension, clearly state what the document specifies and note that it contains no evidence or indication supporting the queried claim. If no relevant evidence is found at all, state:
   "I couldn't find enough information to answer this question in your uploaded documents."
5. CLINICAL & TOPICAL PRECISION: Strictly distinguish between distinct concepts:
   - Contraindications: Only conditions under which the drug must NOT be used. Never confuse adverse reactions with contraindications.
   - Boxed Warnings: Only human black-box warnings. Never confuse animal nonclinical toxicology studies with human boxed warnings.
"""


def _format_tool_output_for_llm(tool_name: str, tool_out: dict[str, Any]) -> str:
    """Formats tool outputs into clean, high-signal readable text for the model."""
    if not tool_out.get("success", False):
        return f"Error executing {tool_name}: {tool_out.get('error', 'Unknown error')}"

    data = tool_out.get("data")
    if tool_name == "search_documents" and isinstance(data, list):
        if not data:
            return "No matching document passages found."
        passages = []
        for i, chunk in enumerate(data, 1):
            doc = chunk.get("document_title", "Unknown Document")
            sec = chunk.get("section_title", "General")
            text = chunk.get("content", "").strip()
            passages.append(f"[Passage {i}]\nDocument: {doc}\nSection: {sec}\nText:\n{text}")
        return "\n\n".join(passages)

    if tool_name == "get_section" and isinstance(data, dict):
        doc = data.get("document_title", "Unknown Document")
        sec = data.get("section_title", "Section")
        text = data.get("content", "").strip()
        return f"Document: {doc}\nSection: {sec}\nContent:\n{text}"

    return json.dumps(tool_out)


class AgentStep(BaseModel):
    """Execution details for an individual step in the agent loop."""

    step_index: int
    tool_calls: list[dict[str, Any]] = []
    tool_results: list[dict[str, Any]] = []
    latency_ms: float = 0.0


class AgentResponse(BaseModel):
    """Final output of an agent run."""

    query: str
    final_answer: str
    refused: bool
    citations: list[Citation] = []
    trace_id: str
    steps_count: int
    tokens_total: int
    latency_ms: float
    provider: str
    model: str


class AgentLoop:
    """Manages multi-step bounded agent reasoning, tool execution, and audit logging."""

    def __init__(
        self,
        gateway: LLMGateway,
        tools: list[BaseTool],
        session_factory: Any,
        max_steps: int = 5,
        timeout_seconds: float = 60.0,
    ) -> None:
        self.gateway = gateway
        self.tools = {t.name: t for t in tools}
        self.tool_definitions = [t.to_tool_definition() for t in tools]
        self.session_factory = session_factory
        self.max_steps = max_steps
        self.timeout_seconds = timeout_seconds

    async def run(
        self,
        org_id: uuid.UUID,
        query: str,
        user_id: uuid.UUID | None = None,
        session_id: str | None = None,
        preferred_provider: str | None = None,
    ) -> AgentResponse:
        """Executes the agent loop with bounds, citations, and trace persistence."""
        start_time = time.monotonic()
        trace_id = uuid.uuid4()

        messages: list[ChatMessage] = [
            ChatMessage(role="system", content=SYSTEM_PROMPT),
            ChatMessage(role="user", content=query),
        ]

        steps: list[AgentStep] = []
        retrieved_chunks_accumulator: list[dict[str, Any]] = []
        total_prompt_tokens = 0
        total_completion_tokens = 0
        final_answer = ""
        provider_used = "unknown"
        model_used = "unknown"
        execution_error: str | None = None

        logger.info("Starting agent run", trace_id=str(trace_id), org_id=str(org_id), query=query)

        for step_idx in range(1, self.max_steps + 1):
            # Check elapsed timeout
            elapsed = time.monotonic() - start_time
            if elapsed > self.timeout_seconds:
                logger.warning(
                    "Agent run exceeded timeout", elapsed=elapsed, trace_id=str(trace_id)
                )
                final_answer = (
                    "I was unable to complete the research within the allowed execution time."
                )
                break

            step_start = time.monotonic()
            step = AgentStep(step_index=step_idx)

            try:
                # If we already retrieved document passages on a previous step,
                # guide the model to synthesize the final answer rather than endlessly looping.
                if step_idx >= 2 and retrieved_chunks_accumulator:
                    messages.append(
                        ChatMessage(
                            role="user",
                            content=(
                                "You have retrieved relevant document passages. "
                                "Synthesize your final, grounded answer directly now based strictly on the retrieved passages above. "
                                "Include verbatim inline citations in the format [Document: <Title> | Section: <Section> | \"<verbatim quote>\"]. "
                                "Do NOT make any more tool calls."
                            ),
                        )
                    )

                llm_resp = await self.gateway.generate_with_tools(
                    messages=messages,
                    tools=self.tool_definitions,
                    temperature=0.0,
                    preferred_provider=preferred_provider,
                )

                provider_used = llm_resp.provider
                model_used = llm_resp.model
                total_prompt_tokens += llm_resp.usage.prompt_tokens
                total_completion_tokens += llm_resp.usage.completion_tokens

                # Check if model produced tool calls
                if llm_resp.tool_calls:
                    # Append assistant message with tool calls
                    messages.append(
                        ChatMessage(
                            role="assistant",
                            content=llm_resp.content,
                            tool_calls=llm_resp.tool_calls,
                        )
                    )

                    for tc in llm_resp.tool_calls:
                        step.tool_calls.append(
                            {
                                "id": tc.id,
                                "name": tc.function.name,
                                "arguments": tc.function.arguments,
                            }
                        )

                        # Execute tool
                        tool_out = await self._execute_tool(org_id, tc)
                        step.tool_results.append(
                            {
                                "tool_call_id": tc.id,
                                "tool_name": tc.function.name,
                                "success": tool_out.get("success", False),
                                "output": tool_out,
                            }
                        )

                        # Accumulate retrieved chunks if search tool
                        if tc.function.name == "search_documents" and isinstance(
                            tool_out.get("data"), list
                        ):
                            retrieved_chunks_accumulator.extend(tool_out["data"])

                        # Feed clean tool result back into conversation
                        raw_payload = _format_tool_output_for_llm(tc.function.name, tool_out)
                        messages.append(
                            ChatMessage(
                                role="tool",
                                tool_call_id=tc.id,
                                name=tc.function.name,
                                content=raw_payload,
                            )
                        )

                    step.latency_ms = round((time.monotonic() - step_start) * 1000, 2)
                    steps.append(step)

                else:
                    # Final synthesis response reached
                    final_answer = llm_resp.content or "No response generated."
                    step.latency_ms = round((time.monotonic() - step_start) * 1000, 2)
                    steps.append(step)
                    break

            except Exception as e:
                execution_error = str(e)
                logger.error(
                    "Agent step failed", error=str(e), step=step_idx, trace_id=str(trace_id)
                )
                final_answer = f"Agent encountered an internal error during reasoning: {e}"
                break

        # If loop reached max_steps without final answer
        if not final_answer:
            final_answer = "Reached maximum reasoning step limit without finding sufficient evidence to conclude."

        refused = is_refusal(final_answer)
        citations = extract_citations(final_answer, retrieved_chunks=retrieved_chunks_accumulator)
        total_latency_ms = round((time.monotonic() - start_time) * 1000, 2)
        total_tokens = total_prompt_tokens + total_completion_tokens

        # Persist Agent Trace to Database
        await self._persist_trace(
            trace_id=trace_id,
            org_id=org_id,
            user_id=user_id,
            session_id=session_id,
            query=query,
            final_answer=final_answer,
            refused=refused,
            citations=citations,
            steps=steps,
            retrieved_chunks_count=len(retrieved_chunks_accumulator),
            provider=provider_used,
            model=model_used,
            prompt_tokens=total_prompt_tokens,
            completion_tokens=total_completion_tokens,
            total_tokens=total_tokens,
            latency_ms=total_latency_ms,
            error=execution_error,
        )

        return AgentResponse(
            query=query,
            final_answer=final_answer,
            refused=refused,
            citations=citations,
            trace_id=str(trace_id),
            steps_count=len(steps),
            tokens_total=total_tokens,
            latency_ms=total_latency_ms,
            provider=provider_used,
            model=model_used,
        )

    async def run_stream(
        self,
        org_id: uuid.UUID,
        query: str,
        user_id: uuid.UUID | None = None,
        session_id: str | None = None,
        preferred_provider: str | None = None,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Streams live agent reasoning steps, tool activations, and response tokens."""
        start_time = time.monotonic()
        trace_id = uuid.uuid4()

        messages: list[ChatMessage] = [
            ChatMessage(role="system", content=SYSTEM_PROMPT),
            ChatMessage(role="user", content=query),
        ]

        steps: list[AgentStep] = []
        retrieved_chunks_accumulator: list[dict[str, Any]] = []
        total_prompt_tokens = 0
        total_completion_tokens = 0
        final_answer = ""
        provider_used = "unknown"
        model_used = "unknown"
        execution_error: str | None = None

        yield {
            "event": "start",
            "data": {"trace_id": str(trace_id), "query": query},
        }

        for step_idx in range(1, self.max_steps + 1):
            elapsed = time.monotonic() - start_time
            if elapsed > self.timeout_seconds:
                final_answer = (
                    "I was unable to complete the research within the allowed execution time."
                )
                yield {
                    "event": "timeout",
                    "data": {"message": "Execution time limit reached."},
                }
                break

            step_start = time.monotonic()
            step = AgentStep(step_index=step_idx)
            yield {
                "event": "step_start",
                "data": {"step_index": step_idx},
            }

            try:
                llm_resp = await self.gateway.generate_with_tools(
                    messages=messages,
                    tools=self.tool_definitions,
                    temperature=0.0,
                    preferred_provider=preferred_provider,
                )

                provider_used = llm_resp.provider
                model_used = llm_resp.model
                total_prompt_tokens += llm_resp.usage.prompt_tokens
                total_completion_tokens += llm_resp.usage.completion_tokens

                if llm_resp.tool_calls:
                    messages.append(
                        ChatMessage(
                            role="assistant",
                            content=llm_resp.content,
                            tool_calls=llm_resp.tool_calls,
                        )
                    )

                    for tc in llm_resp.tool_calls:
                        parsed_args = tc.get_parsed_arguments()
                        step.tool_calls.append(
                            {
                                "id": tc.id,
                                "name": tc.function.name,
                                "arguments": tc.function.arguments,
                            }
                        )

                        yield {
                            "event": "tool_start",
                            "data": {
                                "step_index": step_idx,
                                "tool_name": tc.function.name,
                                "arguments": parsed_args,
                            },
                        }

                        tool_out = await self._execute_tool(org_id, tc)
                        step.tool_results.append(
                            {
                                "tool_call_id": tc.id,
                                "tool_name": tc.function.name,
                                "success": tool_out.get("success", False),
                                "output": tool_out,
                            }
                        )

                        if tc.function.name == "search_documents" and isinstance(
                            tool_out.get("data"), list
                        ):
                            retrieved_chunks_accumulator.extend(tool_out["data"])

                        yield {
                            "event": "tool_complete",
                            "data": {
                                "step_index": step_idx,
                                "tool_name": tc.function.name,
                                "success": tool_out.get("success", False),
                            },
                        }

                        raw_payload = _format_tool_output_for_llm(tc.function.name, tool_out)
                        messages.append(
                            ChatMessage(
                                role="tool",
                                tool_call_id=tc.id,
                                name=tc.function.name,
                                content=raw_payload,
                            )
                        )

                    step.latency_ms = round((time.monotonic() - step_start) * 1000, 2)
                    steps.append(step)

                else:
                    final_answer = llm_resp.content or "No response generated."
                    step.latency_ms = round((time.monotonic() - step_start) * 1000, 2)
                    steps.append(step)
                    break

            except Exception as e:
                execution_error = str(e)
                final_answer = f"Agent encountered an internal error during reasoning: {e}"
                yield {"event": "error", "data": {"error": str(e)}}
                break

        if not final_answer:
            final_answer = "Reached maximum reasoning step limit without finding sufficient evidence to conclude."

        yield {"event": "synthesis_start", "data": {}}

        # Stream out words for realistic responsive UI rendering
        words = final_answer.split(" ")
        for i, word in enumerate(words):
            delta = word if i == 0 else " " + word
            yield {"event": "token", "data": {"delta": delta}}

        refused = is_refusal(final_answer)
        citations = extract_citations(final_answer, retrieved_chunks=retrieved_chunks_accumulator)
        total_latency_ms = round((time.monotonic() - start_time) * 1000, 2)
        total_tokens = total_prompt_tokens + total_completion_tokens

        await self._persist_trace(
            trace_id=trace_id,
            org_id=org_id,
            user_id=user_id,
            session_id=session_id,
            query=query,
            final_answer=final_answer,
            refused=refused,
            citations=citations,
            steps=steps,
            retrieved_chunks_count=len(retrieved_chunks_accumulator),
            provider=provider_used,
            model=model_used,
            prompt_tokens=total_prompt_tokens,
            completion_tokens=total_completion_tokens,
            total_tokens=total_tokens,
            latency_ms=total_latency_ms,
            error=execution_error,
        )

        final_response = AgentResponse(
            query=query,
            final_answer=final_answer,
            refused=refused,
            citations=citations,
            trace_id=str(trace_id),
            steps_count=len(steps),
            tokens_total=total_tokens,
            latency_ms=total_latency_ms,
            provider=provider_used,
            model=model_used,
        )

        yield {
            "event": "done",
            "data": final_response.model_dump(),
        }

    async def _execute_tool(self, org_id: uuid.UUID, tool_call: ToolCall) -> dict[str, Any]:
        """Safely dispatches and executes a tool call."""
        tool_name = tool_call.function.name
        tool = self.tools.get(tool_name)
        if not tool:
            return {"success": False, "error": f"Tool '{tool_name}' is not recognized."}

        parsed_args = tool_call.get_parsed_arguments()
        try:
            result = await tool.execute(org_id=org_id, **parsed_args)
            return {
                "success": result.success,
                "data": result.data,
                "error": result.error,
            }
        except Exception as e:
            logger.error("Tool execution failed", tool=tool_name, error=str(e), org_id=str(org_id))
            return {"success": False, "error": str(e)}

    async def _persist_trace(
        self,
        trace_id: uuid.UUID,
        org_id: uuid.UUID,
        user_id: uuid.UUID | None,
        session_id: str | None,
        query: str,
        final_answer: str,
        refused: bool,
        citations: list[Citation],
        steps: list[AgentStep],
        retrieved_chunks_count: int,
        provider: str,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        total_tokens: int,
        latency_ms: float,
        error: str | None,
    ) -> None:
        """Persists the trace in the PostgreSQL agent_traces table."""
        try:
            async with self.session_factory() as session:
                serialized_citations = [c.model_dump() for c in citations]
                serialized_steps = [s.model_dump() for s in steps]
                tool_calls_count = sum(len(s.tool_calls) for s in steps)

                trace = AgentTrace(
                    id=trace_id,
                    org_id=org_id,
                    user_id=user_id,
                    session_id=session_id,
                    query=query,
                    final_answer=final_answer,
                    refused=refused,
                    citations=serialized_citations,
                    steps=serialized_steps,
                    tool_calls_count=tool_calls_count,
                    retrieved_chunks_count=retrieved_chunks_count,
                    provider=provider,
                    model=model,
                    tokens_prompt=prompt_tokens,
                    tokens_completion=completion_tokens,
                    tokens_total=total_tokens,
                    latency_ms=latency_ms,
                    error=error,
                )
                session.add(trace)
                await session.commit()
                logger.info("Agent trace persisted", trace_id=str(trace_id), org_id=str(org_id))
        except Exception as e:
            logger.error("Failed to persist agent trace", error=str(e), trace_id=str(trace_id))

    async def _enqueue_for_review(
        self,
        org_id: uuid.UUID,
        trace_id: uuid.UUID,
        query: str,
        answer: str,
        retrieved_chunks: list[dict[str, Any]],
        trigger_reason: str,
        confidence_score: float | None = None,
    ) -> None:
        """Enqueues an item into the human review queue."""
        try:
            from apps.api.src.models.review_queue import ReviewQueueItem

            async with self.session_factory() as session:
                item = ReviewQueueItem(
                    id=uuid.uuid4(),
                    org_id=org_id,
                    trace_id=trace_id,
                    query=query,
                    answer=answer,
                    retrieved_chunks=retrieved_chunks,
                    trigger_reason=trigger_reason,
                    confidence_score=confidence_score,
                    status="pending",
                )
                session.add(item)
                await session.commit()
                logger.info(
                    "Query enqueued for human review",
                    org_id=str(org_id),
                    trigger_reason=trigger_reason,
                    trace_id=str(trace_id),
                )
        except Exception as e:
            logger.error(
                "Failed to enqueue item for human review", error=str(e), trace_id=str(trace_id)
            )
