"""The Membase client: one developer key, the account's memory.

    from membase import Membase

    client = Membase()                       # MEMBASE_API_KEY, optional MEMBASE_BASE_URL
    local = Membase(local=True)              # the same API on this machine (membase-ai[local])
    client.add("Call notes …", container="mv-…", custom_id="call-1")
    client.search("what did we decide about the ledger")
    client.profile(q="working hours")

Every method is one operation of the agent protocol (the REST namespace under
``https://api.app.membase.io/v1``); the access level, reach and confirmation rules are enforced
server-side, so nothing here can do what the key cannot.

``local=`` runs the same operations on this machine instead: the membase-core engine under
``~/.membase`` (or the given directory), answering the same routes with the same shapes, so code
moves between the hosted memory and a local one by changing the constructor.
"""

from __future__ import annotations

import os
import random
import time
from typing import Any

import httpx

from ._version import __version__
from .errors import APIConnectionError, APITimeoutError, error_for

DEFAULT_BASE_URL = "https://api.app.membase.io"
#: A search is a turn inside the user's memory; the first one after a quiet spell can take up
#: to a minute while the memory wakes, so the default is generous.
DEFAULT_TIMEOUT = 90.0
DEFAULT_MAX_RETRIES = 2
_RETRY_STATUSES = {408, 409, 429}


class Membase:
    """The client. Thread-safe for reads; one instance per process is fine."""

    def __init__(
        self,
        api_key: str | None = None,
        *,
        base_url: str | None = None,
        timeout: float | None = DEFAULT_TIMEOUT,
        max_retries: int = DEFAULT_MAX_RETRIES,
        http_client: httpx.Client | None = None,
        local: str | os.PathLike | bool | None = None,
    ) -> None:
        """Hosted with an API key; local with ``local=True`` (``~/.membase``) or a directory.
        With neither, ``MEMBASE_API_KEY`` picks hosted and ``MEMBASE_LOCAL`` picks local."""
        if local is None and api_key is None and not os.environ.get("MEMBASE_API_KEY"):
            env = (os.environ.get("MEMBASE_LOCAL") or "").strip()
            local = True if env.lower() in {"1", "true", "yes"} else (env or None)
        if local not in (None, False):
            from .requirements import require_local

            require_local()
            from .local import LocalTransport

            self.api_key = ""
            self.base_url = LocalTransport.BASE_URL
            self.max_retries = 0
            self._owns_http = True
            self._http = httpx.Client(
                base_url=self.base_url,
                transport=LocalTransport(None if local is True else local),
                timeout=None,
            )
            self.containers = _Containers(self)
            self.documents = _Documents(self)
            self.memories = _Memories(self)
            return
        api_key = api_key if api_key is not None else os.environ.get("MEMBASE_API_KEY")
        if not api_key:
            raise ValueError(
                "no API key: pass api_key= or set MEMBASE_API_KEY "
                "(Connect › Developer keys in the Membase app), or use local=True"
            )
        self.api_key = api_key
        self.base_url = (base_url or os.environ.get("MEMBASE_BASE_URL") or DEFAULT_BASE_URL).rstrip(
            "/"
        )
        self.max_retries = max(0, int(max_retries))
        self._owns_http = http_client is None
        self._http = http_client or httpx.Client(base_url=self.base_url, timeout=timeout)
        self.containers = _Containers(self)
        self.documents = _Documents(self)
        self.memories = _Memories(self)

    # -- the four verbs most code needs ---------------------------------------------------

    def add(
        self,
        content: str | None = None,
        *,
        container: str,
        url: str | None = None,
        title: str = "",
        metadata: dict | None = None,
        custom_id: str = "",
    ) -> dict:
        """Hand a document (its text, or a public ``url`` to fetch) to a container. Returns at
        once with ``status: queued`` and a ``document_id``; the container learns it in the
        background — ``documents.get(id)["learned"]`` turns true when it has. The same
        ``custom_id`` again is a no-op, so retries are safe."""
        body: dict[str, Any] = {"container": container, "title": title, "custom_id": custom_id}
        if content is not None:
            body["content"] = content
        if url is not None:
            body["url"] = url
        if metadata is not None:
            body["metadata"] = metadata
        return self._request("POST", "/v1/documents", json=body)

    def search(self, q: str, *, container: str | None = None, limit: int | None = None) -> dict:
        """Passages the containers hold on ``q``, most relevant first, each naming its
        container. ``container`` omitted searches every container in reach. ``limit`` is how
        many passages you get in all, not per container (1-50): a fan-out splits that budget,
        taking each container's best before any container's second, and left unset it covers
        every container in reach so none goes unheard. Retrieval,
        not an answer — ``ask`` is the agent's answer. ``containers[]`` in the result marks
        any container that could not answer yet (still waking)."""
        body: dict[str, Any] = {"q": q}
        if container is not None:
            body["container"] = container
        if limit is not None:
            body["limit"] = limit
        return self._request("POST", "/v1/search", json=body)

    def profile(self, q: str | None = None) -> dict:
        """Who the user is: ``static`` (standing facts), ``dynamic`` (the most recently
        changed facts) and, with ``q``, ``results`` relevant to the topic. Needs a key minted
        with the profile tick."""
        return self._request("GET", "/v1/profile", params={"q": q} if q else None)

    def ask(self, message: str, *, model: str | None = None) -> dict:
        """The exposed agent's answer to ``message`` (an agent-endpoint credential)."""
        body: dict[str, Any] = {"message": message}
        if model is not None:
            body["model"] = model
        return self._request("POST", "/v1/ask", json=body)

    def rules(self) -> dict:
        """The user's standing rules for how their memory is used by this credential."""
        return self._request("GET", "/v1/rules")

    # -- plumbing -------------------------------------------------------------------------

    def close(self) -> None:
        if self._owns_http:
            self._http.close()

    def __enter__(self) -> Membase:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def _request(
        self,
        method: str,
        path: str,
        *,
        json: dict | None = None,
        params: dict | None = None,
    ) -> Any:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json",
            "User-Agent": f"membase-ai-python/{__version__}",
        }
        attempt = 0
        while True:
            try:
                r = self._http.request(method, path, json=json, params=params, headers=headers)
            except httpx.TimeoutException as e:
                if attempt < self.max_retries:
                    attempt += 1
                    time.sleep(_backoff(attempt))
                    continue
                raise APITimeoutError(f"{method} {path} timed out") from e
            except httpx.HTTPError as e:
                if attempt < self.max_retries:
                    attempt += 1
                    time.sleep(_backoff(attempt))
                    continue
                raise APIConnectionError(f"{method} {path}: {e}") from e
            if 200 <= r.status_code < 300:
                return r.json() if r.content else None
            if (
                r.status_code in _RETRY_STATUSES or r.status_code >= 500
            ) and attempt < self.max_retries:
                attempt += 1
                time.sleep(_backoff(attempt, r.headers.get("Retry-After")))
                continue
            try:
                body = r.json()
            except ValueError:
                body = {"error": {"message": r.text}}
            raise error_for(r.status_code, body)


