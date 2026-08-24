from __future__ import annotations

import json

import click
from rich.console import Console
from rich.table import Table

from ..context import Ctx

console = Console()


@click.command()
@click.argument("query")
@click.option("--page", default=1, show_default=True, help="Result page number.")
@click.option("--category", "category_n", help="Micro Center category N= facet value.")
@click.option("--json", "as_json", is_flag=True, help="Emit JSON instead of a table.")
@click.pass_obj
def search(ctx: Ctx, query: str, page: int, category_n: str | None, as_json: bool) -> None:
    """Search the catalog and list matching products with price/stock at --store.

    This is the catalog drill-down entry point: pipe --json output to a second
    `mcenter product <id>` call (or your own logic) to inspect a specific hit
    further.
    """
    store = ctx.resolve_store()
    results = ctx.client().search(query, store, page=page, category_n=category_n)

    if as_json:
        click.echo(json.dumps([r.__dict__ for r in results], indent=2))
        return

    if not results:
        console.print(f"[yellow]No results for '{query}' at store {store}.[/yellow]")
        return

    table = Table(title=f"'{query}' @ store {store} (page {page})")
    table.add_column("ID")
    table.add_column("Name", max_width=50)
    table.add_column("Price", justify="right")
    table.add_column("Stock")
    table.add_column("Brand")

    for r in results:
        table.add_row(
            r.product_id,
            r.name,
            f"${r.price:.2f}" if r.price is not None else "-",
            r.stock_text or "-",
            r.brand or "-",
        )
    console.print(table)
