from __future__ import annotations

import pytest

from microcenter_cli.urls import SORT_OPTIONS, product_url, search_url


def test_search_url_basic():
    url = search_url("ryzen", "121")
    assert "Ntt=ryzen" in url
    assert "storeid=121" in url
    assert "page=1" in url
    assert "sortby=" not in url  # no sort requested -> site default


def test_search_url_sort():
    for name, site_value in SORT_OPTIONS.items():
        assert f"sortby={site_value}" in search_url("ryzen", "121", sort=name)


def test_search_url_invalid_sort_raises():
    with pytest.raises(ValueError, match="unknown sort"):
        search_url("ryzen", "121", sort="not-a-real-sort")


def test_search_url_rpp_and_category():
    url = search_url("ryzen", "121", category_n="4294966995", rpp=96)
    assert "N=4294966995" in url
    assert "rpp=96" in url


def test_search_url_escapes_special_characters():
    url = search_url("ryzen 9 & friends", "1 21")
    assert "&" not in url.split("Ntt=")[1].split("&")[0]  # the literal & got encoded, not passed through
    assert "storeid=1+21" in url or "storeid=1%2021" in url


def test_product_url_escapes_id():
    url = product_url("../etc/passwd")
    assert "../" not in url
