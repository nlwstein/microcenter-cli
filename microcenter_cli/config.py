"""Config precedence: CLI flags > env vars > ~/.config/microcenter-cli/config.toml > defaults."""

from __future__ import annotations

import os
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path

from platformdirs import user_config_dir

CONFIG_DIR = Path(user_config_dir("microcenter-cli"))
CONFIG_FILE = CONFIG_DIR / "config.toml"
SESSION_FILE = CONFIG_DIR / "session.json"


class ConfigError(RuntimeError):
    pass


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


# (field name, minimum allowed value) -- anything below this is almost certainly a
# typo (e.g. request_timeout_seconds = 0) that would otherwise fail confusingly deep
# inside curl_cffi rather than with a message that points at the actual config field.
_MINIMUMS: dict[str, float] = {
    "session_ttl_seconds": 0,
    "request_timeout_seconds": 1.0,
    "max_retries": 1,
    "retry_backoff_seconds": 0.0,
    "min_request_interval_seconds": 0.0,
}


def _clamp(cfg: Config) -> None:
    for field_name, minimum in _MINIMUMS.items():
        value = getattr(cfg, field_name)
        if value < minimum:
            print(
                f"[mcenter] warning: config '{field_name}' = {value} is below the "
                f"sane minimum ({minimum}); using {minimum} instead.",
                file=sys.stderr,
            )
            setattr(cfg, field_name, minimum if isinstance(value, float) else int(minimum))


def load_config() -> Config:
    cfg = Config()

    if CONFIG_FILE.exists():
        try:
            data = tomllib.loads(CONFIG_FILE.read_text())
        except tomllib.TOMLDecodeError as exc:
            raise ConfigError(f"couldn't parse {CONFIG_FILE}: {exc}") from exc

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

    _clamp(cfg)
    return cfg
