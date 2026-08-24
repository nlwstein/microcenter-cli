from __future__ import annotations

import time
import webbrowser

import click
from rich.console import Console

from .. import session as session_store
from ..context import Ctx

console = Console()

MICROCENTER_HOME = "https://www.microcenter.com/"

MANUAL_IMPORT_HELP = """
Fallback if `mcenter session interactive` doesn't work for your setup (e.g. Chrome
not installed, or browser_cookie3 can't read your profile):

  1. Open https://www.microcenter.com/ in your everyday Chrome/Firefox/Safari.
  2. Click the "Verify you are human" checkbox if you're shown one.
  3. Open devtools -> Network tab, reload, click any request to microcenter.com.
  4. Under Request Headers, find "Cookie:" and copy its full value.
  5. Also copy your browser's User-Agent (devtools console: `navigator.userAgent`).
  6. Run:  mcenter session import --cookie-header "<paste>" --user-agent "<paste>"
"""

NO_SESSION_HELP = f"""
No usable session yet. Run:

  mcenter session interactive

That opens Micro Center in your actual, normal (non-automated) browser -- solve the
"Verify you are human" checkbox there if shown, come back to this terminal and press
Enter, and the cookie gets read straight out of your browser's own cookie store.
{MANUAL_IMPORT_HELP}"""


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
        console.print(NO_SESSION_HELP)
        return
    fresh = s.is_fresh(ctx.config.session_ttl_seconds)
    state = "[green]fresh[/green]" if fresh else "[yellow]stale (may still work)[/yellow]"
    console.print(f"session: {state}, age {s.age_seconds():.0f}s, ua={s.user_agent[:60]}...")


@session.command("interactive")
@click.option(
    "--browser",
    default="chrome",
    show_default=True,
    help="Which installed browser to read the cookie back out of (see browser_cookie3 "
    "for supported names: chrome, firefox, edge, safari, ...).",
)
def interactive_cmd(browser: str) -> None:
    """Open Micro Center in your real browser, wait for you to clear any Cloudflare
    check, then read the resulting session cookie straight out of that browser's own
    (already-installed, non-automated) cookie store.

    This never attaches an automation protocol to the browser at any point -- it's
    just your browser doing what it normally does, plus this tool reading its cookie
    jar afterward, the same way a password manager or sync extension would.
    """
    console.print(f"Opening {MICROCENTER_HOME} in your default browser...")
    webbrowser.open(MICROCENTER_HOME)
    click.prompt(
        "Solve the 'Verify you are human' check if you're shown one, wait for the "
        "page to finish loading normally, then press Enter here",
        default="",
        show_default=False,
        prompt_suffix=" ",
    )

    try:
        s = session_store.from_installed_browser(browser=browser)
    except session_store.BrowserCookieError as exc:
        console.print(f"[red]error:[/red] {exc}")
        console.print(MANUAL_IMPORT_HELP)
        raise SystemExit(1) from None

    session_store.save(s)
    ua_note = f", ua detected: {s.user_agent[:60]}..." if s.user_agent else " (UA not detected)"
    console.print(f"[green]Session captured.[/green] {len(s.cookies)} cookies cached{ua_note}")


@session.command("import")
@click.option("--cookie-header", required=True, help="Raw Cookie: header value from devtools.")
@click.option("--user-agent", required=True, help="Your browser's navigator.userAgent.")
def import_cmd(cookie_header: str, user_agent: str) -> None:
    """Manually import a session by pasting a Cookie header (fallback for when
    `session interactive` doesn't work). See `mcenter session status` for the steps."""
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
