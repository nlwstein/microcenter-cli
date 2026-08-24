from __future__ import annotations

import click
from rich.console import Console

from .. import session as session_store
from ..context import Ctx

console = Console()


@click.group()
def session() -> None:
    """Manage the cached Cloudflare-cleared session (the only thing that opens a browser)."""


@session.command("status")
@click.pass_obj
def status(ctx: Ctx) -> None:
    """Show whether a cached session exists and how fresh it is."""
    s = session_store.load()
    if not s.cookies:
        console.print("[yellow]No cached session. Run `mcenter session bootstrap`.[/yellow]")
        return
    fresh = s.is_fresh(ctx.config.session_ttl_seconds)
    state = "[green]fresh[/green]" if fresh else "[yellow]stale[/yellow]"
    console.print(f"session: {state}, age {s.age_seconds():.0f}s, ua={s.user_agent[:60]}...")


@session.command("bootstrap")
@click.option(
    "--no-headless",
    is_flag=True,
    help="Show the browser window (useful for debugging a failing challenge solve).",
)
def bootstrap_cmd(no_headless: bool) -> None:
    """Force a fresh Cloudflare-challenge solve via Playwright and cache the result."""
    from .. import bootstrap

    console.print("Launching browser to clear Cloudflare...")
    s = bootstrap.bootstrap(headless=not no_headless)
    session_store.save(s)
    console.print(f"[green]Session bootstrapped.[/green] {len(s.cookies)} cookies cached.")


@session.command("clear")
def clear_cmd() -> None:
    """Delete the cached session, forcing a re-bootstrap on next use."""
    session_store.clear()
    console.print("Session cache cleared.")
