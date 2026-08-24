"""Tests for cli.main()'s own exception-translation wrapper -- distinct from
test_cli.py, which exercises Click's own error handling via CliRunner. main()
is a thin function calling sys.exit directly, so it's tested by invoking it
directly and catching SystemExit, with sys.argv patched (argv[0] is ignored
by Click but conventionally present) and capsys catching the printed output.
"""

from __future__ import annotations

import sys

import pytest

from microcenter_cli import cli as cli_module
from microcenter_cli.client import MicroCenterBlockedError, MicroCenterNotFoundError
from microcenter_cli.config import Config
from microcenter_cli.context import Ctx


class RaisingClient:
    def __init__(self, exc: Exception):
        self._exc = exc

    def search_page(self, *a, **kw):
        raise self._exc

    product = search_page


@pytest.mark.parametrize(
    "exc",
    [
        MicroCenterBlockedError("no valid session. Run `mcenter session interactive`."),
        MicroCenterNotFoundError("no product with id '999999'"),
    ],
)
def test_main_translates_microcenter_errors_cleanly(monkeypatch, capsys, exc):
    monkeypatch.setattr(cli_module, "load_config", lambda: Config())
    monkeypatch.setattr(Ctx, "client", lambda self: RaisingClient(exc))
    monkeypatch.setattr(sys, "argv", ["mcenter", "search", "widget", "--store", "121"])

    with pytest.raises(SystemExit) as exc_info:
        cli_module.main()

    assert exc_info.value.code == 1
    err = capsys.readouterr().err
    assert str(exc) in err
    assert "Traceback" not in err
