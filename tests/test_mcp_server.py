"""Offline tests: tool registration/schema only, no network, no session
required. Live agent behavior against real data was validated by hand (see
CLAUDE.md) -- that needs a real session and isn't something CI can run."""

from __future__ import annotations

import asyncio

from microcenter_cli.mcp_server import mcp


def test_expected_tools_are_registered():
    tools = asyncio.run(mcp.list_tools())
    names = {t.name for t in tools}
    assert names == {"search_products", "get_product", "find_store", "list_stores"}


def test_tools_have_descriptions():
    tools = asyncio.run(mcp.list_tools())
    for tool in tools:
        assert tool.description, f"{tool.name} has no description (agents need this)"


def test_find_store_and_list_stores_work_without_a_session():
    """These two don't touch MicroCenterClient at all -- pure local lookups,
    should work with no session configured."""
    from microcenter_cli.mcp_server import find_store, list_stores

    assert find_store("cambridge")["id"] == "121"
    assert len(list_stores()) > 0
