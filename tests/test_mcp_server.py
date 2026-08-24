"""Offline tests: tool registration/schema/serialization only, no network, no
session required. Live agent behavior against real data was validated by hand
(see CLAUDE.md) -- that needs a real session and isn't something CI can run.
"""

from __future__ import annotations

import asyncio
import json

from microcenter_cli.mcp_server import mcp


def test_expected_tools_are_registered():
    tools = asyncio.run(mcp.list_tools())
    names = {t.name for t in tools}
    assert names == {
        "search_products",
        "get_product",
        "get_products",
        "find_store",
        "list_stores",
    }


def test_tools_have_descriptions():
    tools = asyncio.run(mcp.list_tools())
    for tool in tools:
        assert tool.description, f"{tool.name} has no description (agents need this)"


def test_find_store_and_list_stores_work_without_a_session():
    """These two don't touch MicroCenterClient at all -- pure local lookups,
    should work with no session configured."""
    from microcenter_cli.mcp_server import find_store, list_stores

    assert find_store("cambridge")["id"] == "121"
    assert len(list_stores()["stores"]) > 0


def test_list_returning_tools_serialize_as_a_single_content_block():
    """Regression test for a real bug found live: a tool returning a bare
    list[dict] (the original get_products/list_stores shape) gets serialized
    by the MCP framework as one content block *per list item*, not one block
    containing the JSON array -- so a client doing the natural
    json.loads(result.content[0].text) silently only sees the first item.
    Every tool here must return a dict (wrapping any list inside a key), and
    this checks the actual serialized shape via call_tool(), not just the
    Python-level return type -- that's what caught the bug in the first
    place, reading the source wouldn't have.
    """
    result = asyncio.run(mcp.call_tool("list_stores", {}))
    assert len(result.content) == 1
    parsed = json.loads(result.content[0].text)
    assert isinstance(parsed, dict)
    assert isinstance(parsed["stores"], list)
    assert len(parsed["stores"]) > 1  # would trivially pass at 1 even if broken
