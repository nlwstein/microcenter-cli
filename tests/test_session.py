from microcenter_cli.session import guess_browser_from_ua, parse_cookie_header


def test_parse_cookie_header():
    header = "cf_clearance=abc123; __cf_bm=xyz; storeSelected=121"
    cookies = parse_cookie_header(header)
    assert cookies == {"cf_clearance": "abc123", "__cf_bm": "xyz", "storeSelected": "121"}


def test_parse_cookie_header_ignores_junk():
    assert parse_cookie_header("  ; a=1;;  b=2 ") == {"a": "1", "b": "2"}


def test_guess_browser_from_ua():
    firefox_ua = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:130.0) Gecko/20100101 Firefox/130.0"
    chrome_ua = (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
    )
    edge_ua = chrome_ua + " Edg/130.0.0.0"

    assert guess_browser_from_ua(firefox_ua) == "firefox"
    assert guess_browser_from_ua(chrome_ua) == "chrome"
    assert guess_browser_from_ua(edge_ua) == "edge"
