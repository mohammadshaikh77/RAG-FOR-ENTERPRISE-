#!/usr/bin/env python3
"""Convenience executable for launching the Cite MCP Server via stdio or SSE."""

import sys
from pathlib import Path

# Ensure repo packages are available in Python path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))
sys.path.insert(0, str(ROOT_DIR / "packages" / "mcp" / "src"))
sys.path.insert(0, str(ROOT_DIR / "packages" / "agent" / "src"))
sys.path.insert(0, str(ROOT_DIR / "packages" / "rag" / "src"))
sys.path.insert(0, str(ROOT_DIR / "packages" / "llm" / "src"))

from cite_mcp.__main__ import main  # noqa: E402

if __name__ == "__main__":
    main()
