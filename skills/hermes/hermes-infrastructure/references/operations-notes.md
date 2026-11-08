# Operations Notes (migrated from MEMORY.md 2026-09-13)

Procedural/troubleshooting content migrated out of the always-injected memory store during the
2026-09-13 prune. Memory is capped at 12K chars and re-sent on every turn, so procedures belong
here where they load only when relevant. Source snapshot: `git -C ~/.hermes show 91b3be0:memories/MEMORY.md`.

## Renaming a profile directory under a live multiplexed gateway

Do NOT `mv` a profile dir (`~/.hermes/profiles/<name>`) while the multiplexed gateway serves it. The rename itself is fine, but the NEXT gateway teardown **recreates the old-named path**: the dying process writes its teardown state (state.db WAL retirement, lock files) back to its remembered HERMES_HOME, and the recreated shell (template SOUL.md, fresh state.db, no memories/skills) counts as a profile again via identity markers — it re-registers on the next scan and the old bot name comes back in every surface.

Clean sequence for a profile rename (otto → cruz, verified 2026-10-18):

1. Kill/close every live session for that profile (desktop isolated-serve processes carry `HERMES_HOME=.../profiles/<old>` in env; `mcp_death_supervisor` and pyright-langserver children pin it too).
2. **Restart the gateway BEFORE renaming** (`hermes gateway restart` from a shell outside the app, or have the user `/restart`), so no process holds the old home. Verify `hermes gateway list` no longer shows the profile.
3. `cp -a` backup, `mv` the dir, then update the literal `profiles/<old>` string across the renamed tree (build_store.py BASE paths, SKILL.md, memories, cache indexes, checkpoints/curator ledgers). Leave `logs/`, `.curator_backups/blobs/` (content-addressed — editing breaks sha256 names), and runtime `gateway.lock` (the gateway rewrites it).
4. Swap the CLI alias wrapper (`hermes profile alias <old> --remove`, `hermes profile alias <new>` — wrapper lives in `~/.local/bin/`, and profile discovery treats it as a registry entry independent of the directory).
5. Re-register in the desktop Bots tab and relaunch. If the gateway re-homed a phantom shell anyway, deleting the old name from the Bots tab tombstoned it (`profiles/.deleted/<name>`) and unserved it live via the control socket — no second restart needed.

Signs the phantom came back: a <1/10th size copy of the profile with a template SOUL.md and empty memories/skills, plus the old name still listed by `hermes profile list` with `Gateway: running` despite `profiles/<old>` being absent.

## Alert routing on the Studio (audited 2026-09-16)

Everything infra-alerting is **Discord-only, and has been since 2026-08-28**; Telegram keeps only
two paths (deadman + gateway lifecycle notices), both documented below. Map:

| Producer | Where it pages |
|---|---|
| Memory, Clef Window, Gateway Lifecycle, llama-swap Sentinel (own cron jobs), plus Auth / Health / Outcomes (folded into the daily infra digest), plus Weekly Report | Discord #alert-infra `1522663709091168537` (via cron `deliver`) |
| `hermes-git-backup.sh` (launchd, daily 03:30) | Discord #alert-infra, posted by the script itself via `hermes send -t discord` — independent of the cron ticker |
| `watchdog_deadman.sh` (launchd, 10m) | **Telegram DM only** (`hermes send -t telegram`: home channel) — ticker staleness + broken alert path |
| Gateway start/stop notices | Both DMs (Discord `1539964352575307797` + Telegram `2058810010`) |
| Briefs / Gmail triage | #news-brief `1542864535826735194` / #alert-email `1544358067318038568` |

**Coverage gaps that remain:** Prometheus/node_exporter/blackbox/Grafana all run with **zero alert
rules**; Mnemosyne `sync-serve` has no watcher (its 6h health cron is disabled);
`llama_swap_monitor.py` was retired Oct 2026 — dormant since ~18 Sep (nothing scheduled it), and the llama-swap Sentinel absorbed both of its checks (:9292 models + MacBook :8999).

**How to audit this class of question:** read `j['deliver']` for every job in
`~/.hermes/cron/jobs.json`, then grep `~/.hermes/scripts/*.sh` for direct `"$HERMES_BIN" send -t`
calls (script-level sends bypass cron routing entirely), then
`/usr/libexec/PlistBuddy -c "Print :ProgramArguments" ~/Library/LaunchAgents/*.plist` for launchd
producers. `delivery_outcome` in `~/.hermes/cron/executions.db` shows `delivered` vs `suppressed`
(empty output) vs null, but not the target.

## Prometheus / node_exporter / Grafana (Studio)

All three are brew services (`sh.brew.prometheus`, `sh.brew.node_exporter`, `sh.brew.grafana`).
Prometheus 3.14 binds loopback `:9090`; since 2026-09-16 it is also reachable tailnet-only at
`https://studio.taile85139.ts.net:9090` via `tailscale serve --bg --https=9090 http://127.0.0.1:9090`.
**Grafana is on `:3001`; `:3000` has no listener** — the Open WebUI container that used to hold it was decommissioned 2026-09-23 (no container, no image, no launchd job, no tailscale serve mapping). Retention 15d.

- **No alert rules anywhere**: Prometheus has no `rule_files`, Grafana has 0 rows in `alert_rule` and
no receivers. The stack can be read, never pages.
- Metric sources: `macmon` (job `studio`/`macbook`, `:9199`, CPU/GPU/RAM/power/temp), node_exporter
(`:9100`) with the **textfile collector** at `/opt/homebrew/var/node_exporter/textfiles`, and
blackbox HTTP probes (`:9115`). Collector jobs (`com.*.textfile`) rewrite `agent_health.prom`,
`hermes_usage.prom`, `claude_code_usage.prom` every few minutes; series land under `job="node-studio"`.
- `hermes_model_*` labels: `host`, `model`, `provider`, `kind` (input/output/cache_read/reasoning),
`tier` (cloud/local/unknown). `claude_code_*` adds `project`. `agent_running` /
`agent_last_exit_status` are keyed by launchd `label`.
- **Prometheus has no saved dashboards or image export**, so the repeatable views are
  (a) bookmarks: `/query?gN.expr=...&gN.tab=0|1&gN.range_input=24h` (any number of graphs, tab=1 is
  the table view), and (b) `~/.hermes/monitoring/prom_snapshot.py --hours N`, which renders
  `fleet/studio/usage/claude_code.png` from the query API. Query cheatsheet:
`~/.hermes/monitoring/prometheus-queries.md`.
- **macOS tailnet self-test trap:** you cannot curl your own `100.x` address from the node that owns
it (no `tailscale0`); a `000` there is not evidence the service is unreachable. Verify from another
node.

## The outcomes watchdog (`scripts/watchdog_outcomes.sh`)

Hourly `no_agent` job `a51280fccc82`; stdout is the alert, empty output = healthy. Sections: cron
status/delivery errors, git-backup freshness, **hindsight dump freshness (added 2026-09-16)**, runaway
`hermes serve`, MCP servers enabled-but-failing. Tunables are env vars:
`OUTCOMES_MAX_SERVE`, `OUTCOMES_BACKUP_MAX_AGE_H` (36), `OUTCOMES_MCP_MAX_AGE_SEC` (8h),
`OUTCOMES_HINDSIGHT_MAX_AGE_H` (**80h** — the dump job is Mon/Wed/Fri, so 36h false-pages every
Monday), `OUTCOMES_ALERT_REPEAT` (5 cycles before auto-ack and quiet for 24h).

- The hindsight check reads the **newest dump's mtime** (`~/backups/hindsight/hindsight-*.dump`),
not the log text — the log's `Sun Sep 13 03:10:07 EDT 2026` stamps need locale/zone parsing.
- `alert_key <key> <msg>` turns the key into a **filename**, so the key is sanitized to
`[:alnum:]._:-` before use. An unsanitized key (a cron message containing `/` and a newline) built a
nonexistent nested path, the state write failed under `set -e`, and the watchdog died silently —
taking every alert it exists to send with it.
- Silence one alert by hand: `~/.hermes/scripts/ack_outcomes.sh <key>` (`-r` to un-ack). State lives
in `~/.hermes/state/watchdog-outcomes/<key>.{count,first_seen,last_seen,ack_until,sig}`.
- **Test edits in an isolated `HERMES_HOME`**, not just `bash -n`: the script dies on a missing
`cron/jobs.json`, so a real-state dry run proves nothing about the branches you added.

Procedural/troubleshooting content migrated out of the always-injected memory store during the
2026-09-13 prune. Memory is capped at 12K chars and re-sent on every turn, so procedures belong
here where they load only when relevant. Source snapshot: `git -C ~/.hermes show 91b3be0:memories/MEMORY.md`.

Procedural/troubleshooting content migrated out of the always-injected memory store during the
2026-09-13 prune. Memory is capped at 12K chars and re-sent on every turn, so procedures belong
here where they load only when relevant. Source snapshot: `git -C ~/.hermes show 91b3be0:memories/MEMORY.md`.

## macOS / Tailscale networking

- macOS Tailscale uses the **utun4** interface; there is **no `tailscale0`**. Binding a process to
a `100.x` address directly will not work.
- **RETIRED 2026-09-27**: the Hermes web UI (`127.0.0.1:8787`, `com.hermes.webui`) is disabled.
It was NOT tailnet-exposed despite this note and its own launcher comment claiming so — `tailscale
serve` maps 5200, 6333, 8010, 8188 and 8642, never 8787. Nothing depended on it (no hermes-agent
call sites, cron `platform: webui` is provenance only, state dir last written Sep 22), so it was
retired rather than repaired. See DEV-408.
- The tailnet binding rule still applies to the services that ARE served: bind loopback and let
`tailscale serve` map them; clients reach those only on the tailnet with **MagicDNS enabled**.

