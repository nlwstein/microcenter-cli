from __future__ import annotations

from curl_cffi import requests as curl_requests

from . import parser, session, urls
from .config import Config
from .models import ProductDetail, SearchResult

IMPORT_HINT = (
    "no valid session. Solve the checkbox by hand in a real browser and run "
    "`mcenter session import` (see `mcenter session status` for the exact steps)."
)


class MicroCenterError(RuntimeError):
    pass


class MicroCenterBlockedError(MicroCenterError):
    """Cloudflare challenged us — no cached session, or it's been invalidated."""


class MicroCenterClient:
    """Plain-HTTP client (TLS-impersonated via curl_cffi) that reuses a session
    cookie imported from a real, human-solved browser session (see
    `mcenter session import`). Micro Center's Turnstile checkbox rejects any
    automation-controlled browser outright, so nothing in this library can solve
    it itself — it can only detect when the imported session has gone stale and
    say so clearly.
    """

    def __init__(self, config: Config):
        self.config = config
        self._session = session.load()
        if not self._session.cookies:
            raise MicroCenterBlockedError(IMPORT_HINT)

    def _get(self, url: str, store_id: str) -> str:
        cookies = {**self._session.cookies, "storeSelected": store_id}
        headers = {
            "User-Agent": self._session.user_agent or "Mozilla/5.0",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }
        resp = curl_requests.get(
            url, impersonate="chrome", cookies=cookies, headers=headers, timeout=30
        )

        if resp.status_code == 403 or parser.looks_like_challenge_page(resp.text):
            raise MicroCenterBlockedError(
                f"session was rejected fetching {url} — it's likely expired/invalidated. "
                + IMPORT_HINT
            )

        resp.raise_for_status()
        return resp.text

    def search(
        self, query: str, store_id: str, *, page: int = 1, category_n: str | None = None
    ) -> list[SearchResult]:
        html = self._get(urls.search_url(query, store_id, page, category_n), store_id)
        return parser.parse_search_results(html, store_id)

    def product(self, product_id: str, store_id: str) -> ProductDetail:
        html = self._get(urls.product_url(product_id), store_id)
        return parser.parse_product_page(html, product_id, store_id)

    def raw_fetch(self, url: str, store_id: str) -> str:
        """Escape hatch for calibrating parser.py against real pages."""
        return self._get(url, store_id)
