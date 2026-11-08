---
name: hermes-infrastructure
description: "Hermes infrastructure configuration and troubleshooting."
version: 1.0.0
license: MIT
author: Hermes Curator
tags: [hermes, configuration, gateway, dashboard, webui, memory, backup, multiplexing, troubleshooting]
metadata:
  hermes:
    tags: [hermes, configuration, gateway, dashboard, webui, memory, backup, multiplexing, troubleshooting]
---

# Hermes Infrastructure

This umbrella covers configuration and troubleshooting of Hermes Agent infrastructure: gateway processes, multi-profile setups, dashboard authentication, WebUI issues, memory providers, configuration management, backup strategies, desktop plugins, themes, and TUI widgets.

Consolidates the former `hermes-troubleshooting` skill.

## When to Use

- Gateway not connecting or restarting frequently
- "Invalid API key" errors on port 8642
- Profile switching shows "disconnected gateway"
- Dashboard login loop or auth failures
- WebUI 409 agent_runtime_stale
- Memory provider unavailable
- Provider configuration issues
- Need to back up Hermes config

## Core Workflows

### Gateway Troubleshooting

1. Check gateway status: `hermes gateway list`
2. Check g

### Living Inventory

> **When to Use:** When creating a single, git-versioned document that tracks your full technology estate (hardware, network, services, models, cloud accounts) as a living ops reference.

#### Procedure

1. **Define scope:** Decide whether to cover the full estate or a subset (e.g., AI/ML core only).
2. **Choose shape:** Opt for a hybrid Markdown doc + generator script — auto-regenerate volatile sections (services, ports, models) while preserving hand-edited sections.
3. **Set up structure:**
   - Document: `~/.hermes/docs/stack-inventory.md`
   - Script: `~/.hermes/scripts/stack-inventory.py`
4. **Use marker-based regeneration:** Wrap each auto section in `<!-- BEGIN AUTO: <section> -->` and `<!-- END AUTO: <section> -->`. Only content between markers is rewritten.
5. **Seed curated sections:** Populate hardware, cloud, and backup rows from existing knowledge (memory, configs) with `(unverified)` labels until confirmed.
6. **Run the script:** `python3 ~/.hermes/scripts/stack-inventory.py` — each probe runs locally, fast, and fails gracefully.
7. **Commit the result:** The script auto-commits after regeneration (via `git add` and `git commit`).

#### Pitfalls

- **Probe failure is a feature, not a bug:** If a probe fails (e.g., MacBook share down, llama-swap dead), the script should output `⚠ probe failed: <reason>` in that section and continue, never aborting. Never use `set -e` or `exit on error`.
- **Marker mismanagement breaks the doc:** If a `BEGIN`/`END` marker is misplaced or missing, the script may delete or overwrite hand-edited content. Always verify the markers are correctly paired and not duplicated.

#### Support File

- `references/inventory-markers.md` — contains the full marker syntax and best practices for use across all inventory tasks.ateway logs: `tail -f ~/.hermes/logs/gateway.error.log`
3. For plugin crashes: check for SIDECARD_CRASHED errors, remove problematic credentials
4. For API server auth: set `API_SERVER_KEY` in `~/.hermes/.env`
5. For session isolation: ensure `/api/profiles/sessions` respects profile parameter

### Multi-Profile Setup

1. Enable multiplexing: `hermes config set gateway.multiplex_profiles true`
2. Sync OAuth tokens from shared store to profile files
3. Verify token expiration times match across profiles

### Dashboard Authentication

1. Register dashboard: `hermes dashboard register --username <name> --password <pass>`
2. Fix session TTL: unset or set to 43200 (12h)
3. Check basic_auth config for empty passwords

Pitfall: Oversized or heavily vendored skills (e.g., >5MB or high file-count dependencies) can introduce file-count spikes that trip the automated structural guards (like git-backup), leading to deferred commits and operational risk. Ensure skills are minimal and dependencies are managed externally.

Pitfall: Client-Side Model Caching
**Pitfall:** If a model selection results in a 404 error but the model ID is unknown to the agent's logic, check the client's local storage (LevelDB) for lingering entries.
**Why:** The client application maintains a persistent cache of models it has interacted with, independent of the host model configuration. If a model is selected via a direct input or a corrupted state, the client state (LevelDB) will hold the ID, leading to a hard 404 on the server side, as the server only validates against its active configuration.

## Hermes browser sessions (dedicated Chrome profile)

Chrome now **refuses remote debugging on the default profile** (`DevTools remote debugging requires a non-default data directory`). Hermes browser work therefore uses a **dedicated profile** on the MacBook:

- **Profile dir:** `/Users/prasta/.hermes/browser-profile` (persistent — NOT the scratch dir, which prunes after 24h idle). Log into sites once; the session persists across runs.
- **Launch (on the MacBook, in a terminal with Full Disk Access):**
  ```bash
  "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --remote-debugging-port=9222 --user-data-dir=/Users/prasta/.hermes/browser-profile --no-first-run --no-default-browser-check about:blank
  ```
- **Tunnel to the Studio:** `ssh -N -L 9222:127.0.0.1:9222 macbook` (background). Then the Studio's browser tools drive the MacBook's Chrome via `127.0.0.1:9222`.

**Pitfalls hit (2026-10-18):**
- Launching Chrome via plain SSH (`ssh macbook 'chrome ...'`) does NOT attach to the GUI session — the process runs but never binds the port. Use `open -a "Google Chrome" --args ...` or launch from a terminal on the MacBook itself.
- `launchctl asuser <uid> open ...` from SSH fails with `Could not switch to audit session: Operation not permitted`.
- A terminal **without Full Disk Access** cannot write Chrome's `SingletonLock` in the profile dir → `Operation not permitted` and DevTools never starts. Grant the terminal Full Disk Access (System Settings → Privacy & Security → Full Disk Access) or use Terminal.app.
- Chrome binds DevTools to `[::1]` (IPv6) by default; the tunnel must target `127.0.0.1:9222` and Chrome must be launched with `--user-data-dir` for the port to bind at all.
- A stuck Chrome process (spinning at 99% CPU, not binding) needs `kill -9`; `osascript quit` and `pkill` may not take.
- **Login state lives in the profile dir, not a named profile.** Creating a profile called "Hermes Agent" in the MAIN Chrome lands it in the main data dir (Profile 4) — the Hermes instance can't see it. Just log into sites in the Hermes profile's Default; the session persists.
- **Facebook Marketplace form quirks via CDP:** category/condition dropdowns may not expand via programmatic click (OOPIF-rendered popup); `browser_type` on a textarea can look duplicated in the live preview while the actual field value is clean (verify with `document.querySelector('textarea')`). Photo upload needs manual drag-drop (CDP `DOM.setFileInputFiles` unavailable on this bridge). Save the draft early — a stray navigation wipes the form.

