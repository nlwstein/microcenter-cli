from __future__ import annotations

import click
from rich.console import Console
from rich.table import Table

from .. import stores as store_table

console = Console()


@click.group()
def stores() -> None:
    """Look up Micro Center store ids."""


@stores.command("list")
def list_stores() -> None:
    """Print the known (best-effort, may be stale) store directory."""
    table = Table(title="Known Micro Center stores")
    table.add_column("ID")
    table.add_column("State")
    table.add_column("City")
    for s in sorted(store_table.STORES.values(), key=lambda s: (s.state, s.city)):
        table.add_row(s.id, s.state, s.city)
    console.print(table)
    console.print(
        "[dim]Best-effort static list — Micro Center opens/closes stores. "
        "If yours is missing, find the id in the site's own store picker and pass "
        "--store <id> directly.[/dim]"
    )


@stores.command("find")
@click.argument("query")
def find_store(query: str) -> None:
    """Find a store id by state/city substring, e.g. `mcenter stores find cambridge`."""
    match = store_table.find(query)
    if match:
        console.print(f"{match.id}  ({match.label})")
    else:
        console.print(f"[yellow]No match for '{query}'.[/yellow] See `mcenter stores list`.")
