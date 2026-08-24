"""Shared CLI context — kept separate from cli.py to avoid circular imports
between the root group and the command modules."""

from __future__ import annotations

from dataclasses import dataclass

from .client import MicroCenterClient
from .config import Config


@dataclass
class Ctx:
    config: Config
    store_id: str | None = None

    def resolve_store(self) -> str:
        store = self.store_id or self.config.default_store
        if not store:
            raise ClickUsageError(
                "no store specified — pass --store <id>, set MICROCENTER_STORE, or "
                "set default_store in config.toml. See `mcenter stores list`."
            )
        return store

    def client(self) -> MicroCenterClient:
        return MicroCenterClient(self.config)


class ClickUsageError(RuntimeError):
    pass
