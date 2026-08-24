"""Thin, dependency-free entry point for the `mcenter-mcp` console script.

Why this file exists rather than pointing the entry point straight at
mcp_server:main: pyproject.toml's [project.scripts] entry points can't be
conditional on an optional dependency being installed -- `mcenter-mcp` gets
registered (and its shim script created) regardless of whether `.[mcp]` was
requested. mcp_server.py imports `mcp` at module level (its @mcp.tool()
decorators need a real MCPServer instance to exist at import time), so
without this wrapper, running `mcenter-mcp` after a plain `pip install
microcenter-cli` crashed with a raw ModuleNotFoundError traceback -- found
live, testing the actual installed package, not hypothetically. This module
has zero dependency on `mcp` itself, so it always imports fine; the real
import only happens inside the try below.
"""

from __future__ import annotations

import sys


def main() -> None:
    try:
        from .mcp_server import main as _main
    except ImportError:
        print(
            "error: MCP support isn't installed. Run:\n"
            '  uv tool install --editable ".[mcp]"   (from a local checkout), or\n'
            '  pip install "microcenter-cli[mcp]"    (from PyPI)',
            file=sys.stderr,
        )
        raise SystemExit(1) from None
    _main()


if __name__ == "__main__":
    main()
