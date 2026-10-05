"""The client's own behaviour, against scripted transports (ported from the platform's SDK tests, whose hosted-app half stays in membase-platform), and how it picks hosted or local."""

from __future__ import annotations

import httpx
import pytest

from membase import APIConnectionError, Membase, RateLimitError, UnprocessableEntityError


def test_the_sdk_needs_a_key_and_reads_the_environment(monkeypatch):
    monkeypatch.delenv("MEMBASE_API_KEY", raising=False)
    monkeypatch.delenv("MEMBASE_LOCAL", raising=False)
    with pytest.raises(ValueError, match="MEMBASE_API_KEY"):
        Membase()
    monkeypatch.setenv("MEMBASE_API_KEY", "mbk_env")
    monkeypatch.setenv("MEMBASE_BASE_URL", "https://api.example.test/")
    c = Membase()
    assert c.api_key == "mbk_env" and c.base_url == "https://api.example.test"
    c.close()


def test_the_sdk_retries_429_and_5xx_then_raises_the_last_answer():
    answers = [
        httpx.Response(
            429,
            json={"error": {"code": "rate_limited", "message": "budget"}},
            headers={"Retry-After": "0"},
        ),
        httpx.Response(503, json={"error": {"code": "provider_unavailable", "message": "down"}}),
        httpx.Response(200, json={"containers": [{"id": "mv-1", "name": "A"}]}),
    ]
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return answers.pop(0)

    http = httpx.Client(transport=httpx.MockTransport(handler), base_url="https://api.example.test")
    c = Membase("mbk_test", http_client=http, max_retries=2)
    assert c.containers.list()["containers"][0]["id"] == "mv-1"
    assert len(seen) == 3
    assert seen[0].headers["authorization"] == "Bearer mbk_test"
    assert seen[0].headers["user-agent"].startswith("membase-ai-python/")

    answers[:] = [
        httpx.Response(
            429,
            json={"error": {"code": "rate_limited", "message": "budget"}},
            headers={"Retry-After": "0"},
        ),
        httpx.Response(
            429,
            json={"error": {"code": "rate_limited", "message": "budget"}},
            headers={"Retry-After": "0"},
        ),
    ]
    c2 = Membase("mbk_test", http_client=http, max_retries=1)
    with pytest.raises(RateLimitError) as e:
        c2.containers.list()
    assert e.value.code == "rate_limited" and e.value.status == 429

    answers[:] = [
        httpx.Response(
            422,
            json={
                "error": {
                    "code": "capability_unavailable",
                    "message": "no model",
                    "retryable": True,
                }
            },
        ),
    ]
    with pytest.raises(UnprocessableEntityError) as e:
        Membase("mbk_test", http_client=http, max_retries=0).search("q")
    assert e.value.code == "capability_unavailable" and e.value.retryable is True


def test_the_sdk_turns_a_dead_connection_into_a_connection_error():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused", request=request)

    http = httpx.Client(transport=httpx.MockTransport(handler), base_url="https://api.example.test")
    with pytest.raises(APIConnectionError):
        Membase("mbk_test", http_client=http, max_retries=1).containers.list()


def test_local_is_chosen_by_argument_or_environment(monkeypatch, tmp_path):
    monkeypatch.delenv("MEMBASE_API_KEY", raising=False)
    monkeypatch.setenv("MEMBASE_LOCAL", str(tmp_path / "env-store"))
    c = Membase()
    assert c.base_url == "http://membase.local" and c._http._transport.backend.root == tmp_path / "env-store"
    c.close()
    c = Membase(local=tmp_path / "arg-store")
    assert c._http._transport.backend.root == tmp_path / "arg-store"
    c.close()
    monkeypatch.setenv("MEMBASE_API_KEY", "mbk_env")
    c = Membase()
    assert c.base_url.startswith("https://")
    c.close()
