"""MCP server exposing catalog search and per-store price/stock as agent tools.

Thin wrapper over MicroCenterClient -- no logic lives here beyond translating
between MCP tool calls and the same library the CLI uses. Requires a session
already set up via `mcenter session interactive` (see README); an agent cannot
bootstrap that itself, same constraint as the CLI, and errors say so.

Install: `uv tool install --editable ".[mcp]"` (or `pip install ".[mcp]"`)
Run:     `mcenter-mcp` (stdio transport, the standard way an MCP client launches
          a local server -- point your client's MCP config at this command)
"""

from __future__ import annotations

from mcp.server.mcpserver import MCPServer

from . import stores as store_table
from .client import MicroCenterClient, MicroCenterError
from .config import load_config

mcp = MCPServer(
    name="microcenter",
    title="Micro Center Catalog",
    description=(
        "Search Micro Center's product catalog and check exact price/in-stock "
        "status at a specific store. Read-only -- does not place orders."
    ),
    version="0.2.0",
)


def _client() -> MicroCenterClient:
    return MicroCenterClient(load_config())


@mcp.tool()
def search_products(query: str, store_id: str, page: int = 1) -> dict:
    """Search Micro Center's catalog for products matching a query, with
    price/stock at a specific store. Returns one page of results plus
    pagination info (total_items, total_pages, has_next). Use find_store first
    if you only have a city/state name, not a store id."""
    try:
        result = _client().search_page(query, store_id, page=page)
    except MicroCenterError as exc:
        return {"error": str(exc)}
    return {
        "page": result.page,
        "total_items": result.total_items,
        "total_pages": result.total_pages,
        "has_next": result.has_next,
        "results": [r.__dict__ for r in result.results],
    }


@mcp.tool()
def get_product(product_id: str, store_id: str) -> dict:
    """Get the authoritative price and in-stock status for one specific Micro
    Center product id at one specific store. More precise than the stock_text
    returned by search_products, which is a coarser signal -- use this to
    confirm before reporting a final answer."""
    try:
        detail = _client().product(product_id, store_id)
    except MicroCenterError as exc:
        return {"error": str(exc)}
    return detail.__dict__


@mcp.tool()
def find_store(query: str) -> dict:
    """Look up a Micro Center store id by city/state name, e.g. 'cambridge'.
    Best-effort/incomplete list -- see list_stores for everything known."""
    match = store_table.find(query)
    if match is None:
        return {"error": f"no known store matching '{query}'"}
    return {"id": match.id, "state": match.state, "city": match.city}


@mcp.tool()
def list_stores() -> list[dict]:
    """List all known Micro Center store ids (best-effort, may be incomplete)."""
    return [{"id": s.id, "state": s.state, "city": s.city} for s in store_table.STORES.values()]


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
