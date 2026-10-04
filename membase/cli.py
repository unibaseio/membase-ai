"""``membase``: the Membase command line, hosted or local.

    membase --local add "We picked Postgres for the ledger"
    membase --local search "what did we pick for the ledger?"
    membase --local import ~/Downloads/claude-export.json
    membase --local serve                  # the /v1 API on http://127.0.0.1:8787
    membase --local mcp                    # MCP server over stdio

Hosted with ``MEMBASE_API_KEY``; local with ``--local [DIR]`` or ``MEMBASE_LOCAL`` (default store
``~/.membase``, needs ``membase-ai[local]``). Answers print as JSON.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from ._version import __version__
from .client import Membase
from .errors import MembaseError


def _client(args: argparse.Namespace) -> Membase:
    if args.local is not None:
        return Membase(local=True if args.local == "" else args.local)
    return Membase(api_key=args.api_key, base_url=args.base_url)


def _print(obj: Any) -> None:
    print(json.dumps(obj, ensure_ascii=False, indent=2, default=str))


def _cmd_import(args: argparse.Namespace, m: Membase) -> Any:
    try:
        from membase_core.sources import load_sessions
    except ImportError:
        raise SystemExit("membase import reads chat exports with the local engine: pip install 'membase-ai[local]'")
    sessions: list[dict] = []
    for f in args.files:
        sessions += load_sessions(f)
    if not sessions:
        raise SystemExit("no sessions found")
    transport = m._http._transport  # noqa: SLF001 - the local transport, when local
    backend = getattr(transport, "backend", None)
    if backend is not None:
        return backend.import_sessions(sessions, args.container)
    # Hosted: each session becomes a document the container learns.
    out = []
    for s in sessions:
        text = "\n".join(f"{t['role']}: {t['content']}" for t in s["turns"])
        out.append(m.add(text, container=args.container, title=s["session_id"],
                         custom_id=f"session:{s['session_id']}"))
    return {"sessions": len(out), "documents": out}


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="membase", description="Membase — long-term memory for AI.")
    p.add_argument("--version", action="version", version=__version__)
    p.add_argument("--local", nargs="?", const="", default=None, metavar="DIR",
                   help="use local memory (default store ~/.membase) instead of the hosted API")
    p.add_argument("--api-key", default=None, help="hosted API key (default MEMBASE_API_KEY)")
    p.add_argument("--base-url", default=None, help="hosted API base URL (default MEMBASE_BASE_URL)")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("containers", help="list the containers in reach")

    s = sub.add_parser("search", help="search memory")
    s.add_argument("q")
    s.add_argument("--container")
    s.add_argument("--limit", type=int)

    a = sub.add_parser("add", help="remember one fact or a short exchange")
    a.add_argument("content")
    a.add_argument("--container")
    a.add_argument("--static", action="store_true", help="a standing fact about the user (profile)")
    a.add_argument("--title", default="")

    d = sub.add_parser("documents", help="documents: add / list / get / delete")
    dsub = d.add_subparsers(dest="doc_cmd", required=True)
    da = dsub.add_parser("add", help="give a container raw material: a file, --url or --text")
    da.add_argument("path", nargs="?")
    da.add_argument("--url")
    da.add_argument("--text")
    da.add_argument("--container", default=None)
    da.add_argument("--title", default="")
    da.add_argument("--custom-id", default="")
    dl = dsub.add_parser("list")
    dl.add_argument("--container")
    dg = dsub.add_parser("get")
    dg.add_argument("document_id")
    dd = dsub.add_parser("delete")
    dd.add_argument("document_id")
    dd.add_argument("--confirm", action="store_true")

    f = sub.add_parser("forget", help="forget one memory by id")
    f.add_argument("memory_id")
    f.add_argument("--container")
    f.add_argument("--confirm", action="store_true")

    pr = sub.add_parser("profile", help="who the user is")
    pr.add_argument("q", nargs="?")

    k = sub.add_parser("ask", help="an answer composed from memory")
    k.add_argument("message")

    i = sub.add_parser("import", help="import chat exports (Claude, ChatGPT, markdown, JSON)")
    i.add_argument("files", nargs="+")
    i.add_argument("--container")

    sv = sub.add_parser("serve", help="serve local memory over HTTP on the /v1 routes")
    sv.add_argument("--host", default="127.0.0.1")
    sv.add_argument("--port", type=int, default=8787)

    mc = sub.add_parser("mcp", help="run the MCP server")
    mc.add_argument("--transport", choices=("stdio", "sse", "streamable-http"), default="stdio")
    mc.add_argument("--host", default="127.0.0.1")
    mc.add_argument("--port", type=int, default=8765)
    return p


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.cmd == "serve":
        from .local.server import serve

        serve(args.host, args.port, root=args.local or None)
        return 0
    try:
        m = _client(args)
        if args.cmd == "mcp":
            from .mcp import run

            run(m, transport=args.transport, host=args.host, port=args.port)
            return 0
        if args.cmd == "containers":
            out = m.containers.list()
        elif args.cmd == "search":
            out = m.search(args.q, container=args.container, limit=args.limit)
        elif args.cmd == "add":
            out = m.memories.add(args.content, container=args.container, static=args.static, title=args.title)
        elif args.cmd == "documents":
            if args.doc_cmd == "add":
                if args.path:
                    content = Path(args.path).read_text()
                    title = args.title or Path(args.path).stem
                else:
                    content, title = args.text, args.title
                if (content is None) == (args.url is None):
                    raise SystemExit("documents add needs exactly one of PATH, --text or --url")
                out = m.add(content, container=args.container or "default", url=args.url,
                            title=title, custom_id=args.custom_id)
            elif args.doc_cmd == "list":
                out = m.documents.list(container=args.container)
            elif args.doc_cmd == "get":
                out = m.documents.get(args.document_id)
            else:
                out = m.documents.delete(args.document_id, confirm=args.confirm)
        elif args.cmd == "forget":
            out = m.memories.forget(args.memory_id, container=args.container, confirm=args.confirm)
        elif args.cmd == "profile":
            out = m.profile(args.q)
        elif args.cmd == "ask":
            out = m.ask(args.message)
        else:
            out = _cmd_import(args, m)
        _print(out)
        m.close()
        return 0
    except MembaseError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
