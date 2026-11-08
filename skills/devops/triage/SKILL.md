---
name: triage
description: "Diagnose a reported infra issue on the Hermes stack."
version: 1.0.0
license: MIT
author: Ionga
tags: [devops, troubleshooting, hermes, gateway, llama-swap, cron, mcp, watchdog]
metadata:
  hermes:
    tags: [devops, troubleshooting, hermes, gateway, llama-swap, cron, mcp, watchdog]
---

# Infra Triage

Invoked as `/triage <what's wrong>` from Discord (or any gateway), or `/triage` alone.
Patrick reports a symptom in plain language; this runs the right checks and comes back with a
diagnosis. The argument is the report — if it is empty, ask what's failing and stop.

## Output contract

Patrick reads this on a phone. Lead with the verdict, not the search.

1. **Verdict** — one line. Real failure, false positive, or already-fixed-but-still-paging.
2. **Evidence** — only the command output that proves the verdict, trimmed to the load-bearing
   lines. Never paste a log dump.
3. **Cause** — labeled `known` / `likely` / `unverified`. Never state an inference as fact.
4. **Fix** — one action, phrased as a question. Never execute a write, restart, send, or delete
   without asking first.

Do not narrate the checks. If a check was uninformative, it does not appear.

## Step 1 — route the symptom

| Report | Subsystem | Start at |
|---|---|---|
| "paging", "alert won't stop", "flapping" | watchdog / outcomes | `~/.hermes/state/*_fails`, `watchdog_outcomes.sh` |
| "gateway down / restarting / not responding" | gateway | `launchctl`, `gateway.log`, `state/gateway.heartbeat` |
| "brief failed", "job didn't run", "no output" | cron | `hermes cron runs <id>`, `cron/executions.db` |
| "model won't load", "404 on a model" | llama-swap | `curl 127.0.0.1:9292/v1/models` |
| "tool missing", "X connector broken" | MCP | `hermes mcp test <name>`, `errors.log` |
| "can't reach the MacBook / mini" | host / tailnet | `last -5`, `launchctl print gui/501/...` |
| "embeddings / memory off" | embedding / mnemosyne | `:9292` embeddings, mnemosyne health |
| unclear | run the general battery | Step 2 |

## Step 2 — general battery

Run these together. They are cheap and cover most reports. Full by-subsystem command list:
`references/check-battery.md`.

```bash
launchctl list | grep -iE "hermes|llama"
cat ~/.hermes/state/gateway.heartbeat; cat ~/.hermes/state/gateway.lifecycle.json
curl -s 127.0.0.1:9292/v1/models   # id + status.value == loaded/unloaded
hermes cron list; hermes cron doctor; hermes cron incidents
grep -E "ERROR|CRITICAL" ~/.hermes/logs/errors.log | tail -20
```

## Step 3 — traps that make a real fault look fake, or vice versa

Full detail lives in the `hermes-infrastructure` skill. The ones that bite in triage:

- **A watchdog alert is a rolling window, not a live fault.** `watchdog_outcomes.sh` counts
  failures over an 8h window. After a fix the count keeps clearing the threshold for ~9h.
  Check whether the count is still *growing* before calling it live.
- **`(N recent failures)` tallies re-page forever.** An alert message carrying a volatile
  number changes its signature every cycle and defeats the auto-ack. Fix the message, not by acking.
- **`curl -sf` in a probe destroys the error body.** All distinct faults collapse into one
  useless string. This hid a renamed llama-swap model for ~39h. Use `-s` + `%{http_code}`.
- **A renamed llama-swap id fails as `404 no router for requested model` on a LIVE endpoint** —
  a liveness-only check reports healthy while the consumer silently gets nothing.
  `studio-*` → `ms-*` was one such rename. Grep consumers before trusting a probe.
- **MCP: `parked` lines keep printing after the fix.** A parked server re-runs the transport
  with the config captured at first registration, so a correct config edit never lands. Tell:
  `hermes mcp test <name>` (fresh process) connects while `errors.log` keeps logging
  `failed initial connection ... parking` every ~300s. Fix with `/reload-mcp`, not an edit.
