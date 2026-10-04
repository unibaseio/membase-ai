"""The ``automem_*`` MCP tools: a client's auto-memory notes, backed up on the Membase Hub.

Entries are signed by the wallet and encrypted with a key derived from it, so the same
``MEMBASE_PRIVATE_KEY`` restores them on another device. Needs the ``protocol`` extra.
"""

from __future__ import annotations

from typing import Any

from .automem import AutoMemory, AutoMemoryStore


def _automem_to_dict(mem: AutoMemory) -> dict[str, Any]:
    return {
        "id": mem.id,
        "scope": mem.scope,
        "type": mem.type,
        "name": mem.name,
        "description": mem.description,
        "content": mem.content,
        "client": mem.client,
        "source_session_id": mem.source_session_id,
        "created_at": mem.created_at,
        "updated_at": mem.updated_at,
        "extra": mem.extra,
    }


def register_automem_tools(mcp: Any, private_key: str) -> None:
    store: AutoMemoryStore | None = None

    def _get_automem() -> AutoMemoryStore:
        nonlocal store
        if store is None:
            try:
                from .automem import ProtocolLog

                log = ProtocolLog.from_private_key(private_key)
            except ImportError as exc:
                raise RuntimeError(
                    "automem needs membase-protocol (the Membase Hub client) and cryptography"
                ) from exc
            store = AutoMemoryStore(log)
        return store

    @mcp.tool(
        name="automem_save",
        description=(
            "Persist a single auto-memory record to the user's decentralized "
            "membase store. Auto-memories are durable, structured notes a "
            "client (e.g. Claude Code) keeps across sessions: user role facts, "
            "feedback rules, project context, references.\n"
            "\n"
            "This tool is the WRITE path. The client should also keep a local "
            "copy (e.g. a markdown file); membase is the cross-device backup.\n"
            "\n"
            "Required fields:\n"
            "  scope:        'user' for cross-project, 'project:<repo-name>' "
            "for project-bound\n"
            "  type:         one of 'user' | 'feedback' | 'project' | 'reference'\n"
            "  name:         short stable identifier (filename-style)\n"
            "  description:  one-line summary used for relevance ranking\n"
            "  content:      the full memory body (markdown, with frontmatter "
            "if the client uses it)\n"
            "\n"
            "Optional:\n"
            "  id:                  stable uuid; if omitted, derived from "
            "scope+name (so re-saves under the same name update in place)\n"
            "  source_session_id:   the session that triggered this memory, "
            "for later audit\n"
            "  client:              identifier of the writing client "
            "(default 'claude-code')\n"
            "  extra:               free-form JSON sidecar\n"
            "\n"
            "Returns the canonical record (with id, created_at, updated_at)."
        ),
    )
    def automem_save(
        scope: str,
        type: str,
        name: str,
        description: str,
        content: str,
        id: str | None = None,
        client: str = "claude-code",
        source_session_id: str | None = None,
        extra: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        store = _get_automem()
        mem = store.save(
            scope,
            type=type,
            name=name,
            description=description,
            content=content,
            id=id,
            client=client,
            source_session_id=source_session_id,
            extra=extra,
        )
        return {"ok": True, "memory": _automem_to_dict(mem)}

    @mcp.tool(
        name="automem_list",
        description=(
            "List the current state of auto-memories in a given scope.\n"
            "\n"
            "Pass scope='user' to enumerate cross-project memories, or "
            "scope='project:<repo-name>' for project-bound ones. Pass "
            "scope=None (omit) to enumerate every scope this wallet "
            "owns.\n"
            "\n"
            "Returns the FOLDED current view: tombstoned memories are not "
            "returned, and each id appears at most once with its latest save. "
            "Sorted by updated_at descending.\n"
            "\n"
            "Use this when a user asks to restore memories on a new device, "
            "or to enumerate what is currently durable for this wallet."
        ),
    )
    def automem_list(scope: str | None = None) -> dict[str, Any]:
        store = _get_automem()
        if scope is None:
            grouped = store.list_all()
            return {
                "scopes": {
                    s: [_automem_to_dict(m) for m in mems]
                    for s, mems in grouped.items()
                }
            }
        mems = store.list(scope)
        return {"scope": scope, "memories": [_automem_to_dict(m) for m in mems]}

    @mcp.tool(
        name="automem_fetch",
        description=(
            "Fetch a single auto-memory by (scope, id). Returns null if the id "
            "is unknown or has been tombstoned. Use this when the client knows "
            "the id (e.g. from a prior automem_list) and wants the full body."
        ),
    )
    def automem_fetch(scope: str, id: str) -> dict[str, Any]:
        store = _get_automem()
        mem = store.fetch(scope, id)
        if mem is None:
            return {"scope": scope, "id": id, "memory": None}
        return {"scope": scope, "id": id, "memory": _automem_to_dict(mem)}

    @mcp.tool(
        name="automem_delete",
        description=(
            "Tombstone an auto-memory. Membase is append-only; this writes a "
            "delete event so future reads of (scope, id) return null. Prior "
            "save events remain in history for audit."
        ),
    )
    def automem_delete(scope: str, id: str) -> dict[str, Any]:
        store = _get_automem()
        store.delete(scope, id)
        return {"ok": True, "scope": scope, "id": id}
