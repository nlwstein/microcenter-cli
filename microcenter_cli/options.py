"""Shared --store option for leaf commands.

Click only accepts group-level options (`--store` on `cli`) *before* the
subcommand name, e.g. `mcenter --store 121 search ryzen`, which surprises anyone
used to `--store` working anywhere. Every leaf command that needs a store also
takes its own --store, in the position people actually reach for
(`mcenter search ryzen --store 121`), and it overrides the group-level one when
both are given.
"""

from __future__ import annotations

from typing import TypeVar

import click

from .context import Ctx

F = TypeVar("F", bound=click.decorators.FC)


def store_option(f: F) -> F:
    return click.option(
        "--store", "store_override", help="Store id to query (overrides group/config default)."
    )(f)


def resolve_store(ctx: Ctx, store_override: str | None) -> str:
    if store_override:
        ctx.store_id = store_override
    return ctx.resolve_store()
