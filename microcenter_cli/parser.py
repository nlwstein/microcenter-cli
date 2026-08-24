"""HTML parsing for search/category listing pages and product detail pages.

Selectors below are transcribed from a known-good historical scraper
(github.com/justingee193/microcenter-scraper) plus the JS-var extraction pattern
documented by the Level1Techs "Automated Microcenter stock checking" thread.
Micro Center is a live commercial site — these WILL drift over time. If parsing
starts coming back empty, use `mcenter debug fetch <url> --out page.html` to
capture real HTML and recalibrate the selectors here; nothing else in the
library needs to change.
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


def parse_search_results(html: str, store_id: str) -> list[SearchResult]:
    soup = BeautifulSoup(html, "html.parser")
    results: list[SearchResult] = []

    for container in soup.find_all("div", class_="detail_wrapper"):
        anchor = container.find("a")
        if anchor is None:
            continue

        stock_el = container.find("div", class_="stock")
        rating_el = container.find("div", class_="ratingstars")
        offer_el = container.find("div", class_="highlight")

        results.append(
            SearchResult(
                product_id=(anchor.get("data-id") or "").strip(),
                name=(anchor.get("data-name") or "").strip(),
                price=_float_or_none(anchor.get("data-price")),
                category=(anchor.get("data-category") or "").strip() or None,
                brand=(anchor.get("data-brand") or "").strip() or None,
                stock_text=stock_el.get_text(strip=True) if stock_el else None,
                rating=(rating_el.find("img") or {}).get("alt")
                if rating_el and rating_el.find("img")
                else None,
                reviews=rating_el.find("span").get_text(strip=True)
                if rating_el and rating_el.find("span")
                else None,
                offer=offer_el.get_text(strip=True) if offer_el else None,
                store_id=store_id,
            )
        )

    return results


# Product pages embed state as inline JS assignments rather than a JSON blob, e.g.
# `var inStock = true;` / `'inStock':'True'` / `productPrice = 329.99;` depending on
# the page template in use. Match loosely across quote styles and separators.
_VAR_PATTERNS = {
    "in_stock": re.compile(r"""inStock['"]?\s*[:=]\s*['"]?(true|false|True|False)""", re.IGNORECASE),
    "price": re.compile(r"""productPrice['"]?\s*[:=]\s*['"]?([\d]+\.?[\d]*)"""),
    "sku": re.compile(r"""(?:sku|productSKU)['"]?\s*[:=]\s*['"]([A-Za-z0-9\-]+)['"]"""),
}


def parse_product_page(html: str, product_id: str, store_id: str) -> ProductDetail:
    soup = BeautifulSoup(html, "html.parser")

    title_tag = soup.find("title")
    name = title_tag.get_text(strip=True) if title_tag else None
    if name and " | Micro Center" in name:
        name = name.split(" | Micro Center")[0].strip()

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