def _backoff(attempt: int, retry_after: str | None = None) -> float:
    if retry_after:
        try:
            return min(float(retry_after), 30.0)
        except ValueError:
            pass
    return min(0.5 * (2 ** (attempt - 1)), 8.0) * (0.5 + random.random())


class _Containers:
    def __init__(self, client: Membase) -> None:
        self._c = client

    def list(self) -> dict:
        """The containers this key may use — every one, for the account's owner."""
        return self._c._request("GET", "/v1/containers")


class _Documents:
    def __init__(self, client: Membase) -> None:
        self._c = client

    def list(self, *, container: str | None = None) -> dict:
        """The documents the containers in reach have read, newest first, each with
        ``learned``."""
        return self._c._request(
            "GET", "/v1/documents", params={"container": container} if container else None
        )

    def get(self, document_id: str) -> dict:
        """One document, with whether its container has learned it yet."""
        return self._c._request("GET", f"/v1/documents/{document_id}")

    def delete(self, document_id: str, *, confirm: bool = False) -> dict:
        """Remove one document everywhere (the file goes to the Files trash). Needs Full
        access and ``confirm=True``; without it the answer is ``status:
        confirmation_required`` with a ``how`` sentence to relay, not an error."""
        return self._c._request(
            "DELETE", f"/v1/documents/{document_id}", params={"confirm": _flag(confirm)}
        )


class _Memories:
    def __init__(self, client: Membase) -> None:
        self._c = client

    def add(
        self,
        content: str,
        *,
        container: str | None = None,
        static: bool = False,
        title: str = "",
    ) -> dict:
        """Save one fact. ``static=True`` is a standing fact about the user and goes to their
        profile; otherwise a note the container reads. ``container`` may be omitted when
        exactly one is in reach."""
        body: dict[str, Any] = {"content": content, "static": static, "title": title}
        if container is not None:
            body["container"] = container
        return self._c._request("POST", "/v1/memories", json=body)

    def forget(
        self, memory_id: str, *, container: str | None = None, confirm: bool = False
    ) -> dict:
        """Forget one learned fact. Same confirmation rule as ``documents.delete``."""
        params: dict[str, Any] = {"confirm": _flag(confirm)}
        if container is not None:
            params["container"] = container
        return self._c._request("DELETE", f"/v1/memories/{memory_id}", params=params)


def _flag(v: bool) -> str:
    return "true" if v else "false"
