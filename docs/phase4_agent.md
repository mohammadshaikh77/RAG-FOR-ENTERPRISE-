# Phase 4: Bounded Tool-Calling Agent, Grounded Citations, and Traces

## 1. Overview
Phase 4 equips Cite with an intelligent, multi-step clinical reasoning agent. The agent uses tools to retrieve clinical evidence, inspect structured drug data, compare drugs side-by-side, evaluate dosages, and produce grounded, verified citations.

## 2. Implemented Architecture
- **LLM Gateway Layer (`packages/llm`)**:
  - Normalized OpenAI-compatible protocol (`generate`, `generate_with_tools`).
  - Providers: `GroqProvider` (`llama-3.1-8b-instant`), `GeminiProvider` (`gemini-1.5-flash`), `OllamaProvider` (`llama3.1:8b`), and deterministic `MockLLMProvider`.
  - Rate limiting: token-bucket rate limiter (`TokenBucketLimiter`) with retry and exponential backoff on HTTP 429.
  - Caching: `LLMCache` with SHA-256 deterministic key generation.
  - Prioritized failover: automatic fallback across configured providers.
- **Relational Tables**:
  - `drug_metadata`: Extracted clinical records (`drug_name`, `brand_name`, `generic_name`, `drug_class`, `has_boxed_warning`, `route`, `product_ndc`, `manufacturer_name`, `boxed_warning_summary`).
  - `agent_traces`: Full audit logs (`query`, `final_answer`, `refused`, `citations`, `steps`, `tool_calls_count`, `retrieved_chunks_count`, `provider`, `model`, `tokens_prompt`, `tokens_completion`, `tokens_total`, `latency_ms`, `error`).
- **5 Whitelisted Tools (`packages/agent/src/agent/tools/`)**:
  1. `search_documents(query, section_filter, top_k)`: Scoped hybrid retrieval over clinical chunks.
  2. `get_section(document_id, section_name)`: Full-text extraction of specific clinical sections.
  3. `compare_documents(doc_a_id, doc_b_id, topic)`: Aligned side-by-side section comparison.
  4. `query_structured_data(query_type, parameters)`: Strictly read-only parameterized querying over `drug_metadata` (no arbitrary SQL).
  5. `calculator(expression)`: Safe AST arithmetic evaluation (+, -, *, /, //, %, **). Zero `eval()`.
- **Citations & Refusal Engine (`agent/citations.py`)**:
  - Format: `[Document: <Doc Title> | Section: <Section Name> | "<quoted span>"]`.
  - Span verification against retrieved chunks.
  - Explicit refusal detection on unanswerable or unsupported questions.
- **Agent API Endpoints (`apps/api/src/routers/agent.py`)**:
  - `POST /agent/query`: Runs bounded reasoning loop, returns answer, verified citations, tokens, and trace ID.
  - `GET /agent/traces`: Lists past execution traces for authenticated organization.
  - `GET /agent/traces/{trace_id}`: Step-by-step breakdown of tool calls, inputs, outputs, and latency.

## 3. Acceptance Verification
All acceptance checks pass:
- **Bounded execution**: Loops terminate strictly at `max_steps` without infinite recursion.
- **Refusal path**: Unanswerable and out-of-domain queries trigger refusal rather than hallucination.
- **Tenant isolation**: Cross-tenant trace queries return HTTP 404; queries are strictly isolated to tenant documents.
- **Safe execution**: Calculator blocks malicious arbitrary code injection; structured query blocks SQL injection.
- **30/30 automated tests pass** across unit, integration, and API suites.
