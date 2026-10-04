"""Auto-memory store: a durable, multi-device backup of a client's notes on the Membase
Protocol hub.

The hub keeps each object id write-once, so records are not updated in place: every save and
delete is appended to an event log, and the current state is the log folded in order. This also
means two devices writing at once cannot lose each other's updates.

:class:`ProtocolLog` keeps that log in the wallet's own ``automem`` domain: entries are signed
by the wallet and encrypted with a key derived from it (the scheme membase-protocol uses for
cross-device session sync), so the same private key restores them on any device.
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


VALID_TYPES = ("user", "feedback", "project", "reference")


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


# ---------------------------------------------------------------------------
# Store
# ---------------------------------------------------------------------------


DOMAIN = "automem"
_KEY_LABEL = "automem-v1"


class ProtocolLog:
    """Append-only, encrypted log of byte entries on the Membase Protocol hub, for one wallet.

    ``append`` returns once the entry is listed (the hub client uploads through a background
    queue), so a store reads its own writes.
    """

    def __init__(self, hub: Any, wallet: Any, *, read_back_timeout: float = 15.0) -> None:
        import base64

        from cryptography.fernet import Fernet

        self._hub = hub
        self._owner = wallet.address
        key = wallet.signer.derive_symmetric_key(_KEY_LABEL)
        self._fernet = Fernet(base64.urlsafe_b64encode(key))
        self._read_back_timeout = read_back_timeout

    @classmethod
    def from_private_key(cls, private_key: str, hub_url: str | None = None) -> "ProtocolLog":
        """Wallet from a hex private key; hub URL from the SDK's config (``MEMBASE_HUB``)."""
        from membase_protocol.config import load_config
        from membase_protocol.core.persistence.hub_client import HubClient
        from membase_protocol.core.persistence.wallet import Wallet

        wallet = Wallet.from_key(private_key)
        return cls(HubClient(wallet, hub_url or load_config([]).hub.url), wallet)

    def append(self, entry: bytes) -> None:
        # A nanosecond timestamp as the sequence number: unique across devices in practice,
        # and it orders the log by time.
        self._hub.put_entry(DOMAIN, time.time_ns(), self._fernet.encrypt(entry))
        deadline = time.monotonic() + self._read_back_timeout
        while entry not in self.entries():
            if time.monotonic() > deadline:
                raise TimeoutError(f"hub entry not listed after {self._read_back_timeout}s")
            time.sleep(0.25)

    def entries(self) -> list[bytes]:
        """Decrypted entries in write order; entries this wallet cannot decrypt are skipped."""
        from cryptography.fernet import InvalidToken

        out: list[bytes] = []
        for raw in self._hub.list_entries(self._owner, DOMAIN):
            try:
                out.append(self._fernet.decrypt(bytes(raw)))
            except InvalidToken:
                continue
        return out


def _record(raw: dict[str, Any], scope: str) -> AutoMemory | None:
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


class AutoMemoryStore:
    """Auto-memory CRUD as an event log (:class:`ProtocolLog` in production).

    Events are ``{"op": "save", "scope", "record"}`` and ``{"op": "delete", "scope", "id"}``.
    """

    def __init__(self, log: Any) -> None:
        self._log = log

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
        prior = self._state()[1].get((scope, mem_id))
        mem = AutoMemory(
            id=mem_id,
            scope=scope,
            type=type,
            name=name,
            description=description,
            content=content,
            client=client,
            source_session_id=source_session_id,
            created_at=prior.created_at if prior else ts,
            updated_at=ts,
            extra=extra or {},
        )
        self._append({"op": "save", "scope": scope, "record": asdict(mem)})
        return mem

    def delete(self, scope: str, mem_id: str) -> None:
        _validate_scope(scope)
        _validate_id(mem_id)
        if (scope, mem_id) in self._state()[1]:
            self._append({"op": "delete", "scope": scope, "id": mem_id})

    def list(self, scope: str) -> list[AutoMemory]:
        _validate_scope(scope)
        memories = [m for (s, _), m in self._state()[1].items() if s == scope]
        memories.sort(key=lambda m: m.updated_at, reverse=True)
        return memories

    def fetch(self, scope: str, mem_id: str) -> AutoMemory | None:
        _validate_scope(scope)
        _validate_id(mem_id)
        return self._state()[1].get((scope, mem_id))

    def list_scopes(self) -> list[str]:
        return sorted(self._state()[0])

    def list_all(self) -> dict[str, list[AutoMemory]]:
        return {scope: self.list(scope) for scope in self.list_scopes()}

    # -- internals --------------------------------------------------------

    def _append(self, event: dict[str, Any]) -> None:
        self._log.append(json.dumps(event, ensure_ascii=False, sort_keys=True).encode("utf-8"))

    def _state(self) -> tuple[set[str], dict[tuple[str, str], AutoMemory]]:
        """Scopes ever written to, and the live records, from the log folded in order."""
        scopes: set[str] = set()
        live: dict[tuple[str, str], AutoMemory] = {}
        for raw in self._log.entries():
            try:
                event = json.loads(raw.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                continue
            if not isinstance(event, dict) or not isinstance(event.get("scope"), str):
                continue
            scope = event["scope"]
            if event.get("op") == "save" and isinstance(event.get("record"), dict):
                mem = _record(event["record"], scope)
                if mem is not None:
                    scopes.add(scope)
                    live[(scope, mem.id)] = mem
            elif event.get("op") == "delete":
                live.pop((scope, str(event.get("id"))), None)
        return scopes, live
