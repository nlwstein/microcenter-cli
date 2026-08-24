"""Parser tests against synthetic fixtures built from real captured HTML shape
(see parser.py docstring for the full annotated structure and provenance). These
pin down parser.py's contract; if real captured HTML (via `mcenter debug fetch`)
parses differently, update both the fixtures here and parser.py together.
"""

from microcenter_cli.parser import (
    looks_like_challenge_page,
    parse_product_page,
    parse_search_page,
    parse_search_results,
)

SEARCH_FIXTURE = """
<html><body>
<div class="result_right">
  <div class="details">
    <div class="detail_wrapper">
      <div class="highlight clear"></div>
      <p class="sku">SKU: 815944</p>
      <div class="h2">
        <a data-id="691349" data-name="AMD Ryzen 9 9950X3D" data-price="549.99"
           data-brand="AMD" data-category="Processors/CPUs"
           class="productClickItemV2" href="/product/691349/">AMD Ryzen 9 9950X3D</a>
      </div>
    </div>
    <div class="price_wrapper">
      <div class="stock">
        <span class="inventoryCnt">25 <span class="msgInStock">IN STOCK</span></span>
        <span class="storeName"> at Cambridge Store</span>
      </div>
      <div class="price"><span itemprop="price">$549.99</span></div>
    </div>
  </div>
</div>
<div class="result_right">
  <div class="details">
    <div class="detail_wrapper">
      <p class="sku">SKU: 999999</p>
      <div class="h2">
        <a data-id="777777" data-name="Sold Out Widget" data-price="19.99"
           data-brand="Acme" data-category="Widgets"
           class="productClickItemV2" href="/product/777777/">Sold Out Widget</a>
      </div>
    </div>
    <div class="price_wrapper">
      <div class="stock"><span class="msgOutOfStock">OUT OF STOCK</span></div>
    </div>
  </div>
</div>
</body></html>
"""

PRODUCT_FIXTURE = """
<html><head><title>
\tAMD Ryzen 9 9950X3D Granite Ridge - Micro Center
</title></head>
<body><script>
'inStock':'True',
"productPrice":"549.99",
"sku": "815944"
</script></body></html>
"""

CHALLENGE_FIXTURE = "<html><head><title>Just a moment...</title></head><body></body></html>"

# SEARCH_FIXTURE plus real pagination markup (status line, items-per-page
# selector, rel="next" link) -- as it'd appear on a middle page of results.
SEARCH_FIXTURE_WITH_PAGINATION = f"""
<html><head><link rel="next" href="/search/search_results.aspx?Ntt=ryzen&page=2"></head>
<body>
<span class="itemsPerPage">24</span>
{SEARCH_FIXTURE[SEARCH_FIXTURE.find("<body>") + 6 : SEARCH_FIXTURE.find("</body>")]}
<p class="status">1 - 24 of 183 items</p>
</body></html>
"""

# Same, but the last page: no rel="next" at all.
SEARCH_FIXTURE_LAST_PAGE = SEARCH_FIXTURE_WITH_PAGINATION.replace(
    '<link rel="next" href="/search/search_results.aspx?Ntt=ryzen&page=2">', ""
).replace("1 - 24 of 183 items", "169 - 183 of 183 items")


def test_parse_search_results():
    results = parse_search_results(SEARCH_FIXTURE, store_id="121")
    assert len(results) == 2

    first = results[0]
    assert first.product_id == "691349"
    assert first.name == "AMD Ryzen 9 9950X3D"
    assert first.price == 549.99
    assert first.brand == "AMD"
    assert "IN STOCK" in first.stock_text
    assert first.store_id == "121"
    assert first.offer is None  # empty highlight div -> None, not ""

    second = results[1]
    assert second.product_id == "777777"
    assert "OUT OF STOCK" in second.stock_text


def test_parse_product_page():
    detail = parse_product_page(PRODUCT_FIXTURE, product_id="691349", store_id="121")
    assert detail.name == "AMD Ryzen 9 9950X3D Granite Ridge"
    assert detail.price == 549.99
    assert detail.in_stock is True
    assert detail.sku == "815944"
    assert detail.store_id == "121"


def test_looks_like_challenge_page():
    assert looks_like_challenge_page(CHALLENGE_FIXTURE) is True
    assert looks_like_challenge_page(SEARCH_FIXTURE) is False


def test_parse_search_page_with_next():
    page = parse_search_page(SEARCH_FIXTURE_WITH_PAGINATION, store_id="121", requested_page=1)
    assert len(page.results) == 2
    assert page.items_per_page == 24
    assert page.total_items == 183
    assert page.total_pages == 8
    assert page.has_next is True


def test_parse_search_page_last_page():
    page = parse_search_page(SEARCH_FIXTURE_LAST_PAGE, store_id="121", requested_page=8)
    assert page.total_items == 183
    assert page.has_next is False


def test_double_encoded_entities_are_cleaned_up():
    # Micro Center's own data-name attributes sometimes contain a literal
    # "&quot;" post-decode (double-encoded), e.g. for a 13.4" laptop listing.
    fixture = """
    <div class="result_right"><div class="details"><div class="detail_wrapper">
      <div class="h2"><a data-id="1" data-name="ROG Flow 13.4&amp;quot; Laptop"
         data-price="999.99" data-brand="ASUS" href="/product/1/">x</a></div>
    </div><div class="price_wrapper"><div class="stock">In stock</div></div>
    </div></div>
    """
    results = parse_search_results(fixture, store_id="121")
    assert results[0].name == 'ROG Flow 13.4" Laptop'
