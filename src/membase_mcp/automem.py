"""Membase-backed auto-memory store (durable, multi-device backup of a client's notes).

Flat key-value layout under owner ``MEMBASE_ACCOUNT``: ``automem/__scopes__`` (scope list),
``automem/<scope>/index`` (id -> summary) and ``automem/<scope>/blob/<id>`` (full record).
Index updates are read-modify-write, last-write-wins.
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


VALID_TYPES = ("user", "feedback", "project", "reference")
ROOT = "automem"
SCOPES_KEY = f"{ROOT}/__scopes__"


@dataclass(frozen=True)
class AutoMemory:
    """A single auto-memory record (current-state view)."""

    id: str
    scope: str
    type: str
    name: str
    description: str
    content: str
    client: str = "claude-code"
    source_session_id: str | None = None
    created_at: str = ""
    updated_at: str = ""
    extra: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _validate_scope(scope: str) -> None:
    if not scope or "/" in scope:
        raise ValueError(f"invalid scope: {scope!r} (must be non-empty, no slashes)")


def _validate_type(type_: str) -> None:
    if type_ not in VALID_TYPES:
        raise ValueError(f"type must be one of {VALID_TYPES}, got {type_!r}")


def _validate_id(mem_id: str) -> None:
    if not mem_id or "/" in mem_id:
        raise ValueError(f"invalid memory id: {mem_id!r} (must be non-empty, no slashes)")


def _stable_id_for(scope: str, name: str) -> str:
    """Stable id from (scope, name), so re-saving under the same name updates in place."""
    h = hashlib.sha1(f"{scope}/{name}".encode()).hexdigest()
    return h[:16]


def _index_key(scope: str) -> str:
    return f"{ROOT}/{scope}/index"


def _blob_key(scope: str, mem_id: str) -> str:
    return f"{ROOT}/{scope}/blob/{mem_id}"


def _decode_json(raw: Any, default: Any) -> Any:
    if raw is None:
        return default
    if isinstance(raw, (bytes, bytearray)):
        try:
            raw = raw.decode("utf-8")
        except UnicodeDecodeError:
            return default
    if isinstance(raw, str):
        if not raw.strip():
            return default
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return default
    return raw


def _index_summary(mem: AutoMemory) -> dict[str, Any]:
    return {
        "id": mem.id,
        "name": mem.name,
        "description": mem.description,
        "type": mem.type,
        "client": mem.client,
        "created_at": mem.created_at,
        "updated_at": mem.updated_at,
    }


# ---------------------------------------------------------------------------
# Store
# ---------------------------------------------------------------------------


class MembaseAutoMemoryStore:
    """Auto-memory CRUD on top of the membase hub key-value primitives."""

    def __init__(
        self,
        account: str | None = None,
        hub_client: Any | None = None,
    ) -> None:
        self.account = account or os.environ.get("MEMBASE_ACCOUNT") or "default"
        if hub_client is None:
            from membase.storage.hub import hub_client as default_client
            hub_client = default_client
        self._hub = hub_client

    # -- low-level KV helpers ---------------------------------------------

    def _put_json(self, key: str, value: Any) -> None:
        # Bucket = account: unique per user, and bypasses the hub's auto-bucket logic, which
        # rejects non-dict JSON payloads.
        self._hub.upload_hub(
            self.account,
            key,
            json.dumps(value, ensure_ascii=False),
            bucket=self.account,
        )

    def _get_json(self, key: str, default: Any) -> Any:
        try:
            raw = self._hub.download_hub(self.account, key)
        except Exception:
            return default
        return _decode_json(raw, default)

    # -- public API -------------------------------------------------------

    def save(
        self,
        scope: str,
        *,
        type: str,
        name: str,
        description: str,
        content: str,
        id: str | None = None,
        client: str = "claude-code",
        source_session_id: str | None = None,
        extra: dict[str, Any] | None = None,
    ) -> AutoMemory:
        _validate_scope(scope)
        _validate_type(type)
        mem_id = id or _stable_id_for(scope, name)
        _validate_id(mem_id)

        ts = _now_iso()
        prior = self._fetch_blob(scope, mem_id)
        created_at = prior.created_at if prior else ts

        mem = AutoMemory(
            id=mem_id,
            scope=scope,
            type=type,
            name=name,
            description=description,
            content=content,
            client=client,
            source_session_id=source_session_id,
            created_at=created_at,
            updated_at=ts,
            extra=extra or {},
        )

        self._put_json(_blob_key(scope, mem_id), asdict(mem))

        index = self._read_index(scope)
        index[mem_id] = _index_summary(mem)
        self._write_index(scope, index)

        scopes = set(self._read_scopes())
        if scope not in scopes:
            scopes.add(scope)
            self._put_json(SCOPES_KEY, sorted(scopes))

        return mem

    def delete(self, scope: str, mem_id: str) -> None:
        _validate_scope(scope)
        _validate_id(mem_id)
        index = self._read_index(scope)
        if mem_id in index:
            del index[mem_id]
            self._write_index(scope, index)
        # The hub has no delete; the index is the source of truth for what exists.

    def list(self, scope: str) -> list[AutoMemory]:
        _validate_scope(scope)
        index = self._read_index(scope)
        memories: list[AutoMemory] = []
        for mem_id in index:
            mem = self._fetch_blob(scope, mem_id)
            if mem is not None:
                memories.append(mem)
        memories.sort(key=lambda m: m.updated_at, reverse=True)
        return memories

    def fetch(self, scope: str, mem_id: str) -> AutoMemory | None:
        _validate_scope(scope)
        _validate_id(mem_id)
        index = self._read_index(scope)
        if mem_id not in index:
            return None
        return self._fetch_blob(scope, mem_id)

    def list_scopes(self) -> list[str]:
        return sorted(self._read_scopes())

    def list_all(self) -> dict[str, list[AutoMemory]]:
        return {scope: self.list(scope) for scope in self.list_scopes()}

    # -- internals --------------------------------------------------------

    def _read_scopes(self) -> list[str]:
        raw = self._get_json(SCOPES_KEY, [])
        if not isinstance(raw, list):
            return []
        return [s for s in raw if isinstance(s, str)]

    def _read_index(self, scope: str) -> dict[str, dict[str, Any]]:
        raw = self._get_json(_index_key(scope), {})
        if isinstance(raw, list):
            # tolerate older/alternative shape: list of summaries
            return {entry["id"]: entry for entry in raw if isinstance(entry, dict) and "id" in entry}
        if isinstance(raw, dict):
            return {k: v for k, v in raw.items() if isinstance(v, dict)}
        return {}

    def _write_index(self, scope: str, index: dict[str, dict[str, Any]]) -> None:
        self._put_json(_index_key(scope), index)

    def _fetch_blob(self, scope: str, mem_id: str) -> AutoMemory | None:
        raw = self._get_json(_blob_key(scope, mem_id), None)
        if not isinstance(raw, dict):
            return None
        try:
            return AutoMemory(
                id=raw["id"],
                scope=raw.get("scope", scope),
                type=raw.get("type", ""),
                name=raw.get("name", ""),
                description=raw.get("description", ""),
                content=raw.get("content", ""),
                client=raw.get("client", "claude-code"),
                source_session_id=raw.get("source_session_id"),
                created_at=raw.get("created_at", ""),
                updated_at=raw.get("updated_at", ""),
                extra=raw.get("extra") or {},
            )
        except (KeyError, TypeError):
            return None
