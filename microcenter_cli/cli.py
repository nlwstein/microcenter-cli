"""mcenter — root Click group and shared context."""

from __future__ import annotations

import sys

import click
from curl_cffi.requests import RequestsError

from . import __version__
from .client import MicroCenterBlockedError, MicroCenterError
from .config import ConfigError, load_config
from .context import Ctx


@click.group()
@click.version_option(__version__, prog_name="mcenter")
@click.option("--store", help="Store id to query (overrides config/env default).")
@click.option("-v", "--verbose", is_flag=True, help="Log each request/response to stderr.")
@click.pass_context
def cli(ctx: click.Context, store: str | None, verbose: bool) -> None:
    """Search Micro Center's catalog and check per-store stock/price."""
    config = load_config()
    if verbose:
        config.verbose = True
    ctx.obj = Ctx(config=config, store_id=store)


# subcommands register themselves on import
from .commands import debug as _debug
from .commands import product as _product
from .commands import search as _search
from .commands import session as _session
from .commands import stores as _stores

cli.add_command(_search.search)
cli.add_command(_product.product)
cli.add_command(_product.products)
cli.add_command(_stores.stores)
cli.add_command(_session.session)
cli.add_command(_debug.debug)


def main() -> None:
    """Console-script entry point with friendly error handling.

    click.UsageError (and thus context.ClickUsageError) is deliberately NOT
    caught here -- Click's own standalone-mode invocation (the default for
    calling `cli()` directly, same as under CliRunner in tests) already catches
    it, prints it, and exits with the right code before it would ever reach
    this try/except.
    """
    try:
        cli()
    except ConfigError as exc:
        click.secho(f"error: {exc}", fg="red", err=True)
        sys.exit(1)
    except MicroCenterBlockedError as exc:
        click.secho(f"error: {exc}", fg="red", err=True)
        sys.exit(1)
    except MicroCenterError as exc:
        click.secho(f"error: {exc}", fg="red", err=True)
        sys.exit(1)
    except RequestsError as exc:
        click.secho(f"error: network problem talking to Micro Center: {exc}", fg="red", err=True)
        sys.exit(1)
    except KeyboardInterrupt:
        click.secho("\ninterrupted", fg="yellow", err=True)
        sys.exit(130)
    except Exception as exc:  # noqa: BLE001 - last-resort guard against raw tracebacks
        click.secho(f"error: unexpected: {exc}", fg="red", err=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
