"""Missing pieces are named before anything starts: Python version, engine, MCP library."""

from __future__ import annotations

import pytest

from membase import Membase, MissingDependencyError, cli, requirements
from membase.requirements import INSTALL_LOCAL, local_unavailable, mcp_unavailable


def test_local_needs_python_312():
    reason = local_unavailable((3, 11), find=lambda name: object())
    assert "Python 3.12" in reason and "Python 3.11" in reason and "hosted API" in reason


def test_local_needs_the_engine():
    assert INSTALL_LOCAL in local_unavailable((3, 12), find=lambda name: None)
    assert local_unavailable((3, 13), find=lambda name: object()) is None


def test_mcp_needs_the_library_and_points_hosted_users_at_the_url():
    reason = mcp_unavailable(find=lambda name: None)
    assert INSTALL_LOCAL in reason and requirements.HOSTED_MCP_URL in reason
    assert mcp_unavailable(find=lambda name: object()) is None


@pytest.fixture
def no_engine(monkeypatch):
    monkeypatch.setattr(requirements, "local_unavailable", lambda: f"local memory needs the engine: {INSTALL_LOCAL}")


def test_a_local_client_fails_at_construction(no_engine, tmp_path):
    with pytest.raises(MissingDependencyError, match="unibaseio-membase\\[local\\]"):
        Membase(local=tmp_path)


def test_the_cli_says_what_to_install_instead_of_a_traceback(no_engine, tmp_path, capsys, monkeypatch):
    assert cli.main(["--local", "serve"]) == 1
    assert INSTALL_LOCAL in capsys.readouterr().err
    assert cli.main(["serve"]) == 1
    assert INSTALL_LOCAL in capsys.readouterr().err
    assert cli.main(["--store", str(tmp_path), "search", "x"]) == 1
    assert INSTALL_LOCAL in capsys.readouterr().err
    monkeypatch.setattr(requirements, "mcp_unavailable", lambda: f"membase mcp needs the MCP library: {INSTALL_LOCAL}")
    monkeypatch.delenv("MEMBASE_API_KEY", raising=False)
    assert cli.main(["mcp"]) == 1
    assert "MCP library" in capsys.readouterr().err


def test_local_is_a_flag_and_store_picks_the_directory():
    p = cli._parser()
    a = p.parse_args(["--local", "serve"])
    assert a.local is True and a.cmd == "serve" and a.store is None
    a = p.parse_args(["--local", "mcp"])
    assert a.cmd == "mcp"
    a = p.parse_args(["--store", "/tmp/x", "search", "q"])
    assert a.store == "/tmp/x" and a.cmd == "search"
