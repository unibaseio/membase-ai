"""MCP tools for the agent-memory track.

Tools are ``async`` and run the synchronous pipeline on a worker thread: ``async_to_sync``
refuses to run on a thread that already hosts an event loop.
"""

from __future__ import annotations

import asyncio
from typing import Any, Callable

from membase_core.agent import ingest as _ingest
from membase_core.agent import search as _search

__all__ = ["register_mcp_tools"]


def register_mcp_tools(mcp: Any, get_engine: Callable[[], Any]) -> None:
    @mcp.tool(
        name="agent_ingest",
        description=(
            "Memorize an agent trace (OpenAI chat-completions messages: user / assistant / "
            "assistant+tool_calls / tool rows). Splits it into trajectory cells, distils each "
            "closed cell with >= 3 tool rounds into a reusable case (task_intent, approach, "
            "key_insight, quality_score), clusters cases by task, and maintains one reusable "
            "skill per cluster. Call it when a multi-step tool-using task has finished."
        ),
    )
    async def agent_ingest(
        messages: list[dict[str, Any]],
        agent_id: str,
        session_id: str | None = None,
        is_final: bool = True,
    ) -> dict[str, Any]:
        engine = get_engine()
        sid = session_id or f"mcp-{agent_id}"
        res = await asyncio.to_thread(
            _ingest.ingest_agent_trace, engine.conn, engine.faiss, messages,
            agent_id=agent_id, session_id=sid, is_final=is_final,
        )
        try:
            engine.faiss.save()
        except Exception:  # noqa: BLE001 -- the store is still consistent in memory
            pass
        return res

    @mcp.tool(
        name="agent_search",
        description=(
            "Retrieve an agent's past cases (concrete solved tasks with the approach that "
            "worked) and skills (distilled reusable procedures) relevant to a task. Call it "
            "BEFORE starting a non-trivial tool-using task so proven approaches and known "
            "pitfalls are in context. kind: cases | skills | both. method: hybrid (default) | "
            "keyword | vector | agentic (LLM-guided multi-round)."
        ),
    )
    async def agent_search(
        query: str,
        agent_id: str,
        kind: str = "both",
        method: str = "hybrid",
        top_k: int = 10,
        enable_llm_rerank: bool = False,
    ) -> dict[str, Any]:
        engine = get_engine()
        if kind not in ("cases", "skills", "both"):
            raise ValueError("kind must be one of cases, skills, both")
        if method not in ("hybrid", "keyword", "vector", "agentic"):
            raise ValueError("method must be one of hybrid, keyword, vector, agentic")
        return await asyncio.to_thread(
            _search.search_agent, engine.conn, engine.faiss, query,
            agent_id=agent_id, kind=kind, method=method, top_k=top_k, enable_llm_rerank=enable_llm_rerank,
        )

    @mcp.tool(
        name="agent_skills",
        description="List every skill the agent has distilled so far (name, description, content, confidence, source cases).",
    )
    async def agent_skills(agent_id: str) -> dict[str, Any]:
        engine = get_engine()
        skills = await asyncio.to_thread(_search.list_skills, engine.conn, agent_id)
        return {"agent_id": agent_id, "skills": skills}
