from __future__ import annotations

from urllib.parse import quote_plus

SEARCH_URL = "https://www.microcenter.com/search/search_results.aspx"


def search_url(query: str, store_id: str, page: int = 1, category_n: str | None = None) -> str:
    params = [f"Ntt={quote_plus(query)}", "NTK=all", f"page={page}", f"storeid={store_id}"]
    if category_n:
        params.insert(0, f"N={category_n}")
    return f"{SEARCH_URL}?{'&'.join(params)}"


def product_url(product_id: str) -> str:
    # Verified against a real product page (mcenter debug fetch): Micro Center
    # serves the page for /product/<id>/<anything>, matching by id alone and
    # ignoring the slug text -- but a bare /product/<id>/ with no slug segment at
    # all 404s. So a throwaway slug segment is required, not optional.
    return f"https://www.microcenter.com/product/{product_id}/product"
