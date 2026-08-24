"""HTML parsing for search/category listing pages and product detail pages.

Selectors calibrated 2026-08 against real captured pages (via `mcenter debug
fetch`), replacing an earlier best-guess based on a years-old scraper whose
selectors had drifted (it assumed the anchor with the data-id/data-name/etc.
attributes was the *first* `<a>` in a `div.detail_wrapper`, and that stock/price
lived inside that same div -- neither is true anymore).

Current per-product-tile shape on a search/category page:

    <div class="result_right">
      <div class="details">
        <div class="detail_wrapper">
          <p class="sku">SKU: 815944</p>
          ...
          <div class="h2">
            <a class="productClickItemV2 ..." data-id="691349" data-name="..."
               data-price="549.99" data-brand="AMD" data-category="..."
               href="/product/691349/...">...</a>
          </div>
        </div>
        <div class="price_wrapper">          <!-- sibling of detail_wrapper, not a child -->
          <div class="stock">
            <span class="inventoryCnt">25 <span class="msgInStock">IN STOCK</span></span>
            <span class="storeName"> at Cambridge Store</span>
          </div>
          <div class="price">...<span itemprop="price">...$549.99</span></div>
        </div>
      </div>
    </div>

`div.result_right` is the reliable per-tile container (one per product, matches
result count); `div.detail_wrapper` alone is not, since it doesn't include price/
stock. Ratings/review counts are loaded client-side via a Bazaarvoice widget and
are not present in the raw HTML at all, so those fields are best-effort/usually
None.

If this drifts again: `mcenter debug fetch <url> --out page.html`, then diff
against the shape above.
"""

from __future__ import annotations

import re

from bs4 import BeautifulSoup

from .models import ProductDetail, SearchResult


def _float_or_none(text: str | None) -> float | None:
    if not text:
        return None
    cleaned = re.sub(r"[^0-9.]", "", text)
    try:
        return float(cleaned) if cleaned else None
    except ValueError:
        return None


def _text_or_none(el) -> str | None:
    if el is None:
        return None
    text = el.get_text(" ", strip=True)
    return text or None


def parse_search_results(html: str, store_id: str) -> list[SearchResult]:
    soup = BeautifulSoup(html, "html.parser")
    results: list[SearchResult] = []

    for container in soup.find_all("div", class_="result_right"):
        anchor = container.find("a", attrs={"data-id": True})
        if anchor is None:
            continue

        results.append(
            SearchResult(
                product_id=(anchor.get("data-id") or "").strip(),
                name=(anchor.get("data-name") or "").strip(),
                price=_float_or_none(anchor.get("data-price")),
                category=(anchor.get("data-category") or "").strip() or None,
                brand=(anchor.get("data-brand") or "").strip() or None,
                stock_text=_text_or_none(container.find("div", class_="stock")),
                rating=None,  # loaded client-side (Bazaarvoice), not in raw HTML
                reviews=None,  # same
                offer=_text_or_none(container.find("div", class_="highlight")),
                store_id=store_id,
            )
        )

    return results


# Product pages embed state as inline JS/JSON-ish assignments, e.g.
# `'inStock':'True'` / `"productPrice":"549.99"` / `"sku": "815944"`. Match loosely
# across quote styles and separators since these vary by field.
_VAR_PATTERNS = {
    "in_stock": re.compile(r"""inStock['"]?\s*[:=]\s*['"]?(true|false)""", re.IGNORECASE),
    "price": re.compile(r"""productPrice['"]?\s*[:=]\s*['"]?([\d]+\.?[\d]*)"""),
    "sku": re.compile(r"""(?:sku|productSKU)['"]?\s*[:=]\s*['"]([A-Za-z0-9\-]+)['"]"""),
}


def parse_product_page(html: str, product_id: str, store_id: str) -> ProductDetail:
    soup = BeautifulSoup(html, "html.parser")

    title_tag = soup.find("title")
    name = title_tag.get_text(strip=True) if title_tag else None
    if name and " - Micro Center" in name:
        name = name.rsplit(" - Micro Center", 1)[0].strip()

    in_stock: bool | None = None
    if m := _VAR_PATTERNS["in_stock"].search(html):
        in_stock = m.group(1).lower() == "true"

    price: float | None = None
    if m := _VAR_PATTERNS["price"].search(html):
        price = _float_or_none(m.group(1))

    sku: str | None = None
    if m := _VAR_PATTERNS["sku"].search(html):
        sku = m.group(1)

    return ProductDetail(
        product_id=product_id,
        sku=sku,
        name=name,
        price=price,
        in_stock=in_stock,
        store_id=store_id,
    )


def looks_like_challenge_page(html: str) -> bool:
    return "Just a moment" in html[:2000]
