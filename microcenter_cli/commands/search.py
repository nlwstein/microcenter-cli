from __future__ import annotations

import json

import click
from rich.console import Console
from rich.table import Table

from ..context import Ctx
from ..filters import FilterSpec, filter_results
from ..options import apply_verbose, resolve_store, store_option, verbose_option
from ..urls import SORT_OPTIONS, VALID_RESULTS_PER_PAGE

console = Console()


@click.command()
@click.argument("query")
@store_option
@verbose_option
@click.option("--page", default=1, show_default=True, help="Result page number.")
@click.option(
    "--all-pages",
    is_flag=True,
    help="Fetch every page and combine results (rate-limited; see --per-page to reduce "
    "the number of requests needed).",
)
@click.option(
    "--per-page",
    "rpp",
    type=click.Choice([str(n) for n in VALID_RESULTS_PER_PAGE]),
    help=f"Results per page ({', '.join(str(n) for n in VALID_RESULTS_PER_PAGE)}). "
    "Site default applies if omitted.",
)
@click.option(
    "--sort",
    type=click.Choice(list(SORT_OPTIONS)),
    help="Sort order (verified against the site's own 'Sort by' dropdown, not guessed). "
    "Affects which items land on page 1, not just their order within it -- combine with "
    "--all-pages for a true cheapest-first sweep (--sort price-low).",
)
@click.option(
    "--category",
    "category_n",
    help="Raw N= category facet code, copied from the site's own category-browse URL "
    "(no name-lookup table -- Micro Center's category ids drift and a stale mapping "
    "would silently return the wrong category, which is worse than not having one).",
)
@click.option(
    "--in-stock-only", is_flag=True, help="Drop results without a recognized in-stock signal."
)
@click.option("--max-price", type=float, help="Drop results above this price (or with no price).")
@click.option("--min-price", type=float, help="Drop results below this price (or with no price).")
@click.option(
    "--exclude",
    "exclude_terms",
    multiple=True,
    help="Case-insensitive substring to exclude from results (repeatable), e.g. "
    "--exclude laptop --exclude 'gaming pc' to prune non-component results out of a "
    "component search.",
)
@click.option(
    "--category-contains",
    help="Case-insensitive substring match against each result's own category text "
    "(client-side, using the category Micro Center already returned per-item -- not "
    "a guess at their internal facet codes, see --category).",
)
@click.option("--json", "as_json", is_flag=True, help="Emit JSON instead of a table.")
@click.pass_obj
def search(
    ctx: Ctx,
    query: str,
    store_override: str | None,
    verbose_override: bool,
    page: int,
    all_pages: bool,
    rpp: str | None,
    sort: str | None,
    category_n: str | None,
    in_stock_only: bool,
    max_price: float | None,
    min_price: float | None,
    exclude_terms: tuple[str, ...],
    category_contains: str | None,
    as_json: bool,
) -> None:
    """Search the catalog and list matching products with price/stock at --store.

    This is the catalog drill-down entry point: pipe --json output to a second
    `mcenter product <id>` call (or your own logic) to inspect a specific hit
    further.
    """
    apply_verbose(ctx, verbose_override)
    store = resolve_store(ctx, store_override)
    rpp_int = int(rpp) if rpp else None

    if all_pages:
        results = list(
            ctx.client().search_all(query, store, category_n=category_n, rpp=rpp_int, sort=sort)
        )
        meta_note = f"{len(results)} results across all pages"
    else:
        result_page = ctx.client().search_page(
            query, store, page=page, category_n=category_n, rpp=rpp_int, sort=sort
        )
        results = result_page.results
        total = result_page.total_items
        meta_note = (
            f"page {page}"
            + (f"/{result_page.total_pages}" if result_page.total_pages else "")
            + (f", {total} total" if total is not None else "")
        )

    spec = FilterSpec(
        in_stock_only=in_stock_only,
        max_price=max_price,
        min_price=min_price,
        exclude=exclude_terms,
        category_contains=category_contains,
    )
    unfiltered_count = len(results)
    results = filter_results(results, spec)
    if not spec.is_noop and unfiltered_count != len(results):
        meta_note += f", {len(results)} after filters"

    if as_json:
        click.echo(json.dumps([r.__dict__ for r in results], indent=2))
        return

    if not results:
        console.print(f"[yellow]No results for '{query}' at store {store}.[/yellow]")
        return

    table = Table(title=f"'{query}' @ store {store} ({meta_note})")
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
