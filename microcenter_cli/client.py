from __future__ import annotations

from curl_cffi import requests as curl_requests

from . import parser, session, urls
from .config import Config
from .models import ProductDetail, SearchResult


class MicroCenterError(RuntimeError):
    pass


class MicroCenterBlockedError(MicroCenterError):
    """Cloudflare challenged us even after a fresh bootstrap."""


class MicroCenterClient:
    """Plain-HTTP client (TLS-impersonated via curl_cffi) that reuses a cached,
    browser-bootstrapped Cloudflare session. Bootstraps automatically on cold
    start or when the cached session goes stale/gets invalidated — that's the
    only time a browser process gets spawned.
    """

    def __init__(self, config: Config):
        self.config = config
        self._session = session.load()

    def _ensure_session(self, *, force: bool = False) -> None:
        if not force and self._session.is_fresh(self.config.session_ttl_seconds):
            return
        from . import bootstrap  # deferred: keeps playwright off the import path

        self._session = bootstrap.bootstrap(headless=self.config.headless_bootstrap)
        session.save(self._session)

    def _get(self, url: str, store_id: str, *, _retried: bool = False) -> str:
        self._ensure_session()
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
            if _retried:
                raise MicroCenterBlockedError(
                    f"still challenged after a fresh session bootstrap ({url})"
                )
            self._ensure_session(force=True)
            return self._get(url, store_id, _retried=True)

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