## Gateway Multiplexing

### Gateway keeps restarting every ~30s

Root cause: Plugin sidecar crashes (particularly Photon) cause continuous gateway restarts.
Fix: Remove Photon credentials, disable via config, remove stale state files.

### OAuth tokens diverge across profiles

Root cause: Separate per-profile gateway processes run independently.
Fix: Enable single-process multiplexing, verify tokens synchronized.

### Sessions from one profile appear in another

Root cause: Desktop sends profile query but API server returns default-profile sessions.
Fix: The `/api/profiles/sessions` endpoint must respect the profile parameter.

## WebUI Operations

### 409 agent_runtime_stale on /api/chat/start

Root cause: WebUI runs its own in-process agent runtime separate from the gateway.
Fix: Route webui chat through the gateway. Set config, export env vars, restart.

### macOS Tailscale binding quirk

macOS Tailscale uses utun4, not tailscale0. Do not bind HTTP server to 100.x.x.x.

## Backup Strategy

Configuration-only: track config.yaml, memories, and skills — not runtime state.

## Desktop Plugins

Write plugins for the Hermes desktop app: statusbar items, layout panes, command-palette commands, keybinds, routes, and themes.

## Color Themes

Author a Hermes skin — one YAML file that themes the CLI, TUI, and desktop GUI at once.

## Provider Configuration

Configure AI providers in Hermes and set up Mixture of Agents (MoA) presets.

### Hiding providers from the model pickers (folded from the MBP hermes-model-picker skills)

`model_catalog.excluded_providers` hides provider rows from every picker surface (CLI `hermes model`, TUI, gateway, dashboard) without disabling the provider's tools. Read in `hermes_cli/inventory.py`.

```bash
hermes config set model_catalog.excluded_providers '["xai", "alibaba"]'
```

Slugs are case-insensitive and match canonical ids or aliases (`qwen` maps to `alibaba`). Do not reach for `hermes tools` or provider deletion to tidy a picker.

### Editing config.yaml from inside a session (folded from the MBP hermes-config-management skill)

- Scalars: `hermes config set <key> <value>`; add `--profile <name>` to write `~/.hermes/profiles/<name>/config.yaml` instead.
- Nested blocks (lists, mappings, `moa:` presets): the setter cannot express them. Write the block from the shell (`python3 -c` with PyYAML, or a here-doc) and validate with `python3 -c "import yaml; yaml.safe_load(open('$HOME/.hermes/config.yaml'))"`.
- Prove a model or fallback change end to end before reporting it done: `hermes chat -q "Reply with exactly: fallback OK" --provider <p> --model <id>`. A parsed YAML is not a working provider.
- The MBP-era guard ("Agent cannot modify security-sensitive configuration") is not present in the current checkout; the rules above still apply because the setter is the only path that validates keys.

## TUI Widgets & Dock Panels

Author widget apps for the Hermes TUI (`hermes --tui`): glanceable ambient panels docked above the status bar, or modal overlays.

### The "widget /X is live" line is an announcement, not an error

Every `.mjs` in `$HERMES_HOME/tui-widgets/` is imported and registered on each TUI start
(and hot-reloaded on every change — the directory is watched), then announced as a **system
transcript line**: `widget /<id> is live — type /<id> to open`. Source:
`ui-tui/src/sdk/userWidgets.ts` (`loadUserWidgets`, `readdir` filtered to `.mjs`) feeds
`ui-tui/src/app/useMainApp.ts` (`onUserWidgets` → `sys(...)`). It fires on every launch for
every registered widget and is unconditional — no config key silences it. Deleting the
`.mjs` is the only mute, and it also emits one `widget /<id> removed (file deleted)` line.

So when a user reports "still getting this error" and the on-screen text says a widget is
live, the question is *which artifact was actually removed*, not what the message means.

### Retiring a widget's server does NOT retire the widget

A dashboard typically has two independent pieces with the same name:

- the **server** — a LaunchAgent (`~/Library/LaunchAgents/ai.<name>.plist`, disabled by
  renaming to `.disabled` + archiving to `state/retired-launchagents/`) serving a proxy port;
- the **TUI widget** — `<name>.mjs` (+ its `.html` / `server.py` / `run.sh` siblings) under
  `~/.hermes/tui-widgets/`.

Retiring the LaunchAgent kills the proxy port and leaves the widget file untouched, so the
TUI keeps announcing it forever. Both must be dealt with in one change.

**A claimed removal is not a removal — verify the file, not the report.** A prior session
recorded "no `llama-swap-dashboard` files remain under `~/.hermes/tui-widgets`" while all
four files sat there for another seven days, still re-registering on every launch. Before
telling the user a widget is gone:

```bash
ls -la ~/.hermes/tui-widgets/           # the .mjs IS the registration
launchctl list | grep -i <name>         # server-state, independent of the widget
grep '<name>' ~/.hermes/logs/tui_gateway_crash.log | tail -5   # 'user widgets registered:'
```

The `user widgets registered: <ids>` line (written via `recordParentLifecycle`) is the
receipt that a widget loaded in a given TUI process; its timestamp pins the launch that
produced the announcement the user is complaining about. Archive rather than delete —
`~/.hermes/_archive/<name>-<date>/` — since the widget is usually still functional (it
falls back to direct API calls when its proxy is down) and may be wanted back.

## NPM Override Safety

### Problem: `npm install` in the web workspace drops the nanoid@3.3.18 override

Root cause: npm install can remove the `nanoid@^3: 3.3.18` override from the root `package.json`, re-introducing GHSA-2v37-7h3g-55p8.

