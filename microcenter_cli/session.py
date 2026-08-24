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
import time
from dataclasses import asdict, dataclass, field

from .config import SESSION_FILE


@dataclass
class Session:
    cookies: dict[str, str] = field(default_factory=dict)
    user_agent: str = ""
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
