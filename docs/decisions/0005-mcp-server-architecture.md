# ADR 0005: Model Context Protocol (MCP) Server Architecture & Multi-Tenant Scoping

## Status
Accepted

## Context
Phase 5 requires exposing the Cite platform's document intelligence capabilities (`cite_search`, `cite_get_section`, `cite_compare_drugs`, `cite_query_structured`, `cite_audit_trace`) to external AI coding assistants and agents (Claude Desktop, Cursor, Antigravity, custom agent orchestrators) via Anthropic's open Model Context Protocol (MCP).

Key architectural challenges:
1. **Multi-Tenancy Enforcement**: In a multi-tenant enterprise system, an external MCP client must never leak documents or citations across organization boundaries.
2. **Dual Transport Support**: Desktop IDEs and agents (Claude Desktop, Cursor) prefer standard I/O (`stdio`), while web/remote agent frameworks require HTTP Server-Sent Events (`SSE`).
3. **SDK Compatibility**: Official `mcp` Python SDK (v2.x) renames `FastMCP` to `MCPServer` and shifts schema attributes to `input_schema`.

## Decisions

### 1. Official Python `mcp` SDK with `MCPServer`
- **Choice**: Implemented server using the official Anthropic `mcp` package (`packages/mcp/src/cite_mcp/server.py`), leveraging `mcp.server.mcpserver.MCPServer`.
- **Why**: Native support for tool decorators (`@mcp_server.tool()`), standard JSON-RPC 2.0 message validation, and built-in transports for both `stdio` and `sse`.

### 2. Mandatory Query-Level Tenant Scoping
- **Choice**: Every MCP tool call resolves and binds the tenant organization UUID through `resolve_tenant_id`:
  1. Priority 1: Explicit `tenant_id` argument in tool call
  2. Priority 2: Configured default tenant on the server instance
  3. Priority 3: `CITE_TENANT_ID` environment variable
  4. Priority 4: `CITE_AUTH_TOKEN` / `CITE_API_KEY` JWT bearer token with decoded `org_id` claim
- **Why**: Prevents cross-tenant data leakage. If an external client attempts an unauthenticated query or requests data from an unowned document, the server returns an explicit authentication error or empty result without exposing other organizations' data.

### 3. Dual Transport Architecture: Stdio CLI & FastAPI Mounted SSE
- **Choice**:
  - **Stdio Transport**: Executable entrypoint `scripts/run_mcp_server.py` (or `python -m cite_mcp`) for local IDE integration (Claude Desktop, Cursor).
  - **SSE Transport**: Mounted directly onto the FastAPI application at `/mcp` (`app.mount("/mcp", mcp_server.sse_app())`) for remote HTTP/SSE agent connections on port 8000.
- **Why**: External agents can integrate either as a child subprocess without needing a running web server, or over network HTTP without managing separate process lifecycles.

### 4. Human-Friendly Parameter Normalization
- **Choice**: Tools accept both raw UUIDs and human-readable drug names (e.g. `document_id_or_title="Naproxen"`). The server automatically resolves human names against the tenant's ingested documents before dispatching to underlying retrieval tools.
- **Why**: External LLM agents frequently emit drug names rather than 36-character UUIDs; auto-resolution prevents unnecessary tool round-trips.

## Consequences
- Clean, standard integration with Claude Desktop, Cursor, and any MCP-compliant agent.
- Verified zero cross-tenant leakage across direct search, section retrieval, and structured queries.
- Zero extra hosting cost or separate daemon required (runs in-process or via FastAPI mount).
