# microcenter-cli

CLI, library, and **MCP server** for Micro Center catalog search, drill-down, and
per-store stock + price. No official Micro Center API exists, and no maintained MCP
server or CLI for this was found on GitHub as of 2026-08 — this fills that gap.
Verified end-to-end against live microcenter.com data, not just synthetic fixtures.

Free and open source. If it's useful to you, [Sponsor this project](#support-this-project)
— there's no paid tier, no account, no gated features; sponsorship funds maintenance
(Micro Center's HTML *will* drift again, see [When this breaks](#when-this-breaks)),
not access.

## Agent / MCP support

The flagship use case here is **agentic querying** — an agent comparing prices,
checking stock across stores, or answering "is X in stock near me" shouldn't need a
human driving a browser tab. `mcenter-mcp` exposes the same search/product-lookup
capability the CLI has as MCP tools:

```bash
uv tool install --editable ".[mcp]"   # pulls in the mcp SDK (not a default dependency)
mcenter-mcp                            # stdio transport — point your MCP client at this command
```

Tools exposed: `search_products`, `get_product`, `find_store`, `list_stores` — same
underlying library as the CLI, same session, same rate limiting. Tested against real
multi-step agent tasks (search → filter by stock → drill into `get_product` for the
authoritative answer; comparing the same product's stock across several stores in one
flow) — this is genuinely the thing a generic price-comparison tool doesn't do well,
since most are store-agnostic and Micro Center's actual differentiator is same-day
local pickup.

The one thing MCP doesn't change: an agent still can't bootstrap its own session (see
below) — a human runs `mcenter session interactive` once, same as for the CLI.

## Why this needs a manual step, and always will

microcenter.com sits behind a Cloudflare **Turnstile challenge that is a real "Verify
you are human" checkbox** — not a transparent JS check. Confirmed by hand, in order:

1. Plain `curl`/`requests` with a real browser User-Agent → 403, Cloudflare
   interstitial, even from a residential IP.
2. TLS-impersonated HTTP (`curl_cffi`, Chrome fingerprint) → still 403. Real
   JS-execution challenge, not just TLS/UA fingerprinting.
3. Playwright (headless *and* headed, with `navigator.webdriver` patched and
   `--disable-blink-features=AutomationControlled`) → renders an actual clickable
   checkbox in a `challenges.cloudflare.com` iframe. Clicking it programmatically
   gets accepted for a moment, then **Cloudflare detects the CDP automation
   attachment itself and reverts the checkbox** — confirmed visually, the "Chrome is
   being controlled by automated test software" infobar is present the whole time.

So: no automation tool — headless or headed, Playwright/Puppeteer/Selenium/whatever —
can pass this, because the tell isn't the click, it's that something is driving the
browser via an automation protocol at all. This tool doesn't try to defeat that.

**The only path is a human solving it once in their own, un-automated browser**, then
handing the resulting session to this tool. Two ways to do that:

### Preferred: `session interactive`

```bash
mcenter session interactive                     # auto-detects your OS default browser
mcenter session interactive --browser firefox    # or force one explicitly
```

Opens Micro Center in your actual default browser (via `webbrowser.open` — a normal
OS-level browser launch, no debugging/automation protocol attached at any point).
Solve the checkbox there if you're shown one, come back to the terminal and press
Enter, and the tool reads `cf_clearance` straight out of that browser's own cookie
store (`browser_cookie3`, the same mechanism a password manager or sync extension
uses — not automation, just reading state off disk after the fact). If the check is
still verifying when you press Enter, it asks whether to check again rather than
failing outright.

`--browser` needs to match whatever your OS actually opened — `webbrowser.open`
launches your *default* browser, which isn't necessarily Chrome. Omitting `--browser`
auto-detects it (macOS: reads LaunchServices' registered `http` handler), so this
should just work; pass `--browser` explicitly only if auto-detection guesses wrong or
you're on a non-macOS host (falls back to assuming `chrome` there for now). The tool
also auto-detects a matching User-Agent from the installed browser binary's
`--version` output and remembers which browser was used, so later requests
TLS-impersonate the right one (Chrome vs. Firefox have distinguishable fingerprints).

### Fallback: `session import`

If `browser_cookie3` can't read your profile for some reason:

1. Open https://www.microcenter.com/ in your everyday Chrome/Firefox/Safari.
2. Click "Verify you are human" if shown.
3. DevTools → Network tab → reload → click any request to microcenter.com → Request
   Headers → copy the full `Cookie:` value.
4. Copy your browser's `navigator.userAgent` (DevTools console).
5. `mcenter session import --cookie-header "<paste>" --user-agent "<paste>"`
   (browser is inferred from the UA string automatically).

---

Either way it's cached to `~/.config/microcenter-cli/session.json` (path via
`platformdirs`, permissions forced to `0600` — it holds a live session cookie, treat
it like a credential) and reused as plain TLS-impersonated HTTP (`curl_cffi`) for
every subsequent search/product call — no browser involved for normal use. When the
client gets challenged again (session expired/invalidated), it raises a clear error
telling you to re-run `session interactive` — it does not, and cannot, try to solve
it itself.

Session lifetime is not yet characterized empirically. `session_ttl_seconds` (default
1200s) only controls what `session status` calls "possibly stale" as a heads-up; it
doesn't expire or block anything on its own.

## Install

```bash
uv tool install --editable .            # CLI only
uv tool install --editable ".[mcp]"     # CLI + MCP server (mcenter-mcp)
```

## Usage

```bash
mcenter stores find cambridge                    # -> 121
mcenter search "ryzen 9 3900x" --store 121
mcenter search "ryzen 9 3900x" --store 121 --json
mcenter product 608316 --store 121               # exact price + in-stock for one item
mcenter session status
```

`--store` (and `-v`/`--verbose`) work either before or after the subcommand —
`mcenter search foo --store 121` and `mcenter --store 121 search foo` are both fine.
Set a default store once instead of passing `--store` every time — env var
`MICROCENTER_STORE`, or `default_store` in `config.toml` (see `config.example.toml`,
copy to the path `platformdirs` reports for this app).

### Pagination

Search results are genuinely paginated (parsed from the page's own "1 - 24 of 183
items" status line and `rel="next"` link — not assumed from echoing back request
params, which the site can silently clamp):

```bash
mcenter search ryzen --store 121                        # page 1 only (default)
mcenter search ryzen --store 121 --page 3
mcenter search ryzen --store 121 --per-page 96           # 24/48/96, fewer requests needed
mcenter search ryzen --store 121 --all-pages             # every page, rate-limited
mcenter search ryzen --store 121 --all-pages --per-page 96 --json  # fewest requests, full set
```

`--json` output for a single page is a plain list of results; `--all-pages --json` is
the full concatenated list across every page.

### Robustness

- **Retries**: transient network failures (dropped connection, DNS hiccup, 5xx) retry
  with exponential backoff (`max_retries`, `retry_backoff_seconds` in config). A
  403/challenge is deliberately *never* retried — that means the session is dead, and
  retrying just burns requests against it for nothing.
- **Rate limiting**: a floor (`min_request_interval_seconds`, default 0.75s) between
  consecutive requests, enforced everywhere but especially relevant to `--all-pages`
  firing off several requests back-to-back. Keeps normal use from looking like a burst
  to Cloudflare's bot-management, which is exactly what got us into the session-import
  dance in the first place.
- **Timeouts**: configurable per-request timeout (`request_timeout_seconds`, default 30s).
- **`-v`/`--verbose`**: logs every request/response (method, URL, status, retries) to
  stderr — the first thing to reach for when something's behaving oddly.
- **Clear failure modes**: a nonexistent product id raises a distinct
  `MicroCenterNotFoundError` (HTTP 404) rather than silently returning empty fields; a
  200 response that fails to parse anything useful (structure drift) raises instead of
  silently returning a mostly-`None` result; an unrecognized `--store` id warns but
  doesn't block (Micro Center returns *some* results for an unknown store id rather
  than erroring, so refusing outright would be wrong — the static store table is
  known-incomplete, see `stores.py`).

