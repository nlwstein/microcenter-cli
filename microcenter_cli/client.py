from __future__ import annotations

import sys
import time
from urllib.parse import urlparse

from curl_cffi import requests as curl_requests
from curl_cffi.requests.exceptions import ConnectionError as CurlConnectionError
from curl_cffi.requests.exceptions import CurlError, DNSError, SSLError

from . import parser, session, urls
from .config import Config
from .models import ProductDetail, ProductLookupResult, SearchPage, SearchResult

IMPORT_HINT = (
    "no valid session. Run `mcenter session interactive` (see `mcenter session "
    "status` if that doesn't work for your setup)."
)

# Network-level failures worth retrying (transient: dropped connection, DNS
# hiccup, TLS handshake blip). Deliberately does NOT include anything that means
# "the server answered and said no" -- a 403/challenge or 404 retrying against the
# same expired session / nonexistent product just burns requests for nothing.
_RETRYABLE_EXCEPTIONS = (CurlConnectionError, DNSError, SSLError, CurlError)

# Safety cap for --all-pages, independent of whatever the site's own pagination
# metadata claims -- if total_items parsing is ever wrong, this stops it from
# looping until Cloudflare notices instead of stopping cleanly.
MAX_AUTO_PAGES = 50

# `mcenter debug fetch <url>` accepts an arbitrary URL, but every request attaches
# the live session cookie -- without this check, `debug fetch https://evil.example/`
# would hand cf_clearance (a bearer credential for the session) to a third party.
_ALLOWED_HOST_SUFFIX = "microcenter.com"


class MicroCenterError(RuntimeError):
    pass


class MicroCenterBlockedError(MicroCenterError):
    """Cloudflare challenged us — no cached session, or it's been invalidated."""


class MicroCenterNotFoundError(MicroCenterError):
    """The requested product id doesn't resolve to a real product page."""


class _RateLimiter:
    """Enforces a minimum gap between consecutive requests. Not thread-safe --
    this client isn't used concurrently anywhere in the CLI."""

    def __init__(self, min_interval_seconds: float):
        self.min_interval = min_interval_seconds
        self._last_request_at: float | None = None

    def wait(self) -> None:
        if self._last_request_at is None:
            self._last_request_at = time.monotonic()
            return
        elapsed = time.monotonic() - self._last_request_at
        remaining = self.min_interval - elapsed
        if remaining > 0:
            time.sleep(remaining)
        self._last_request_at = time.monotonic()


