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
from .filters import FilterSpec, filter_results
from .urls import SORT_OPTIONS

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
def search_products(
    query: str,
    store_id: str,
    page: int = 1,
    sort: str | None = None,
    in_stock_only: bool = False,
    max_price: float | None = None,
    min_price: float | None = None,
    exclude: list[str] | None = None,
    category_contains: str | None = None,
) -> dict:
    """Search Micro Center's catalog for products matching a query, with
    price/stock at a specific store. Returns one page of results plus
    pagination info (total_items, total_pages, has_next). Use find_store first
    if you only have a city/state name, not a store id.

    sort: one of "match" (default/relevance), "rating", "reviews", "price-low",
    "price-high", "newest" -- verified against the site's own sort options, not
    guessed. Changes which items land on this page, not just their order.

    The filter params (in_stock_only, max_price, min_price, exclude,
    category_contains) are applied client-side to what the page actually
    returned -- useful for pruning noise a plain keyword search picks up (e.g.
    exclude=["laptop", "gaming pc"] to keep only standalone components), and
    for catching things a price-only filter can silently get wrong (e.g. a
    laptop SO-DIMM ranking as "cheapest RAM" ahead of a desktop-compatible
    module -- check category_contains/name yourself when it matters).
    """
    if sort is not None and sort not in SORT_OPTIONS:
        return {"error": f"unknown sort '{sort}' -- valid: {', '.join(SORT_OPTIONS)}"}

    try:
        result = _client().search_page(query, store_id, page=page, sort=sort)
    except MicroCenterError as exc:
        return {"error": str(exc)}

    spec = FilterSpec(
        in_stock_only=in_stock_only,
        max_price=max_price,
        min_price=min_price,
        exclude=tuple(exclude or ()),
        category_contains=category_contains,
    )
    results = filter_results(result.results, spec)

    return {
        "page": result.page,
        "total_items": result.total_items,
        "total_pages": result.total_pages,
        "has_next": result.has_next,
        "results_before_filter": len(result.results),
        "results": [r.__dict__ for r in results],
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
def get_products(product_ids: list[str], store_id: str) -> dict:
    """Batch version of get_product -- verify a whole shortlist (e.g. from
    search_products) in one call instead of one per item. One bad id doesn't
    fail the rest; check each entry's "error" field.

    Returns a dict wrapping the list (not a bare list): the MCP framework
    serializes a bare list[...] return as one content block *per item*
    instead of a single JSON array, so a client doing the natural
    json.loads(result.content[0].text) would silently only see the first
    result. Wrapping in {"results": [...]} keeps this to one block, one
    json.loads(), the whole list -- confirmed against a real MCP client
    session, not just by reading the framework's source.
    """
    results = _client().products(product_ids, store_id)
    return {
        "results": [
            {"product_id": r.product_id, "detail": r.detail.__dict__ if r.detail else None, "error": r.error}
            for r in results
        ]
    }


@mcp.tool()
def find_store(query: str) -> dict:
    """Look up a Micro Center store id by city/state name, e.g. 'cambridge'.
    Best-effort/incomplete list -- see list_stores for everything known."""
    match = store_table.find(query)
    if match is None:
        return {"error": f"no known store matching '{query}'"}
    return {"id": match.id, "state": match.state, "city": match.city}


@mcp.tool()
def list_stores() -> dict:
    """List all known Micro Center store ids (best-effort, may be incomplete).

    Returns {"stores": [...]}, not a bare list -- see get_products' docstring
    for why (a bare list return serializes as one content block per item).
    """
    return {
        "stores": [{"id": s.id, "state": s.state, "city": s.city} for s in store_table.STORES.values()]
    }


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
