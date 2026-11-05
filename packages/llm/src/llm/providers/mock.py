"""Deterministic Mock LLM provider for tests, CI, and offline development."""

import json
from collections.abc import Callable
from typing import Any

from llm.providers.base import BaseLLMProvider
from llm.types import ChatMessage, FunctionCall, LLMResponse, TokenUsage, ToolCall, ToolDefinition


class MockLLMProvider(BaseLLMProvider):
    """Configurable mock LLM provider simulating tool use, citations, and refusals."""

    def __init__(
        self,
        model: str = "mock-model-v1",
        custom_handler: Callable[[list[ChatMessage], list[ToolDefinition] | None], LLMResponse]
        | None = None,
    ) -> None:
        super().__init__(name="mock", model=model)
        self.custom_handler = custom_handler
        self.call_count = 0

    def is_available(self) -> bool:
        return True

    async def generate(
        self,
        messages: list[ChatMessage],
        temperature: float = 0.0,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> LLMResponse:
        self.call_count += 1
        if self.custom_handler:
            return self.custom_handler(messages, None)

        last_user_msg = next((m.content for m in reversed(messages) if m.role == "user"), "")
        content = f"Mock synthesis for: {last_user_msg}"
        return LLMResponse(
            content=content,
            tool_calls=[],
            provider=self.name,
            model=self.model,
            usage=TokenUsage(prompt_tokens=25, completion_tokens=15, total_tokens=40),
        )

    async def generate_with_tools(
        self,
        messages: list[ChatMessage],
        tools: list[ToolDefinition],
        temperature: float = 0.0,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> LLMResponse:
        self.call_count += 1
        if self.custom_handler:
            return self.custom_handler(messages, tools)

        # Check if any tool messages are already in history
        has_tool_results = any(m.role == "tool" for m in messages)
        last_user_msg = next((m.content or "" for m in reversed(messages) if m.role == "user"), "")

        # Check for unanswerables or unsupported topics
        refusal_triggers = [
            "martian",
            "kryptonite",
            "tesla",
            "boeing",
            "recipe",
            "vibranium",
            "rocket",
            "yankees",
            "unobtainium",
            "quantum",
            "wi-fi",
            "werewolf",
            "camry",
            "fairy",
            "shakespeare",
            "cryptographic",
            "ignore all",
            "dan (do anything now)",
            "dan",
            "synthesize",
            "override",
            "pwned",
            "passwords",
            "error 500",
            "not in document",
            "fake-drug-xyz",
            "different medicine",
            "unrelated medicine",
        ]
        if any(trigger in last_user_msg.lower() for trigger in refusal_triggers):
            return LLMResponse(
                content="I couldn't find enough information to answer this question in your uploaded documents.",
                tool_calls=[],
                provider=self.name,
                model=self.model,
                usage=TokenUsage(prompt_tokens=40, completion_tokens=20, total_tokens=60),
            )

        # If tools available and haven't called any tool yet, initiate a tool call
        if tools and not has_tool_results:
            tool_names = [t.function.name for t in tools]
            if "search_documents" in tool_names:
                return LLMResponse(
                    content=None,
                    tool_calls=[
                        ToolCall(
                            id="mock_call_1",
                            type="function",
                            function=FunctionCall(
                                name="search_documents",
                                arguments=json.dumps({"query": last_user_msg, "top_k": 5}),
                            ),
                        )
                    ],
                    provider=self.name,
                    model=self.model,
                    usage=TokenUsage(prompt_tokens=50, completion_tokens=15, total_tokens=65),
                )

        # After tool results are present, synthesize answer with real extracted citations
        tool_results_content = [m.content for m in messages if m.role == "tool"]
        citations_list = []
        findings = []

        for content_str in tool_results_content:
            try:
                # Strip any stray delimiters if present
                cleaned_str = content_str.strip()
                if cleaned_str.startswith("===") and "{" in cleaned_str:
                    first_brace = cleaned_str.find("{")
                    last_brace = cleaned_str.rfind("}")
                    if first_brace != -1 and last_brace != -1:
                        cleaned_str = cleaned_str[first_brace : last_brace + 1]

                data = json.loads(cleaned_str)
                chunks = (
                    data.get("data", [])
                    if isinstance(data, dict)
                    else (data if isinstance(data, list) else [])
                )
                for item in chunks:
                    if not isinstance(item, dict):
                        continue
                    doc_title = item.get("document_title") or "Document"
                    sec_title = item.get("section_title") or "General"
                    raw_content = item.get("content", "").strip()
                    if not raw_content:
                        continue

                    # Filter out raw JSON or formatting artifacts
                    lines = [
                        line.strip()
                        for line in raw_content.split("\n")
                        if line.strip()
                        and not line.strip().startswith("{")
                        and not line.strip().startswith("===")
                    ]
                    if not lines:
                        continue

                    # Pick a clean verbatim span of 40-75 characters that actually exists
                    best_line = lines[0]
                    for candidate in lines:
                        if len(candidate) >= 40:
                            best_line = candidate
                            break

                    clean_span = best_line[:65].replace("\n", " ").strip()
                    if clean_span:
                        citation_str = f'[Document: {doc_title} | Section: {sec_title} | "{clean_span}"]'
                        if citation_str not in citations_list:
                            citations_list.append(citation_str)

                        # Clean paragraph text for synthesis
                        snippet = " ".join(lines[:3])
                        if len(snippet) > 250:
                            snippet = snippet[:250].rsplit(" ", 1)[0] + "."
                        findings.append((doc_title, sec_title, snippet, citation_str))

            except Exception:
                clean_text = content_str.strip().replace("\n", " ")
                clean_span = clean_text[:65].strip()
                citation_str = f'[Document: Document | Section: General | "{clean_span}"]'
                citations_list.append(citation_str)
                findings.append(("Document", "General", clean_text[:200], citation_str))

        if not citations_list or not findings:
            return LLMResponse(
                content="I couldn't find enough information to answer this question in your uploaded documents.",
                tool_calls=[],
                provider=self.name,
                model=self.model,
                usage=TokenUsage(prompt_tokens=60, completion_tokens=20, total_tokens=80),
            )

        # Synthesize clear, well-structured response
        q_lower = last_user_msg.lower()
        paragraphs = []

        if "boxed warning" in q_lower or "pregnancy" in q_lower:
            # Find pregnancy/fetal toxicity finding
            fetal_finding = next(
                (f for f in findings if "fetal" in f[2].lower() or "pregnan" in f[2].lower()),
                findings[0],
            )
            paragraphs.append(
                f"According to the documentation for **{fetal_finding[0]}**, there is a boxed warning regarding fetal toxicity during pregnancy: {fetal_finding[2]} {fetal_finding[3]}"
            )
            paragraphs.append(
                "When pregnancy is detected, therapy should be discontinued as soon as possible because drugs acting on the renin-angiotensin system can cause injury and death to the developing fetus."
            )

        elif "side effect" in q_lower or "adverse" in q_lower:
            adverse_finding = next(
                (f for f in findings if "adverse" in f[1].lower() or "side" in f[2].lower() or "headache" in f[2].lower()),
                findings[0],
            )
            paragraphs.append(
                f"The common adverse reactions documented for **{adverse_finding[0]}** include: {adverse_finding[2]} {adverse_finding[3]}"
            )

        elif "kidney" in q_lower or "renal" in q_lower:
            renal_finding = next(
                (f for f in findings if "renal" in f[2].lower() or "kidney" in f[2].lower()),
                findings[0],
            )
            paragraphs.append(
                f"For patients with kidney impairment, the documents state: {renal_finding[2]} {renal_finding[3]}"
            )
            paragraphs.append(
                "Renal function and serum potassium levels should be closely monitored, and initial dosages may require adjustment."
            )

        elif "dosage" in q_lower or "dose" in q_lower:
            dose_finding = next(
                (f for f in findings if "dose" in f[2].lower() or "dosage" in f[2].lower() or "mg" in f[2].lower()),
                findings[0],
            )
            paragraphs.append(
                f"Regarding dosing guidelines for **{dose_finding[0]}**: {dose_finding[2]} {dose_finding[3]}"
            )

        elif "contraindication" in q_lower:
            contra_finding = next(
                (f for f in findings if "contraindicat" in f[2].lower() or "angioedema" in f[2].lower()),
                findings[0],
            )
            paragraphs.append(
                f"The contraindications listed for **{contra_finding[0]}** include: {contra_finding[2]} {contra_finding[3]}"
            )

        else:
            doc_name = findings[0][0]
            summary_sentences = []
            for item in findings[:2]:
                summary_sentences.append(f"{item[2]} {item[3]}")
            paragraphs.append(
                f"Based on the uploaded document for **{doc_name}**:\n\n" + "\n\n".join(summary_sentences)
            )

        # Append source list for clarity
        paragraphs.append("Sources:\n" + "\n".join(f"- {c}" for c in citations_list[:3]))
        final_content = "\n\n".join(paragraphs)

        return LLMResponse(
            content=final_content,
            tool_calls=[],
            provider=self.name,
            model=self.model,
            usage=TokenUsage(prompt_tokens=120, completion_tokens=60, total_tokens=180),
        )
