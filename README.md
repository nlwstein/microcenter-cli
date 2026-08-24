# microcenter-cli

CLI/library for Micro Center catalog search, drill-down, and per-store stock + price.
No official Micro Center API exists, and no maintained MCP server or CLI for this was
found on GitHub as of 2026-08 — this fills that gap.

## Why this isn't a simple `requests` script

microcenter.com sits behind Cloudflare's **managed bot-detection challenge**
(`cf-mitigated: challenge`), on every route including `/robots.txt`. Confirmed:

- Plain `curl`/`requests` with a real browser User-Agent → 403, Cloudflare
  interstitial (`<title>Just a moment...</title>`), even from a residential IP.
- TLS-impersonated HTTP (`curl_cffi`, Chrome fingerprint) → still 403. This is a real
  JS-execution challenge, not just TLS/UA fingerprinting or IP reputation.

So a real browser JS environment has to clear the challenge at least once. This tool
pays that cost as rarely as possible:

1. **`bootstrap.py`** — the *only* place a browser (Playwright/Chromium) runs. Loads
   the homepage, waits out the challenge, harvests the resulting cookies
   (`cf_clearance` etc.) and User-Agent.
2. Cached to `~/.config/microcenter-cli/session.json` (path via `platformdirs`).
3. **Everything else** — search, catalog drill-down, per-product stock/price — is
   plain TLS-impersonated HTTP (`curl_cffi`) reusing that cached session. No browser
   involved for normal use.
4. If a request comes back challenged anyway (cookie expired/invalidated), the client
   auto-bootstraps once and retries transparently.

Cookie lifetime is not yet characterized empirically — `session_ttl_seconds` (default
1200s) is a conservative starting guess, configurable. Tighten or loosen it once
you've observed how long a real session survives in practice.

## Install

```bash
uv tool install --editable .
playwright install chromium   # one-time, only needed for the bootstrap step
```

## Usage

```bash
mcenter stores find cambridge          # -> 121
mcenter --store 121 search "ryzen 9 3900x"
mcenter --store 121 search "ryzen 9 3900x" --json
mcenter --store 121 product 608316     # exact price + in-stock for one item
mcenter session status
mcenter session bootstrap --no-headless   # watch it solve the challenge, for debugging
```

Set a default store once instead of passing `--store` every time — env var
`MICROCENTER_STORE`, or `default_store` in `config.toml` (see
`config.example.toml`, copy to the path `platformdirs` reports for this app).

### Agent / catalog-drilling usage

`search --json` and `product --json` are meant to be chained by an agent: search
broadly, pick a `product_id` from the results, then call `product` for the
authoritative price/stock at a specific store. `mcenter debug fetch <url>` is an
escape hatch that returns raw HTML through the same session-aware client, for cases
the structured commands don't cover yet.

## When this breaks

Micro Center's HTML is not a stable contract. `parser.py` documents exactly which
selectors it depends on and how to recalibrate them (`mcenter debug fetch <url> --out
page.html`, diff against what `parser.py` expects). If Cloudflare starts hard-failing
the Playwright bootstrap too (e.g. switches to an interactive Turnstile checkbox),
that's a bigger problem — see `bootstrap.py`'s error message for the diagnostic path
(`--no-headless` to watch it).

## Repo conventions

Python + Click + rich + `uv`, per the standard homelab CLI tool pattern (see
`lan-ops/portainer-cli` for the reference layout this mirrors).
