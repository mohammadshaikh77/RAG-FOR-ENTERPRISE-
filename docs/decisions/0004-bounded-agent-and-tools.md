# ADR 0004: Bounded Tool-Calling Agent Loop, Grounded Citations, and Safe Execution

## Status
Accepted

## Context
Phase 4 requires an intelligent agent capable of reasoning over complex clinical documentation, executing multi-step tool calls, calculating clinical dosages, and producing strictly grounded answers with citations.
Unconstrained agent loops risk infinite recursion loops, high latency, token quota exhaustion, arbitrary code execution, and ungrounded hallucinations.

## Decisions

### 1. Hard Bounded Loop (Step, Time, and Token Budgets)
- **Choice**: The agent execution loop is strictly bounded: `max_steps = 5` (configurable up to 10), per-run timeout (60 seconds), and automatic token tallying.
- **Why**: Prevents runaway tool loops or model repetition from exhausting free-tier rate limits or blocking the API worker. If the agent reaches `max_steps` without synthesizing, it halts and reports refusal or partial evidence rather than looping infinitely.

### 2. Zero `eval()` / Safe AST Calculator
- **Choice**: Calculator tool strictly parses Python's Abstract Syntax Tree (`ast.parse(expr, mode="eval")`) and evaluates only mathematical binary and unary operators (`+`, `-`, `*`, `/`, `//`, `%`, `**`).
- **Why**: Using Python's native `eval()` or `exec()` exposes the platform to arbitrary remote code execution (RCE) via prompt injection. AST validation provides complete computational safety with zero external sandboxing overhead.

### 3. Read-Only Parameterized Structured Querying
- **Choice**: The `query_structured_data` tool exposes 5 whitelisted parameterized query templates (`list_classes`, `filter_by_class`, `filter_by_boxed_warning`, `get_drug_info`, `find_drugs`) executed via SQLAlchemy ORM.
- **Why**: Models must never execute raw SQL against the database. Parameterized whitelisted templates prevent SQL injection and guarantee that every query is strictly tenant-scoped (`WHERE org_id = :org_id`).

### 4. Mandatory Citation Spans & Explicit Refusal Path
- **Choice**: The agent is instructed to format citations as `[Document: <Title> | Section: <Section> | "<exact quoted span>"]`. Citations are programmatically verified against retrieved chunk contents. When evidence is insufficient, the agent is constrained to produce an explicit refusal statement (`"I cannot answer this question based on the provided documents..."`) rather than hallucinating answers.

### 5. Persistent Execution Audit Traces
- **Choice**: Every agent run writes a full JSON trace to the `agent_traces` table: step history, tool calls, tool results, retrieved chunks, token consumption, latency, and model/provider identity.
- **Why**: Full auditability is mandatory in regulated clinical and enterprise environments. The UI and admin dashboard can replay exact reasoning traces for quality inspection and evaluation.

## Consequences
- Guaranteed upper bound on latency and token consumption per query.
- Full trace persistence for downstream LLM-as-a-judge evaluation and human audit.

