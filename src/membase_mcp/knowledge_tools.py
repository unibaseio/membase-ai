"""MCP tools for the knowledge store: ``knowledge_ingest`` and ``knowledge_search``.

Tools are ``async`` and hop to a worker thread: the service uses ``async_to_sync``, which
refuses to run on the thread that owns the MCP event loop.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any, Callable

from membase_algo.types import ParsedContent

from memory.knowledge import service
from memory.knowledge.errors import KnowledgeError
from memory.knowledge.parse import parse_file

__all__ = ["register_mcp_tools"]


def _ingest_sync(engine: Any, *, path: str | None, text: str | None, title: str | None,
                 category_id: str | None, app_id: str, project_id: str) -> dict[str, Any]:
    if path:
        p = Path(path).expanduser()
        parsed = parse_file(p)
        result = service.create_document(
            engine.conn, engine.faiss, parsed, title=title or p.stem, source_name=p.name,
            source_type="file", category_id=category_id or None, app_id=app_id, project_id=project_id,
        )
    elif text:
        result = service.create_document(
            engine.conn, engine.faiss, ParsedContent(text=text), title=title or "Untitled",
            source_name=None, source_type="text", category_id=category_id or None,
            app_id=app_id, project_id=project_id,
        )
    else:
        raise KnowledgeError("provide either `path` or `text`")
    engine.faiss.save()
    return {"ok": True, **result.__dict__}


def _search_sync(engine: Any, *, query: str, top_k: int, method: str, include_content: bool,
                 app_id: str, project_id: str) -> dict[str, Any]:
    result = service.search_knowledge(
        engine.conn, engine.faiss, query, method=method, top_k=top_k,
        include_content=include_content, app_id=app_id, project_id=project_id,
    )
    return {"ok": True, "hits": [h.to_dict() for h in result.hits], "total": result.total,
            "took_ms": round(result.took_ms, 1)}


def register_mcp_tools(mcp: Any, get_engine: Callable[[], Any]) -> None:
    @mcp.tool(
        name="knowledge_ingest",
        description=(
            "Add a document to the user's knowledge base. Give `path` (a local file: "
            "md/txt read directly; pdf, images, docx, html, eml through the multimodal "
            "parser) OR `text` (raw content). The document is split into a topic tree "
            "(membase KnowledgeExtractor) and classified into a category; every topic "
            "becomes searchable with knowledge_search. Returns doc_id, category_id and "
            "topic_count."
        ),
    )
    async def knowledge_ingest(
        path: str | None = None,
        text: str | None = None,
        title: str | None = None,
        category_id: str | None = None,
        app_id: str = "default",
        project_id: str = "default",
    ) -> dict[str, Any]:
        try:
            return await asyncio.to_thread(
                _ingest_sync, get_engine(), path=path, text=text, title=title,
                category_id=category_id, app_id=app_id, project_id=project_id,
            )
        except KnowledgeError as exc:
            return {"ok": False, "error": type(exc).__name__, "message": str(exc)}

    @mcp.tool(
        name="knowledge_search",
        description=(
            "Search the user's knowledge base (documents ingested with knowledge_ingest) "
            "for topics answering `query`. Use it for questions about the CONTENT of the "
            "user's documents, papers, manuals or notes -- as opposed to memory_search, "
            "which covers what the user said in past conversations. `method` is hybrid "
            "(default), keyword or vector. Returns ranked topics with summary, topic_path, "
            "category and the source document; set include_content for the full section text."
        ),
    )
    async def knowledge_search(
        query: str,
        top_k: int = 10,
        method: str = "hybrid",
        include_content: bool = False,
        app_id: str = "default",
        project_id: str = "default",
    ) -> dict[str, Any]:
        try:
            return await asyncio.to_thread(
                _search_sync, get_engine(), query=query, top_k=top_k, method=method,
                include_content=include_content, app_id=app_id, project_id=project_id,
            )
        except KnowledgeError as exc:
            return {"ok": False, "error": type(exc).__name__, "message": str(exc)}