Fix: Ensure the override is present in package.json after every `npm install`.

## Remote (HTTP) MCP Server Auth

### `auth: bearer` + `env:` on a `url:` server silently sends no credentials

`env:` is **stdio-only** (`hermes mcp add --help` says so). For `url:` transports the
client builds headers from `config["headers"]` plus the OAuth provider; `env` is ignored.
`auth` accepts only `oauth` or `header` — `bearer` is not a value.

Symptoms: `hermes mcp test <name>` prints `Auth: none`; `agent.log` shows repeated `401`
against the server URL followed by
`MCP server '<name>' failed initial connection after 3 attempts, parking until a reconnect
is requested (state: connecting → parked)`. No tools register, so the server is missing from
`tool_search` while sibling servers' tools appear normally.

**Check the token store before re-running an OAuth flow.** A completed handshake already
leaves `~/.hermes/mcp-tokens/<name>.client.json` (DCR client) and `<name>.json` (access +
refresh token). But the provider is only built when `auth_type == "oauth"`, so with
`auth: bearer` the stored token is never read, never refreshed, never sent. Fix the config,
not the flow:

```bash
hermes config set mcp_servers.<name>.auth oauth
hermes mcp test <name>          # expect: Auth: OAuth 2.0 / Connected / Tools discovered
```

Expired access tokens are fine — the refresh token is used on connect.

**A config fix does NOT reach a process that already has the server registered.** This is
the trap that makes a correct fix look like it never landed. `discover_mcp_tools()` only
connects servers missing from the in-process registry (`_select_new_servers` skips names
already in `_core._servers`); a known-but-parked server is merely signalled to reconnect,
and the revival loop re-runs the transport with the **config dict captured at first
registration** (`mcp_tool_server_run.py` binds `self._config` once in `_prepare_run`,
before the retry loop). Edit config.yaml under a running gateway and it keeps retrying the
old auth indefinitely.

Tell-tale: `hermes mcp test <name>` (fresh process) connects and lists tools while
`errors.log` keeps logging `MCP server '<name>' failed initial connection after 3 attempts,
parking until a reconnect is requested` every ~300 s (`_PARKED_RETRY_INTERVAL`), long after
the config was corrected. The `httpx2` INFO lines above those warnings carry the real
status — `401` = no Authorization header sent, `403 restricted_resource` = the wrong key
type was sent.

So always reload, not just edit:

- Gateway / Discord / Telegram: run the `/reload-mcp` slash command. It calls
  `shutdown_mcp_servers()` then `discover_mcp_tools()`, which re-reads config.yaml. Surgical
  and it does not disturb other sessions (it does invalidate that session's prompt cache).
- Or restart the process
  (`launchctl kickstart -k gui/$(id -u)/ai.hermes.gateway`). This kills every in-flight
  turn on that gateway — check for running sessions before doing it.
- A fresh CLI/TUI process (`hermes -z`, `hermes mcp test`) always reads the current config,
  which is why a probe can look healthy while the gateway stays broken.

### Stale parked failures keep paging long after the fix

`scripts/watchdog_outcomes.sh` counts `failed initial connection` lines for enabled
servers over an **8-hour** window (`OUTCOMES_MCP_MAX_AGE_SEC`, default 28800), so its tally
keeps clearing `OUTCOMES_MCP_MIN_FAILURES` (5) for hours after the last 401 and the alert
keeps firing on its hourly cron. Check whether those lines are still *growing* before
treating the alert as a live fault.

The same script's `alert_key` auto-ack (quiet after `OUTCOMES_ALERT_REPEAT`, default 5,
identical cycles) only engages when the alert text is byte-stable. Any message carrying a
volatile tally — `notion (102 recent failures)` → `(99 recent failures)` — changes the
signature every cycle, resets the counter, and re-pages a known condition forever.
`alert_key` now normalizes `(NN ...)` to `(N)` before comparing; keep new alert messages
free of volatile numbers, or extend that normalization.

Two traps when muting one of these alerts:

- **`ack_outcomes.sh <key>` alone is not enough below the threshold.** The ack window was
  only consulted once `count >= OUTCOMES_ALERT_REPEAT` (5), so a manual ack on a fresh
  alert printed the loud line anyway for 5 more cycles. Fixed: the ack is now honored at
  any count. If you are on an older copy, seed `<key>.count` to 5 as well.
- **The tally is a rolling window, not a live fault.** After fixing the server, the count
  keeps clearing `OUTCOMES_MCP_MIN_FAILURES` until the last failure ages out of the 8h
  window (~9h of pages at a 5-min retry cadence). Confirm the count is no longer *growing*
  before believing the alert.

An MCP fix is only verified when you can see it in the log: a
`registered N tool(s)` line for that server plus **zero** new `401`/`403` lines after it.
The reload itself is visible as `MCP OAuth '<name>': tokens file changed (...)`, followed
by `GET`/`DELETE -> 405` (normal discovery probing on servers that only implement POST).

### Notion hosted MCP is OAuth-only

`https://mcp.notion.com/mcp` rejects an `ntn_` integration key with
`403 restricted_resource: "Endpoint unavailable."` Integration keys are valid against
`https://api.notion.com/v1` only. Do not reach for header auth here; use `auth: oauth`.
The deprecated open-source `@notionhq/notion-mcp-server` stdio server is the token-auth
alternative.

### Notion MCP SQL mode can return stale property values

`query_data_sources` SQL mode reads a snapshot that can lag behind recent edits: a select
value edited on the page still returns the old option. Rows mode and `fetch` on the page
return the live value. **Before reporting any property value as current, confirm it with
`fetch` or rows mode.** This applies even to plain `select` columns, not just rich text.
Also note the SQL table exposes `createdTime` but not last-edited time, so SQL answers
"what was added" — use `fetch`/`page_last_edited_at` for "what changed".

### Portal connector gateway: 404 means unentitled, not misconfigured

On `https://connector-gateway.nousresearch.com`, probe `/v1/connectors` with four headers:
no auth, a bogus bearer, a valid bearer, and the token without the `Bearer` prefix.
`401 AUTH_ERROR` on the first two and **`404 {"error":"Not found"}` with the valid token**
means the route exists but is hidden from this principal (`tools/tool_gateway/config.py`:
"404 routes degrade to local-only"). Confirm by decoding the access token payload — a
`tool_access.enabled: false` claim or missing connector entries in `tool_access.coverage`
is the entitlement, and nothing on the local machine fixes it. Surface it to the user as an
account-side issue.

