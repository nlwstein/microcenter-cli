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
