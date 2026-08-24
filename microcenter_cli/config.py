"""Config precedence: CLI flags > env vars > ~/.config/microcenter-cli/config.toml > defaults."""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass
from pathlib import Path

from platformdirs import user_config_dir

CONFIG_DIR = Path(user_config_dir("microcenter-cli"))
CONFIG_FILE = CONFIG_DIR / "config.toml"
SESSION_FILE = CONFIG_DIR / "session.json"


@dataclass
class Config:
    default_store: str | None = None
    # Purely informational staleness threshold shown by `session status` — an
    # imported session isn't proactively refreshed (nothing can do that
    # automatically, see session.py), it's just flagged as possibly-stale past
    # this age so you know to check whether `mcenter session import` is needed.
    session_ttl_seconds: int = 1200
    request_timeout_seconds: float = 30.0
    # Retried only for transient network failures (timeouts, connection resets,
    # 5xx) -- a 403/challenge response is never retried, since retrying it just
    # burns requests against the same expired session (see client.py).
    max_retries: int = 3
    retry_backoff_seconds: float = 1.0
    # Minimum gap enforced between consecutive requests (see client.py's
    # RateLimiter). Mainly matters for --all-pages, where several requests go
    # out back-to-back -- keeps that from looking like a burst to Cloudflare's
    # bot-management, which is exactly what we can't afford to re-trigger.
    min_request_interval_seconds: float = 0.75
    verbose: bool = False


def load_config() -> Config:
    cfg = Config()

    if CONFIG_FILE.exists():
        data = tomllib.loads(CONFIG_FILE.read_text())
        cfg.default_store = data.get("default_store", cfg.default_store)
        cfg.session_ttl_seconds = data.get("session_ttl_seconds", cfg.session_ttl_seconds)
        cfg.request_timeout_seconds = data.get(
            "request_timeout_seconds", cfg.request_timeout_seconds
        )
        cfg.max_retries = data.get("max_retries", cfg.max_retries)
        cfg.retry_backoff_seconds = data.get("retry_backoff_seconds", cfg.retry_backoff_seconds)
        cfg.min_request_interval_seconds = data.get(
            "min_request_interval_seconds", cfg.min_request_interval_seconds
        )

    if v := os.environ.get("MICROCENTER_STORE"):
        cfg.default_store = v
    if v := os.environ.get("MICROCENTER_SESSION_TTL"):
        cfg.session_ttl_seconds = int(v)
    if v := os.environ.get("MICROCENTER_TIMEOUT"):
        cfg.request_timeout_seconds = float(v)
    if v := os.environ.get("MICROCENTER_VERBOSE"):
        cfg.verbose = v not in ("0", "false", "False")

    return cfg
