"""On-disk cache of a Cloudflare-cleared session (cookies + matching User-Agent).

microcenter.com sits behind a Cloudflare Turnstile challenge that is an actual
"verify you are human" checkbox (see README) — and Cloudflare detects and rejects
solves that come from an automation-controlled browser (Playwright/Puppeteer/CDP),
regardless of whether a real click is dispatched. So there is no automatable
bootstrap for this: a human has to solve it once in their own, un-automated
browser, and hand the resulting cookie to this tool (`mcenter session import`).
This module just caches whatever session was imported and reuses it for many
subsequent plain-HTTP requests until it expires or gets invalidated.
"""

from __future__ import annotations

import json
import platform
import subprocess
import time
from dataclasses import asdict, dataclass, field

from .config import SESSION_FILE

MICROCENTER_DOMAIN = "microcenter.com"

# UA doesn't vary by CPU arch on macOS -- Apple Silicon Chrome/Firefox both still
# report "Intel Mac OS X" in their UA string. Known, deliberate quirk, not a bug here.
# Keyed by the same names browser_cookie3 uses (chrome, firefox, edge, ...), since
# that's what --browser takes.
_MAC_BROWSER_INFO: dict[str, tuple[str, str]] = {
    "chrome": (
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/{version} Safari/537.36"
        ),
    ),
    "firefox": (
        "/Applications/Firefox.app/Contents/MacOS/firefox",
        (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:{version}) "
            "Gecko/20100101 Firefox/{version}"
        ),
    ),
    "edge": (
        "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
        (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/{version} Safari/537.36 Edg/{version}"
        ),
    ),
}

# curl_cffi impersonation target for each browser_cookie3 name -- picks the TLS/HTTP2
# fingerprint that should actually match whichever browser solved the challenge.
IMPERSONATE_BY_BROWSER: dict[str, str] = {
    "chrome": "chrome",
    "edge": "chrome",  # Edge is Chromium; curl_cffi has no distinct Edge profile
    "firefox": "firefox",
}


@dataclass
class Session:
    cookies: dict[str, str] = field(default_factory=dict)
    user_agent: str = ""
    browser: str = "chrome"
    saved_at: float = 0.0

    def age_seconds(self) -> float:
        return time.time() - self.saved_at

    def is_fresh(self, ttl_seconds: int) -> bool:
        return bool(self.cookies) and self.age_seconds() < ttl_seconds


def load() -> Session:
    if not SESSION_FILE.exists():
        return Session()
    try:
        data = json.loads(SESSION_FILE.read_text())
        return Session(**data)
    except (json.JSONDecodeError, TypeError):
        return Session()


def save(session: Session) -> None:
    SESSION_FILE.parent.mkdir(parents=True, exist_ok=True)
    SESSION_FILE.write_text(json.dumps(asdict(session), indent=2))


def clear() -> None:
    if SESSION_FILE.exists():
        SESSION_FILE.unlink()


def detect_user_agent(browser: str) -> str | None:
    """Best-effort UA string matching the actually-installed browser, so it lines up
    with whatever version just solved the challenge. Returns None if we can't tell
    (unsupported OS/browser, binary not found at the expected path) -- caller should
    fall back to asking the user or to curl_cffi's own impersonation default."""
    if platform.system() != "Darwin":
        return None
    info = _MAC_BROWSER_INFO.get(browser)
    if not info:
        return None
    path, template = info
    try:
        out = subprocess.run(
            [path, "--version"], capture_output=True, text=True, timeout=5, check=False
        )
        # "Google Chrome 130.0.6723.92" / "Mozilla Firefox 130.0.1" -> last token
        version = out.stdout.strip().rsplit(" ", 1)[-1]
    except (OSError, subprocess.SubprocessError):
        return None
    return template.format(version=version)


class BrowserCookieError(RuntimeError):
    pass


def from_installed_browser(*, browser: str = "chrome") -> Session:
    """Pull a live cf_clearance (and friends) straight out of a real, already-running
    browser's own cookie store -- no automation protocol involved at any point, so
    none of the CDP-detection issues documented at the top of this module apply.
    Requires the user to have just solved the challenge in that same browser."""
    import browser_cookie3

    try:
        loader = getattr(browser_cookie3, browser)
    except AttributeError as exc:
        raise BrowserCookieError(f"unsupported browser '{browser}'") from exc

    try:
        jar = loader(domain_name=MICROCENTER_DOMAIN)
    except Exception as exc:  # browser_cookie3 raises varied, undocumented types
        raise BrowserCookieError(
            f"couldn't read {browser}'s cookie store: {exc}. Falling back to "
            "`mcenter session import` (paste the Cookie header manually) will "
            "always work regardless of this."
        ) from exc

    cookies = {c.name: c.value for c in jar}
    if "cf_clearance" not in cookies:
        raise BrowserCookieError(
            "no cf_clearance cookie found for microcenter.com in your browser yet -- "
            "make sure the page finished loading (past any 'Verify you are human' "
            "checkbox) before retrying."
        )

    user_agent = detect_user_agent(browser) or ""
    return Session(cookies=cookies, user_agent=user_agent, browser=browser, saved_at=time.time())


def guess_browser_from_ua(user_agent: str) -> str:
    """Classify a pasted User-Agent well enough to pick a curl_cffi impersonation
    profile (see IMPERSONATE_BY_BROWSER) -- doesn't need to be precise, just Chrome-
    family vs. Firefox."""
    ua = user_agent.lower()
    if "firefox" in ua and "seamonkey" not in ua:
        return "firefox"
    if "edg/" in ua:
        return "edge"
    return "chrome"


def parse_cookie_header(header: str) -> dict[str, str]:
    """Parse a raw `Cookie: a=1; b=2` header value, as copy-pasted from browser
    devtools (Network tab -> a request -> Request Headers -> Cookie), into a dict."""
    cookies: dict[str, str] = {}
    for part in header.split(";"):
        part = part.strip()
        if not part or "=" not in part:
            continue
        key, _, value = part.partition("=")
        cookies[key.strip()] = value.strip()
    return cookies
