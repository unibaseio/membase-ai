"""The knowledge and agent MCP tools: argument handling and result shapes, with the engine's
services stubbed (their behaviour is tested in the engine repository)."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from membase_mcp import agent_tools, knowledge_tools


class FakeMCP:
    def __init__(self) -> None:
        self.tools: dict[str, object] = {}

    def tool(self, *, name: str, description: str = ""):
        def deco(fn):
            self.tools[name] = fn
            return fn

        return deco


def _engine():
    saves = []
    return SimpleNamespace(conn=object(), faiss=SimpleNamespace(save=lambda: saves.append(1))), saves


def test_knowledge_tools(monkeypatch):
    calls = {}

    def create_document(conn, faiss, parsed, **kw):
        calls["create"] = (parsed.text, kw)
        return SimpleNamespace(document_id="d1", topic_count=2)

    def search_knowledge(conn, faiss, query, **kw):
        calls["search"] = (query, kw)
        hit = SimpleNamespace(to_dict=lambda: {"document": {"title": "Vector Databases"}})
        return SimpleNamespace(hits=[hit], total=1, took_ms=1.234)

    monkeypatch.setattr(knowledge_tools.service, "create_document", create_document)
    monkeypatch.setattr(knowledge_tools.service, "search_knowledge", search_knowledge)
    mcp, (engine, saves) = FakeMCP(), _engine()
    knowledge_tools.register_mcp_tools(mcp, lambda: engine)
    assert set(mcp.tools) == {"knowledge_ingest", "knowledge_search"}

    ing = asyncio.run(mcp.tools["knowledge_ingest"](text="HNSW graphs", title="Vector Databases"))
    assert ing == {"ok": True, "document_id": "d1", "topic_count": 2} and saves == [1]
    assert calls["create"][0] == "HNSW graphs"
    assert calls["create"][1]["title"] == "Vector Databases" and calls["create"][1]["source_type"] == "text"

    res = asyncio.run(mcp.tools["knowledge_search"](query="HNSW", method="keyword"))
    assert res == {"ok": True, "hits": [{"document": {"title": "Vector Databases"}}], "total": 1, "took_ms": 1.2}
    assert calls["search"][0] == "HNSW" and calls["search"][1]["method"] == "keyword"

    err = asyncio.run(mcp.tools["knowledge_ingest"]())
    assert err["ok"] is False and err["error"] == "KnowledgeError"


def test_agent_tools(monkeypatch):
    calls = {}

    def ingest_agent_trace(conn, faiss, messages, **kw):
        calls["ingest"] = kw
        return {"cases": 1}

    def search_agent(conn, faiss, query, **kw):
        calls["search"] = (query, kw)
        return {"cases": [], "skills": []}

    monkeypatch.setattr(agent_tools._ingest, "ingest_agent_trace", ingest_agent_trace)
    monkeypatch.setattr(agent_tools._search, "search_agent", search_agent)
    monkeypatch.setattr(agent_tools._search, "list_skills", lambda conn, agent_id: [{"id": "s1"}])
    mcp, (engine, saves) = FakeMCP(), _engine()
    agent_tools.register_mcp_tools(mcp, lambda: engine)
    assert set(mcp.tools) == {"agent_ingest", "agent_search", "agent_skills"}

    assert asyncio.run(mcp.tools["agent_ingest"]([{"role": "user", "content": "fix"}], "coder")) == {"cases": 1}
    assert calls["ingest"] == {"agent_id": "coder", "session_id": "mcp-coder", "is_final": True}
    assert saves == [1]
    asyncio.run(mcp.tools["agent_search"]("deploy", "coder", "both", "hybrid"))
    assert calls["search"][1]["kind"] == "both" and calls["search"][1]["method"] == "hybrid"
    assert asyncio.run(mcp.tools["agent_skills"]("coder")) == {"agent_id": "coder", "skills": [{"id": "s1"}]}
    with pytest.raises(ValueError):
        asyncio.run(mcp.tools["agent_search"]("q", "coder", "bogus"))
