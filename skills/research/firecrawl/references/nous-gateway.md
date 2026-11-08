# Firecrawl CLI on the Mac Studio — Nous Tool Gateway route

## Why this exists

The direct Firecrawl key (`FIRECRAWL_API_KEY` in `~/.hermes/.env`) sits on the
free plan: 1000 credits per billing cycle. Mid-cycle the balance hits 0 and
every direct call returns **HTTP 402 Payment Required** until the cycle resets.
That failure is not obvious from the CLI — calls just fail.

The Nous Portal already covers Firecrawl on its Tool Gateway, so the CLI can
ride the subscription instead of a spent free tier.

## What is installed

| Path | What |
|---|---|
| `~/.local/bin/firecrawl-nous` | wrapper: mints a Nous token, sets gateway URL + key, execs the real CLI |
| `~/.local/bin/firecrawl` | symlink to `firecrawl-nous`, so plain `firecrawl` uses the gateway (`~/.local/bin` precedes `/opt/homebrew/bin` on PATH) |
| `/opt/homebrew/bin/firecrawl` | the real CLI (`firecrawl-cli`) |

The wrapper reads a live Nous Subscriber OAuth token via
`tools.managed_tool_gateway.read_nous_access_token()` from the Hermes checkout at
`~/.hermes/hermes-agent`. That call refreshes the token when it nears expiry, so
there is no hardcoded token and nothing to re-auth by hand. It then exports:

```
FIRECRAWL_API_URL=https://firecrawl-gateway.nousresearch.com
FIRECRAWL_API_KEY=<live Nous access token>
```

## Gotchas

- `firecrawl --status` and `firecrawl credit-usage` **cannot read account info**
  through the gateway; the gateway serves no team/credit endpoint. Expect
  "Could not fetch account info" and an empty credit prompt. Not a failure.
- Direct-plan balance (the only way to see it):
  `curl -s -H "Authorization: Bearer $FIRECRAWL_API_KEY" https://api.firecrawl.dev/v2/team/credit-usage`
- Nous balance: `GET https://portal.nousresearch.com/api/oauth/account` with the
  token at `credential_pool.nous[0].access_token` in `~/.hermes/auth.json`.
- `~/.hermes/.env` is **not** auto-exported into Hermes terminal sessions, so a
  bare `firecrawl` sees no key unless the wrapper supplies one.
- Do **not** put the gateway origin in `~/.hermes/.env` as `FIRECRAWL_API_URL`.
  The Hermes web tools' direct path also reads that key, and it would pair the
  gateway origin with the wrong credential. The wrapper is deliberately CLI-only.
- The wrapper writes nothing to disk; it is safe to re-run and safe to delete.

## Bypass / revert

Direct route (works only with plan credits, and the only route that reports balance):

```bash
FIRECRAWL_API_KEY="$(grep -E '^FIRECRAWL_API_KEY=' ~/.hermes/.env | cut -d= -f2-)" \
  /opt/homebrew/bin/firecrawl --status
```

Drop the shadow so plain `firecrawl` is direct again, keeping the wrapper available:

```bash
rm ~/.local/bin/firecrawl
```

Full revert: also delete `~/.local/bin/firecrawl-nous`.

## Related surface (not the CLI)

Hermes' own `web_search` / `web_extract` tools are routed separately by
`config.yaml`:

```yaml
web:
  backend: nous
  search_backend: nous
```

That managed selection names no provider directly: the registry maps it to
**Perplexity for search** (served by the gateway to any Nous identity, no
funding check) and **Firecrawl for extract** (billed). Both require the
matching vendored plugin enabled — `web/perplexity` for search and
`web/firecrawl` for extract. A stale process registry after enabling a plugin
needs a restart; `python -c` in a fresh process is the way to confirm the
runtime resolution.
