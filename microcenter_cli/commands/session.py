from __future__ import annotations

import time

import click
from rich.console import Console

from .. import session as session_store
from ..context import Ctx

console = Console()

IMPORT_HELP = """
Micro Center's Cloudflare Turnstile checkbox rejects solves from any
automation-controlled browser (Playwright, Puppeteer, Selenium, etc.) even when a
real click is dispatched — it detects the CDP automation attachment itself. So this
has to be a human, in a normal (non-automated) browser, one time:

  1. Open https://www.microcenter.com/ in your everyday Chrome/Firefox/Safari.
  2. Click the "Verify you are human" checkbox if you're shown one.
  3. Open devtools -> Network tab, reload, click any request to microcenter.com.
  4. Under Request Headers, find "Cookie:" and copy its full value.
  5. Also copy your browser's User-Agent (devtools console: `navigator.userAgent`).
  6. Run:  mcenter session import --cookie-header "<paste>" --user-agent "<paste>"
"""


@click.group()
def session() -> None:
    """Manage the imported Cloudflare-cleared session."""


@session.command("status")
@click.pass_obj
def status(ctx: Ctx) -> None:
    """Show whether an imported session exists and how fresh it is."""
    s = session_store.load()
    if not s.cookies:
        console.print("[yellow]No session imported.[/yellow]")
        console.print(IMPORT_HELP)
        return
    fresh = s.is_fresh(ctx.config.session_ttl_seconds)
    state = "[green]fresh[/green]" if fresh else "[yellow]stale (may still work)[/yellow]"
    console.print(f"session: {state}, age {s.age_seconds():.0f}s, ua={s.user_agent[:60]}...")


@session.command("import")
@click.option("--cookie-header", required=True, help="Raw Cookie: header value from devtools.")
@click.option("--user-agent", required=True, help="Your browser's navigator.userAgent.")
def import_cmd(cookie_header: str, user_agent: str) -> None:
    """Import a session solved by hand in a real browser. See `mcenter session status`
    for the copy-paste instructions."""
    cookies = session_store.parse_cookie_header(cookie_header)
    if "cf_clearance" not in cookies:
        console.print(
            "[yellow]warning:[/yellow] no cf_clearance cookie found in what you pasted — "
            "make sure you copied the Cookie header from a request made *after* solving "
            "the checkbox, not before."
        )
    s = session_store.Session(cookies=cookies, user_agent=user_agent, saved_at=time.time())
    session_store.save(s)
    console.print(f"[green]Session imported.[/green] {len(cookies)} cookies cached.")


@session.command("clear")
def clear_cmd() -> None:
    """Delete the cached session."""
    session_store.clear()
    console.print("Session cache cleared.")