## Gateway: lifecycle, launchd, Photon

- The Studio gateway runs as a launchd service. Restart with the modern syntax:

```bash
launchctl bootout gui/$(id -u)/ai.hermes.gateway
sleep 3
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/ai.hermes.gateway.plist
```

- **The agent cannot restart the gateway from inside it** — the guard blocks it (SIGTERM would kill
the command before it completed), and a detached/delayed wrapper is refused too. Hand the user
`/restart` in chat (graceful; drains active runs first) or `hermes gateway restart` from a shell
outside the app.
- **Photon sidecar** needs `npm install` in `plugins/platforms/photon/sidecar/`.
- API server listens on **:8642**; desktop app remote is `studio.taile85139.ts.net:9119`.
- MBP convenience aliases: `hstudio`, `hrun` (plus `hwork`, `hpersonal`).

## Gateway lifecycle notifications

Sent per-platform to the HOME channel, gated by `gateway_restart_notification` (currently `true`).
There is **no dedicated alerts-channel routing in core** (feature request filed:
NousResearch/hermes-agent #76780). These are the **only** messages that still reach Telegram: the
start/stop notice goes to the Telegram DM `2058810010` *and* the Discord DM
`1539964352575307797`.

**Destination control lives in the cron job's `deliver`, not in config.** `telegram.allowed_chats`
is an *inbound group gate* (`plugins/platforms/telegram/adapter.py::_check_group_trigger_rules`,
skipped entirely when empty) — it never routed outbound alerts. To retire a platform as an alert
target, edit every job's `deliver` string (set with `hermes cron ...`; tracked in
`~/.hermes/cron/jobs.json`, which the git backup commits, so the switch is auditable).

Legacy Telegram alerts channel: `-1003940233719` ("Hermes Alerts"). It was the watchdog fan-out
target until 2026-08-28, when every watchdog job's `deliver` became Discord-only. The bot is still
an admin of it; `allowed_chats` no longer lists it. To stop it cold, remove the bot from the
channel (or leave it — nothing targets it).

## config.yaml corruption pattern (Hermes)

List-valued fields (`plugins.enabled`, `model_catalog.excluded_providers`) sometimes get written as
Python/JSON **strings** instead of YAML lists. They still load, and are silently ignored. Fixed
`plugins.enabled` on the Studio 2026-08-02; filed Linear DEV-347.

**Always type-check list fields when auditing config.** To hide a provider from Hermes pickers use
`model_catalog.excluded_providers` — `hermes tools disable` does **not** hide providers.

Remember `hermes config set <key> <value>` is the only sanctioned write path; the `patch` tool
refuses `config.yaml` outright.

## `memory` tool: `replace` on `target=user` clobbers the whole file

Verified 2026-09-17. Calling the memory tool with `action=replace`, `target=user`, and an `old_text`
substring that matched inside the **first** entry rewrote `USER.md` down to that entry plus the
trailing one. 5,528 chars and 9 `##` sections became 769 chars and 2 entries. The other 8 sections
(Identity, Professional, Qualcomm accounts, Home AI Stack, Communication Preferences, Technical
Conventions, Community, Interests) were gone from disk.

**Never use the memory tool to edit USER.md.** Edit `~/.hermes/memories/USER.md` directly with the
`patch` tool, then re-check the section count. Same care for MEMORY.md.

Recovery path, in order:

1. `git -C ~/.hermes show HEAD:memories/USER.md` — `memories/` is in the .gitignore allowlist, so the
   pre-clobber version is in git. This is the fastest and most complete source.
2. `~/.hermes/memories/USER.md.bak-prune-*` — prune-era backups, older but present.
3. Before restoring, confirm byte size **and** `grep -c '^## '` against the known-good counts.

Then prove the restore with `git diff memories/USER.md`: the diff must contain only the intended
change. A diff showing whole-file replacement means the restore is wrong.

One follow-on trap: `memories/` is whitelisted, so any stray file dropped there (e.g. a
`.CLOBBERED-*` rescue copy) gets committed by the next backup run. Clean up rescue copies.

## Disabling an MCP server

`hermes mcp` has **no `disable` subcommand**. Manually comment out or remove the server in
`~/.hermes/config.yaml` under **both** `mcp.servers` and any later top-level block, then restart the
gateway. (See also the MCP auth/reload traps in SKILL.md — an already-registered server keeps
retrying with its captured config until the process reloads.)

## Dashboard auth internals

Dashboard auth uses an `scrypt` `password_hash` plus an HMAC secret. A past OAuth mismatch turned
out to be a **redirect URI mismatch**, fixed by matching the dashboard's canonical URL.

## Git / GitHub

- GitHub hard-blocks objects over **100 MB** (e.g. `state.db`). Keep them excluded from commits or
  pushes fail.
- Hermes backup remote: origin is `https://github.com/prasta1/backup-hermes-macstudio.git`.

### In `~/.hermes`, never commit without naming the path

`scripts/hermes-git-backup.sh` runs `git add -A` (line 150) and only *then* applies its
structural-change guard: more than `BACKUP_MAX_FILES` (default 50) files or
`BACKUP_MAX_DELETES` (default 15) deletions and it alerts `DEFERRED ... review and commit
manually, auto-backup skipped`. **It defers without unstaging.** The index keeps the whole
backlog, so from that moment the repo has a populated staged index waiting for a human.

Consequence: `git add <one-file>` followed by a bare `git commit` commits the entire staged
backlog under your message. Measured 2026-11-02: a commit labelled for a single script landed
**57 paths** (28 added, 27 modified, 2 renames).

```bash
# Rule: name the path in the commit too. This takes only that path from the index and
# leaves everything else staged exactly as it was.
git -C ~/.hermes commit -m "<message>" -- <path>
```

Check for a pre-staged backlog before staging anything, and make it the first command of any
commit step here:

```bash
git -C ~/.hermes diff --cached --name-only | wc -l    # non-zero before you stage = you are not alone
```

To split a swept commit after the fact, and only while it is unpushed:

```bash
git -C ~/.hermes reset --soft HEAD~1
git -C ~/.hermes commit -m "<message>" -- <path>      # the rest stays staged
```

This is a commit-shape rule, not a safety one: `config.yaml` and `.env` are gitignored at this
root, and a deferred backlog is ordinary backup content (skills, plugins, memories, plans,
llama-swap config, cron state). Audit a commit you did not intend to write with
`git show --pretty=format: --name-status HEAD | wc -l` and `scripts/hermes-secret-scan.py`
(0 in-repo findings is the pass), and remember the deferral guard is the review step you just
consumed.

## Skills directory hygiene (historical churn, resolved)

`~/.hermes/skills/` accumulated symlinks/submodule pointers to `~/.agents/skills/`, which produced
unworkable ~394-file git churn. Symlinked external skill roots also make "every SKILL.md change is a
normal file modification" an unsafe assumption when staging.

**Standing rule: skills live as real directories under `~/.hermes/skills/`.** If the churn returns,
restore by copying the real trees from `~/.agents/skills/` back in as normal directories.

## OOM triage

Distinguish three cases: **container cap hit** vs **leak** vs **host-pressure collateral kill**.
LM Studio Metal OOM plus orphan helper processes plus low `vm_stat` free pages indicates *host
pressure*, not a container limit.

## Hermes-webui vs gateway (separate launchd jobs)

`hermes-webui/server.py` (`com.hermes.webui`, :8787, **retired/disabled 2026-09-27**) and the
gateway (`ai.hermes.gateway`, :8642) are **separate launchd jobs**. The 409 `agent_runtime_stale` fix is to set config.yaml
`webui_chat_backend: gateway` and export the gateway-mode env vars in `hermes-webui-launch.sh`.
That workaround is retired.

**Quirk:** `/api/health/agent`'s `gateway_chat` field reads **env vars only**, never config.yaml.

## `hermes update` merge conflict on the custom `local` branch

The updater tracks `local` (fork branch: discord brief embeds, config/email fixes) and merges
`origin/main` **in place** rather than resetting. On conflict it aborts the whole update and
leaves the tree unchanged — nothing was half-applied, so resolve in
`~/.hermes/hermes-agent` and re-run.

1. **Preview without touching the tree:** `git merge-tree --write-tree --name-only local origin/main`
   (git ≥ 2.38) prints the conflicted paths. Expect it to be one file, not many.
2. `git merge origin/main` — let every other file auto-merge.
3. **Resolve by keeping BOTH sides; never drop the local side.** Read both diffs against the
   merge base (`git diff $(git merge-base local origin/main) <side> -- <path>`).
4. **The trap: an upstream refactor of the block your local code sits next to.** Keeping the
   local hunk verbatim re-introduces a stale override that silently reverts upstream's
   refactor. In the Sep-2026 merge, upstream replaced `DiscordAdapter.send_exec_approval` with
   `_EA_*` constants + `_exec_approval_cmd_budget` + `_send_exec_approval_prompt`, moving the
   public method to `BasePlatformAdapter`. Correct resolution: keep the local additions
   (`_parse_brief_content`, `_send_brief_embed`), **delete** the local `send_exec_approval`
   override, splice upstream's block after it.
   Verify the deletion landed: `'send_exec_approval' in DiscordAdapter.__dict__` must be
   `False` while `hasattr(...)` stays `True` via the base class.
