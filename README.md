# microcenter-cli

CLI/library for Micro Center catalog search, drill-down, and per-store stock + price.
No official Micro Center API exists, and no maintained MCP server or CLI for this was
found on GitHub as of 2026-08 — this fills that gap.

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
mcenter session interactive
```

Opens Micro Center in your actual default browser (via `webbrowser.open` — a normal
OS-level browser launch, no debugging/automation protocol attached at any point).
Solve the checkbox there if you're shown one, come back to the terminal and press
Enter, and the tool reads `cf_clearance` straight out of that browser's own cookie
store (`browser_cookie3`, the same mechanism a password manager or sync extension
uses — not automation, just reading state off disk after the fact). Defaults to
Chrome; pass `--browser firefox` etc. for others.

### Fallback: `session import`

If `browser_cookie3` can't read your profile for some reason:

1. Open https://www.microcenter.com/ in your everyday Chrome/Firefox/Safari.
2. Click "Verify you are human" if shown.
3. DevTools → Network tab → reload → click any request to microcenter.com → Request
   Headers → copy the full `Cookie:` value.
4. Copy your browser's `navigator.userAgent` (DevTools console).
5. `mcenter session import --cookie-header "<paste>" --user-agent "<paste>"`

---

Either way it's cached to `~/.config/microcenter-cli/session.json` (path via
`platformdirs`) and reused as plain TLS-impersonated HTTP (`curl_cffi`) for every
subsequent search/product call — no browser involved for normal use. When the client
gets challenged again (session expired/invalidated), it raises a clear error telling
you to re-run `session interactive` — it does not, and cannot, try to solve it
itself.

Session lifetime is not yet characterized empirically. `session_ttl_seconds` (default
1200s) only controls what `session status` calls "possibly stale" as a heads-up; it
doesn't expire or block anything on its own.

## Install

```bash
uv tool install --editable .
```

## Usage

```bash
mcenter stores find cambridge          # -> 121
mcenter --store 121 search "ryzen 9 3900x"
mcenter --store 121 search "ryzen 9 3900x" --json
mcenter --store 121 product 608316     # exact price + in-stock for one item
mcenter session status
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
page.html`, diff against what `parser.py` expects). If you start getting
`MicroCenterBlockedError`, that's the session step above — re-run
`mcenter session interactive`.

## Repo conventions

Python + Click + rich + `uv`, per the standard homelab CLI tool pattern (see
`lan-ops/portainer-cli` for the reference layout this mirrors).
