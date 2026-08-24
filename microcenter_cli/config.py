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


def load_config() -> Config:
    cfg = Config()

    if CONFIG_FILE.exists():
        data = tomllib.loads(CONFIG_FILE.read_text())
        cfg.default_store = data.get("default_store", cfg.default_store)
        cfg.session_ttl_seconds = data.get("session_ttl_seconds", cfg.session_ttl_seconds)

    if v := os.environ.get("MICROCENTER_STORE"):
        cfg.default_store = v
    if v := os.environ.get("MICROCENTER_SESSION_TTL"):
        cfg.session_ttl_seconds = int(v)

    return cfg