5. **Take upstream's helper swaps inside the same hunk** — e.g. local `return {"error": ...}`
   became upstream `send_error(...)` from `gateway.platforms._shared`. Keep upstream.
6. Verify before committing: no leftover markers (`grep -n '^<<<<<<<\|^>>>>>>>\|^=======$'`),
   `python3 -m py_compile <file>`, then import the plugin for real:
   `./venv/bin/python3 -c "import importlib; importlib.import_module('plugins.platforms.discord.adapter')"`.
   **The Studio has NO pytest in any venv or system Python — the MacBook is the only box that runs
   the suite** (`venv/bin/python`, pytest 9.1.1 as of 2026-10-02). Sync changed files over SSH to
   run tests there; verify they match with `shasum -a256` before trusting a result.
7. `git add <paths> && git commit --no-edit`, confirm
   `git rev-list --left-right --count local...origin/main` ends in `0`, then re-run `hermes update`
   to finish dependency sync + service restart.

**Never `git reset --hard` or rebase to "fix" this** — local commits must survive.

## Two-machine commits: verify the parent before calling it a fork (2026-10-02)

The Studio and the MacBook each hold a `local` checkout of `~/.hermes/hermes-agent`. A change made
on both produces **two commits with different SHAs that share the same parent** — siblings, not a
diverged history. Confirm with `git rev-parse HEAD^` on each before characterizing it:

```
Studio:  edd949fc15  ─┐
                      ├─ parent: 1bb632be38  (identical)
MBP:     6c370f2778  ─┘
```

Identical trees, differing tips. **There is nothing to reconcile and no work is lost** — the only
consequence is that a future `git push` from one side cannot fast-forward the other, which needs a
`fetch` plus `reset --hard` (or a cherry-pick), not a merge.

**Do not infer divergence from differing SHAs.** During the Honcho prune I reported the two commits
as having "no shared ancestry" by reasoning from the SHAs alone, without checking parents. They
shared full ancestry, one commit deep. Read `HEAD^` before making any claim about fork state.

Pick a canonical machine at the moment you first push or open a PR — not before. While `local` stays
unpushed (deliberately: it carries ~40 private patches absent from any remote), duplicated local
commits cost nothing.

## Wide pytest sweeps on the MacBook: raise the fd limit first

The MBP shell has `ulimit -n 256`. Running thousands of tests in one pytest process exhausts file
descriptors and produces a wall of `OSError: [Errno 24] Too many open files` reported as mass `E`
errors that look exactly like broken code. Measured 2026-10-02: the same sweep reported mass errors
at the default limit and **2207 passed** with the limit raised.

```bash
ssh macbookpro 'cd ~/.hermes/hermes-agent && ulimit -n 10240 && venv/bin/python -m pytest tests/hermes_cli/ -q -p no:randomly'
```

`pytest-timeout` is **not** installed (`--timeout=` is an unrecognized argument), so bound a run
with the shell `timeout` command instead.

**Establish a baseline before blaming your own change.** `git stash push --include-untracked`,
re-run, `git stash pop`. Two known pre-existing failures on the MBP as of 2026-10-02:
6 in `tests/hermes_cli/test_commit_build_cli.py` and 2 Telegram collection errors from a missing
`python-telegram-bot`. Both reproduce identically with changes stashed.

Also: `ulimit -n 256` on the MBP means a *partial* run can hide which failures are real. Read the
actual `AssertionError`, not the pass/fail list — during this prune two successive "fixes" were
attempts against a false negative (a piped-away merge exit code read as "0 conflicts" when the
merge had failed outright).

## Bundled plugins: the greyed-out capability list is a directory scan

Settings -> Capabilities enumerates providers by **iterating the plugin directories**, not from any
config flag. `plugins/memory/_iter_provider_dirs()` is a bare `iterdir()` over
`plugins/memory/`, first-seen-wins across bundled, user, and project roots. There is **no exclusion
or tombstone mechanism** — `hermes plugins disable memory/<name>` does not work for bundled
providers (they are not in the plugin registry, so the command reports "No plugin named ...").

So a greyed-out row for a bundled provider is not a stale config entry. It means the directory
exists and no config file was found at any `resolve_config_path()` candidate. The only way to
remove one is to delete its directory from the checkout, which means a local commit that the next
`hermes update` will re-conflict against — see the `hermes update` section above. Enable
`git config rerere.enabled true` (done 2026-10-02 on both machines) so repeat conflicts resolve
themselves.

Deleting a bundled provider does **not** stop `hermes update` from calling into it: check
`hermes_cli/update_cmd_maint.py` for per-update syncs that import the removed module. The Honcho
removal found `_sync_profiles_after_update()` calling `import_provider_module("honcho", "cli")` on
every update, hidden inside `suppress(Exception)` — it could not crash the update, which is exactly
why it would have failed silently forever.

## Codebase review method

When reviewing an entire codebase with no fixed point, classify findings as: **hard break**,
**latent risk**, **polish/data quality**. Report exact `file:line` references and lead with what is
currently broken before latent risk or polish.

## Disk space: Time Machine local snapshots

Local Time Machine snapshots pin disk blocks after deletion, so `df -h` under-reports free space. Reclaim with `sudo tmutil thinlocalsnapshots /` (needs a real Terminal; the Hermes TUI has no sudo TTY).

## Moved from MEMORY.md (pruned 2026-10-06)

Procedures and tool quirks that were taking every-turn memory space. Facts only, verbatim where possible.

### LFM2.5 (and Liquid-style templates) reasoning behavior — measured 2026-10-13

Liquid's LFM2.5 chat template **hardcodes `assistant\n thinking` as the generation prompt** — every
request starts with reasoning, and the default budget (`--reasoning-budget -1`) is unrestricted.

- `--reasoning off` and `--no-reasoning-preserve` do **NOT** stop thinking. The template overrides
  them; `--no-reasoning-preserve` only keeps history clean (it controls whether prior thinking is
  re-emitted), it does not prevent new thinking.
- The real lever is **`--reasoning-budget N`**: 0 = direct answer, 200 = brief reasoning then
  answer, -1 = unrestricted. Measured: **budget 0 is NOT reliably correct on multi-step reasoning**
  — the UD build answered a 2-step algebra problem right once at budget 0, then WRONG on three
  greedy redraws (15,15,15 vs correct 12). A single "correct" draw is not verification; redraw
  greedy (temp 0) before trusting a budget setting.
- **256 is the verified setting for both LFM2.5 builds** (2026-10-13): correct on algebra, riddle
  and facts at temp 0, ~200-280 tokens per answer. QAD needs it to be trustworthy, UD too.
- **Per-request `reasoning_budget` in the API body is IGNORED** by llama-server — the flag must be
  in the server's `cmd:` line in llama-swap config.
- **QAD ≠ "reasoning-only"**: LFM2.5 QAD-Q4_0 switches to `content` after thinking, same as the
  UD build; the pull-time note claiming it never does was wrong. Same template byte-for-byte.
- Task split that emerged: direct-answer capable model (UD) thrives at budget 0; the QAD build
  gave a WRONG algebra answer at budget 0 (10 vs 12) and needs a positive cap (256) to stay
  trustworthy. Do not blanket-set budget 0 across models — verify per model.
- No MTP heads on LFM2.5 GGUFs (verified in headers, zero nextn tensors) — ngram-simple only.
- Speed guess at pull time ("expect 150-200 tok/s") was wrong: measured ~98-115 tok/s on this box.

### Laya decision-model server — RETIRED 2026-10-20
- **RETIRED**: `ai.laya.serve` launchd job archived to `~/.hermes/state/retired-launchagents/ai.laya.serve.plist.retired-*`, venv `~/.venv/laya` (937M) and HF cache entry `models--convaiinnovations--laya` deleted. Nothing referenced it (not in llama-swap config, not in hermes config; the only cron mention was a stale `last_error` string). Do not re-enable without asking.
- Historical (pre-retirement): served `/v1/systemone` on 127.0.0.1:8000, MPS backend, `HF_HUB_OFFLINE=1`. Checkpoint cache `~/models/.hf/hub/models--convaiinnovations--laya` (typed-decisions subfolder, ~843MB). API key `~/.hermes/secrets/laya.key`. Wrapper `~/.venv/laya/serve_laya.sh`. Client `scripts/jev_query.py` pins `model='typed-decisions'`.
- AUTO-ROUTING PITFALL (historical): with `model=None`, confident-English text routes to the 'english' checkpoint (bundle-repo root, ~330MB) instead of typed-decisions. With only typed-decisions cached + `HF_HUB_OFFLINE=1` that throws `OfflineModeIsEnabled`, masked as HTTP 500. ALWAYS send `model='typed-decisions'`.

### clef-flash vs Laya bakeoff (2026-10-03, real ground truth)
47 real emails, all labeled by Patrick: clef-flash recall 100% / FP 17%; Laya recall 75% / FP 71% (it never really gated). clef-flash is the better gate (11x slower, 20x footprint). Data: `~/.hermes/cache/scratch/clef_test_set.json`, `clef_bakeoff_results.json`. Email triage still has no automated ground-truth collection (approved.log/sent.log empty).

### clef-flash — A2 windowed serving + watchdog (2026-10-20)