## Memory hygiene: what may enter Hindsight, and how a retraction works

Hindsight stores observations with **no confidence signal** distinguishing "this is true"
from "this is what the agent said and later retracted." A correction is retained as just
another fact, so the next session retrieves the error and its correction at equal weight and
keeps whichever embeds more closely. That is a known retrieval property, not a hypothesis —
expect stale clusters to outrank fresh corrections.

### Rule: procedures and self-errors do not belong in Hindsight

**Hindsight is for facts about Patrick's world** — machine topology, ports, credentials
locations, project state. Those are stable and benefit from being prefetched.

**An agent's own mistake is a procedure lesson, and procedures belong in this skill**, read
deliberately when relevant. A wrong causal story sitting in a prefetch is worse than no
memory at all, because it gets applied to the next problem with total confidence. Concrete
instance: a retained "use byte count instead of du, du has MiB-vs-decimal-GB issues" — the
cause was invented. The real failure was BSD `du` silently ignoring a GNU `--exclude` flag.
That false lesson would have misfired on the next disk measurement.

**Dates on every fact.** A memory reading "a dry run identified 39 valid skills" is
meaningless without a date; the 2026-10-01 MBP consolidation found 171. Undated counts read
as current.

### A factual claim enters memory only after verification

Verify first, retain second. In order:

1. Run the command that produces the number. Read its output.
2. Confirm the output means what you think — check flags exist on this platform, check the
   path prefix, check the count is stable across two runs.
3. **Then** write it to a file or to memory.
4. If a correction is needed later, correct **the artifact**, not the chat. A retraction
   delivered only in conversation leaves a wrong file in the hot path and makes the user the
   sync mechanism.

Never state a number that was not derived in the current turn from visible tool output. A
figure carried forward from an earlier turn is an assumption wearing a fact's clothes.

### MEMORY.md line budget is a hard gate

`MEMORY.md` and `USER.md` are capped by `memory.memory_char_limit` / `memory.user_char_limit`.
**Shipped defaults are 2,200 and 1,375 chars** — `tools/memory_tool.py` reads
`mem_cfg.get("memory_char_limit", 2200)` / `("user_char_limit", 1375)`, and the `MemoryStore`
constructor in `tools/memory_tool_store.py` carries the same defaults. **This install overrides both**
(`config.yaml`: 20,000 / 8,000), and the tool's `usage` line reports only the *effective* limit, so
never read that number as the default. **At 100% every `add` is refused** until something is freed in
the same batch. A correction that is *longer*
than the text it replaces silently pushes the file over and locks out writes. Measured 2026-10-01:
replacing a 2-line wrong entry with a 3-line right one put the file at 12,016 / 12,000 (that
measurement predates the cap change).

So after **any** edit — correction included — re-check with the tool's own report, not a guess:

```bash
python3 -c "d=open('/Users/macstudio/.hermes/memories/MEMORY.md',encoding='utf-8').read(); print(len(d),'of 20000')"
```

**A direct file edit is safe if you re-check the format invariant**, because the tool re-reads from
disk on its next call rather than holding a cache. After writing the file by hand, verify all three
of: entry count unchanged, no trailing newline, and `raw == "\n§\n".join(raw.split("\n§\n"))`.
A file that fails the round-trip refuses every subsequent write. Prove the store is healthy with one
small real `patch` through the tool afterwards — a successful patch is the receipt.

Correct entries in place and short. Put the reasoning in this skill, not in the entry.

### Cross-check MEMORY.md against Hindsight before trusting either

The two stores drift independently and can contradict each other. Real instance:
`MEMORY.md` asserted that two GGUF models had "broken symlinks with escaped backslashes"
while Hindsight separately recorded that the claim was false — the models had simply been
retired from the llama-swap config. The wrong claim sat in the file injected into every turn.

When a memory and a recalled observation disagree, **go to the source** — `curl -s
127.0.0.1:9292/v1/models`, read the actual config, stat the actual file. Neither store is
authoritative over the filesystem.

## `git clean -x` at `~/.hermes` would destroy 14.4 GB and your credentials

`~/.hermes` is a private backup repo (`git@github.com:prasta1/backup-hermes-macstudio.git`)
and it **contains** a second, independent repo: `~/.hermes/hermes-agent/`, the agent's own
source (`origin` = NousResearch/hermes-agent, `prasta1` = your fork, branch `local`).

The outer `.gitignore` opens with `/*` (allowlist style) and never un-ignores
`hermes-agent`, so `git ls-files hermes-agent` returns **0** — the backup has never seen a
single byte of source. That separation is correct and deliberate. Do not "fix" it by moving
the checkout to `~/Projects/` (breaks `hermes update`, launchd jobs, and skills that
reference the path) or by making it a submodule (a gitlink in a backup allowlist restores
nothing).

**`git clean -fd` is safe. `git clean -xfd` / `-fdX` is not.** The `-x` flag also removes
*ignored* files, and at `~/.hermes` almost everything is ignored. Measured 2026-10-01:
`git clean -nxd` reports **520 paths across ~212 top-level entries, ~14.5 GB**. The path
count is stable; the entry and byte totals drift by a little between runs because the
directory is live (caches, `state.db-wal`, session files move under you). No confirmation,
no undo, and the backup repo cannot restore any of it — the source was never tracked there.
This has already happened once: a `git clean -fdX` sweep across several projects purged the
`.git` inside `~/.hermes/hermes-agent`.

### What it destroys, in order of how much it should worry you

**Tier 1 — unrecoverable, no remote and no regeneration.** `.env` *and 6*
`.env.bak-*` copies, `auth.json`, `google_client_secret.json`, `google_token.json`,
`.webui_password`, `mcp-tokens/`, `secrets/`, `secrets.tar.gz.cms.bak-*`. Also `config.yaml`
plus **16** `config.yaml.bak-*` variants, `memories/`, `skills/`, `cron/`, `sessions/`,
`plugins/`, `profiles/`, `scripts/`, `llama-swap/`. Live credentials are the first thing
`-x` reaches. **This is the tier that makes the command unacceptable, independent of
anything else.**