### Agent / catalog-drilling usage

`search --json` and `product --json` are meant to be chained by an agent: search
broadly (optionally `--all-pages` for the complete result set), pick a `product_id`
from the results, then call `product` for the authoritative price/stock at a specific
store. `mcenter debug fetch <url>` is an escape hatch that returns raw HTML through
the same session-aware client, for cases the structured commands don't cover yet. See
also `.claude/skills/microcenter/SKILL.md` for an agent-oriented usage guide, and
`CLAUDE.md` for the codebase's own conventions/gotchas if you're modifying it.

## What this doesn't do (on purpose)

No purchasing. This is read-only — search, price, stock. Automating an actual
checkout is a much bigger jump in both technical risk (against the same
Cloudflare-protected surface) and trust than catalog lookups, and isn't something
this project does.

## Known limitations

- **No category name lookup.** `--category` only accepts a raw `N=` facet code
  copied from the site's own category-browse URL. A name→code table was attempted
  (transcribed from a years-old reference scraper) and **confirmed wrong** — searching
  "amd processors/cpus" returned laptops and gaming PCs, not CPUs. Micro Center's
  internal category ids have clearly been renumbered since. Rather than ship a
  shortcut that silently returns the wrong category (worse than no shortcut at all),
  it was removed. There's also no way to recalibrate this the way `parser.py` gets
  recalibrated — a plain keyword-search page doesn't expose any live `N=` codes in its
  static HTML to check against.
- **Ratings/review counts are always `None`.** Loaded client-side via a Bazaarvoice
  widget, not present in the raw HTML at all.
- **Store directory is a static, known-incomplete table** (see `stores.py`) — no
  official store-list API exists either.
- **Session lifetime is uncharacterized.** No data yet on how long a `cf_clearance`
  cookie actually stays valid in practice.

## When this breaks

Micro Center's HTML is not a stable contract. `parser.py` documents exactly which
selectors it depends on and how to recalibrate them (`mcenter debug fetch <url> --out
page.html`, diff against what `parser.py` expects — this is exactly how the current
selectors were calibrated, replacing an initial best-guess based on a stale reference
scraper that turned out not to match reality at all). If you start getting
`MicroCenterBlockedError`, that's the session step above — re-run
`mcenter session interactive`.

This is exactly the kind of thing sponsorship funds, and exactly the kind of thing
contributions help with even more directly — if you hit a parsing break, a PR with
the fix (following the recalibration workflow above) is worth more than a report.

## Support this project

Free, open source, no paid tier. If this saves you time — especially if you're
building agent/MCP tooling on top of it — consider sponsoring to help fund the
ongoing maintenance this kind of scraping-adjacent tool inherently needs (Micro
Center's HTML *will* drift; someone has to notice and fix it). No sponsorship tier
unlocks anything — everything here is already unlocked.

## License

MIT — see [LICENSE](LICENSE).

## Repo conventions

Python + Click + rich + `uv`, per the standard homelab CLI tool pattern (see
`lan-ops/portainer-cli` for the reference layout this mirrors). See `CLAUDE.md` for
this repo's specific conventions and gotchas.
