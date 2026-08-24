"""Shared CLI context — kept separate from cli.py to avoid circular imports
between the root group and the command modules."""

from __future__ import annotations

from dataclasses import dataclass

import click

from . import stores
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
        if not store.isdigit():
            click.secho(
                f"warning: store id '{store}' doesn't look numeric — Micro Center store "
                "ids are normally 2-3 digits (see `mcenter stores list`). Trying it anyway.",
                fg="yellow",
                err=True,
            )
        elif store not in stores.STORES:
            # Not blocking: the static table is known-incomplete (see stores.py),
            # so an unrecognized id may just be a store missing from it, not a typo.
            click.secho(
                f"warning: store id '{store}' isn't in the known store list -- it may "
                "still be valid (the list is best-effort/incomplete), or it may be a "
                "typo. See `mcenter stores list`.",
                fg="yellow",
                err=True,
            )
        return store

    def client(self) -> MicroCenterClient:
        return MicroCenterClient(self.config)


class ClickUsageError(RuntimeError):
    pass