**Tier 2 — expensive but recoverable.** `hermes-agent/` (4.4 GB, 173,415 files) re-clones
from GitHub, **but the ~40 private patches on branch `local` exist in no pushed remote** —
a re-clone loses them. `browser-profile/` 4.8 GB, `installs/` 2.6 GB, `node/` 1.1 GB,
`tools/` 949 MB, `backups/` 923 MB, `state-snapshots/` 453 MB, `service-venvs/` 517 MB.
`skills-archive-mbp-2026-10-01/` and `mbp-skills-manifest-2026-10-01.txt` are SHA-256
verified but exist on this disk only.

**Tier 3 — genuinely ephemeral.** `cache/` 834 MB, `chrome-debug/` 268 MB, every `*.pid`,
`*.lock`, `*.mutex`, `.DS_Store`, `spawn-ledger.json.tmp*`. This is the only tier a `-x`
clean should ever be pointed at.

Also in the blast radius, and worth knowing about: **`.hermes/`** — a second, nested copy of
the state directory (2 files, 16 KB) sitting inside the first.

### The rule

Never run a `-x` clean at `~/.hermes`. If something under that root needs clearing, name the
paths explicitly — `git clean -nd <path>` then `git clean -fd <path>` — so the blast radius
is the thing you typed, not the whole tree.

```bash
# MANDATORY before any recursive clean under ~/.hermes, from the root:
git -C ~/.hermes clean -nxd | head -60     # read it, every time
git -C ~/.hermes clean -nxd | wc -l        # if this is not a small number, stop
```

If the output contains `Would remove .env/` or `Would remove hermes-agent/`, stop and clean
from inside the subdirectory instead. Recovering a destroyed inner checkout means re-cloning
and re-applying the local patches, not `git checkout` in the outer repo:

```bash
git clone https://github.com/prasta1/hermes-agent.git ~/.hermes/hermes-agent
git -C ~/.hermes/hermes-agent checkout local
```

## Script Watchdogs (`~/.hermes/scripts/watchdog_*.sh`)

These run as `no_agent` cron jobs: **exit 0 = silent, non-zero = the cron system pages with
stdout**. Three traps, each of which turns a 30-second fix into hours of noise:

- **Never `curl -sf` in a probe.** `-f` discards the error body, collapsing every distinct
  fault into one useless string. A renamed llama-swap model returned
  `404 {"error":"no router for requested model"}`; the probe reported only
  `no valid embedding array` — for **156 consecutive runs (~39h)**. Use `-s` and capture both
  status and body (`-w '\n%{http_code}'`, split, keep ~200 chars) and print them in the alert.
- **Never `| head -c N` under `set -o pipefail`.** On a large *healthy* body head closes the
  pipe early, SIGPIPEs the upstream, and `set -e` aborts with **exit 141** — a false
  "script failed" page on a working endpoint. Truncate in bash: `flat="${body//$'\n'/}"`
  then `"${flat:0:200}"`.
- **Never `[[ cond ]] && echo x` as a statement under `set -e`.** A false test makes the whole
  list return 1 and aborts the script, silently dropping every line after it — which hides
  *which* endpoint failed. Use explicit `if [[ cond ]]; then echo x; fi` in alert output.

Always exercise BOTH paths after editing a watchdog: the healthy one must be silent with
**exit 0** (run it 2-3x), and a forced failure must reach the threshold and print the real
cause. Back up first (`cp watchdog_x.sh watchdog_x.sh.bak-$(date +%Y%m%d-%H%M%S)`) and reset
`~/.hermes/state/<name>_fails` afterwards so a test does not leave a count behind.

**A check whose target cannot exist reports success.** `~/bin/cruft-check.sh` (weekly cruft
report, reached via the `~/.hermes/scripts/cruft-check.sh` wrapper) ran its drift check as
`git -C "$HOME" status --short` — and `$HOME` is not a git repo, so `rev-parse` failed, the
loop body never ran, and the TL;DR printed a confident `Tracked-config drift: 0 file(s)`
while `~/.hermes` (the repo meant) carried real modifications. When a check reports clean,
confirm its target actually resolves before trusting the zero. The same script also reads
`launchctl list` and reports every non-zero last-exit status as a failing agent — which
flags `ai.hermes.gateway` with exit 75 while it is running (see the restart conventions
above: 75 is a declared success). Only an agent that is actually down (`PID == -`) with a
non-declared-success code is failing.

### llama-swap upstream (llama-server) stderr is live-SSE only — not grep-able by a cron watchdog

llama-swap captures each llama-server's stderr as the "upstream" log stream, served live at
`/logs/stream/upstream` (and `/api/events/logs?stream=upstream`). It is **not** written to any
file: `GET /logs` (the buffered endpoint) carries only llama-swap's own INFO lines, and
`llama-swap.out.log`/`err.log` (launchd StandardOut/Err) hold the same. There is no config
option to persist upstream logs to disk.

Consequence: a one-shot line that fires at model load — e.g. llama.cpp's
`warning: current allocated size is greater than the recommended max working set size`
(Metal init, `MTLDevice.recommendedMaxWorkingSetSize`) — is gone from the stream seconds
after the model loads. A 5-min cron watchdog cannot grep it; adding such a grep is dead code
that silently never fires. To catch it you need a persistent subscriber to the upstream SSE
stream writing to a file (a new launchd daemon), or capture at load time inside llama-swap
itself. The aggregate wired-memory check (`watchdog_mem.sh`, 62GB on the 96GB Studio ≈ 77%
of the 80GB `iogpu.wired_limit_mb` cap) already covers the same underlying condition, so
skipping the per-model line is defensible.

### llama-swap model renames break consumers pinning the old id

llama-swap ids are referenced by name in more places than the config: watchdog scripts
(`EMBEDDING_MODEL`), cron job model fields, and `ms-*` / `studio-*` prefixes baked into
prompts. When ids are renamed, grep for the old prefix in the same change:

