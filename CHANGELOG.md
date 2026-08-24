# CHANGELOG


## v0.2.1 (2026-08-24)

### Bug Fixes

- Get_products/list_stores silently dropped all but the first result
  ([`db55f77`](https://github.com/nlwstein/microcenter-cli/commit/db55f77ac94afe337339d0518ae84e66658b0e84))

Real bug, found live while manually testing the MCP tools end-to-end (not manufactured to trigger
  the release pipeline): both tools returned a bare list[dict]. The MCP framework serializes a bare
  list return as one content block *per item*, not one block containing the JSON array. Any client
  doing the natural json.loads(result.content[0].text) -- which is exactly what an agent or this
  project's own test client does -- silently got only the first result and never knew the rest
  existed. search_products was unaffected; it already returned a dict.

Fixed by wrapping both in a dict ({"results": [...]}, {"stores": [...]}), matching the pattern
  search_products already used. Confirmed against a real stdio MCP client session, not just by
  inspection: get_products with 3 ids (one deliberately bad) now returns all 3 in one content block.

Added a regression test that checks the actual serialized content-block count via call_tool(), not
  just the Python-level return type -- reading the source wouldn't have caught this, only exercising
  the real protocol did.

61 tests passing (was 60).

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>

### Chores

- Add PyPI publishing via python-semantic-release
  ([`eefc2ae`](https://github.com/nlwstein/microcenter-cli/commit/eefc2ae0b329c388599af3d1acf3012efbbf9c19))

.github/workflows/release.yml: on push to main, re-runs the same test gate as test.yml
  (self-contained, not a cross-workflow dependency), then python-semantic-release computes the
  version bump from conventional commits since the v0.2.0 baseline tag
  (docs:/chore:/test:/ci:/refactor: don't trigger a release, only feat/fix/perf/breaking changes
  do), updates pyproject.toml + microcenter_cli/__init__.py, tags, creates a GitHub Release, and
  publishes to PyPI via Trusted Publishing (OIDC, no stored token).

Deliberately a chore: commit -- doesn't trigger a release itself. One thing that still needs a
  human: registering this workflow as a Trusted Publisher on the PyPI project page (pypi.org account
  required, can't be done via CLI). Until that's done, the release job will succeed through the
  version-bump/tag/ GitHub-Release steps but the final PyPI publish step will fail -- expected, not
  a bug, just means "not wired up to PyPI yet."

Verified locally: `semantic-release version --print-last-released` correctly resolves the v0.2.0
  baseline tag; config validated against the actual installed python-semantic-release rather than by
  inspection alone.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>


## v0.2.0 (2026-08-24)

### Bug Fixes

- Allow --store on subcommands, not just before them
  ([`0d23bb2`](https://github.com/nlwstein/microcenter-cli/commit/0d23bb224e0a500c06624cd3e037231bd65d722c))

Click only accepted --store on the root group (mcenter --store 121 search ...), which nobody reaches
  for instinctively -- mcenter search ryzen --store 121 errored. search/product/debug now each take
  their own --store too, overriding the group/config default when given.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>

- Ci wasn't installing the mcp extra or linting tests/
  ([`7609ed2`](https://github.com/nlwstein/microcenter-cli/commit/7609ed2367f804781bde5d594569281f842a527a))

Would have failed on this exact commit's own test_mcp_server.py (ModuleNotFoundError: mcp) once the
  pipeline actually ran. Also: ruff check never covered tests/ despite linting it locally as a
  matter of course all session -- fixed both.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>

- Don't leak the session cookie to arbitrary hosts, warn on truncated --all-pages
  ([`83a0df7`](https://github.com/nlwstein/microcenter-cli/commit/83a0df7c1df5d9565add12ca3198f39380337d75))

- `mcenter debug fetch <url>` accepted any URL but attached the live session cookie regardless --
  cf_clearance is effectively a bearer credential, and `debug fetch https://evil.example/` would
  have handed it over. All requests now check the URL's host is microcenter.com or a subdomain
  before attaching cookies; anything else raises immediately without ever sending the request. -
  search_all() hitting its MAX_AUTO_PAGES safety cap now warns to stderr instead of silently
  returning a truncated result set that looks complete.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>

- Drop non-viable Playwright auto-bootstrap for manual session import
  ([`f66bd40`](https://github.com/nlwstein/microcenter-cli/commit/f66bd403285d72a768cf7eb959a5a4e09352ed44))

Confirmed by hand (headless and headed Playwright, stealth-patched navigator.webdriver,
  --disable-blink-features=AutomationControlled): Micro Center's Cloudflare Turnstile is a real
  'verify you are human' checkbox that rejects solves from any CDP-automated browser regardless of
  whether a real click is dispatched -- it detects the automation attachment itself, not the click.
  So there is no automatable bootstrap for this, full stop.

Replaced with: a human solves the checkbox once in their own real browser, copies the Cookie header
  + User-Agent out of devtools, and hands them to `mcenter session import`. The client now detects a
  stale/rejected session and raises a clear, actionable error instead of trying to self-heal.

Drops the playwright dependency entirely.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>

- Github Actions workflow venv, not --system install
  ([`721b984`](https://github.com/nlwstein/microcenter-cli/commit/721b984e841293293ce7b49b9c6074ba22d88d32))

Ubuntu's system Python is PEP 668 'externally managed' -- unlike the python:3.12-slim image
  .gitlab-ci.yml runs in, --system install refused outright. Switched to a real uv-managed venv + uv
  run. Verified locally with nektos/act (upgraded 0.2.62 -> 0.2.89) before pushing again, not just
  by inspection this time.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>

- Make session capture browser-aware (Firefox, Edge, not just Chrome)
  ([`e64c3d2`](https://github.com/nlwstein/microcenter-cli/commit/e64c3d283b017372a162f33f877a625802d89695))

session interactive defaulted --browser to chrome, so solving the checkbox in a different default
  browser (e.g. Firefox) read an empty cookie jar. Now:

- Session records which browser was used - detect_user_agent() supports Chrome/Firefox/Edge on
  macOS, not just Chrome - client.py picks curl_cffi's matching impersonation profile (chrome vs
  firefox TLS/HTTP2 fingerprint) based on which browser solved it - manual `session import` infers
  browser from the pasted User-Agent

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>

- Recalibrate parser against real captured HTML
  ([`14d3e46`](https://github.com/nlwstein/microcenter-cli/commit/14d3e46846e2a74730aae8fa30e0c702307be7c5))

Verified live with a real imported session (mcenter debug fetch):

- Search results: the per-tile container is div.result_right, not div.detail_wrapper -- stock/price
  live in a sibling price_wrapper div, not inside detail_wrapper. The data-id/data-name/etc. anchor
  is nested inside detail_wrapper > div.h2, not the first <a> in the tile (that's an empty
  Compare-checkbox link). This is why search was returning all-empty rows. - Ratings/reviews are
  loaded client-side via Bazaarvoice and aren't in the raw HTML at all -- fields kept for compat,
  always None now, documented why. - Product page var-extraction (inStock/productPrice/sku) already
  matched reality, just fixed the title-cleanup separator (' - Micro Center', not ' | Micro
  Center'). - product_url(): a bare /product/<id>/ 404s, needs a throwaway slug segment (Micro
  Center matches by id and ignores the slug text itself).

Confirmed end-to-end against microcenter.com: 'mcenter search ryzen' and 'mcenter product 691349'
  both return correct real price/stock/name data.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>

- Validate/clamp config values, URL-escape store_id/product_id/category
  ([`6cf097d`](https://github.com/nlwstein/microcenter-cli/commit/6cf097d37edd96550412f378d62547415f2ac635))

- A typo'd config.toml value (e.g. request_timeout_seconds = 0) previously failed deep inside
  curl_cffi with a cryptic error. Now clamped to a sane minimum at load time with a clear stderr
  warning naming the actual field. - Malformed config.toml (bad TOML syntax) now raises a clear
  ConfigError naming the file, instead of an unhandled TOMLDecodeError traceback. -
  store_id/category_n/product_id are now quote_plus'd into URLs instead of interpolated raw -- a
  stray '&' or '#' in any of them could otherwise have injected extra query params or truncated the
  URL.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>

### Chores

- Add MIT license
  ([`c245828`](https://github.com/nlwstein/microcenter-cli/commit/c24582862d198493ac82573c24e655f98ebeacdf))

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>

### Continuous Integration

- Add GitHub Actions test workflow, mirroring .gitlab-ci.yml
  ([`8090afa`](https://github.com/nlwstein/microcenter-cli/commit/8090afa198dbe23e106eec96e567b37ac992df9a))

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>

### Documentation

- Fix inaccurate claim in CLAUDE.md about past CI failures
  ([`09a893d`](https://github.com/nlwstein/microcenter-cli/commit/09a893dcd9a6c4c2d03857db9b0e41000c5c9eab))

Every pipeline in this repo's history has actually passed -- the line claiming lint-only failures
  had passed tests but failed CI before was not true and shouldn't have been written. Replaced with
  the real (still valid) reason to check CI rather than trust a local run: different environment.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>

- Remove Support this project / sponsorship section
  ([`1b2a8a0`](https://github.com/nlwstein/microcenter-cli/commit/1b2a8a0fd4ebb93d6f2e7f3d5741643f69c08f8e))

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>

### Features

- Add session interactive command to auto-capture cookies from a real browser
  ([`8b5751e`](https://github.com/nlwstein/microcenter-cli/commit/8b5751ec7e2e16d0cb2b3f45777449430a5eb924))

Adds `mcenter session interactive`: opens Micro Center in the user's actual default browser via
  webbrowser.open (a plain OS-level launch, no CDP/automation protocol attached at any point), waits
  for the human to clear the Turnstile checkbox and confirm in the terminal, then reads cf_clearance
  straight out of that browser's own cookie store via browser_cookie3 -- the same mechanism a
  password manager or sync extension uses, not automation.

Also auto-detects a matching User-Agent from the installed Chrome binary's --version output, so it
  lines up with whichever version actually solved the challenge.

The existing manual `session import` (paste a devtools Cookie header) stays as a documented fallback
  for setups browser_cookie3 can't read.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>

- Auto-detect OS default browser for session interactive
  ([`03e834b`](https://github.com/nlwstein/microcenter-cli/commit/03e834b5b82d1a78b0da08cce6407e62a6d0d0c0))

Previously defaulted --browser to 'chrome' unconditionally, which produced a confusing 'no
  cf_clearance found' error for anyone whose default browser isn't Chrome (hit this live: user's
  default is Firefox). Now reads macOS LaunchServices' registered http-scheme handler (defaults read
  ... LSHandlers) and maps the bundle id to a browser_cookie3 name automatically; --browser still
  available to override. Falls back to 'chrome' on non-macOS or an unrecognized handler.

Also: session interactive no longer fails outright on the first check if the challenge is still
  verifying (matches the site's own 'this may take a few seconds' messaging) -- asks whether to
  check again instead of forcing a full command re-run.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>

- Initial scaffold for Micro Center catalog/stock CLI
  ([`9d5ece9`](https://github.com/nlwstein/microcenter-cli/commit/9d5ece905e58d9038a9df701d471f6aa699e0ea6))

- session-cache client: Playwright bootstrap only on cold start/expiry, plain TLS-impersonated HTTP
  (curl_cffi) for everything else - search/product/stores/session/debug commands (Click + rich) -
  parser.py against known-good DOM structure, with a documented recalibration path (mcenter debug
  fetch) since Micro Center's HTML is unversioned and will drift

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>

- Mcp server support; reposition README for open-source + sponsorship
  ([`9f49d5d`](https://github.com/nlwstein/microcenter-cli/commit/9f49d5d468a60f14997d9378d8b3069f0c51aba4))

Adds microcenter_cli/mcp_server.py: search_products/get_product/find_store/ list_stores as MCP
  tools, thin wrapper over the existing MicroCenterClient -- no new logic, just an MCP transport on
  top of what already existed. Optional dependency (`pip install ".[mcp]"`), new mcenter-mcp console
  script.

Validated against real multi-step agent tasks before committing (search -> filter by stock -> drill
  into get_product for the authoritative answer; comparing one product's stock across several stores
  in one flow -- the actual differentiator vs. generic price trackers, since Micro Center's real
  advantage is same-day local pickup and most trackers are store-agnostic).

README repositioned: leads with the MCP/agentic use case as the flagship capability, adds a "Support
  this project" section (free/open-source, no paid tier -- sponsorship funds maintenance, doesn't
  gate anything), and an explicit "no purchasing" scope note. Reflects a deliberate choice to
  publish this openly rather than build a paid product on top of it: Micro Center's own Terms of Use
  prohibit commercial use/transfer of scraped materials to third parties, which a hosted paid
  service does and a published open-source tool that each user runs for themselves does not.

42 tests passing (was 39).

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>

- Real pagination, retry/rate-limit robustness, browser-aware TLS, docs+skill (v0.2.0)
  ([`7466b60`](https://github.com/nlwstein/microcenter-cli/commit/7466b60d2a38d13e349a47d4a8bbb83d8afb9b22))

Pagination: - parser.parse_search_page() extracts total_items/items_per_page/has_next from the
  page's own status line + rel=next link (not from echoing back request params, which the site can
  silently clamp) - client.search_page() / search_all() (auto-paginating generator, rate-limited,
  capped at MAX_AUTO_PAGES=50 as a safety net independent of site metadata) - search command:
  --page, --all-pages, --per-page {24,48,96} - Verified live: 183-item 'ryzen' search, 8 pages @
  24/page or 2 @ 96/page, all unique ids either way

Robustness: - Retries w/ exponential backoff for transient network errors and 5xx only -- never for
  403/challenge, which just means the session is dead - Rate limiting: enforced minimum gap between
  consecutive requests - Configurable timeout/retries/backoff/rate-limit via config.toml -
  -v/--verbose request logging to stderr (also fixed to work as a per-command flag, not just
  group-level, same fix already applied to --store) - MicroCenterNotFoundError for real 404s instead
  of silently-empty fields; MicroCenterError when a 200 fails to parse anything useful (structure
  drift) - Non-blocking store-id validation warning (confirmed MC tolerates unknown store ids rather
  than erroring, so this can't be a hard failure) - session.json forced to 0600 (it holds a live
  session cookie) - session interactive/import now remember which browser solved the challenge and
  curl_cffi-impersonates the matching TLS/HTTP2 fingerprint (chrome vs. firefox), instead of always
  assuming chrome - Fixed double-encoded HTML entities (literal '&quot;' in some product names) -
  Fixed product_url() 404ing on a bare /product/<id>/ with no slug segment - Attempted a category
  name->N=code lookup table; confirmed it returns wrong categories (renumbered since the reference
  scraper), removed rather than shipped broken -- see README Known Limitations

Docs: - README rewritten: pagination, robustness, known limitations, current state - CLAUDE.md:
  dev-facing conventions, the Cloudflare investigation writeup (so it isn't re-litigated),
  recalibration workflow - .claude/skills/microcenter/SKILL.md: agent-facing usage guide

Tests: 15 passing (was 6) -- pagination fixtures, retry/rate-limit logic via monkeypatched
  curl_cffi.requests.get, entity-unescaping.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>

- Sort, client-side filtering, and batch product lookup
  ([`598ed92`](https://github.com/nlwstein/microcenter-cli/commit/598ed92b4eb786192ab71cffcb552c9acde2e081))

Directly from dogfooding the tool on a real "cheapest desktop build" task and noting the friction:

- urls.py: --sort (match/rating/reviews/price-low/price-high/newest), values verified live against
  the site's own "Sort by" dropdown, not guessed. Affects which items land on a page, not just their
  order -- combine with --all-pages for a true cheapest-first sweep. - filters.py: new pure,
  offline-testable module for --in-stock-only, --max-price/--min-price, --exclude (repeatable
  substrings), and --category-contains -- applied client-side to fields already parsed from a real
  response. Deliberately not another guessed N= facet code (see the category-lookup postmortem in
  README/CLAUDE.md) -- this can't return the wrong category, worst case it filters nothing. -
  client.products() / CLI `products` command / MCP get_products: batch product() lookup for
  verifying a shortlist in one call instead of N, with per-item error isolation (one bad id doesn't
  fail the batch). - search_products (MCP) gained the same sort/filter params as the CLI, plus a
  results_before_filter count so an agent can tell filtering actually ran.

Live-verified against real inventory: sorted+filtered DDR4 search, batch lookup of a real 3-part
  shortlist. Also surfaced a good, honest limitation worth knowing: --exclude "so-dimm" didn't catch
  "Laptop Memory Kit" listings that aren't literally labeled SO-DIMM -- the filter is
  exact-substring, not semantic, exactly as documented.

60 tests passing (was 42): test_filters.py, test_urls.py new; test_cli.py and test_mcp_server.py
  extended for the new flags/tool.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>

### Testing

- Add CLI-level wiring tests via CliRunner; make ClickUsageError a real click.UsageError
  ([`c518d04`](https://github.com/nlwstein/microcenter-cli/commit/c518d04d3d269649b76d767b0e5d191174afc4be))

Adds tests/test_cli.py: 11 tests exercising the actual Click command wiring with a fake client (no
  network), specifically including a regression test for --store working both before and after the
  subcommand name -- the exact class of bug that shipped for real earlier in this session (pure
  client/parser unit tests didn't and wouldn't catch it).

Writing these surfaced that ClickUsageError being a plain RuntimeError meant it only got clean
  formatting through cli.py's main() wrapper, not through Click's own standalone-mode invocation
  (which is what CliRunner uses, and what the raw `cli()` call in main() already goes through too,
  unbeknownst to that surrounding try/except). Made it a real click.UsageError instead: Click's own
  machinery now handles it consistently everywhere, prints a Usage:/--help hint for free, and uses
  the conventional exit code 2 instead of 1. Removed the now-dead except ClickUsageError branch from
  main().

37 tests passing total (was 26).

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>

- Cover cli.main()'s exception-translation wrapper directly
  ([`1298c8e`](https://github.com/nlwstein/microcenter-cli/commit/1298c8ef5030c48e38d76760e890b29c1832b471))

test_cli.py exercises Click's own error handling via CliRunner, which never goes through main()
  itself (main() calls cli() the same way CliRunner does internally, so its surrounding try/except
  was previously only verified by hand). Adds direct tests invoking main() with a fake client
  raising MicroCenterBlockedError / MicroCenterNotFoundError, asserting clean stderr output, exit
  code 1, and no traceback.

39 tests passing total (was 37).

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
