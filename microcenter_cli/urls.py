from __future__ import annotations

from urllib.parse import quote, quote_plus

SEARCH_URL = "https://www.microcenter.com/search/search_results.aspx"

# The only values the site's own "Items per page" dropdown offers (see
# parser.py's docstring for where this was observed). Passing anything else
# isn't known to error, but there's no evidence it's honored either.
VALID_RESULTS_PER_PAGE = (24, 48, 96)


def search_url(
    query: str,
    store_id: str,
    page: int = 1,
    category_n: str | None = None,
    rpp: int | None = None,
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
    return f"{SEARCH_URL}?{'&'.join(params)}"


def product_url(product_id: str) -> str:
    # Verified against a real product page (mcenter debug fetch): Micro Center
    # serves the page for /product/<id>/<anything>, matching by id alone and
    # ignoring the slug text -- but a bare /product/<id>/ with no slug segment at
    # all 404s. So a throwaway slug segment is required, not optional.
    return f"https://www.microcenter.com/product/{quote(product_id, safe='')}/product"