```bash
grep -rn "studio-" ~/.hermes/scripts/ ~/.hermes/cron/jobs.json ~/.hermes/config.yaml
curl -s 127.0.0.1:9292/v1/models | jq -r '.data[].id'   # current truth
```

A renamed id fails as `404 no router for requested model` — on a *live* endpoint, so any
liveness-only check reports healthy while the consumer silently gets nothing.

## MEMORY.md Maintenance

### Canonical format: small entries joined by `\n§\n`

From `tools/memory_tool_store.py`: `ENTRY_DELIMITER = "\n§\n"`, and
`_write_file` is exactly `ENTRY_DELIMITER.join(entries)`. Two consequences
people get wrong:

- **No trailing newline is correct.** It is not a defect; do not "fix" it.
- The file must satisfy `raw == ENTRY_DELIMITER.join(_parse_entries(raw))` or
  the drift guard (`_drift_error`) refuses every subsequent write. Verify after
  any hand edit.

### Never "organize" a memory file into topical sections

`== [SECTION] ==` headers and a leading `#` comment block are **not part of the
format**. They are ordinary text. Because sections are separated by newlines
rather than the delimiter, grouping collapses many facts into ONE entry. Costs
measured on a real file (2026-09-12):

- The char budget counts that one block as one entry, and it can easily be
  90%+ of the file.
- The memory tool can only add/remove/replace at **entry** granularity. It
  cannot prune one section out of the big block.
- A `remove` whose anchor matches text inside the big block risks targeting the
  entire 80+ line block. Treat that as destructive before it succeeds.

### When the store is over cap, `add` is always refused

The failure message reports current usage. If it is over the limit, every add
fails until something is freed **in the same batch** (ops apply atomically and
the limit is checked on the final result).

### Anchor matching is unreliable for pruning; edit the file directly

Observed: a 15-char anchor at a section start matched, while several plain
prose substrings from mid-entry (`for faster test feedback`, `pytest -n 4`,
`environment-specific...`) all returned "no entry matched" despite being
present verbatim. The rule is not documented and could not be characterised
from outside. **Do not burn repeated attempts on it.** After ~2 failures, stop
and edit the file directly:

```bash
cp ~/.hermes/memories/MEMORY.md \
   ~/.hermes/memories/MEMORY.md.bak-directedit-$(date +%Y%m%d-%H%M%S)
```

Then use `patch` on a range from a section header through the end of file,
preserving the `§` separators exactly. Verify with a char count and an entry
split:

```bash
python3 -c "d=open('MEMORY.md',encoding='utf-8').read(); print(len(d), len(d.split(chr(10)+'§'+chr(10))))"
```

The tool re-reads from disk on its next call, so a direct edit is picked up
with no stale-cache clobber risk. Confirm by making one small `add` afterwards
and checking the usage line and `entry_count`.

### `replace` rewrites the WHOLE entry — never pass a narrow anchor

`replace` is entry-granular: `old_text` only *identifies which entry* to rewrite, and
`content` becomes that entry's entire new text. A one-line anchor therefore deletes every
other fact sharing that entry. Measured: a `replace` aimed at the single `Job search:` line
in `USER.md` (the whole profile was one ~4.5 KB entry) left the file with **2 entries / 361
chars**. Same class hits `MEMORY.md` whenever entries were previously merged into a block.

**For a line edit inside an existing entry, use `patch` on the file, not `replace`.**

**Recover from version control, never by retyping.** `~/.hermes` is a git repo and both
memory files are tracked:

```bash
git -C ~/.hermes show HEAD:memories/USER.md > ~/.hermes/memories/USER.md
ls -lt ~/.hermes/memories/MEMORY.md.bak-*        # the tool writes its own pre-edit backups
```

HEAD can lag recent entries, so for MEMORY.md prefer the newest `.bak-*` and splice back
only the damaged entry. Verify by comparing entry **sets**, not `diff` — the tool also
normalizes formatting (`== [SECTION] ==` headings → `§` separators, split lines), so a raw
diff is mostly noise.

```python
import re
def entries(t):
    t = re.sub(r'^== .*? ==$', '', t, flags=re.M).replace('§', '\n')
    return {l.strip() for l in t.splitlines() if l.strip() and not l.strip().startswith('#')}
print(sorted(entries(open(bak).read()) - entries(open(cur).read())))   # real losses only
```

### Prune before you need room, not after

A store at 99% rejects the next add outright. When a reviewed memory entry goes
stale (completed migrations, one-off skill-update notes, superseded paths),
remove it at the time you notice, while the tool still has room to operate.

## Mac nodes: GUI LaunchAgent vs system LaunchDaemon

A job in `~/Library/LaunchAgents` lives in the `gui/<uid>` domain and **cannot start until
someone logs in interactively**. With **FileVault On** automatic login is impossible, so after
an unclean reboot the Mac sits at the login window with every login-bound service dead.

**Never read "online on tailnet" as "the machine is serving".** Tailscale's network extension
runs system-level, so the peer reports `Online: true` at the login window while llama-swap and
the Hermes gateway are both down. Measured on the MacBook: console session crashed at
2026-09-12 23:21:42, next `console` login 2026-09-13 05:57:40 — **6h36m** in which the
Studio's health watchdog was correctly paging into a channel that already said "online on
tailnet". A sustained MacBook `:8999` outage after a reboot is almost always this, not a dead
model stack.

Diagnose it from the Studio in three commands (SSH works at the login window — Remote Login is
a system service, so no one has to log in):

```bash
last -5                 # a "crash" session end + the next `console` login time
ssh macbookpro 'launchctl print gui/501/ai.llama-swap | grep -E "state|runs|last exit"'
# runs = 1 and a run time equal to the login time == it has only ever started at login
ssh macbookpro 'fdesetup status; sudo -n true 2>&1'   # FileVault blocks auto-login
```

Durable fix: run it from the **system** domain with `UserName` set, so it starts at boot with
no login. Install to `/Library/LaunchDaemons/ai.llama-swap.plist` (`UserName=prasta`,
`RunAtLoad`, `KeepAlive`) and retire the GUI copy, or the two fight for the port. Needs root —
there is no passwordless sudo on the MacBook, so stage the plist and hand over the command.
Because the listen address is the Tailscale IP, `run.sh` must **wait for the address** before
exec'ing; from the system domain at boot it otherwise dies with `EADDRNOTAVAIL` and KeepAlive
retry-loops.

