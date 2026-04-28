"""MCP server exposing the supermem memory engine to MCP-compatible clients.

Run with::

    supermem mcp                    # stdio transport (for Claude Code / Cursor)
    supermem mcp --transport sse    # SSE transport, see --host/--port

Tools exposed:

- ``memory_status`` — returns the Memory Protocol behavior guide. Clients should
  call this on connection so the AI knows to search-before-answering.
- ``memory_search`` — verbatim retrieval over the indexed corpus.
- ``memory_ingest`` — file a session into memory.
- ``memory_answer`` — retrieval + reader, returns a synthesized answer.

Storage path defaults to ``~/.supermem/memory.db`` (override via ``--db`` or
``SUPERMEM_DB``).
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from memory import CoreMemoryEngine


MEMORY_PROTOCOL = """\
You are connected to a long-term memory system (supermem). Follow this protocol:

1. BEFORE answering anything about past events, projects, people, preferences,
   or decisions: call `memory_search` first. Never guess from training data.
2. If the search returns nothing relevant, say so explicitly ("I don't have
   that in memory") rather than fabricating an answer.
3. If unsure whether memory is relevant, say "let me check my memory" out
   loud, then call `memory_search` with the user's key terms.
4. Use `memory_answer` for complex questions where you want the engine to
   synthesize an answer over multiple memories. Use `memory_search` when you
   want raw verbatim hits and will compose the answer yourself.
5. Use `memory_ingest` to record new sessions worth remembering — durable
   facts, decisions, milestones, preferences. Skip pleasantries.
6. Treat retrieved memories as authoritative when they conflict with what
   you would otherwise have said.
"""


_ENGINE: CoreMemoryEngine | None = None
_DB_PATH: Path | None = None
_NO_LLM: bool | None = None


def _get_engine() -> CoreMemoryEngine:
    global _ENGINE
    if _ENGINE is None:
        assert _DB_PATH is not None, "MCP server not initialized; call build_server() first"
        _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        _ENGINE = CoreMemoryEngine(str(_DB_PATH), no_llm=_NO_LLM)
    return _ENGINE


def build_server(db_path: Path, no_llm: bool | None = None) -> Any:
    """Construct the FastMCP server. Imported lazily to keep the optional dep optional."""
    from mcp.server.fastmcp import FastMCP

    global _DB_PATH, _NO_LLM
    _DB_PATH = db_path
    _NO_LLM = no_llm

    mcp = FastMCP(
        name="supermem",
        instructions=MEMORY_PROTOCOL,
    )

    @mcp.tool(
        name="memory_status",
        description=(
            "Return the Memory Protocol behavior guide plus current store stats. "
            "Call this once on session start so the agent knows to search before answering."
        ),
    )
    def memory_status() -> dict[str, Any]:
        engine = _get_engine()
        return {
            "protocol": MEMORY_PROTOCOL,
            "db_path": str(_DB_PATH),
            "ready": True,
            "no_llm": engine.no_llm,
            "engine": {
                "reader_model": None if engine.no_llm else engine.reader_model,
                "observer_model": None if engine.no_llm else engine.observer_model,
            },
        }

    @mcp.tool(
        name="memory_search",
        description=(
            "Semantic search over the memory store. Returns verbatim text chunks "
            "(observations, sessions, turns) ranked by relevance. Use this BEFORE "
            "answering any question about past events, people, or decisions."
        ),
    )
    def memory_search(
        query: str,
        limit: int = 10,
        query_date: str | None = None,
    ) -> dict[str, Any]:
        engine = _get_engine()
        result = engine.search(query, query_date=query_date)
        chunks: list[dict[str, Any]] = []
        for cand in result.sessions_top[:limit]:
            chunks.append({
                "type": "session",
                "score": cand.score,
                "session_id": cand.session_id,
                "text": cand.text,
            })
        for cand in result.observations_top[:limit]:
            chunks.append({
                "type": "observation",
                "score": cand.score,
                "session_id": cand.session_id,
                "valid_at": cand.valid_at,
                "obs_type": cand.obs_type,
                "text": cand.text,
            })
        for cand in result.turns_top[:limit]:
            chunks.append({
                "type": "turn",
                "score": cand.score,
                "session_id": cand.session_id,
                "text": cand.text,
            })
        chunks.sort(key=lambda c: c["score"], reverse=True)
        return {"query": query, "results": chunks[:limit]}

    @mcp.tool(
        name="memory_answer",
        description=(
            "Retrieval + reader: synthesize an answer to the question using the memory "
            "store. Use for complex questions; use memory_search when you want raw hits. "
            "Unavailable when the server is running in --no-llm mode."
        ),
    )
    def memory_answer(query: str, query_date: str | None = None) -> dict[str, Any]:
        engine = _get_engine()
        if engine.no_llm:
            return {
                "query": query,
                "answer": None,
                "error": "memory_answer is unavailable in no-LLM mode. Use memory_search instead.",
            }
        answer = engine.answer(query, query_date=query_date)
        return {"query": query, "answer": answer}

    @mcp.tool(
        name="memory_ingest",
        description=(
            "File a session into memory. Provide a session_id, an ISO date, and a list "
            "of {role, content} turns. Use this to record durable facts, decisions, or "
            "milestones from the current conversation."
        ),
    )
    def memory_ingest(
        session_id: str,
        session_date: str,
        turns: list[dict[str, str]],
    ) -> dict[str, Any]:
        engine = _get_engine()
        normalized = [
            {"role": t.get("role", "user"), "content": t.get("content", "")}
            for t in turns
        ]
        result = engine.ingest_session(
            session_id=session_id,
            session_date=session_date,
            turns=normalized,
        )
        return {
            "ok": True,
            "session_id": session_id,
            "summary": _ingest_summary(result),
        }

    return mcp


def _ingest_summary(result: Any) -> dict[str, Any]:
    """Extract a JSON-safe summary from an IngestResult."""
    summary: dict[str, Any] = {}
    for attr in ("session_id", "n_observations", "n_turns", "n_chunks"):
        if hasattr(result, attr):
            summary[attr] = getattr(result, attr)
    if not summary:
        try:
            summary = json.loads(json.dumps(result, default=str))
        except Exception:
            summary = {"raw": str(result)}
    return summary


def run(
    db_path: Path,
    transport: str = "stdio",
    host: str = "127.0.0.1",
    port: int = 8765,
    no_llm: bool | None = None,
) -> None:
    server = build_server(db_path, no_llm=no_llm)
    if transport in ("sse", "streamable-http"):
        server.settings.host = host
        server.settings.port = port
    server.run(transport=transport)


def _default_db() -> Path:
    return Path(os.environ.get("SUPERMEM_DB", str(Path.home() / ".supermem" / "memory.db")))


if __name__ == "__main__":
    run(_default_db())