clef is the Gmail triage classifier (9B Qwen3.5 + joint schema head, served on `:8001` via torch/MPS — **cannot ride llama-swap**, the joint head isn't in the GGUF quants). It was resident 24/7 (~19GB RAM) for a once-daily 7:30 job. Now windowed:

- **`ai.clef.serve.plist`**: `RunAtLoad=false` (no auto-start at login), `KeepAlive=true` (reliable during window). Manual — only boots when the window job starts it.
- **`ai.clef.window-start`** (launchd, 07:00): runs `~/.hermes/scripts/clef-window.sh start` → bootstraps clef, polls `:8001/health` up to 180s.
- **`ai.clef.window-stop`** (launchd, 08:00): runs `clef-window.sh stop` → boots clef out.
- **`clef-window.sh`**: start/stop wrapper; logs to `~/.hermes/logs/clef-window.log`. Manual use: `bash ~/.hermes/scripts/clef-window.sh start|stop`.
- **Watchdog**: cron job `c4ff863785fd` "Infra Watchdog Clef Window" (`no_agent`, every 5m, Discord #alert-infra). Runs `watchdog_clef.sh` — **silent outside 07:00–08:00** (clef is supposed to be down), alerts if clef is down *during* the window (means the triage is silently failing open → emails classified "reference" + needs_review). Tunables: `CLEF_HEALTH_URL`, `CLEF_WINDOW_START_HH`/`END_HH`.
- **Fail-open behavior**: `triage.py`'s `clef_gate()` and `classify_email()` both fail open — if clef is down, emails get "reference" + needs_review instead of properly triaged. That's why the watchdog matters: it's a silent degradation otherwise.
- Model + venv + plist stay fully onboard for future use; just `clef-window.sh start` whenever needed.

### Hermes Desktop version fence / `client_upgrade_required` (2026-10-19)

The desktop app's session mutations (archive/rename/delete) are gated by a **mutation fence** in `hermes_cli/web_server_sessions.py` (`_mutate_session_request`). A client that sends no mutation identity (`request_id`/`expected_revision`/`expected_generation`) gets `409 client_upgrade_required: this app is out of sync (different versions) with the Hermes backend; update the app to edit sessions`. The code comment names the cutoff: "A pre-fence client (Desktop <= 0.22.2) sends none of the identity."

**The version-label trap that makes this hard to diagnose:** the desktop UI's version label shows the **connected gateway's** version (resolved live from `GET /api/health` via `resolveGatewayVersion` → `firstRealVersion`), NOT the app's own. The app's own version is a placeholder (`0.0.0` in `package.json`/`Info.plist`; `install-stamp.json` has `displayVersion: null`). So the UI can show `v0.22.2+1891` — identical to the backend — while the app is actually a pre-fence build. The "different versions" error and the label contradict each other. Filed upstream: NousResearch/hermes-agent #139742 (fence) + #139333 (version label).

**The fix:** update the desktop app to a build carrying the fenced client. The in-app updater self-blocks on the `stable` channel (it won't serve pre-fence builds), so use the terminal:
```bash
hermes update --set-channel main   # follows every commit; clears the fence
```
`--set-channel stable` re-pins to release cadence. Both halves must be at/past the fence commit. The Studio backend is the gateway owner; the MacBook is a thin client over ssh bridge.

### Launchd job retirement convention (2026-10-20)

To retire a launchd job cleanly (archive, don't destroy):
```bash
launchctl bootout gui/$(id -u)/<label> 2>&1 || true   # unload if loaded
mkdir -p ~/.hermes/state/retired-launchagents
mv ~/Library/LaunchAgents/<label>.plist ~/.hermes/state/retired-launchagents/<label>.plist.retired-$(date +%Y%m%d-%H%M%S)
```
Archived plists are recoverable. Retired 2026-10-20: `ai.laya.serve`, `com.macpaw.CleanMyMac5.Updater`, `com.google.GoogleUpdater.wake`, `com.google.keystone.{agent,xpcservice}`, `com.prasta.lmstudio-server` (was already `.disabled`), and the MacBook's `ai.hermes.gateway`.

**MacBook `ai.hermes.gateway` was cruft:** the MacBook is a thin client to the Studio gateway (ssh bridge), so it needs no local gateway. The launchd job was a leftover; the updater kept trying to restart it and failing with `launchctl exit 5` (osascript-wrapped plist + session-type quirk). Removed. **The updater's "gateway PID" on the MacBook is the remote Studio gateway seen through the ssh bridge, not a MacBook process** — don't mistake it for a local gateway.

### Service details
- Unsloth Studio is NOT retired: re-enabled 2026-10-04, launchd `com.unsloth.studio` RunAtLoad+KeepAlive, tailnet-only http://studio.taile85139.ts.net:8888.
- `~/.hermes/scripts/port-inventory.sh` grounds on the llama-swap proxy, not upstream ports; its known-inactive list is the authority on expected-down.
- oMLX retired on both Macs (Studio off since 2026-09-21, `ai.omlx` disabled). Bionic is active on the Studio (:41343, loopback).
- Zed ACP: launch with `hermes` + `["acp"]` and `HERMES_SKILLS_DIR` set; do NOT use `acp serve`.
- Stdio MCP subprocesses get a sanitized env: provider keys must be in the server's own config.yaml `env:` block; `.env` alone is not enough.
- Web UI :8787 RETIRED 2026-09-27 (launchd job disabled).

### Hermes-tracked background processes are reaped by gateway shutdown (verified 2026-10-20)
- A `terminal(background=true)` process is owned by the Hermes gateway: a gateway shutdown/interrupt SIGTERMs it, even mid-work. Verified when a ComfyUI server (`proc_...`, `python main.py --port 8188`) died mid-sampling with no traceback — its process record later showed `termination_source: gateway_shutdown`. Same signature killed a second instance the same evening.
- Consequence: long-running jobs (ComfyUI generation batches, big model loads) must NOT rely on a Hermes-tracked background shell surviving across turns. Launch daemons detached instead (`comfy launch --background`, launchd, or a manual detached process), and poll them with SHORT foreground calls — a timed-out foreground call may also reap the shared process group (suspected, unproven: a 420s foreground sleep timeout coincided with one death).
- `comfy launch --background` is currently broken on the Studio (FileNotFoundError: 'comfy' inside comfy-cli); `nohup ... & disown` is rejected by the terminal tool wrapper. Practical detachment path today: launchd, or accept the tracked-shell risk for jobs that finish within the turn.

## Supply-chain triage: package implants, CA anchors, PHP (verified 2026-10-21)

### litellm 1.107.0 credential stealer (PyPI, ~7h window on 2026-10-21)

The implant is THREE files at the TOP LEVEL of site-packages, not inside the package: `cook.pth`
(`import cook`), `cook.py` (~22252 B, `exec(zlib.decompress(b64decode(...)))`), `sitecustomize.py`
(~25509 B loader/stealer). Injection route: `pyproject.toml [tool.maturin] data = "cook"`.

Read-only triage path (never install or run exploit code):

- `find <venv>/lib/python*/site-packages -maxdepth 1 \( -name 'cook*' -o -name 'litellm-1.107*' \)`
  — maxdepth 1 matters: `.pth` import hooks only bite at top level.
- Compare `sitecustomize.py` size and header against the legit inventory below. Size is the tell.
- `/private/tmp` markers: macOS self-cleans /tmp in ~3 days and on reboot, so absent markers is NOT
  proof of non-execution. An absent *package* is proof; an absent marker is not.
- Clean releases: <=1.106.1, 1.106.2, 1.107.0rc1, 1.107.0rc2, plus whatever replaced the pulled
  version. Companions `litellm-proxy-extras==0.4.110` and `litellm-enterprise==0.1.78` were clean.

Legit `sitecustomize.py` inventory on these hosts, do not re-flag:

- LM Studio vendored runtimes: ~496-507 B, sha256 `6bacc291...`, identical across copies.
- Homebrew python 3.12-3.15 (MacBook): 3404 B, opens `# This file is created by Homebrew and is
  executed on each python startup`.
- Debian container files (OrbStack images): e.g. `/usr/lib/python3.13/sitecustomize.py` 155 B
  (`# apport.py hook, see /usr/share/doc/python3/README.Debian`).
- zsh trap: an unmatched glob aborts the whole command line with no output. Drive the MacBook with
  `ssh macbook bash -s <<'EOF'` plus `shopt -s nullglob`, and scope `find` to venv roots — a
  whole-home `find` times out.

### CA trust stores: what a certifi bump actually changes

Never reason from release dates — diff the label sets. Method: fetch from the PyPI JSON API
(`urls[].digests.sha256`, `upload_time`; there is NO top-level `sha256` key), unzip
`certifi/cacert.pem`, parse `# Label:` + SHA1/SHA256 comment blocks, set-diff.

Verified 2026-10-21:

- The compromised anchor is `emSign ECC Root CA - G3`, SHA1 `3043fa4f...`, SHA256 `86a1ecba...`.
- certifi `2026.10.18` (117 certs) removed ALL FOUR emSign roots. `2026.10.19` (120 certs, uploaded
  Oct 20 02:24 UTC) reinstated the three non-compromised ones and keeps `ECC-G3` out. The
  compromised anchor is absent from both new releases, so 2026.10.19 is the bump target.
- Trusting the *root* is what matters here: certifi ships no CRL/OCSP, so a fraudulent leaf signed by
  a revoked intermediate still validates as long as its root is in the bundle. Browsers are not the
  gap (Chrome/Firefox blocked Oct 17, Apple Oct 19, Microsoft Oct 20; eMudhra revoked Oct 18).
  This class of risk is network-positioned MITM only — it does not mean anything is compromised today.

Scope on these hosts:

- Studio: EVERY certifi bundle on disk carries `ECC-G3` (~43 files: live venvs, uv cache archives,
  pip-vendored copies). Highest-impact single file is what bare `python3` resolves to:
  `certifi.where()` → `~/Library/Python/3.9/lib/python/site-packages/certifi/cacert.pem` (2026.6.17).
- MacBook: the five Homebrew `certifi/cacert.pem` bundles (192 certs, dist-info `2026.10.18`) have
  ZERO emSign lines. Carriers = older venv/pipx/uv-tool bundles (2026.2.25 → 2026.7.22),
  `Library/Python/3.9`, and pip-vendored copies (py3.11/3.12/3.13 = 12 emSign lines, py3.14 = 0).
- Caveat: a 192-cert Homebrew bundle is not the byte-identical PyPI wheel (PyPI 10.18 = 117 certs).
  Report what grep proves about the on-disk file; do not claim provenance.

Fix procedure: `pip install --upgrade certifi==<target>` per live env (uv: `uv pip install -U
certifi`, or `uv tool upgrade`), then `uv cache clean certifi` so cached wheels stop propagating the
stale bundle into new venvs, and `python -m pip install -U pip` to refresh pip-vendored copies.
certifi is read per connection so most clients pick it up without a restart; long-running daemons
that built their SSL context at import may need one. Neither machine sets `SSL_CERT_FILE` /
`REQUESTS_CA_BUNDLE` in Hermes config or launchd plists, so a bump actually takes effect.

### php2shell (CVE-2026-109618 / CVE-2026-109619)

PHP 5.4.0 → 8.5.11, unauthenticated RCE. Fixed only in 8.2.35 / 8.3.36 / 8.4.27 / 8.5.12. PHP 7.4
(EOL Nov 2022) gets a source-only backport for self-builders and NO binary patch on shared hosts, so
a 7.4 site is permanent-exposure. `session.upload_progress.enabled=Off` closes only -109618; -109619
(SAPI multipart parser) stays exploitable — PHP's own advisory says partial measures "do not make an
installation safe". Never clone or run PoC repos in this class; the leaker persona and dropper
pattern (`petecooper`, MALFEX) has shipped malware-laced PoCs before.

- Local hosts: no `php`, no `composer`, nothing listening on 80/443/8000/8080/9000 on either Mac →
  N/A locally. The exposure lives on `cambridgehistoricalsociety.org` (legacy FatCow/Newfold shared
  hosting, PHP 7.4.10, no self-serve PHP version selector, origin IP answers TLS directly so any edge
  WAF is bypassable, SFTP 2222 open). Real fixes there are host-side (Newfold rebuild/migrate) or
  removing PHP entirely if the content is effectively static.
- Support channel reality: Network Solutions chat endpoints all return 403 (dead). Phone
  1-800-333-7680 (24/7); escalation `reputation@newfold.com`. Watch the `netsolinc.com` unrelated
  domain trap. Lineage: FatCow → EIG (2005) → Newfold Digital (2021) → Network Solutions (2026).
- Converging threat class: the July 2026 Packagist campaign (`dinushchathurya` dev-versions) targeted
  cPanel/WHM via poisoned GitHub Actions runners; a legacy cPanel-class shared host is in scope.

### Standing hygiene findings (2026-10-21, unresolved)

- MacBook `~/.zsh_history` contains a plaintext `lin_api_…` token. Hash-compare before calling it
  live: it is NOT the Studio Linear MCP token and NOT the MBP `~/.hermes/.env` value → stale or
  superseded. `~/Projects/backups/dotfiles-macbook/sync.sh` copies `.zshrc/.zshenv/.zprofile` but NOT
  `.zsh_history`, and refuses credential-shaped content, so it was never pushed. Revoke as hygiene;
  nothing breaks. Method: compare `shasum -a 256` prefixes, never print the secret, and watch for
  quote-stripping differences between parsers producing mismatched hashes for the same value.
- MacBook n8n (OrbStack) binds `*:5678` on IPv4 and IPv6 → LAN-reachable, and n8n holds workflow
  credentials. Recommend loopback bind plus `tailscale serve`.
- `honcho-cli` is still an installed uv tool on the MacBook although Honcho is retired, so a
  certifi/uv sweep will touch a dead tool.
- OVHcloud CLI October 2026 compromise is stealer-adjacent to the litellm pattern; not yet swept.


## Refreshing certifi trust stores fleet-wide (applied 2026-10-21)

- Scripts: `certifi_bump.py` (classify/apply) + `certifi_prepare.py` (stage build) under
  `~/.hermes/backups/certifi-bump-2026-10-21/`. Scratch copies die in 24h — the durable dir holds the
  verified wheels, the clean `cacert.pem`, and `.orig` copies of every file swapped.
- Provenance: download the replacement wheel with `curl` (keychain trust), never pip/uv through the
  tainted store; sha256-verify against PyPI's published digest, extract `cacert.pem` from the verified
  wheel, and cross-check byte equality between hosts.
- What 2026.10.19 actually contains: 120 anchors, the flagged emSign G3 pair gone, legitimate siblings
  (`emSign Root CA - G1`, `Root CA - C1`, `ECC Root CA - C3`) RETAINED — 3 certs, 9 comment lines. After
  a bump a store showing those 9 lines is correct, not residue; only `emSign.*G3` must read 0. Bundle
  lineage decides the sibling count: Homebrew's `certifi` formula ships a Mozilla-lineage bundle with
  **zero** emSign anchors while the PyPI wheel keeps the three legitimate ones, so "0 siblings" on a brew
  path and "3 siblings" on a pip-vendored path are both normal.
- By kind: venvs and interpreter site trees get `uv pip install --python <venv>/bin/python --no-index
  --no-deps --reinstall certifi.whl`; pip's vendored copy, uv cached venvs/wheel archives, and
  app-bundled runtimes (LM Studio, llmster) have no usable pip — swap `cacert.pem` in place.
- Scan interpretation: `~/.local/state/hermes-audit-adapted/` stores (hundreds of `swap-cache`/
  `install-venv` entries under `runs/*/home/...`) are throwaway test-harness sandboxes, NOT live — leave
  them; they regenerate each harness run. Hermes's OWN managed toolchain python is a real live store:
  `~/.hermes/tools/python-3.14*/lib/python3.14/site-packages/pip/_vendor/certifi/cacert.pem` (user-owned,
  swap in place; backup to `hermes-tools-python-cacert.pre-swap`). OrbStack `image-layer` entries are
  rebuild-only, never host-editable.
- Hermes toolchain self-heals pip from its bundled ensurepip wheel
  (`~/.hermes/tools/python-3.14*/lib/python3.14/ensurepip/_bundled/pip-*.whl`) and WILL re-seed the tainted
  vendored certifi within hours of a live-store swap — so swapping `cacert.pem` is NOT durable alone.
  Patch the wheel too (replace `pip/_vendor/certifi/cacert.pem` inside the zip, keep the same version,
  backup the original wheel): the re-seed then produces clean certifi. The wheel installs pip 26.2.1
  (bundled certifi tainted); `pip install --upgrade pip` reaches 26.2.2 (clean).
- PEP 668 refuses `pip install --user` on uv-managed and Homebrew pythons: swap the store in place
  (backup kept) instead of adding `--break-system-packages`.
- Homebrew ships vendored stores `0444`; owned-but-unwritable is NOT a sudo case — chmod, unlink,
  write, restore the mode. Always unlink before writing so a cache copy can't bleed through a hard
  link into a real venv. Restore the mode as an **octal** (`stat -f %OLp` → `chmod 444`), never by
  feeding `stat -f %Sp` (the symbolic `-r--r--r--`) into `chmod`: the leading dashes make chmod
  parse it as flags and the file lands `--w-------` — write-only, unreadable by every consumer
  (verified: pip then fails with Permission denied). Capture the mode BEFORE the temporary `chmod u+w`.
- A tool that bails on `not os.access(path, W_OK)` will mislabel owned-but-444 files as "sudo-only".
  Treat that verdict as a classification hint, not a fact: check `stat -f %Su` before asking for sudo.
- `uv cache clean certifi` does not reach uv's cached *venvs* (`archive-v0/*/pyvenv.cfg` trees), which
  keep seeding stale stores into new envs; refresh those in place.
- `brew reinstall` can break mid-pour (it unlinks the old Cellar dir, then errors) and leave a dangling
  `/opt/homebrew/share/ca-certificates` link — re-run it and verify the Cellar version dir plus the
  regenerated `/opt/homebrew/etc/ca-certificates/cert.pem`. Also: brew's auto-update can swap a Cellar
  version dir under a running scan, so an entry looks dirty-then-clean; re-verify by digest, not path.
- Remote hosts: pass `--no-cache-clean` (deleting their cache entries is out of scope) and run under
  `nohup` with a log. A local ssh timeout kills the pipe but leaves the orphan scanning; kill it and
  relaunch detached rather than re-running blind.
- Out of scope for a file bump: OrbStack image layers (rebuild/re-pull the image) and root-owned system
  stores (sudo).
- Both Macs ship a SECOND Apple toolchain under `/Applications/Xcode.app/Contents/Developer`, whose
  python 3.9 `pip/_vendor/certifi/cacert.pem` is a distinct root-owned file (identical digest on both
  boxes, dirty). `xcode-select -p` says which toolchain `/usr/bin/python3` actually resolves to, so the
  Xcode copy can be dormant-but-dirty. Any scan whose roots omit Xcode under-reports silently: add the
  root, then re-verify rather than trusting the previous "clean" verdict.
- Never `read_text()` a cloud-resident store: `~/Library/CloudStorage` (Dropbox/iCloud) holds dataless
  placeholders (`stat().st_blocks == 0`), and reading one makes macOS download it — a scan then looks
  wedged at 0% CPU. Prune `CloudStorage`, `.Trash`, `Backups.backupdb` from `find` and skip dataless
  files. Same for `.git` and `node_modules`.
- Root-owned vendored stores are mode 644: plain `sudo cp` of the clean bundle works, target mode
  preserved. Never swap certifi over `/etc/ssl/cert.pem`: the two stores are largely disjoint families.
  Measured on the Studio — Apple 128 anchors, certifi 120, only ~67 in common; ~61 Apple-only anchors
  (Baltimore CyberTrust Root, DigiCert Global Root CA / High Assurance EV / Assured ID, GeoTrust, VeriSign,
  Entrust, QuoVadis, SwissSign, TrustCor, Staat der Nederlanden, Sonera, Camerfirma, certSIGN, T-Systems,
  XRamp, Trustwave, e-Tugra, … plus the flagged emSign G3) would vanish under a blind overwrite, while
  ~53 certifi-only newer roots (GlobalSign R46/E46, OISTE, BJCA, TrustAsia, vTrus …) would be added. Strip
  that file in place
  instead (`sudo python3 strip_g3.py /etc/ssl/cert.pem --apply --backup-dir <durable>`): 128 → 127
  anchors, only the flagged cert leaves. Apple's file interleaves a full OpenSSL text dump per cert, so
  2 `emSign ... G3` label lines survive the region removal — cosmetic, trips only grep-based detectors.
  Revert: `sudo cp /etc/ssl/cert.pem.pre-strip /etc/ssl/cert.pem`.
- certifi does NOT fix macOS itself: `SystemRootCertificates.keychain` anchors `emSign ECC Root CA - G3`
  (SHA256 `86a1ecba...`) plus `emSign Root CA - G1` on both Macs, so SecureTransport (curl, Safari,
  native TLS) stays exposed until Apple ships a trust update. The root keychain is on a sealed
  read-only volume — the anchor cannot be deleted. The lever is a **deny trust setting**:
  `security find-certificate -c "emSign ECC Root CA - G3" -p /System/Library/Keychains/SystemRootCertificates.keychain > export.pem`
  (verify its digest against the advisory), then `sudo security add-trusted-cert -d -r deny -p ssl export.pem`;
  Revert is `sudo security remove-trusted-cert -d <exported pem>`: macOS has **no `delete-trusted-cert`
  subcommand** (`security` answers "unknown command"), and `remove-trusted-cert` takes a cert FILE, not
  `-c NAME`. Without `-d` the write targets the user domain and fails in any non-GUI session:
  "authorization was denied since no user interaction was possible" — so this only runs from a real
  Terminal.app with sudo. Proof of effect is the record itself (`security dump-trust-settings -d` → SSL
  policy, `kSecTrustSettingsResultDeny`), never `security verify-cert`: on a self-signed root it returns
  CT noise or a false "certificate verification successful" whether or not the deny is in force.
- Enumerate anchors with `openssl crl2pkcs7 -nocrl -certfile <pem> | openssl pkcs7 -print_certs -noout`,
  never `security verify-cert`: on a self-signed root it returns CT noise ("Unable to find at least 2
  signed certificate timestamps") that says nothing about trust. A label-scanning helper reporting
  "(no emSign anchors)" means only "no certifi-style `# Issuer` labels" — absence must be proven by
  digest or by that openssl enumeration.
- Long-running daemons hold the store in memory: restart after bumping (gateway API :8642,
  llama-swap :9292, email-triage crons, litellm).
- Inventory drifts mid-work: brew auto-update swaps Cellar version dirs and Codex prunes its
  `~/.codex/runtimes/<tool>` trees, so a file that was dirty (or clean) earlier may simply be gone. At
  verification time re-check existence before reporting a path as dirty or fixed, and never reuse a
  prior pass's file list as the current one.
- `strip_g3.py` supports `--labels-only` (clear dangling header regions for certs an earlier pass
  removed — Mozilla `Name` + `======` pairs, certifi `# Issuer` runs) for bundles already free of the
  certificate. For a mode-444 file, `chmod 644` → run → `chmod 444`: note the tool captures the mode
  *at read time*, so it restores whatever mode was set beforehand — restore the original explicitly
  after, or the file stays writable.

### Hermes Desktop session-mutation fence

Archive/rename/delete of a session 409s with `client_upgrade_required` ("this app is out of sync
(different versions) with the Hermes backend") when the desktop client predates the fence. Fix: run
`hermes update` on the machine hosting the desktop app, with `--force` if it refuses as "already up
to date", to pull a fenced build — verified 2026-10-19, after which a desktop archive went through.
The desktop's own version label is a placeholder (0.0.0 stamp; the UI shows the connected gateway's
version). After the update the in-app updater may report "updates available" — that is the channel
now tracking main, not a defect.

## web_search dying on an unregistered "perplexity" provider (fixed 2026-10-26)

**SUPERSEDED 2026-11-03. Do not apply the fix below; it was reversed on or before 2026-11-02
(`config.yaml` mtime 2026-11-02 08:30; the CLI wrapper was created 2026-11-01 12:26).** Current,
verified state on the Studio: `web.backend: nous` + `web.search_backend: nous`, no `use_gateway` in
the `web:` block, and `web/perplexity` IS in `plugins.enabled`. Live resolution
(`hermes-agent/.venv/bin/python3`, importing `tools.web_tools`): `_get_search_backend() ->
perplexity`, `_get_extract_backend() -> firecrawl`, `is_managed_route() -> True`. Search is gateway
Perplexity (free to any Nous identity), extract is gateway Firecrawl **billed to Nous**, and the
personal key is never read. Both tools exercised live 2026-11-03.

`use_gateway: true` is NOT inert beside a name key: it is the legacy shim that reads as the `nous`
selection regardless of the name (see below). That is why the MacBook's `backend: firecrawl` +
`use_gateway: true` still resolves managed, and the managed route works there too: search and managed
Firecrawl extract were both exercised live on that host 2026-11-03 (subscriber identity
`pruster@protonmail.com`). The billing-semantics paragraph below still holds and is exactly why the
two config shapes are not equivalent.

**Identity-check pitfall (this cost me a wrong claim once, 2026-11-03).** The Nous Subscriber
identity lives in `auth.json` **`providers.nous`**; the reader is
`tools.managed_tool_gateway.read_nous_access_token()`. **`credential_pool.nous` is the INFERENCE
credential pool** and is empty on a host that holds no inference credentials of its own, so reading
the pool and concluding "no Nous identity" is the wrong instrument. Separately, one
`is_available()` / `resolve_free_search_gateway` call returning None did not reproduce (3/3 clean on
retest), so treat a single "no usable Nous identity" as a transient to re-test, not a structural
fact; the error text sends you to `/login` even when the identity was present all along.

Personal key status 2026-11-03: valid but exhausted (free plan, 0/1000 credits, resets
2026-11-09), so any direct call returns 402. Same key on both hosts. The CLI rides the gateway
instead (`~/.local/bin/firecrawl` -> `firecrawl-nous`); detail in the `firecrawl` skill's
`references/nous-gateway.md`.

Symptom: every `web_search` call fails with `web is configured to use 'perplexity' (set via hermes
tools), but no registered web search provider has that name`. Not model- or session-specific.

Cause: with `web.use_gateway: true` the managed Nous route is selected, and
`tools/web_tools.py::_get_search_backend()` returns the literal `"perplexity"` for that route
(`return "perplexity" if _managed_web_search() else _get_backend()` — the gateway serves free
Perplexity fast-search for Nous identities). The `web/perplexity` plugin is catalog-listed but NOT in
`tools.enabled` (only `web/ddgs`, `web/exa`, `web/firecrawl` are), so nothing registers under that
name. The selection is strict — it errors instead of falling back.

Fix: `hermes config set web.search_backend firecrawl` (Firecrawl has a key in `.env` and is enabled),
then `hermes config set web.backend firecrawl` to take extract off the managed route as well. The
writes normalize the section to `backend: firecrawl` + `search_backend: firecrawl` and drop the old
`use_gateway` / empty `extract_backend` keys. Verified live 2026-10-26 against
cambridgehistoricalsociety.org with both `web_search` and `web_extract`.

**Billing semantics, easy to get wrong:** the resolved *backend name* does not say who pays. A `nous`
selection and a `firecrawl` selection both resolve to the string `firecrawl`. The authority is
`plugins/web/firecrawl/provider.py::is_managed_route()`, whose contract is "`nous` → managed Tool
Gateway ONLY; any other stored backend → direct Firecrawl ONLY (never a silent managed fallback billed
to Nous)". So a *vendor name* pin means the user's own key; only the literal sentinel `nous` uses the
gateway. A partial pin SPLITS the two capabilities — with `search_backend: firecrawl` and
`backend: nous`, search billed the user's key while extract billed Nous. Check the split with
`is_managed_route()` per capability; never assume the section is uniform. Note also that
`_managed_search_fallback` fires only for a `perplexity` provider on the managed route, so a failed
direct-key search drops to the one-shot free keyless ring, never to paid Nous.

To probe the live resolution (the repo has no `venv/`, but `.venv/` does and has ruamel): 
`cd ~/.hermes/hermes-agent && ./.venv/bin/python3 -c "..."` importing
`tools.web_tools._get_search_backend` / `_get_extract_backend` and
`plugins.web.firecrawl.provider.is_managed_route`.

Before fixing, expect to find other sessions/crons that already hit this and silently fell back to
`web_extract` — the error text is recorded repeatedly in `state.db` session content.

## The "serve/dashboard restart pending" warning after `hermes update` (macOS)

`hermes update` snapshots the long-running Hermes processes, updates the code, then restarts what it
owns. Anything it decides it cannot restart gets a durable one-line reminder file at
`~/.hermes/serve_restart_pending/<pid>-<create_time-hex>.json`, and EVERY `hermes` CLI start then
prints `⚠ dashboard [default] pid N: manual restart still pending; this process may still serve
pre-update code` (`hermes_cli/update_serve_obligations.py::warn_pending_manual_serves`,
`defer_manual_serve`).

The reminder self-clears. `warn_pending_manual_serves` unlinks the file once
`_pid_alive_matches(pid, create_time)` is False, so bouncing or killing that exact incarnation ends
the warning. Deleting the JSON by hand only silences it while the stale code keeps serving — do not.

On this Studio the recurring offender is the dashboard. `~/Library/LaunchAgents/ai.hermes.dashboard.plist`
IS a real launchd job (`RunAtLoad`, `KeepAlive` on unsuccessful exit) listening loopback `:9119`, the
desktop app's remote surface. But its `ProgramArguments` wrap the command in
`/usr/bin/osascript -l JavaScript -e 'ObjC.import("stdlib"); $.system("exec ... hermes dashboard --no-open ...")'`.
That extra hop (launchd → osascript → `exec` → launcher → server) puts no unit identity on the actual
server process, and the unit-restart path is systemd-shaped (`is_unit_serve_row`,
`_systemd_restart_commands`) which never applies on macOS. So the scan classifies the server as
`supervisor: manual-serve`, `restart_via: respawn-argv` and files a reminder rather than restarting the
unit. Expect this after every update until the job is bounced:
`launchctl kickstart -k gui/$(id -u)/ai.hermes.dashboard` (modern syntax).

Evidence shape, 2026-10-26 04:06 ET receipt (`~/.hermes/logs/update_receipts/update_*.json`, newest by
name; note `latest.json` is a plugin-check, not the update): `plan.runtimes` =
`gateway pid 71172 supervisor=manual`, `dashboard pid 49094 supervisor=manual-serve restart_via=respawn-argv`,
`serve pid 96136 supervisor=desktop-ssh`. The dashboard incarnation had started 2026-10-23 14:42, so it
was serving three-day-old code.

## Running the hermes-agent test suite on a machine that hosts a live instance (Studio)

Two environment facts break a naive `scripts/run_tests.sh`, and both present as test failures
rather than setup problems. Neither is a regression in whatever you are testing.

### Always fake `HOME`

```bash
HOME=$(mktemp -d) HERMES_PYTHON=~/.hermes/pm/hermes-agent-dev/bin/python \
    scripts/run_tests.sh tests/tools/
```

With the real `HOME`, a live `~/.hermes` exists and several code paths resolve it instead of the
runner's isolated `HERMES_HOME` — a terminal-session init reading `~/.hermes/manifest.json`, and
update-recovery probing the git dir. `tests/home_io_guard.py` correctly refuses that I/O
(`TEST BUG: file I/O against the REAL hermes home: …`) and dozens of unrelated files fail.
Measured on the Studio 2026-11-01, same command and same tree: real `HOME` → 15 failing files
plus 2 error files; faked `HOME` → 4 failing files. Always compare a failing run against a faked
`HOME` before believing a regression.

### Build the env from CI's extra set, not `--all-extras`

```bash
cd ~/.hermes/hermes-agent
python -m pm.build_env --source . --out ~/.hermes/pm/hermes-agent-dev \
    --group dev --group test --extra all --extra anthropic --extra mistral \
    --extra fal --extra modal --extra daytona --extra parallel-web --extra keychain
```

That is `.github/workflows/tests.yml` verbatim. `--all-extras` is the wrong shape: the `all` extra
carries its own policy comment excluding opt-in backends (messaging, telegram, discord, slack, fal,
modal), so it drags in heavy extras CI does not use while still missing what the tests import.
Symptoms of a short env: `ModuleNotFoundError: No module named 'aiohttp'` across the messaging
files (aiohttp arrives via `all` → `hermes-agent[sms]`), and `test_fal_sdk.py` failing at
collection on `fal_client`. Measured: adding the extras took one 858-file run from
`10617 passed / 24 failed / 1 error` to `10672 passed / 7 failed / 0 errors`.

`pm.build_env` is a fresh build, not an in-place sync — remove the existing `--out` directory
first; do not expect it to upgrade in place.

### pytest is absent from the Studio's checkout by policy, and ruff/ty are not

`pyproject.toml` `[dependency-groups]` opens with "Build and test tooling never ships in runtime
payloads". `~/.hermes/hermes-agent/.venv` is the live gateway runtime (143 packages, runtime group
only) and must never be mutated with raw pip/uv (`pm/AGENTS.md:16`, `CONTRIBUTING.md:185`).

`ruff` and `ty` nevertheless work unchanged on the Studio because `scripts/code_health`
resolves them on demand through `uvx` (`~/.local/bin/uvx`), so `python scripts/check` runs fully
(14 checks). `pytest` cannot work that way — it needs the application's dependencies importable
alongside it — which is why a suite run needs the `--out` env above and `HERMES_PYTHON`.

### Verifying "red on base" correctly

`git checkout -- <file>` restores from the **index**, not from the base commit. Once your change
is committed the index holds *your* version, so the "base" run silently tests the patched code and
reports a false green. Pull the base file from a ref instead:

```bash
git show origin/main:tools/web_tools.py > tools/web_tools.py   # assert on a marker before running
git checkout HEAD -- tools/web_tools.py                        # restore your change
```

Assert the marker before trusting the run — e.g. `grep -c 'debug_call_data\["provider"\]'`
returning 0 for the base and 2 for the change. A red/green pair without that check proves nothing.

### Do not pipe the runner through `tail`

`scripts/run_tests.sh` prints its summary line (`=== Summary: N files, N passed, N failed …`) and the
per-file failure list **last**. Piping to `tail -N` discards exactly the part you need and makes a
failing run look like a truncated success. Redirect to a file and grep the file.

### Known-good baseline on the Studio (2026-11-01)

`tests/tools/` — 858 files: **10672 passed, 7 failed, 352 skipped**, 4 failing files:
`test_bot_desktop_resources` (1), `test_delegate` (1), `test_terminal_pipeline_status` (4),
`test_transcription_tools` (1). All 7 reproduce identically on `origin/main` and are macOS-specific
(a `/private/var/tmp` vs `/var/tmp` realpath mismatch, PTY line-continuation echo, terminal status
counts, one mock expectation). Treat that set as expected noise, not signal.

## Moved from MEMORY.md (consolidation 2026-11-02)

Detail pulled out of `MEMORY.md` when it hit 97% of its 20,000-char cap. Nothing here is new:
it is the long form of facts whose one-line version stayed in memory. The consolidated file went
19,491 -> 18,190 chars (39 entries, 16 rewritten, 23 untouched).

### Desktop session fence: upstream archaeology

- **PR 145598** = `gateway/owner_identity.py` commit `8497ce93`, merged 2026-10-28. It fixes the
  LOGIN-stamp variant but deliberately keeps `nous:` stamps FOREIGN on non-Desktop rows, so Cadu's
  `source='ios'` rows still answer `not_found`.
- Still open: **145474**, **143907** (the `nous:`-stamped rows); **143110** (the literal
  `Archive failed: not_found` toast on cold `source='webui'` rows, no linked PR). Candidate
  PR **142105** ("local adoption").
- Superseded measurements: on 2026-10-28 the Studio checkout was pinned at upstream `e04614af7bb`
  (Oct 23) + 2 carried patches, and pid 906 (dashboard/gateway) carried a manual-restart-pending
  warning. As of **2026-11-02** the checkout is `d466221168f` on branch `local` (+5 carried commits,
  merge-based) and the dashboard/gateway pids are 6816 / 43674.
- Reprint of a desktop request: its SSH backends are loopback dashboards with
  `__HERMES_AUTH_REQUIRED__=false` and a token in the page HTML (e.g. 127.0.0.1:51623).

### Supply-chain leftovers (2026-10-21)

- LM Studio's vendored runtimes ship a **legitimate** `sitecustomize.py` (sha256 prefix `6bacc291`)
  — not an implant.
- The Studio has no php/composer installed.
- The litellm 1.107.0 stealer itself: see the supply-chain section above.

### Memory store constants

- `memory.provider` valid sentinels: `""`, `default`, `builtin`, `built-in`, `none`. The literal
  string `memory` is **not** one of them. Source: `agent/memory_provider.py`
  `CORE_MEMORY_PROVIDER_SENTINELS`.
- Cap history: 12,000 chars earlier in 2026, **20,000 as of 2026-11-02**, read from the memory
  tool's own usage line rather than inferred.

### git-backup thresholds

- `BACKUP_MAX_FILES` default **50**, `BACKUP_MAX_DELETES` default **15**. See "In `~/.hermes`,
  never commit without naming the path" above for what the deferral leaves behind.

### MacBook share: mount history

- The keychain item is bound to the tailnet IP `100.68.81.83`; the password-less `ts.net` item was
  deleted (2026-10-13).
- The remount agent was renamed `dev.pdwerx.mount-macbook` -> `local.smb-mount.macbook`; 5-minute
  interval.

### tanker (Synology NAS): host build

- As of 2026-11-02: Intel Celeron J4025, 9GB RAM (~4GB available), `/volume1` 14T at 77%. About 10
  containers running (twenty-\*, immich_\*, mediarium, stash).

### Nous Portal: per-tool config detail

- **pi:** provider lives in `~/.pi/agent/models.json`; the apiKey is read with `!grep` command
  interpolation at request time; 5 portal coding models. `enabledModels` needs **explicit ids**
  because the glob `nous/*` fails (`*` does not cross slashes).
- **opencode:** provider block in `~/.config/opencode/opencode.jsonc` using npm
  `@ai-sdk/openai-compatible`; key in `~/.local/share/opencode/auth.json`, the same store
  `/connect -> Other` writes.

### REA duplication: versions

- Live plugin `~/.hermes/plugins/rea`, pinned `69ea758`, `rea-agents@6.4.0`, skill v37,
  Hermes-adapted.
- Manual copies at `~/.agents/skills/`: `reverse-engineer-anything` v39 + 2 more, kept on purpose
  for non-Hermes use (Codex etc.).

### Output destination: worked examples

- `fleet-catalog` -> iCloud `Hermes/infra/fleet-catalog`; `shit-posting` -> iCloud
  `Hermes/shit-posting`; pre-move drafts remain in the legacy `~/.hermes/outputs/substack-drafts/`.

### Linear project assignment: the case behind the rule

- A `~/.hermes` origin is not a reason to pick `Lab: Hermes`. LIN-460 (benchmark review surface)
  and LIN-461 (engine test) were both mis-filed that way and moved to `Lab: Inference` on
  2026-10-28.

### Profiles: orphan aliases

- Orphan aliases `personal` and `work` existed alongside the real profiles; remove with
  `hermes profile alias <n> --remove`. **Unverified as of 2026-11-02** — confirm before acting.

### HF model-drop watch: state

- State directory `~/.hermes/state/hf-model-watch/`; tuning flags in the script's `--help`.

### Ground-truth rule: the case

- The clef-flash vs Laya bakeoff (2026-10-03) returned the **opposite** verdict on observer-guessed
  labels versus Patrick's real decisions.

### Background_rewrite detail

- `auxiliary.background_review.enabled` was turned off 2026-10-27 after an unattended `skill_manage`
  write landed truncated. Its writes skip the `.curator_ledger.jsonl` audit trail, which is the
  reason the truncation was not caught by the ledger.

### Long-path MCP tool names

- Tool names over the provider's 64-char limit are shortened to a deterministic hash-suffixed name
  (`tools/mcp_tool.py` warns at registration). The cloudflare server alone produces thousands of
  these warnings, which is why log greps for `mcp__cloudflare__` match registration noise, not calls.
### Nous Portal: reading account state

- Read-only, no local action: `GET https://portal.nousresearch.com/api/oauth/account` and
  `GET /api/billing/subscription`, authenticated with the OAuth token from `~/.hermes/auth.json`
  (`credential_pool.nous[0]`). Used 2026-10-27 to confirm the "Super (legacy)" plan and the
  credit/window behaviour.

### iCloud output structure: image-gen

- `Hermes/image-gen/`: one `YYYY-MM-DD-<concept>/` per shoot, each holding `keepers/`, `prompts/`,
  `qc/`, a runlog and `NOTES.md`; `_ledger/` and `_legacy-keepers/` sit above the shoot directories.

### Procedure: measure your own numbers, never estimate them

- A size, saving, count or delta reported from arithmetic done in your head is a guess wearing a
  fact's clothes. Measured 2026-11-02: a memory consolidation was projected at "roughly 3,200 chars
  saved"; measured, it was **1,305**, and one row predicted to save 120 chars instead **grew by 59**.
  The second tranche fixed this by computing each delta from the file in the same run
  (`len(before) - len(after)`) and printing the result before writing.
- So: compute the delta from the artifact, print the measured number even when it is worse than the
  projection, and label anything unmeasured as an estimate with its basis named.

### MCP server invocation detail (trimmed from MEMORY.md 2026-11-02)

- Paths that were dropped from the memory entry as discoverable in one read of `config.yaml`:
  agentmail stdio binary `/opt/homebrew/bin/agentmail-mcp`; comfy-mcp with
  `COMFY_BIN=/Users/macstudio/ComfyUI/venv/bin/comfy`; twenty at `http://tanker:3000/mcp`.
- A text match for `mcp__<server>__` in a log is not a record of use: registration writes one warning
  line per over-long tool name, so the cloudflare server alone generates thousands of them. The
  authoritative record of use is `messages.tool_name` in `state.db`.### MEMORY.md register: telegraphic, with hard boundaries

Measured 2026-11-02. Rewriting the three prose-heaviest entries in a telegraphic register cut them
**2,447 -> 1,892 chars (23%)**: #8 Linear 1023 -> 785, #13 dev toolchain 684 -> 523, #27 output
destination 740 -> 584.

**May be compressed:** articles, copulas (`is`/`are`/`was`), "happens", "the fact that", connective
prose, hedging. `;` separates facts, `->` means becomes/maps to. Restating a fact twice is waste.

**May never be compressed:**

- **Polarity words**: `never`, `always`, `NOT`, `do-not`. "Never commit secrets" is the rule;
  "commit secrets" is the opposite. These are the cheapest chars and the most expensive mistakes.
- **Every path, id, UUID, port, date, count, flag, job id, version.** They are the reason the entry
  exists.
- **The one-clause reason that stops a repeat mistake.** A rule with its "why" survives; a bare rule
  gets re-broken by the next session that reads it as arbitrary.
- **The name of where the long form lives**, e.g. "detail: ops notes".

**Do not invent per-entry abbreviations or a symbol dictionary.** The file is injected into a context
that may not include the legend, so an abbreviation nobody defined is a guess generator. Symbols must
be self-evident (`;`, `->`, `NOT`, `?`) or not used.

**Verification that makes this safe:** before writing, assert a per-entry *must-survive token list*
present in the rewritten text (paths, ids, polarity phrases). The 2026-11-02 pilot asserted 14/11/12
tokens across the three entries: zero missing, all three measurably shorter.

**Gotcha:** if a rewrite script leaves a sentinel in the text and strips it afterwards, its mid-run
length prints disagree with the file. Measure the delta *from the file* after writing, never from the
run's own arithmetic.
### MEMORY.md has more than one writer
`memory.write_approval` is false on this install, so sessions write memory unattended — an
entry can change between two turns of the same conversation. 2026-11-03: entry #3 (BACKUPS) was
rewritten at 08:00:45 by a session other than the one mid-edit, correcting "MacBook Wed+Sun 13:00"
to "daily 13:00 (was Wed+Sun; daily since 2026-10-24)" — +99 chars, no .bak written. Verified true
against two independent sources: the MacBook's ai.hermes.git-backup plist (StartCalendarInterval
Hour 13 Minute 0, no Weekday key = daily) and backup-hermes-macbook's own commit "backup now daily
at 13:00 ET (was Wed+Sun)" dated 2026-10-24. Consequence: a direct file edit to MEMORY.md is a race.
Diff before patching, and treat an unexplained char delta as another writer, not your own arithmetic.
`launchctl print` runs=0 / "never exited" is a since-last-load counter, NOT evidence of failure.

## The estate inventory fails quietly: judge a run by row counts, not its failure count (2026-11-06)

`~/.hermes/docs/estate-inventory/stack-inventory.py` rebuilds the AUTO blocks from live probes. Its
Model Fleet block curls both llama-swap nodes, and a dead endpoint did **not** produce a counted
failure: the per-host `except` appended a bare `- ⚠ macbook: ...` bullet *without* the host's
`### macbook` heading, and `main()` counted only sections whose text *starts with*
`⚠ probe failed`. Net effect, observed for real on 2026-11-06 with the MacBook node accepting TCP
and then closing with zero bytes (curl exit 52/56): the mb-* table vanished, the warning was
invisible to the counter, and the run printed **`8 sections (0 failures)`**. A blank AUTO block is
a failed probe, never "no data".

Fixed the same day: a failed or empty host now emits `### name` + `⚠ probe failed: ...` (heading
kept, marker counted) and `main()` counts occurrences instead of a leading prefix. Verified against
the same dead node: `8 sections (1 failures)`, studio table intact. 53 unittest cases pass on Python
3.14 and 3.9 (the script is stdlib-only, so the 3.9 fallback is safe if a Hermes update prunes the
managed 3.14 toolchain).

Rules that came out of it:

- **Judge a run by its row counts, not its failure count.** `scripts/stack-inventory-refresh.sh`
  does exactly that (>=5 `ms-` rows, >=5 `mb-` rows, <=3 markers) and reverts on failure. Cron
  `4246fc00c25b`, 08:30 on the 1st, #alert-infra; its pre-flight requires both llama-swap nodes to
  answer, because a half-probed doc is worse than a stale one.
- **The generator writes to hardcoded `~/.hermes/docs/estate-inventory/*` paths, not relative to
  `__file__`.** Copying it elsewhere and running it rewrites the LIVE doc. Hit for real; the fix is
  `git -C ~/.hermes checkout -- docs/estate-inventory/`.
- **The generator is unguarded, the wrapper is the guard.** Run the wrapper by hand, not the raw
  script, unless you plan to revert afterwards.
