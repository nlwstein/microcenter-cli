from __future__ import annotations

from microcenter_cli.filters import FilterSpec, filter_results, is_in_stock
from microcenter_cli.models import SearchResult


def _result(**overrides) -> SearchResult:
    defaults = {
        "product_id": "1",
        "name": "Widget",
        "price": 10.0,
        "category": "Widgets",
        "brand": "Acme",
        "stock_text": "5 IN STOCK at Cambridge Store",
        "rating": None,
        "reviews": None,
        "offer": None,
        "store_id": "121",
    }
    defaults.update(overrides)
    return SearchResult(**defaults)


def test_is_in_stock():
    assert is_in_stock(_result(stock_text="25+ IN STOCK at Cambridge Store")) is True
    assert is_in_stock(_result(stock_text="SOLD OUT at Cambridge Store")) is False
    assert is_in_stock(_result(stock_text="NOT CARRIED at Cambridge Store")) is False
    assert is_in_stock(_result(stock_text=None)) is False


def test_noop_spec_returns_input_unchanged():
    results = [_result(), _result(product_id="2")]
    assert filter_results(results, FilterSpec()) == results


def test_in_stock_only():
    results = [
        _result(product_id="a", stock_text="5 IN STOCK at Cambridge Store"),
        _result(product_id="b", stock_text="SOLD OUT at Cambridge Store"),
    ]
    out = filter_results(results, FilterSpec(in_stock_only=True))
    assert [r.product_id for r in out] == ["a"]


def test_max_price_drops_missing_price():
    results = [_result(product_id="a", price=5.0), _result(product_id="b", price=None)]
    out = filter_results(results, FilterSpec(max_price=10.0))
    assert [r.product_id for r in out] == ["a"]


def test_max_and_min_price():
    results = [
        _result(product_id="cheap", price=5.0),
        _result(product_id="mid", price=50.0),
        _result(product_id="expensive", price=500.0),
    ]
    out = filter_results(results, FilterSpec(min_price=10.0, max_price=100.0))
    assert [r.product_id for r in out] == ["mid"]


def test_exclude_terms_case_insensitive():
    results = [
        _result(product_id="a", name="Cool Gaming PC Bundle"),
        _result(product_id="b", name="Cool Motherboard"),
    ]
    out = filter_results(results, FilterSpec(exclude=("GAMING PC",)))
    assert [r.product_id for r in out] == ["b"]


def test_category_contains():
    results = [
        _result(product_id="a", category="Processors/CPUs"),
        _result(product_id="b", category="Laptops/Notebooks"),
        _result(product_id="c", category=None),
    ]
    out = filter_results(results, FilterSpec(category_contains="processor"))
    assert [r.product_id for r in out] == ["a"]


def test_so_dimm_trap_scenario():
    """The exact real-world case that motivated this filter: a laptop SO-DIMM
    ranking as 'cheapest RAM' ahead of a desktop-compatible module."""
    results = [
        _result(product_id="sodimm", name="Performance 8GB DDR4 SO-DIMM Memory Module", price=79.99),
        _result(product_id="desktop", name="Viper Steel 8GB DDR4 Desktop Memory", price=88.99),
    ]
    out = filter_results(results, FilterSpec(exclude=("so-dimm",)))
    assert [r.product_id for r in out] == ["desktop"]
