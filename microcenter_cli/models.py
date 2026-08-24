from __future__ import annotations

from dataclasses import dataclass


@dataclass
class SearchResult:
    """One product tile from a search/category listing page."""

    product_id: str
    name: str
    price: float | None
    category: str | None
    brand: str | None
    stock_text: str | None  # e.g. "In stock", "Sold out", raw as shown on the tile
    rating: str | None
    reviews: str | None
    offer: str | None
    store_id: str

    @property
    def url(self) -> str:
        return f"https://www.microcenter.com/product/{self.product_id}/"


@dataclass
class ProductDetail:
    """Per-store stock + price pulled from a single product page."""

    product_id: str
    sku: str | None
    name: str | None
    price: float | None
    in_stock: bool | None
    store_id: str


@dataclass
class ProductLookupResult:
    """One entry in a batch product() lookup -- exactly one of detail/error is
    set, so one bad id in a batch doesn't take down the others."""

    product_id: str
    detail: ProductDetail | None = None
    error: str | None = None


@dataclass
class SearchPage:
    """One page of search/category results, plus pagination metadata parsed from
    the page itself (see parser.parse_search_meta) -- not guessed from request
    params, since rpp/page can be silently clamped by the site."""

    results: list[SearchResult]
    page: int
    items_per_page: int | None
    total_items: int | None
    has_next: bool

    @property
    def total_pages(self) -> int | None:
        if self.total_items is None or not self.items_per_page:
            return None
        return -(-self.total_items // self.items_per_page)  # ceil div
