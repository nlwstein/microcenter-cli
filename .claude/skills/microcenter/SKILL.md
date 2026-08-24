---
name: microcenter
description: Look up Micro Center product search results, catalog drill-down, and per-store price/stock via the `mcenter` CLI. Use whenever asked about Micro Center inventory, pricing, or "is X in stock at Micro Center" — there's no official API, this CLI is the working substitute.
---

# Micro Center catalog/stock lookups

`mcenter` (this repo, `lan-ops/microcenter-cli`) is a CLI wrapping Micro Center's
catalog search and per-store stock/price. No official API exists — this reverse-
engineers the public site, verified against live data as of 2026-08.

## Before anything else: is there a session?

```bash
mcenter session status
```

If it says "No session imported" or a command fails with `MicroCenterBlockedError`,
**you cannot fix this yourself.** Micro Center's Cloudflare Turnstile checkbox
rejects any automation-controlled browser outright (confirmed: Playwright with full
stealth patching gets detected and reverted specifically because of the CDP
automation attachment, independent of whether a real click happens). Tell the human:

> Run `mcenter session interactive` (opens Micro Center in your real default
> browser; solve the checkbox if shown, then press Enter in the terminal — make
> sure `--browser` matches whichever browser actually opened, e.g. `--browser
> firefox` if Firefox is your default, not the `chrome` default).

Do not attempt to work around this with your own browser automation, curl, or
anything else — it has been tried and structurally cannot work. See this repo's
`CLAUDE.md` and `README.md` if you want the full evidence trail.

## Once a session exists, it's all plain CLI

```bash
mcenter stores find <city or state>              # look up a store id, e.g. "cambridge" -> 121
mcenter stores list                              # full known store table

mcenter search "<query>" --store <id> --json      # search, JSON for chaining
mcenter search "<query>" --store <id> --all-pages --json   # every page, not just the first
mcenter product <product_id> --store <id> --json  # authoritative price/stock for one item
```

Typical drill-down flow: `search --json` to find candidate `product_id`s, then
`product --json` on the one you actually care about for the authoritative price/
in-stock answer (search-result stock text is a coarser signal than the product page).

`--store` and `-v`/`--verbose` work either before or after the subcommand name. A
default store can be preconfigured (`mcenter stores find <name>` to find the id, then
it's a one-time `default_store` config write) — check `mcenter session status` /
ask the human rather than assuming one is set.

## Interpreting output

- `stock_text` on search results is Micro Center's raw string (e.g. "25 IN STOCK at
  Cambridge Store", "OUT OF STOCK") — don't try to parse a number out of it
  programmatically beyond a rough presence check; use `product`'s `in_stock` boolean
  for a clean yes/no.
- `rating`/`reviews` fields are always `None` — loaded client-side, not available.
- A `--category` flag exists on `search` but **only accepts a raw `N=` facet code**
  copied from the site's own category-browse URL, never a plain name — a name-lookup
  table was tried and confirmed to return wrong categories, so don't invent one.

## If it breaks

- `MicroCenterBlockedError` → session expired, tell the human to re-run
  `mcenter session interactive` (see above). Not something you can fix.
- `MicroCenterNotFoundError` → the product id doesn't exist (typo, or delisted).
- Any other parsing-looking failure (empty results that shouldn't be empty, a
  `MicroCenterError` about not being able to parse a 200 response) → Micro Center's
  HTML has likely drifted again. That's a code change (`parser.py` recalibration via
  `mcenter debug fetch`), not something to route around from the calling side.