## Timezone: config.yaml alone does not take effect until the gateway restarts

`timezone` from config.yaml is read at **gateway startup** and bridged into the process env
(`gateway/run.py`: `os.environ["HERMES_TIMEZONE"] = <config timezone>`). `hermes_time.py`
resolves env first, config second, server-local third — so the env var **shadows the config
file** and is inherited by every child (terminal, cron, scripts). Editing config.yaml under a
running gateway changes nothing until that process restarts: a fresh `hermes -z` probe shows
the new zone while cron keeps firing on the old one. Nothing stale is left behind — the
bridge is written unconditionally from config at boot, so one restart is the complete fix.

**Use an IANA name, never a fixed abbreviation.** `EST` is UTC-5 with no DST, so with the
machine on `America/New_York` every cron job fires **one hour late** from March to November,
then silently self-corrects in winter and breaks again in spring. Diagnostic: `date` vs
`hermes config get timezone`, then `echo $HERMES_TIMEZONE`.

The agent **cannot** restart the gateway from inside it (blocked — SIGTERM would kill the
command mid-flight; a detached/delayed wrapper is refused too). Hand it to the user: `/restart`
in chat (graceful, drains active runs first) or `hermes gateway restart` from a shell outside
the app. Then verify: `echo $HERMES_TIMEZONE` in a new child and `hermes_time.now().tzname()`.
Remember `hermes config` is the only write path — `patch` refuses config.yaml outright.

## "Update server unreachable" on a fork-only branch is a lie, not a network fault

The desktop update panel renders "We couldn't reach the update server" whenever the backend's `/api/hermes/update/check` returns `behind: null` with `can_apply: true`. That collapses every null into a network-failure copy. A checkout on a fork-only branch (e.g. `local`, which the official `NousResearch/hermes-agent` origin does not advertise) produces exactly that null — the source check returns `error='branch-local-only'`, `localOnly=true`, and an honest message, but the endpoint used to discard it and the desktop mapped any null to `check-failed`.

**Diagnose before believing the message:** GitHub reachability is not the question. Check the checkout's branch first:
```bash
git -C ~/.hermes/hermes-agent branch --show-current
# a fork-only branch (local) + dirty tree = the real cause, not the network
```

**The Studio is production and may legitimately live on `local`** (its carried patches). The branch is not the problem; the update check lying about it was. Fixed 2026-10-10 (commit 8ee24c5222 on `local`): the endpoint now passes `localOnly`/`branch`/`currentBranch`/`dirty` through and surfaces the real message for known non-network conditions; the desktop maps `localOnly` to an informational state with a clear "you're on a custom branch" line instead of `check-failed`. A dirty tree still makes `hermes update` a silent no-op — that constraint is real and separate from the branch question.

## Updating the `local` branch: the wrapper script and its rebase-conflict path

The Studio's live install runs on `local` (the carried-patches branch). The one-command update is `~/.hermes/scripts/hermes-update-local.sh`: checkout main → `hermes update` → rebase `local` onto the new tip → push to fork → checkout `local` → restart gateway. `updates.auto_switch_parked_branch` is `false` so `hermes update` alone skips loudly instead of silently yanking the checkout off `local`.

**The wrapper's conflict path is a dead end — it aborts mid-rebase with no guidance.** When the carried commit conflicts with the new upstream tip, the script prints "resolve it, then `git add -A && git rebase --continue`" and exits, leaving the tree parked in an interactive rebase on `local`. That is the expected state, not a failure of the script — the carried squash is a single commit, so there is exactly one conflict to resolve.

**Resolving the conflict — the two sides are inverted from a merge.** In a rebase, `--ours` = the new base (upstream HEAD), `--theirs` = the commit being replayed (the carried patch). This is the opposite of a merge, and grabbing the wrong side silently keeps the wrong code. Verify which side you want before `git checkout --ours/--theirs`:

```bash
cd ~/.hermes/hermes-agent
git diff --name-only --diff-filter=U        # the conflicted files
grep -n '^<<<<<<<\|^=======\|^>>>>>>>' <file>   # the conflict blocks
```

**The common case: upstream has absorbed the carried patch's intent — but VERIFY it, don't assume.** The carried patches are the *remaining* live fixes — the ones upstream hasn't absorbed. When one does conflict, it is often because upstream landed a newer, equivalent version of the same change. But **a new upstream feature does not mean the old fix was absorbed.** Real failure (2026-10-23): upstream added a `held` branch to `actions.py` while the carried patch's `localOnly`/`reason` passthrough (8ee24c5222) was *not* absorbed — taking upstream's side dropped the fix and made the desktop show a network-failure lie on `local` again. Before taking upstream's side, grep both versions for the carried patch's distinctive behavior:

```bash
git show e3c3941d0c:<path> | grep -n 'localOnly\|reason and reason not in'   # carried fix
git show HEAD:<path>        | grep -n 'localOnly\|reason and reason not in'   # upstream — empty = NOT absorbed
```

If upstream lacks the carried fix, **merge both sides**: keep upstream's new feature AND re-apply the carried patch's block. The correct resolution is a combination, not a side. Verify the merged file has both features and no conflict markers before continuing.

```bash
git checkout --ours <file>     # rebase: --ours = upstream HEAD
git add <file>
GIT_EDITOR=true git rebase --continue
```

**`git checkout --ours` after `git add` is a no-op.** Once a conflicted file is staged, the conflict state is gone and `--ours`/`--theirs` find nothing to restore. If you staged the wrong side, pull the version you want directly from a ref instead: `git show HEAD:<path> > <path>` (upstream) or `git show e3c3941d0c:<path> > <path>` (the carried commit), then re-add.

**After the rebase, finish the wrapper's remaining steps by hand** (it aborted before them): push `local` to the fork (`git push prasta1 local --force-with-lease`), then restart the gateway from a shell (`hermes gateway restart` — kills in-flight turns, so it must come from outside the app). Verify the live install landed on `local` with the carried commit: `git -C ~/.hermes/hermes-agent branch --show-current` should say `local`, and `hermes --version` should show `local <sha> (+1 carried commit)`.

