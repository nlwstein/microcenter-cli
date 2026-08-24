# microcenter-cli — dev notes

Read `README.md` first for the user-facing picture (why the Cloudflare situation
forces a manual session step, pagination, robustness features). This file is about
working *on* the codebase.

## Commands

```bash
uv pip install -e .              # after any pyproject.toml dependency change
ruff check --fix microcenter_cli/ tests/
pytest -q
mcenter <anything>                # once installed editable, live in .venv/bin/mcenter
```

CI (`.gitlab-ci.yml`) runs exactly `ruff check` + `pytest` on `python:3.12-slim`.
Always run both locally before pushing, and check the pipeline actually went green
(`mcp__gitlab__list_commit_statuses` or the GitLab UI) rather than assuming from a
clean local run alone — CI runs in a different environment (fresh venv, different
Python patch version) than whatever's already installed locally.

## Architecture, briefly

- `session.py` — on-disk cached Cloudflare session (cookies + UA + which browser).
  `~/.config/microcenter-cli/session.json` (via `platformdirs`), forced to `0600`.
- `client.py` — `MicroCenterClient`: TLS-impersonated HTTP (`curl_cffi`) using that
  cached session, with retries/rate-limiting/verbose logging. Never touches a browser.
- `parser.py` — BeautifulSoup extraction from real HTML. The module docstring
  documents the exact current DOM shape and where each field comes from — read it
  before touching selectors, it's not decorative.
- `urls.py` — search/product URL construction. Two non-obvious facts baked in here:
  `/product/<id>/` (no slug) 404s, needs a throwaway slug segment; and pagination
  metadata should never be inferred from echoing back `?page=`/`&rpp=` because the
  site can silently clamp out-of-range values rather than erroring.
- `models.py` — plain dataclasses (`SearchResult`, `ProductDetail`, `SearchPage`).
- `commands/` — one Click command per file, wired into the root group in `cli.py`.
- `options.py` — `--store`/`-v` need to work both before *and* after the subcommand
  name (`mcenter search foo --store 121` reads far more naturally than requiring
  `mcenter --store 121 search foo`, which is all plain Click supports for group-level
  options). Every leaf command that needs either re-declares it via `store_option`/
  `verbose_option` and merges it into `Ctx` via `resolve_store`/`apply_verbose`. If you
  add a new leaf command that talks to the client, wire both in, the same way.

## The Cloudflare situation (don't relitigate this without new evidence)

Confirmed by hand, multiple approaches, documented in detail in README:
plain HTTP → blocked; TLS-impersonated HTTP → still blocked; Playwright (headless
*and* headed, stealth-patched) → renders a real Turnstile checkbox, and clicking it
programmatically gets detected and reverted specifically because of the CDP
automation attachment, not the click itself (visually confirmed: Cloudflare's own
"controlled by automated test software" banner present throughout, verification
resets right after a successful-looking click).

**Conclusion that shaped the whole architecture: no automation tool can solve this,
full stop — not "wasn't clever enough," structurally can't.** Don't spend time trying
harder stealth patches, different CDP flags, non-headless-with-a-real-click, etc. —
already tried, this isn't a fingerprinting problem. If you want to double check
anyway, the fastest confirmation is to open the challenges.cloudflare.com iframe in
any CDP-attached browser and watch it reset after clicking.

The only legitimate path is a human solving it in a genuinely non-automated browser
(`session interactive`, which shells out via `webbrowser.open` — no CDP at all — then
reads the resulting cookie off disk via `browser_cookie3`, the same mechanism a
password manager uses). Don't add a "convenience" auto-bootstrap that secretly uses
Playwright/Selenium/etc. under the hood; it will not work and burns time re-confirming
what's already confirmed.

## Recalibrating parser.py

Micro Center's HTML is not a stable contract and *will* drift again. When it does:

```bash
mcenter debug fetch "<url>" --out /tmp/page.html --store <valid-id>
```

(needs a working session — `mcenter session status` first). Then diff the real
structure against what `parser.py`'s module docstring says it expects, update both
the docstring and the selectors together, and update `tests/test_parser.py`'s
synthetic fixtures to match the new real shape (don't leave stale fixtures passing
against code that no longer matches reality — that's how the original
`div.detail_wrapper`-as-container bug shipped silently in the first place).

The one thing that *doesn't* get fixed this way: category `N=` facet codes. A plain
keyword-search page doesn't expose live category codes in its static HTML at all, so
there's nothing to recalibrate against without more exploration of the category-browse
UI specifically. See README's "Known limitations" — this was tried once, confirmed
wrong (returned laptops for a CPU category), and removed rather than shipped broken.

## Testing conventions

All tests are pure/offline — synthetic HTML fixtures for the parser, monkeypatched
`curl_cffi.requests.get` + `time.sleep` for the retry/rate-limit logic in
`test_client_retry.py`. Nothing in the test suite makes a real network call or
depends on a live session existing. Keep it that way; a test suite that needs a real
Micro Center session to pass isn't one CI can run.

## Version

Bump `pyproject.toml`'s `version` and `microcenter_cli/__init__.py`'s `__version__`
together on notable changes (they're currently both `0.2.0` — search/product/stores/
session commands, pagination, retries/rate-limiting, browser-aware session capture).
