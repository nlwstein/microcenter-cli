"""Solve the Cloudflare challenge once with a real browser, harvest cookies.

This is the ONLY place `microcenter_cli` opens a browser. Everything else in the
library talks plain HTTP using the cookies this produces. Call `bootstrap()`
lazily — on cold start, or when the client detects the cached session has been
invalidated — not on every request.

Requires `playwright install chromium` to have been run once per machine.
"""

from __future__ import annotations

from .session import Session

MICROCENTER_HOME = "https://www.microcenter.com/"


class BootstrapError(RuntimeError):
    pass


def bootstrap(*, headless: bool = True, timeout_seconds: int = 30) -> Session:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:  # pragma: no cover - environment issue, not logic
        raise BootstrapError(
            "playwright is not installed. Run: uv pip install playwright && "
            "playwright install chromium"
        ) from exc

    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(headless=headless)
        except Exception as exc:  # pragma: no cover
            raise BootstrapError(
                "could not launch Chromium. Run: playwright install chromium"
            ) from exc

        try:
            context = browser.new_context()
            page = context.new_page()
            page.goto(MICROCENTER_HOME, timeout=timeout_seconds * 1000)

            # Cloudflare's managed challenge runs its JS check and self-redirects;
            # wait for the interstitial title to go away rather than a fixed sleep.
            page.wait_for_function(
                "document.title !== 'Just a moment...'",
                timeout=timeout_seconds * 1000,
            )
            # Give the clearance cookie a moment to actually be set post-redirect.
            page.wait_for_timeout(1500)

            cookies = {c["name"]: c["value"] for c in context.cookies()}
            user_agent = page.evaluate("() => navigator.userAgent")

            if "cf_clearance" not in cookies:
                raise BootstrapError(
                    "navigated past the challenge title but no cf_clearance cookie "
                    "was set — Micro Center may have changed their challenge, or "
                    "this network/IP is scoring too low to auto-pass (try "
                    "headless=False to watch what happens)."
                )

            import time

            return Session(cookies=cookies, user_agent=user_agent, saved_at=time.time())
        finally:
            browser.close()