class MicroCenterClient:
    """Plain-HTTP client (TLS-impersonated via curl_cffi) that reuses a session
    cookie captured from a real, human-solved browser session (see
    `mcenter session interactive` / `session import`). Micro Center's Turnstile
    checkbox rejects any automation-controlled browser outright, so nothing in this
    library can solve it itself — it can only detect when the session has gone
    stale and say so clearly.
    """

    def __init__(self, config: Config):
        self.config = config
        self._session = session.load()
        if not self._session.cookies:
            raise MicroCenterBlockedError(IMPORT_HINT)
        self._rate_limiter = _RateLimiter(config.min_request_interval_seconds)

    def _log(self, message: str) -> None:
        if self.config.verbose:
            print(f"[mcenter] {message}", file=sys.stderr)

    def _request(self, url: str, store_id: str):
        host = urlparse(url).hostname or ""
        if not (host == _ALLOWED_HOST_SUFFIX or host.endswith(f".{_ALLOWED_HOST_SUFFIX}")):
            raise MicroCenterError(
                f"refusing to send the session cookie to '{host}' -- only "
                f"*.{_ALLOWED_HOST_SUFFIX} URLs are allowed (cf_clearance is a bearer "
                "credential for the session, not something to leak to arbitrary hosts)."
            )

        cookies = {**self._session.cookies, "storeSelected": store_id}
        headers = {
            "User-Agent": self._session.user_agent or "Mozilla/5.0",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }
        impersonate = session.IMPERSONATE_BY_BROWSER.get(self._session.browser, "chrome")

        attempt = 0
        while True:
            attempt += 1
            self._rate_limiter.wait()
            self._log(f"GET {url} (attempt {attempt}/{self.config.max_retries})")
            try:
                resp = curl_requests.get(
                    url,
                    impersonate=impersonate,
                    cookies=cookies,
                    headers=headers,
                    timeout=self.config.request_timeout_seconds,
                )
            except _RETRYABLE_EXCEPTIONS as exc:
                if attempt >= self.config.max_retries:
                    raise MicroCenterError(
                        f"network error fetching {url} after {attempt} attempts: {exc}"
                    ) from exc
                backoff = self.config.retry_backoff_seconds * (2 ** (attempt - 1))
                self._log(f"transient error ({exc}), retrying in {backoff:.1f}s")
                time.sleep(backoff)
                continue

            self._log(f"-> {resp.status_code}")

            if resp.status_code >= 500 and attempt < self.config.max_retries:
                backoff = self.config.retry_backoff_seconds * (2 ** (attempt - 1))
                self._log(f"server error {resp.status_code}, retrying in {backoff:.1f}s")
                time.sleep(backoff)
                continue

            return resp

    def _get(self, url: str, store_id: str) -> str:
        resp = self._request(url, store_id)

        if resp.status_code == 403 or parser.looks_like_challenge_page(resp.text):
            raise MicroCenterBlockedError(
                f"session was rejected fetching {url} — it's likely expired/invalidated. "
                + IMPORT_HINT
            )

        resp.raise_for_status()
        return resp.text

    def search(
        self,
        query: str,
        store_id: str,
        *,
        page: int = 1,
        category_n: str | None = None,
        sort: str | None = None,
    ) -> list[SearchResult]:
        return self.search_page(query, store_id, page=page, category_n=category_n, sort=sort).results

    def search_page(
        self,
        query: str,
        store_id: str,
        *,
        page: int = 1,
        category_n: str | None = None,
        rpp: int | None = None,
        sort: str | None = None,
    ) -> SearchPage:
        html = self._get(urls.search_url(query, store_id, page, category_n, rpp, sort), store_id)
        return parser.parse_search_page(html, store_id, requested_page=page)

    def search_all(
        self,
        query: str,
        store_id: str,
        *,
        category_n: str | None = None,
        rpp: int | None = None,
        sort: str | None = None,
        max_pages: int = MAX_AUTO_PAGES,
    ):
        """Yields SearchResults across every page, stopping when the site stops
        advertising a next page (or max_pages, whichever comes first). Honors the
        same rate limiting as everything else -- this is exactly the situation
        that exists to protect."""
        page = 1
        while page <= max_pages:
            result_page = self.search_page(
                query, store_id, page=page, category_n=category_n, rpp=rpp, sort=sort
            )
            yield from result_page.results
            if not result_page.has_next:
                return
            page += 1

        # Loop exited via the max_pages cap, not because the site ran out of
        # pages -- the caller got a truncated result set and needs to know, not
        # silently believe they have everything.
        print(
            f"[mcenter] warning: stopped at the {max_pages}-page safety cap; "
            "more results existed. Pass a higher max_pages if you really need them all.",
            file=sys.stderr,
        )

    def product(self, product_id: str, store_id: str) -> ProductDetail:
        resp = self._request(urls.product_url(product_id), store_id)

        if resp.status_code == 404:
            raise MicroCenterNotFoundError(f"no product with id '{product_id}'")
        if resp.status_code == 403 or parser.looks_like_challenge_page(resp.text):
            raise MicroCenterBlockedError(
                f"session was rejected fetching product {product_id} — it's likely "
                "expired/invalidated. " + IMPORT_HINT
            )
        resp.raise_for_status()

        detail = parser.parse_product_page(resp.text, product_id, store_id)
        if detail.name is None and detail.price is None and detail.in_stock is None:
            raise MicroCenterError(
                f"got a 200 for product '{product_id}' but couldn't parse anything "
                "useful out of it — either the id is wrong or Micro Center changed "
                "the page structure again (see parser.py, `mcenter debug fetch`)."
            )
        return detail

    def products(self, product_ids: list[str], store_id: str) -> list[ProductLookupResult]:
        """Batch product() lookup -- one call site instead of N, for the common
        "verify a shortlist" pattern. Sequential, not concurrent (this client
        isn't thread-safe and the rate limiter assumes serial requests), but
        still saves N round-trip declarations for a caller. One bad id doesn't
        abort the batch -- its ProductLookupResult just carries an error."""
        results = []
        for product_id in product_ids:
            try:
                detail = self.product(product_id, store_id)
                results.append(ProductLookupResult(product_id=product_id, detail=detail))
            except MicroCenterError as exc:
                results.append(ProductLookupResult(product_id=product_id, error=str(exc)))
        return results

    def raw_fetch(self, url: str, store_id: str) -> str:
        """Escape hatch for calibrating parser.py against real pages."""
        return self._get(url, store_id)
