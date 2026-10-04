"""``membase serve``: the local engine over HTTP, on the same routes as the hosted API.

Point any Membase client at it (``new Membase({baseURL: "http://127.0.0.1:8787"})`` in
TypeScript) to use local memory from another language or process. It binds to localhost by
default; with ``MEMBASE_LOCAL_TOKEN`` set, requests must carry it as their bearer.
"""

from __future__ import annotations

import json
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qsl, urlparse

from .backend import LocalBackend
from .routes import dispatch, error_body


def make_server(host: str = "127.0.0.1", port: int = 8787, root: str | None = None,
                token: str | None = None) -> ThreadingHTTPServer:
    from ..requirements import require_local

    require_local()
    backend = LocalBackend(root)
    token = token if token is not None else (os.environ.get("MEMBASE_LOCAL_TOKEN") or None)
    lock = threading.Lock()

    class Handler(BaseHTTPRequestHandler):
        server_version = "membase-local"

        def log_message(self, fmt: str, *args: object) -> None:  # quiet by default
            return

        def _answer(self, status: int, payload: object) -> None:
            data = json.dumps(payload).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def _handle(self) -> None:
            if token and self.headers.get("Authorization", "") != f"Bearer {token}":
                self._answer(401, error_body(401, "unauthenticated", "bearer token required"))
                return
            url = urlparse(self.path)
            length = int(self.headers.get("Content-Length") or 0)
            try:
                body = json.loads(self.rfile.read(length)) if length else None
            except json.JSONDecodeError:
                self._answer(400, error_body(400, "bad_request", "body is not JSON"))
                return
            with lock if self.command != "GET" else _nolock:
                status, payload = dispatch(backend, self.command, url.path, dict(parse_qsl(url.query)), body)
            self._answer(status, payload)

        do_GET = do_POST = do_DELETE = _handle

    httpd = ThreadingHTTPServer((host, port), Handler)
    httpd.backend = backend  # type: ignore[attr-defined]
    return httpd


class _NoLock:
    def __enter__(self) -> None:
        return None

    def __exit__(self, *exc: object) -> None:
        return None


_nolock = _NoLock()


def serve(host: str = "127.0.0.1", port: int = 8787, root: str | None = None) -> None:
    httpd = make_server(host, port, root)
    print(f"membase: local memory on http://{host}:{port}/v1 (store {httpd.backend.root})", flush=True)  # type: ignore[attr-defined]
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.backend.close()  # type: ignore[attr-defined]
