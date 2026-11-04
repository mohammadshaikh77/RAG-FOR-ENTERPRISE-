"""CLI entrypoint for Cite MCP server."""

import argparse
import os
import sys
import uuid

import structlog

from cite_mcp.server import create_mcp_server

logger = structlog.get_logger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Cite Model Context Protocol (MCP) Server for external AI agent integration."
    )
    parser.add_argument(
        "--transport",
        choices=["stdio", "sse", "streamable-http"],
        default=os.getenv("CITE_MCP_TRANSPORT", "stdio"),
        help="MCP transport protocol (default: stdio)",
    )
    parser.add_argument(
        "--tenant-id",
        type=str,
        default=os.getenv("CITE_TENANT_ID"),
        help="Default tenant organization UUID for all tool queries (optional)",
    )
    parser.add_argument(
        "--host",
        type=str,
        default=os.getenv("CITE_MCP_HOST", "0.0.0.0"),
        help="Host to bind for SSE / HTTP transport",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("CITE_MCP_PORT", "8001")),
        help="Port to bind for SSE / HTTP transport",
    )

    args = parser.parse_args()

    default_tenant = None
    if args.tenant_id:
        try:
            default_tenant = uuid.UUID(args.tenant_id.strip())
        except ValueError:
            sys.stderr.write(f"Invalid --tenant-id UUID: {args.tenant_id}\n")
            sys.exit(1)

    server = create_mcp_server(default_tenant_id=default_tenant)

    if args.transport == "stdio":
        server.run(transport="stdio")
    else:
        server.settings.host = args.host
        server.settings.port = args.port
        server.run(transport=args.transport)


if __name__ == "__main__":
    main()
