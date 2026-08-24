from __future__ import annotations

from urllib.parse import quote, quote_plus

SEARCH_URL = "https://www.microcenter.com/search/search_results.aspx"

# The only values the site's own "Items per page" dropdown offers (see
# parser.py's docstring for where this was observed). Passing anything else
# isn't known to error, but there's no evidence it's honored either.
VALID_RESULTS_PER_PAGE = (24, 48, 96)

# Verified live (mcenter debug fetch against a real search page, grepped for
# sortby= values in the site's own "Sort by" dropdown links) -- these are real,
# not guessed. Maps a friendly CLI/MCP name to the site's own query value.
SORT_OPTIONS: dict[str, str] = {
    "match": "match",  # site default -- relevance
    "rating": "rating",
    "reviews": "numreviews",
    "price-low": "pricelow",
    "price-high": "pricehigh",
    "newest": "newest",
}


def search_url(
    query: str,
    store_id: str,
    page: int = 1,
    category_n: str | None = None,
    rpp: int | None = None,
    sort: str | None = None,
) -> str:
    params = [
        f"Ntt={quote_plus(query)}",
        "NTK=all",
        f"page={page}",
        f"storeid={quote_plus(store_id)}",
    ]
    if category_n:
        params.insert(0, f"N={quote_plus(category_n)}")
    if rpp:
        params.append(f"rpp={rpp}")
    if sort:
        sortby = SORT_OPTIONS.get(sort)
        if not sortby:
            raise ValueError(f"unknown sort '{sort}' -- valid: {', '.join(SORT_OPTIONS)}")
        params.append(f"sortby={sortby}")
    return f"{SEARCH_URL}?{'&'.join(params)}"


def product_url(product_id: str) -> str:
    # Verified against a real product page (mcenter debug fetch): Micro Center
    # serves the page for /product/<id>/<anything>, matching by id alone and
    # ignoring the slug text -- but a bare /product/<id>/ with no slug segment at
    # all 404s. So a throwaway slug segment is required, not optional.
    return f"https://www.microcenter.com/product/{quote(product_id, safe='')}/product"
