"""The TypeScript client against `membase serve`: src/local.test.ts with the server's URL."""

from __future__ import annotations

import os
import shutil
import subprocess
import threading
from pathlib import Path

import pytest

pytest.importorskip("membase_core", reason="needs the local extra")

TS = Path(__file__).resolve().parent.parent / "typescript"


@pytest.mark.skipif(shutil.which("npx") is None or not (TS / "node_modules").is_dir(),
                    reason="needs node and `npm install` in typescript/")
def test_typescript_client_against_local_server(tmp_path):
    from membase.local.server import make_server

    httpd = make_server(port=0, root=str(tmp_path / "store"))
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    try:
        env = {**os.environ, "MEMBASE_LOCAL_BASE_URL": f"http://127.0.0.1:{httpd.server_address[1]}"}
        r = subprocess.run(["npx", "vitest", "run", "src/local.test.ts"], cwd=TS, env=env,
                           capture_output=True, text=True, timeout=300)
        assert r.returncode == 0, r.stdout + r.stderr
        assert "2 passed" in r.stdout, r.stdout
    finally:
        httpd.shutdown()
        httpd.backend.close()
