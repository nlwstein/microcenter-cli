"""mcp_entry.py must never crash with a raw ModuleNotFoundError traceback --
it's the actual `mcenter-mcp` console script, which gets installed regardless
of whether the `mcp` extra is present (entry points can't be conditional on
an optional dependency)."""

from __future__ import annotations

import builtins
import sys

import pytest

from microcenter_cli import mcp_entry


def test_missing_mcp_extra_gives_a_clean_error(monkeypatch, capsys):
    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "mcp" or name.startswith("mcp."):
            raise ImportError(f"No module named '{name}'")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    # Force a real re-import: if microcenter_cli.mcp_server (or mcp itself) is
    # already cached in sys.modules from another test importing it first, `from
    # .mcp_server import main` would just hit the cache and never call
    # __import__ at all, silently not exercising the failure path.
    for mod_name in list(sys.modules):
        if mod_name == "mcp" or mod_name.startswith(("mcp.", "microcenter_cli.mcp_server")):
            monkeypatch.delitem(sys.modules, mod_name, raising=False)

    with pytest.raises(SystemExit) as exc_info:
        mcp_entry.main()

    assert exc_info.value.code == 1
    err = capsys.readouterr().err
    assert "MCP support isn't installed" in err
    assert "Traceback" not in err
