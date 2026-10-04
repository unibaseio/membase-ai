"""``membase-mcp``: run the Membase MCP server (stdio by default)."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from membase_mcp.server import default_db, run


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="membase-mcp",
        description="MCP server for the Membase memory engine.",
    )
    parser.add_argument("--db", type=Path, default=default_db(),
                        help="SQLite path for the memory store (default: MEMBASE_DB or ~/.membase/memory.db).")
    parser.add_argument("--transport", choices=("stdio", "sse", "streamable-http"), default="stdio")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args(argv)

    args.db.parent.mkdir(parents=True, exist_ok=True)
    run(
        args.db,
        transport=args.transport,
        host=args.host,
        port=args.port,
        # The automem_* tools sign and encrypt with this wallet key; read from the environment
        # only, so it never shows up in a process listing.
        private_key=os.environ.get("MEMBASE_PRIVATE_KEY") or None,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
