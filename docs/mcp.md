# Model Context Protocol (MCP) Server — "Cite"

This guide details how to configure, connect, and use Cite's Model Context Protocol (MCP) server with external AI agents, including **Claude Desktop**, **Cursor**, **Antigravity**, and programmatic Python clients.

---

## 1. Overview & Available Tools

Cite implements the official Anthropic Model Context Protocol (`mcp>=1.0.0`), exposing 5 grounded document intelligence tools:

| Tool Name | Parameters | Purpose |
|---|---|---|
| `cite_search` | `query: str`, `top_k: int = 5`, `section_filter: str \| None`, `tenant_id: str \| None` | Hybrid vector semantic + full-text search returning scored chunks with grounded citation markers. |
| `cite_get_section` | `document_id_or_title: str`, `section_title: str`, `tenant_id: str \| None` | Full, unabridged clinical section text (e.g. *Boxed Warning*, *Contraindications*). Accepts UUID or drug name. |
| `cite_compare_drugs` | `drug_a: str`, `drug_b: str`, `aspect: str = "indications"`, `tenant_id: str \| None` | Aligned side-by-side comparative analysis of two drug labels on a specific clinical aspect. |
| `cite_query_structured` | `query_type: str = "list_drugs"`, `drug_class: str \| None`, `boxed_warning_only: bool`, `tenant_id: str \| None` | Parameterized read-only queries over extracted tabular clinical metadata (classes, routes, warnings). |
| `cite_audit_trace` | `trace_id: str`, `tenant_id: str \| None` | Inspects full execution audit telemetry (steps, latency, token consumption) for a previous agent query. |

---

## 2. Multi-Tenant Scoping & Authentication

All queries through the MCP server are strictly tenant-isolated. An external agent can provide tenant credentials in any of the following ways:

1. **Environment Variable (`CITE_TENANT_ID`):**
   ```bash
   export CITE_TENANT_ID="00000000-0000-0000-0000-000000000001"  # Demo Pharma Tenant
   ```
2. **Bearer Token / JWT (`CITE_AUTH_TOKEN`):**
   ```bash
   export CITE_AUTH_TOKEN="eyJhbGciOiJIUzI1NiIsIn..."
   ```
   *The server automatically decodes the `org_id` claim from the JWT.*
3. **Explicit Parameter (`tenant_id`):**
   Pass `tenant_id="00000000-0000-0000-0000-000000000001"` directly in individual tool calls.

---

## 3. Integration Guides

### Option A: Claude Desktop Integration (`stdio`)

Add the following block to your Claude Desktop configuration file:
- **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "cite": {
      "command": "/Users/saimashaikh/Desktop/rag for enterprise/.venv/bin/python",
      "args": [
        "/Users/saimashaikh/Desktop/rag for enterprise/scripts/run_mcp_server.py",
        "--transport",
        "stdio"
      ],
      "env": {
        "CITE_TENANT_ID": "00000000-0000-0000-0000-000000000001",
        "DATABASE_URL": "postgresql+asyncpg://cite_user:cite_password@localhost:5434/cite_db"
      }
    }
  }
}
```

### Option B: Cursor Integration (`stdio`)

In Cursor, configure MCP in project settings or `.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "cite-document-intelligence": {
      "command": ".venv/bin/python",
      "args": ["scripts/run_mcp_server.py", "--transport", "stdio"],
      "env": {
        "CITE_TENANT_ID": "00000000-0000-0000-0000-000000000001"
      }
    }
  }
}
```

### Option C: Remote HTTP / Server-Sent Events (`SSE`)

When the Cite API server is running (`make up` or port 8000), the MCP server is mounted directly at:
```
http://localhost:8000/mcp/sse
```
External agents supporting remote SSE transports can point directly to this URL.

Alternatively, launch a dedicated standalone SSE server on port 8001:
```bash
python scripts/run_mcp_server.py --transport sse --port 8001
```

---

## 4. Programmatic Python Client Usage

You can interact with the MCP server directly in Python using `CiteMCPClient`:

```python
import asyncio
from cite_mcp.server import create_mcp_server
from cite_mcp.client import CiteMCPClient

async def main():
    server = create_mcp_server()
    client = CiteMCPClient(server=server)

    # Search documents with citations
    results = await client.search(
        query="What is the boxed warning for naproxen?",
        top_k=3,
        tenant_id="00000000-0000-0000-0000-000000000001"
    )
    print(results)

    # Compare two drugs side-by-side
    comparison = await client.compare_drugs(
        drug_a="Naproxen",
        drug_b="Celecoxib",
        aspect="indications",
        tenant_id="00000000-0000-0000-0000-000000000001"
    )
    print(comparison)

if __name__ == "__main__":
    asyncio.run(main())
```

---

## 5. Automated Verification

Run the dedicated MCP test suite:
```bash
PYTHONPATH=".:packages/agent/src:packages/llm/src:packages/rag/src:packages/mcp/src" .venv/bin/pytest tests/test_mcp.py -v
```

All 8 tests verify:
1. Tool registration & JSON Schema conformance.
2. Hybrid search with formatted grounded citations.
3. Unabridged section retrieval with human-name resolution.
4. Side-by-side comparative drug analysis.
5. Structured JSON metadata queries.
6. Multi-tenant isolation (zero leakage between Org A and Org B).
7. Unauthenticated invocation refusal.
8. Subprocess stdio connection with `ClientSession`.
