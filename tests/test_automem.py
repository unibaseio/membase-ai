"""Opt-in integration test for the membase-backed auto-memory store (hits the real hub).

Enable with SUPERMEM_TEST_MEMBASE=1; MEMBASE_ACCOUNT, MEMBASE_HUB and MEMBASE_ID are optional.
Each test uses a unique scope so reruns do not collide (the hub is last-write-wins per filename).
"""

from __future__ import annotations

import os
import time
import uuid

import pytest


_RUN_LIVE = os.environ.get("SUPERMEM_TEST_MEMBASE") == "1"
_live = pytest.mark.skipif(
    not _RUN_LIVE,
    reason="Set SUPERMEM_TEST_MEMBASE=1 to run real-hub integration tests.",
)


@pytest.fixture(scope="module")
def store():
    membase = pytest.importorskip("membase.storage.hub")
    from memory.infra.remote.membase_kv import MembaseAutoMemoryStore

    account = os.environ.get("MEMBASE_ACCOUNT") or "supermem-ci"
    return MembaseAutoMemoryStore(account=account, hub_client=membase_algo.hub_client)


@pytest.fixture
def scope():
    """Each test gets a fresh scope so parallel/sequential runs don't share state."""
    return f"test-{uuid.uuid4().hex[:12]}"


def _wait_for(predicate, *, timeout: float = 30.0, interval: float = 0.5):
    deadline = time.time() + timeout
    last = None
    while time.time() < deadline:
        last = predicate()
        if last:
            return last
        time.sleep(interval)
    return last


def _wait_for_state(store, scope, mem_id, *, present: bool, timeout: float = 30.0):
    deadline = time.time() + timeout
    last = None
    while time.time() < deadline:
        last = store.fetch(scope, mem_id)
        if present and last is not None:
            return last
        if not present and last is None:
            return None
        time.sleep(0.5)
    raise AssertionError(
        f"timeout waiting for fetch(scope={scope}, id={mem_id}) "
        f"present={present}; last={last!r}"
    )


@_live
def test_save_then_fetch_roundtrip(store, scope):
    saved = store.save(
        scope,
        type="feedback",
        name="prefer-real-db",
        description="integration tests must hit a real database",
        content="Lead: real DB.\n\n**Why:** prior incident.\n**How to apply:** integration suites only.",
        source_session_id="test-session-001",
    )
    assert saved.id
    assert saved.scope == scope
    assert saved.type == "feedback"
    assert saved.created_at == saved.updated_at  # first save

    got = _wait_for_state(store, scope, saved.id, present=True)
    assert got.id == saved.id
    assert got.name == "prefer-real-db"
    assert got.description == "integration tests must hit a real database"
    assert got.content.startswith("Lead: real DB.")
    assert got.source_session_id == "test-session-001"
    assert got.client == "claude-code"


@_live
def test_save_same_name_updates_in_place(store, scope):
    first = store.save(
        scope,
        type="user",
        name="role",
        description="data scientist",
        content="user is a data scientist",
    )
    _wait_for_state(store, scope, first.id, present=True)

    # Same scope+name => same derived id => second save is an update.
    second = store.save(
        scope,
        type="user",
        name="role",
        description="data scientist working on observability",
        content="user is a data scientist focused on observability",
    )
    assert second.id == first.id
    assert second.created_at == first.created_at
    assert second.updated_at >= first.updated_at

    got = _wait_for(
        lambda: (
            store.fetch(scope, first.id)
            if (m := store.fetch(scope, first.id)) and "observability" in m.description
            else None
        )
    )
    assert got is not None
    assert "observability" in got.description
    assert "observability" in got.content


@_live
def test_list_returns_only_live_records(store, scope):
    a = store.save(scope, type="reference", name="a-doc", description="a", content="aaa")
    b = store.save(scope, type="reference", name="b-doc", description="b", content="bbb")
    c = store.save(scope, type="reference", name="c-doc", description="c", content="ccc")

    _wait_for_state(store, scope, a.id, present=True)
    _wait_for_state(store, scope, b.id, present=True)
    _wait_for_state(store, scope, c.id, present=True)

    store.delete(scope, b.id)
    _wait_for_state(store, scope, b.id, present=False)

    live = store.list(scope)
    live_ids = {m.id for m in live}
    assert a.id in live_ids
    assert c.id in live_ids
    assert b.id not in live_ids


@_live
def test_list_scopes_includes_our_scope(store, scope):
    saved = store.save(
        scope, type="project", name="hello", description="hi", content="hello world"
    )
    _wait_for_state(store, scope, saved.id, present=True)

    scopes = store.list_scopes()
    assert scope in scopes


@_live
def test_delete_then_resave_revives_record(store, scope):
    saved = store.save(
        scope,
        type="feedback",
        name="ephemeral",
        description="will be deleted",
        content="content v1",
    )
    _wait_for_state(store, scope, saved.id, present=True)

    store.delete(scope, saved.id)
    _wait_for_state(store, scope, saved.id, present=False)

    revived = store.save(
        scope,
        type="feedback",
        name="ephemeral",
        description="brought back",
        content="content v2",
    )
    assert revived.id == saved.id

    got = _wait_for(
        lambda: (
            m if (m := store.fetch(scope, saved.id)) and m.description == "brought back" else None
        )
    )
    assert got is not None
    assert got.description == "brought back"
    assert got.content == "content v2"


def test_stable_id_is_deterministic():
    """Pure-function check; no network."""
    from memory.infra.remote.membase_kv import _stable_id_for

    a = _stable_id_for("user", "role")
    b = _stable_id_for("user", "role")
    c = _stable_id_for("project:foo", "role")
    assert a == b
    assert a != c
    assert len(a) == 16
