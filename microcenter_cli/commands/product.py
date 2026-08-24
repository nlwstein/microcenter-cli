from __future__ import annotations

import json

import click
from rich.console import Console

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
