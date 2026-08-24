"""Client-side result filtering. Deliberately client-side, not another URL/N=
facet param: the one time we tried to filter server-side via a guessed category
N= code, it silently returned the wrong category (see parser.py / README's Known
Limitations). Filtering on fields we've already parsed from a real response can't
have that failure mode -- worst case it filters nothing, it can't lie about what
category something is in.
"""

from __future__ import annotations

from dataclasses import dataclass

from .models import SearchResult


def is_in_stock(result: SearchResult) -> bool:
    """Best-effort read of the raw stock_text ("25+ IN STOCK at Cambridge Store",
    "SOLD OUT at Cambridge Store", "NOT CARRIED at Cambridge Store"). Missing/
    unparseable stock_text is treated as NOT in stock -- for an --in-stock-only
    filter, "unknown" should drop the result, not silently keep it."""
    return bool(result.stock_text and "IN STOCK" in result.stock_text.upper())


@dataclass
class FilterSpec:
    in_stock_only: bool = False
    max_price: float | None = None
    min_price: float | None = None
    exclude: tuple[str, ...] = ()  # case-insensitive substrings matched against name
    category_contains: str | None = None  # case-insensitive substring against category

    @property
    def is_noop(self) -> bool:
        return not (
            self.in_stock_only
            or self.max_price is not None
            or self.min_price is not None
            or self.exclude
            or self.category_contains
        )


def filter_results(results: list[SearchResult], spec: FilterSpec) -> list[SearchResult]:
    if spec.is_noop:
        return results

    out = []
    exclude_lower = [term.lower() for term in spec.exclude if term.strip()]
    category_needle = spec.category_contains.lower() if spec.category_contains else None

    for r in results:
        if spec.in_stock_only and not is_in_stock(r):
            continue
        if spec.max_price is not None and (r.price is None or r.price > spec.max_price):
            continue
        if spec.min_price is not None and (r.price is None or r.price < spec.min_price):
            continue
        if exclude_lower and any(term in r.name.lower() for term in exclude_lower):
            continue
        if category_needle and category_needle not in (r.category or "").lower():
            continue
        out.append(r)

    return out
