"""Parser tests against synthetic fixtures built from the known-good DOM shape
(see parser.py docstring for provenance). These pin down parser.py's contract;
if real captured HTML (via `mcenter debug fetch`) parses differently, update
both the fixtures here and parser.py together.
"""

from microcenter_cli.parser import looks_like_challenge_page, parse_product_page, parse_search_results

SEARCH_FIXTURE = """
<html><body>
<div class="detail_wrapper">
  <a data-id="608316" data-name="AMD Ryzen 9 3900X" data-price="329.99"
     data-category="AMD Processors" data-brand="AMD" href="/product/608316/">link</a>
  <div class="stock"><strong>In stock</strong></div>
  <div class="ratingstars"><img alt="4.5 stars"><span>120 reviews</span></div>
  <div class="highlight clear">Open Box available</div>
</div>
<div class="detail_wrapper">
  <a data-id="999999" data-name="Sold Out Widget" data-price="19.99"
     data-category="Widgets" data-brand="Acme" href="/product/999999/">link</a>
  <div class="stock"><strong>Sold out</strong></div>
</div>
</body></html>
"""

PRODUCT_FIXTURE = """
<html><head><title>AMD Ryzen 9 3900X | Micro Center</title></head>
<body><script>
var inStock = true;
var productPrice = 329.99;
var sku = 'MC-608316';
</script></body></html>
"""

CHALLENGE_FIXTURE = "<html><head><title>Just a moment...</title></head><body></body></html>"


def test_parse_search_results():
    results = parse_search_results(SEARCH_FIXTURE, store_id="121")
    assert len(results) == 2

    first = results[0]
    assert first.product_id == "608316"
    assert first.name == "AMD Ryzen 9 3900X"
    assert first.price == 329.99
    assert first.brand == "AMD"
    assert first.stock_text == "In stock"
    assert first.rating == "4.5 stars"
    assert first.reviews == "120 reviews"
    assert first.offer == "Open Box available"
    assert first.store_id == "121"

    second = results[1]
    assert second.stock_text == "Sold out"
    assert second.rating is None


def test_parse_product_page():
    detail = parse_product_page(PRODUCT_FIXTURE, product_id="608316", store_id="121")
    assert detail.name == "AMD Ryzen 9 3900X"
    assert detail.price == 329.99
    assert detail.in_stock is True
    assert detail.sku == "MC-608316"
    assert detail.store_id == "121"


def test_looks_like_challenge_page():
    assert looks_like_challenge_page(CHALLENGE_FIXTURE) is True
    assert looks_like_challenge_page(SEARCH_FIXTURE) is False
