"""Static fallback store directory.

Micro Center has no documented store-list API. This table is transcribed from a
known-good third-party scraper (github.com/justingee193/microcenter-scraper) and is
NOT exhaustive or guaranteed current — Micro Center has ~25 stores and opens/closes
locations occasionally. Treat as a fallback for the common case (mapping a name/state
to a storeid) and prefer `mcenter stores refresh` (once implemented against a real
session) or the storeid printed on an order confirmation / the site's own store
picker when accuracy matters.

storeid is the value used as both the `storeid` query param and the `storeSelected`
cookie on microcenter.com.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Store:
    id: str
    state: str
    city: str

    @property
    def label(self) -> str:
        return f"{self.state} - {self.city}"


STORES: dict[str, Store] = {
    s.id: s
    for s in [
        Store("101", "CA", "Tustin"),
        Store("181", "CO", "Denver"),
        Store("065", "GA", "Duluth"),
        Store("041", "GA", "Marietta"),
        Store("151", "IL", "Chicago"),
        Store("025", "IL", "Westmont"),
        Store("191", "KS", "Overland Park"),
        Store("121", "MA", "Cambridge"),
        Store("085", "MD", "Rockville"),
        Store("125", "MD", "Parkville"),
        Store("055", "MI", "Madison Heights"),
        Store("045", "MN", "St. Louis Park"),
        Store("095", "MO", "Brentwood"),
        Store("075", "NJ", "North Jersey"),
        Store("171", "NY", "Westbury"),
        Store("115", "NY", "Brooklyn"),
        Store("145", "NY", "Flushing"),
        Store("105", "NY", "Yonkers"),
        Store("141", "OH", "Columbus"),
        Store("051", "OH", "Mayfield Heights"),
        Store("071", "OH", "Sharonville"),
        Store("061", "PA", "St. Davids"),
        Store("155", "TX", "Houston"),
        Store("131", "TX", "Dallas"),
        Store("081", "VA", "Fairfax"),
    ]
}


def find(id_or_name: str) -> Store | None:
    """Look up by storeid, or a case-insensitive substring of 'STATE - City'."""
    if id_or_name in STORES:
        return STORES[id_or_name]
    needle = id_or_name.lower()
    for store in STORES.values():
        if needle in store.label.lower():
            return store
    return None