- **Models under 64K context hard-fail agent turns.** `MINIMUM_CONTEXT_LENGTH = 64_000` is
  enforced in `agent/agent_init.py::_enforce_minimum_context` against
  `agent.context_compressor.context_length`. The only escape hatch is provider `lmstudio` + an
  explicit `model.context_length` — `llama-swap` gets no hatch. Watch for a *provider-level*
  `context_length` default silently winning when a per-model lookup misses; the stale 16,384 on
  `providers.llama-swap` produced exactly this.
- **"Online on tailnet" does not mean "the machine is serving".** Tailscale's extension is
  system-level and survives the login window; GUI LaunchAgents (and llama-swap) do not. A
  sustained `:8999` outage after a reboot is the FileVault/login-window trap, not a dead stack.
- **`--ctx-size N --parallel 2` halves the per-request window.** Read the real per-request
  number from `~/.hermes/llama-swap/config.yaml` before declaring a model's capacity.
- **A "timed out after 3600s" script job may already be fixed — check the fix's DATE against the
  failure date before diagnosing.** 3600s is the default `script_timeout_seconds`
  (`hermes_cli/config_defaults.py`), not a configured cap. The program's own per-command
  `/usr/bin/timeout` caps are what usually fire first. Two tells that the current code already
  fixed it: (a) the git/file mtime of the fix lands *after* `last_run_at`, and (b) the report log's
  stale block has **no `# end` marker** while later blocks do — the kill point is the last `##`
  heading before the truncation, and that names the culprit section directly. Also: several
  successful *manual* runs on the fix day do NOT prove a scheduled run works. `executions.db` is
  pruned to the last 1000 rows, so a failure older than that has no row — fall back to
  `last_error` in `jobs.json`. Per the skill's confirm-before-believing rule, the verdict stays
  "fixed but unproven" until the next real tick.

## Step 4 — cron and model failures specifically

The recurring class here is a job failing on a stale model id or an under-floor model.

```bash
hermes cron runs <job_id>          # durable attempts; shows source=builtin|direct
sqlite3 ~/.hermes/cron/executions.db \
  "select substr(started_at,1,19), job_id, status, substr(coalesce(error,''),1,70)
   from executions order by started_at desc limit 20;"
```

A job can fail on `source=builtin` (scheduler tick) and succeed on `source=direct` (manual) —
that split means a resolution/cache problem, not a capacity problem. Say so explicitly rather
than blaming the model.

To resolve a model's real window against live config, run Hermes's own resolver, not a guess:

```bash
cd ~/.hermes/hermes-agent && HERMES_HOME=~/.hermes ./venv/bin/python - <<'PY'
from agent.model_metadata import get_model_context_length, MINIMUM_CONTEXT_LENGTH
print(MINIMUM_CONTEXT_LENGTH)
print(get_model_context_length("ms-qwen3.6-35b-a3b", base_url="http://127.0.0.1:9292/v1",
      api_key="no-key-required", provider="llama-swap"))
PY
```

## Step 5 — confirm before believing a fix

Never report "fixed" from a config edit alone.

- **MCP** — a `registered N tool(s)` line for that server and zero new `401`/`403` after it.
- **Cron** — the next real run, not a manual one.
- **llama-swap** — live `/v1/models` showing the model `loaded` and a probe returning 200.
- **Watchdog** — the count stops growing; the alert clears only after the window drains.

## Boundaries

- Read-only by default. Restarts, sends, edits, and deletes wait for an explicit yes.
- `launchctl kickstart -k gui/$(id -u)/ai.hermes.gateway` kills every in-flight turn on that
  gateway — check for running sessions and ask first.
- Running a cron job manually **delivers to Discord**. Say so before doing it.
- If the fault is account-side (entitlement, expired token, provider quota), say that plainly
  and stop — nothing local fixes it.
