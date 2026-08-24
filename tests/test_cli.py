"""CLI wiring tests via Click's CliRunner. The network client is monkeypatched
out entirely (see FakeClient) -- these exist to catch argument-parsing/wiring
regressions like the one that shipped for real: --store only worked *before*
the subcommand name, and `mcenter search foo --store 121` errored with "no such
option". Pure client/parser unit tests wouldn't have caught that class of bug;
these are specifically here to.
"""

from __future__ import annotations

import json

import pytest
from click.testing import CliRunner

from microcenter_cli import cli as cli_module
from microcenter_cli.config import Config
from microcenter_cli.models import ProductDetail, SearchPage, SearchResult


class FakeClient:
    """Records what it was called with; returns small canned data."""

    def __init__(self):
        self.calls: list[tuple] = []

    def search_page(self, query, store_id, *, page=1, category_n=None, rpp=None, sort=None):
        self.calls.append(("search_page", query, store_id, page, category_n, rpp, sort))
        result = SearchResult(
            product_id="1",
            name="Widget",
            price=9.99,
            category=None,
            brand="Acme",
            stock_text="In stock",
            rating=None,
            reviews=None,
            offer=None,
            store_id=store_id,
        )
        return SearchPage(
            results=[result], page=page, items_per_page=24, total_items=1, has_next=False
        )

    def search_all(self, query, store_id, *, category_n=None, rpp=None, sort=None, max_pages=50):
        self.calls.append(("search_all", query, store_id, category_n, rpp, sort))
        yield self.search_page(query, store_id).results[0]

    def product(self, product_id, store_id):
        self.calls.append(("product", product_id, store_id))
        return ProductDetail(
            product_id=product_id,
            sku="SKU1",
            name="Widget",
            price=9.99,
            in_stock=True,
            store_id=store_id,
        )

    def products(self, product_ids, store_id):
        self.calls.append(("products", tuple(product_ids), store_id))
        from microcenter_cli.models import ProductLookupResult

        return [
            ProductLookupResult(product_id=pid, detail=self.product(pid, store_id))
            for pid in product_ids
        ]

    def raw_fetch(self, url, store_id):
        self.calls.append(("raw_fetch", url, store_id))
        return "<html>raw</html>"


@pytest.fixture
def fake_client(monkeypatch):
    client = FakeClient()
    monkeypatch.setattr(cli_module, "load_config", lambda: Config())
    # Ctx.client() is the single choke point every command goes through.
    from microcenter_cli.context import Ctx

    monkeypatch.setattr(Ctx, "client", lambda self: client)
    return client


@pytest.fixture
def runner():
    return CliRunner()


def test_help_exits_cleanly(runner):
    result = runner.invoke(cli_module.cli, ["--help"])
    assert result.exit_code == 0
    assert "search" in result.output


def test_store_works_before_subcommand(runner, fake_client):
    result = runner.invoke(cli_module.cli, ["--store", "121", "search", "widget"])
    assert result.exit_code == 0, result.output
    assert fake_client.calls[0][2] == "121"


def test_store_works_after_subcommand(runner, fake_client):
    """The exact bug that shipped: --store only worked before the subcommand."""
    result = runner.invoke(cli_module.cli, ["search", "widget", "--store", "121"])
    assert result.exit_code == 0, result.output
    assert fake_client.calls[0][2] == "121"


def test_per_subcommand_store_overrides_group_level(runner, fake_client):
    result = runner.invoke(
        cli_module.cli, ["--store", "999", "search", "widget", "--store", "121"]
    )
    assert result.exit_code == 0, result.output
    assert fake_client.calls[0][2] == "121"


