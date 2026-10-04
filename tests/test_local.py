"""Local memory answers the agent protocol: shapes, refusals and confirmations offline; one
round trip through the real engine and model provider when a key is configured."""

from __future__ import annotations

import os
import threading

import httpx
import pytest

pytest.importorskip("membase_core", reason="needs the local extra (membase-core, Python 3.12+)")

from membase import BadRequestError, Membase, NotFoundError, PermissionDeniedError  # noqa: E402
from membase.local.server import make_server  # noqa: E402


@pytest.fixture
def local(tmp_path):
    m = Membase(local=tmp_path / "store")
    yield m
    m.close()


def test_an_empty_store_has_no_containers_and_finds_nothing(local):
    assert local.containers.list() == {"containers": []}
    out = local.search("anything")
    assert out == {"query": "anything", "results": [], "containers": []}
    assert local.documents.list() == {"documents": []}
    assert local.rules()["rules"] == []


def test_static_memories_land_in_the_profile(local):
    out = local.memories.add("Prefers dark mode", static=True)
    assert out == {"static": True, "status": "recorded", "content": "Prefers dark mode"}
    prof = local.profile()
    assert prof["available"] is True and prof["static"] == ["Prefers dark mode"]
    # The profile is the account's, not a container's.
    assert local.containers.list()["containers"] == []


def test_refusals_answer_in_the_error_envelope(local):
    with pytest.raises(BadRequestError):
        local.search("")
    with pytest.raises(BadRequestError):
        local.search("x", limit=99)
    with pytest.raises(BadRequestError):
        local.add(None, container="notes")                  # neither content nor url
    with pytest.raises(PermissionDeniedError) as e:
        local.search("x", container="nowhere")
    assert e.value.code == "unauthorized"
    with pytest.raises(NotFoundError):
        local.documents.get("doc_missing")
    with pytest.raises(NotFoundError):
        local.memories.forget("default:999")


def test_unknown_fields_are_refused(local):
    r = local._http.post("/v1/search", json={"q": "x", "threshold": 0.5})
    assert r.status_code == 400 and r.json()["error"]["code"] == "bad_request"


def test_the_http_server_answers_the_same_routes(tmp_path):
    httpd = make_server(port=0, root=str(tmp_path / "srv"))
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    try:
        base = f"http://127.0.0.1:{httpd.server_address[1]}"
        remote = Membase("local", base_url=base, max_retries=0)
        remote.memories.add("Works from Singapore", static=True)
        assert remote.profile()["static"] == ["Works from Singapore"]
        assert httpx.get(f"{base}/v1/nope").status_code == 404
        # Path parameters arrive percent-encoded from other clients (the TypeScript one encodes
        # the ':' in a local memory id); the server decodes them.
        r = httpx.delete(f"{base}/v1/memories/default%3A999", params={"confirm": "true"})
        assert r.status_code == 404 and r.json()["error"]["details"] == {"memory_id": "default:999"}
        remote.close()
    finally:
        httpd.shutdown()
        httpd.backend.close()


@pytest.mark.skipif(not os.environ.get("OPENAI_API_KEY"), reason="needs a model provider key")
def test_round_trip_through_the_engine(local):
    added = local.memories.add(
        "User: We picked Postgres for the ledger service.\nAssistant: Noted, Postgres for the ledger.",
        container="Engineering",
    )
    assert added["status"] == "learned" and added["memory_ids"], added
    hits = local.search("what database did we pick for the ledger?", container="engineering")
    assert hits["results"] and "Postgres" in hits["results"][0]["content"]
    assert hits["results"][0]["container"] == "engineering"
    local.memories.add("Prefers dark mode", static=True)
    local.memories.add("User: My sister lives in Lisbon.\nAssistant: Noted.", container="Family")
    answer = local.ask("Which database is the ledger on?")       # two containers: picks the right one
    assert "postgres" in answer["answer"].lower() and answer["container"] == "engineering"
    mid = added["memory_ids"][0]
    assert local.memories.forget(mid)["status"] == "confirmation_required"
    assert local.memories.forget(mid, confirm=True) == {"status": "forgotten", "memory_id": mid}
