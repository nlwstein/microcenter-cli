"""On-disk cache of a Cloudflare-cleared session (cookies + matching User-Agent).

microcenter.com sits behind Cloudflare managed challenge (see README for the full
story: plain HTTP and even TLS-impersonated HTTP get a 403 with `cf-mitigated:
challenge`). The only thing that reliably clears it is a real browser JS
environment. So we pay that cost once (bootstrap.py, Playwright), cache the
resulting cookies here, and reuse them for many subsequent plain-HTTP requests
until they expire or get invalidated.
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