def test_search_json_output_shape(runner, fake_client):
    result = runner.invoke(cli_module.cli, ["search", "widget", "--store", "121", "--json"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert data == [
        {
            "product_id": "1",
            "name": "Widget",
            "price": 9.99,
            "category": None,
            "brand": "Acme",
            "stock_text": "In stock",
            "rating": None,
            "reviews": None,
            "offer": None,
            "store_id": "121",
        }
    ]


def test_search_all_pages_flag(runner, fake_client):
    result = runner.invoke(
        cli_module.cli, ["search", "widget", "--store", "121", "--all-pages", "--json"]
    )
    assert result.exit_code == 0, result.output
    assert fake_client.calls[0][0] == "search_all"


def test_search_missing_store_is_a_clean_usage_error(runner, fake_client):
    result = runner.invoke(cli_module.cli, ["search", "widget"])
    assert result.exit_code != 0
    assert "no store specified" in result.output
    assert "Traceback" not in result.output


def test_product_json_output(runner, fake_client):
    result = runner.invoke(cli_module.cli, ["product", "42", "--store", "121", "--json"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert data["product_id"] == "42"
    assert data["in_stock"] is True


def test_debug_fetch_out_file(runner, fake_client, tmp_path):
    out = tmp_path / "page.html"
    result = runner.invoke(
        cli_module.cli,
        ["debug", "https://www.microcenter.com/x", "--store", "121", "--out", str(out)],
    )
    assert result.exit_code == 0, result.output
    assert out.read_text() == "<html>raw</html>"


def test_stores_find(runner):
    result = runner.invoke(cli_module.cli, ["stores", "find", "cambridge"])
    assert result.exit_code == 0
    assert "121" in result.output


def test_search_sort_passed_through(runner, fake_client):
    result = runner.invoke(
        cli_module.cli, ["search", "widget", "--store", "121", "--sort", "price-low"]
    )
    assert result.exit_code == 0, result.output
    assert fake_client.calls[0][-1] == "price-low"  # sort is the last positional recorded


def test_search_bad_sort_is_a_usage_error(runner, fake_client):
    result = runner.invoke(cli_module.cli, ["search", "widget", "--store", "121", "--sort", "bogus"])
    assert result.exit_code != 0
    assert "Traceback" not in result.output


def test_search_filters_applied(runner, monkeypatch):
    """FakeClient with two results (one in-stock, one not) -- --in-stock-only
    should drop exactly the one that isn't."""
    from microcenter_cli.context import Ctx
    from microcenter_cli.models import SearchPage, SearchResult

    class TwoResultClient:
        def search_page(self, query, store_id, *, page=1, category_n=None, rpp=None, sort=None):
            results = [
                SearchResult(
                    product_id="in-stock-item",
                    name="Widget A",
                    price=10.0,
                    category=None,
                    brand=None,
                    stock_text="5 IN STOCK at Cambridge Store",
                    rating=None,
                    reviews=None,
                    offer=None,
                    store_id=store_id,
                ),
                SearchResult(
                    product_id="sold-out-item",
                    name="Widget B",
                    price=5.0,
                    category=None,
                    brand=None,
                    stock_text="SOLD OUT at Cambridge Store",
                    rating=None,
                    reviews=None,
                    offer=None,
                    store_id=store_id,
                ),
            ]
            return SearchPage(results=results, page=1, items_per_page=24, total_items=2, has_next=False)

    monkeypatch.setattr(cli_module, "load_config", lambda: Config())
    monkeypatch.setattr(Ctx, "client", lambda self: TwoResultClient())

    result = runner.invoke(
        cli_module.cli, ["search", "widget", "--store", "121", "--in-stock-only", "--json"]
    )
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert [r["product_id"] for r in data] == ["in-stock-item"]


def test_products_batch_json_output(runner, fake_client):
    result = runner.invoke(
        cli_module.cli, ["products", "1", "2", "3", "--store", "121", "--json"]
    )
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert [d["product_id"] for d in data] == ["1", "2", "3"]
    assert all(d["detail"]["product_id"] == d["product_id"] for d in data)


def test_session_status_no_session(runner, monkeypatch, tmp_path):
    monkeypatch.setattr(cli_module, "load_config", lambda: Config())
    from microcenter_cli import session as session_module

    # session.py does `from .config import SESSION_FILE` -- a name binding copied
    # at import time, so the patch target is session.SESSION_FILE, not
    # config.SESSION_FILE (patching the latter wouldn't be seen here).
    monkeypatch.setattr(session_module, "SESSION_FILE", tmp_path / "no-such-session.json")
    result = runner.invoke(cli_module.cli, ["session", "status"])
    assert result.exit_code == 0
    assert "No session imported" in result.output
