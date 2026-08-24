from microcenter_cli.session import parse_cookie_header


def test_parse_cookie_header():
    header = "cf_clearance=abc123; __cf_bm=xyz; storeSelected=121"
    cookies = parse_cookie_header(header)
    assert cookies == {"cf_clearance": "abc123", "__cf_bm": "xyz", "storeSelected": "121"}


def test_parse_cookie_header_ignores_junk():
    assert parse_cookie_header("  ; a=1;;  b=2 ") == {"a": "1", "b": "2"}
