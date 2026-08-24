from __future__ import annotations

import json

import click
from rich.console import Console
from rich.table import Table

from ..context import Ctx
from ..options import apply_verbose, resolve_store, store_option, verbose_option

console = Console()


@click.command()
@click.argument("product_id")
@store_option
@verbose_option
@click.option("--json", "as_json", is_flag=True, help="Emit JSON instead of a summary.")
@click.pass_obj
def product(
    ctx: Ctx,
    product_id: str,
    store_override: str | None,
    verbose_override: bool,
    as_json: bool,
) -> None:
    """Look up exact price + in-stock status for one product id at --store."""
    apply_verbose(ctx, verbose_override)
    store = resolve_store(ctx, store_override)
    detail = ctx.client().product(product_id, store)

    if as_json:
        click.echo(json.dumps(detail.__dict__, indent=2))
        return

    stock = "[green]in stock[/green]" if detail.in_stock else "[red]out of stock[/red]"
    if detail.in_stock is None:
        stock = "[yellow]unknown[/yellow]"
    price = f"${detail.price:.2f}" if detail.price is not None else "unknown"
    console.print(f"[bold]{detail.name or product_id}[/bold]  (store {store})")
    console.print(f"  price: {price}    stock: {stock}    sku: {detail.sku or '-'}")


@click.command()
@click.argument("product_ids", nargs=-1, required=True)
@store_option
@verbose_option
@click.option("--json", "as_json", is_flag=True, help="Emit JSON instead of a table.")
@click.pass_obj
def products(
    ctx: Ctx,
    product_ids: tuple[str, ...],
    store_override: str | None,
    verbose_override: bool,
    as_json: bool,
) -> None:
    """Look up price + in-stock status for several product ids at --store in one
    command -- for verifying a shortlist (e.g. from `search`) without a separate
    `product` call per item. One bad id doesn't abort the rest."""
    apply_verbose(ctx, verbose_override)
    store = resolve_store(ctx, store_override)
    results = ctx.client().products(list(product_ids), store)

    if as_json:
        click.echo(
            json.dumps(
                [
                    {"product_id": r.product_id, "detail": r.detail.__dict__ if r.detail else None, "error": r.error}
                    for r in results
                ],
                indent=2,
            )
        )
        return

    table = Table(title=f"{len(results)} product(s) @ store {store}")
    table.add_column("ID")
    table.add_column("Name", max_width=45)
    table.add_column("Price", justify="right")
    table.add_column("Stock")

    for r in results:
        if r.detail:
            stock = "in stock" if r.detail.in_stock else "out of stock"
            price = f"${r.detail.price:.2f}" if r.detail.price is not None else "-"
            table.add_row(r.product_id, r.detail.name or "-", price, stock)
        else:
            table.add_row(r.product_id, f"[red]error: {r.error}[/red]", "-", "-")
    console.print(table)