**A dry-run against the old tip does not cover the post-update state.** The update pulls hundreds of new commits; a conflict can appear only after those land. A clean cherry-pick dry-run against the pre-update `main` proves nothing about the post-update rebase. Expect the conflict to be possible and have the resolution procedure ready.

## Gateway restarts are not crashes — exit 75 and exit 1 are designed

The gateway has two deliberate restart conventions, and both used to be reported as crashes:

- **75** = `GATEWAY_SERVICE_RESTART_EXIT_CODE` (`gateway/restart.py`) = `EX_TEMPFAIL` from
  `sysexits.h`. Raised by `_resolve_gateway_exit_verdict` (`gateway/run_shutdown.py:47`) so the
  supervisor relaunches on new code. The service definition declares it
  (`SuccessExitStatus=75` / `RestartForceExitStatus=75`), and `tests/gateway/test_startup_restart_race.py`
  pins it. `hermes update` restarts the fleet this way.
- **1** = signal-initiated shutdown with no restart request. `run_shutdown.py:49` logs
  `signal-initiated shutdown without restart request` and returns a failure verdict on purpose.

Both exit by **raising** `SystemExit`, not returning. So the diag tag is `asyncio.run.SystemExit`
with a traceback, `gateway.exit_clean` is never written, and the next process's ledger reports the
predecessor as `exited UNCLEANLY (no exit path ran — SIGKILL / OOM / VM death)`
(`gateway/lifecycle_ledger.py`). That verdict is wrong for both paths, and repeating it on every
update is what makes a real crash invisible.

**When told the gateway "crashed", read `gateway-exit-diag.log` for the `code` and `gateway.log`
for the teardown phases before believing it.** A designed exit logs every shutdown phase
(`drain done`, `all adapters disconnected`, `SessionDB close done`) and finishes in ~1.4s. A
SIGKILL/OOM writes no diag event at all.

A 75 exit emits **only** `asyncio.run.SystemExit`; there is no accompanying `gateway.exit_nonzero`.
An exit-1 emits `asyncio.run.returned success=False` + `gateway.exit_nonzero` instead.

`scripts/watchdog_gateway_lifecycle.py` now emits 🔁 for these and keeps 🔴 for anything it cannot
prove intentional. It fails closed on purpose: an exit with no matching intentional marker, or a
`previous_unclean_exit` whose `prior_pid` does not match a recorded intentional exit, still pages.
Pid-stamp the verdict — a SIGKILL cannot inherit the previous life's classification.

Correlate the signal marker by **timestamp, not file position**. A "marker after the last startup
banner" check looks correct and is wrong: this watchdog runs on a 15-minute interval (deliberate; the
deadman covers scheduler death independently), so by the time it reads the file the replacement
process has usually logged its own banner, which flips the comparison and mislabels a clean exit as a
crash.

## Hindsight Insight Querying

To enable direct insight querying from the agent, we have added a wrapper tool.
- Script: `~/.hermes/scripts/hs-query.py`
- Usage: `hs-query <days>`
- Purpose: Retrieve summarized observations from the Hindsight semantic memory graph.

## Archived MBP skills

The MacBook's 171 skills were triaged with Patrick on 2026-10-01: 10 promoted into `skills/`, 3 folded into this skill and `embedding-path-audit`, 157 removed from the working tree, 1 postponed. The per-skill outcome is in `references/archived-mbp-skills-index.md`; the reasoning is in `docs/superpowers/plans/2026-10-01-mbp-skills-archive-triage.md`. Only `skills-archive-mbp-2026-10-01/business/indagate-strategy/` remains on disk (decision pending). Everything removed is recoverable from git history at the commit that deleted it (`git log --diff-filter=D -- skills-archive-mbp-2026-10-01`).

## References

- references/operations-notes.md — procedural/troubleshooting notes (migrated from MEMORY.md)
- references/lfm-reasoning-validation.md — reasoning-template models (LFM2.5): validation protocol, three budget traps, A/B results
- references/archived-mbp-skills-index.md — the 171 MBP skills and what happened to each
- references/multiplexing-behavior.md
- references/oauth-token-sync-recipe.md
- references/photon-sidecar-crash-log-excerpt.md
- references/web-ui-400-auth-callback.md
- references/oauth-gateway-multiplexing.md
- references/api-server-authentication-issue.md
- references/authentication-root-cause-analysis.md
- references/session-listing-bug.md
- references/gateway-multiplexing.md
- references/gateway-session-profile-isolation.md
- references/multi-profile-session-isolation.md
- references/profile-gateway-behavior.md
- references/oauth-token-synchronization.md
- references/profile-distributed-endpoints.md
- references/provider-resolution-chain.md
- references/provider-organization.md
- references/duplicate-provider-fix.md
- references/tailscale-remote-setup.md
- references/WEBSERVER_BINDING.md
- references/PROFILE_LIST_DEDUPE.md
- references/openrouter-free-tier-debug.md
- references/photon-credential-conflict-resolution.md
- references/webui-model-picker-debugging.md
- references/fix-details.md
- references/fix-verification.md
- references/user-experience-analysis.md
- references/user-preference-troubleshooting.md
- references/desktop-gateway-oauth-setup-session.md
- references/hermes-backup.md
- references/hermes-desktop-plugins-session.md
- references/hermes-themes-session.md
- references/hermes-provider-configuration-session.md
- references/hermes-profile-authentication.md
- references/hermes-provider-cleanup.md
- references/session-cleanup.md
- references/distributed-prompt-optimization.md
- references/lmstudio-troubleshooting.md
- references/api-server-session-profile-isolation.md
- references/gateway-api-session-profile-fix.md
- references/oauth-profile-token-sync.md
- references/debugging-hermes-tui-commands.md
- references/switch-to-personal-project.md
- references/gateway-multiplexing-in-multiprofile-setup.md
- references/profile-distributed-endpoints.md

## Templates

- templates/clock.mjs — Complete working clock widget for TUI dock
- templates/skin.yaml — Hermes color theme template
- templates/gateway-multiplexing-config.yaml
- templates/oauth-token-sync-recipe.md
- templates/coding-auxiliary-models.yaml
- templates/moa-preset-examples.yaml
