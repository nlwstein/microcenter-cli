from __future__ import annotations

from pathlib import Path

import click
from rich.console import Console

from ..context import Ctx
from ..options import resolve_store, store_option

console = Console()


@click.command()
@click.argument("url")
@store_option
@click.option("--out", "out_path", type=click.Path(path_type=Path), help="Save HTML to a file.")
@click.pass_obj
def debug(ctx: Ctx, url: str, store_override: str | None, out_path: Path | None) -> None:
    """Fetch a raw URL through the session-aware client — for recalibrating
    parser.py when Micro Center changes their HTML."""
    store = resolve_store(ctx, store_override)
    html = ctx.client().raw_fetch(url, store)
    if out_path:
        out_path.write_text(html)
        console.print(f"wrote {len(html)} bytes to {out_path}")
    else:
        click.echo(html)
