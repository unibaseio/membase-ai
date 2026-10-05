"""The local-only commands that used to live in membase-core's CLI: import and agent."""

from __future__ import annotations

import json
import threading

import pytest

pytest.importorskip("membase_core", reason="needs the local extra")

from membase import cli  # noqa: E402
from membase.local.backend import LocalBackend  # noqa: E402


def test_import_scans_directories_and_dry_runs(tmp_path, capsys):
    chats = tmp_path / "chats" / "nested"
    chats.mkdir(parents=True)
    (chats / "a.md").write_text("**User:** I moved to Lisbon.\n**Assistant:** Noted.\n")
    (chats / "notes.bin").write_bytes(b"\x00")
    assert cli.main(["--store", str(tmp_path / "s"), "import", str(tmp_path / "chats"), "--dry-run"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["would_import"] == 1 and out["files"][0]["format"] == "markdown"
    assert not (tmp_path / "s" / "memory.db").exists()


class _FakeEngine:
    def __init__(self) -> None:
        self.calls: list[tuple] = []
        self._lock = threading.RLock()

    def ingest_agent_trace(self, messages, *, agent_id, session_id=None):
        self.calls.append(("ingest", len(messages), agent_id, session_id))
        return {"cases": 1, "skills_added": 1, "status": "extracted"}

    def search_agent(self, q, *, agent_id, kind, top_k):
        self.calls.append(("search", q, agent_id, kind, top_k))
        return {"cases": [], "skills": [{"id": f"{agent_id}_Deploy_fix"}]}

    def list_skills(self, agent_id):
        return [{"id": f"{agent_id}_Deploy_fix"}]

    def save(self) -> None:
        pass


def test_agent_commands(tmp_path, capsys, monkeypatch):
    fake = _FakeEngine()
    monkeypatch.setattr(LocalBackend, "engine", lambda self, cid: (fake, fake._lock))
    trace = tmp_path / "fix-deploy.json"
    trace.write_text(json.dumps({"messages": [{"role": "user", "content": "deploy the hotfix"}]}))
    store = ["--store", str(tmp_path / "s")]
    assert cli.main([*store, "agent", "ingest", str(trace), "--agent", "coder"]) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "extracted"
    assert fake.calls[0] == ("ingest", 1, "coder", "fix-deploy")
    assert cli.main([*store, "agent", "search", "deploy", "--agent", "coder", "--kind", "skills"]) == 0
    assert json.loads(capsys.readouterr().out)["skills"][0]["id"] == "coder_Deploy_fix"
    assert cli.main([*store, "agent", "skills", "--agent", "coder"]) == 0
    assert json.loads(capsys.readouterr().out)["skills"][0]["id"] == "coder_Deploy_fix"


def test_agent_memory_is_local_only(monkeypatch, capsys):
    monkeypatch.setenv("MEMBASE_API_KEY", "mbk_test")
    monkeypatch.delenv("MEMBASE_LOCAL", raising=False)
    with pytest.raises(SystemExit, match="agent memory is local"):
        cli.main(["agent", "skills", "--agent", "coder"])
