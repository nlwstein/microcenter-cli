from __future__ import annotations

from urllib.parse import quote_plus

SEARCH_URL = "https://www.microcenter.com/search/search_results.aspx"


def search_url(query: str, store_id: str, page: int = 1, category_n: str | None = None) -> str:
    params = [f"Ntt={quote_plus(query)}", "NTK=all", f"page={page}", f"storeid={store_id}"]
    if category_n:
        params.insert(0, f"N={category_n}")
    return f"{SEARCH_URL}?{'&'.join(params)}"


def product_url(product_id: str) -> str:
    # Unverified: assumed (common ecommerce pattern) that Micro Center 301s a
    # bare /product/<id>/ to the canonical slugged URL. Recalibrate with
    # `mcenter debug fetch` against a real product id if this turns out wrong —
    # the client already follows redirects either way.
    return f"https://www.microcenter.com/product/{product_id}/"
