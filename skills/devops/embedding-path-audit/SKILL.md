---
name: embedding-path-audit
description: Audit and verify the embedding inference path on macOS (llama-swap + llama-server).
version: 0.4.1
author: Hermes Agent + Patrick Ruster
license: MIT
tags: [lmstudio, memory, deployment, macos, launchagent, llama-swap, embeddings, watchdog]
---

# Embedding Inference Path (macOS)

> **NOTE:** LM Studio is no longer part of the embedding stack. The legacy
> `lmstudio-memory` LaunchAgent path (:8377) was decommissioned.

**Trigger:** Auditing, migrating, or troubleshooting the embedding/memory
inference path on macOS — especially after `llama-swap`, `llama-server`, Hermes
`config.yaml`, or watchdog scripts change endpoints, or after **any model-id
rename** (see below — this is the recurring failure mode).

## Current State (2026-09-12)

No `lmstudio-memory` LaunchAgents exist in `~/Library/LaunchAgents/`; port
`8377` is not listening.

**Active embedding path:**

| Component | Address | Model | Config source |
|---|---|---|---|
| `llama-server` (backend) | `127.0.0.1:5800` | `ms-bge-m3-1024` | `~/.hermes/llama-swap/config.yaml` |
| `llama-swap` (proxy) | `127.0.0.1:9292/v1` | `ms-bge-m3-1024` | `groups.embeddings.members` |
| Hermes providers | `http://127.0.0.1:9292/v1` | ids in `providers.llama-swap.models` | `config.yaml` |
| Hermes `embedding` provider | `https://studio.taile85139.ts.net:9292/v1` | (no pin) | `config.yaml → providers.embedding` |
| Hindsight memory (Docker) | `host.docker.internal:9292/v1` | embed `ms-bge-m3-1024`; LLM/retain `ms-gemma-4-26b-moe`; reflect/consolidation `ms-gpt-oss-20b` | `~/.hermes/hindsight/hs-run.sh` |
| Watchdog probe | local + tailnet `:9292/v1/embeddings` | `ms-bge-m3-1024` | `watchdog_llama_swap_sentinel.sh` (owns the whole :9292 surface) |

### The id prefix is `ms-` now — renames are the recurring breakage

- 2026-08-10: bare ids (`bge-m3`) → host-prefixed `studio-*`.
- 2026-09-10: `studio-*` → `ms-*` (llama-swap config rewrite).

**No aliases were kept in either rename.** A stale id returns
HTTP 404 `{"error":"no router for requested model","src":"llama-swap"}`.
Fix the caller — never re-add an alias.

**Authoritative id list is always the server, not this doc:**

```bash
curl -s http://127.0.0.1:9292/v1/models | jq -r '.data[].id'
```

## Verification

`scripts/audit_embedding_path.sh` runs the whole audit in one shot (ports, real
embedding call, watchdog, stale-id sweep across every consumer) and prints a
PASS/FAIL report. Use it first; the manual checks below are the fallback.

```bash
# 1. Is llama-server running with --embeddings on :5800?
#    (lazy-loaded by llama-swap: absent until the first embedding request)
lsof -iTCP:5800 -sTCP:LISTEN

# 2. Is llama-swap proxying on :9292?
lsof -iTCP:9292 -sTCP:LISTEN

# 3. Does the embedding endpoint return a vector? Use the CURRENT id.
curl -sf http://127.0.0.1:9292/v1/embeddings \
  -H 'Content-Type: application/json' \
  -d '{"model":"ms-bge-m3-1024","input":"ping"}' \
  | jq '.data[0].embedding | length'      # expect 1024

# 4. Is the embedding probe healthy? The sentinel always exits 0, so SILENCE
#    is the healthy signal here, not the exit code.
~/.hermes/scripts/watchdog_llama_swap_sentinel.sh            # no output = green
cat ~/.hermes/state/sentinel_embed_local_fails 2>/dev/null   # present = long-standing drift
cat ~/.hermes/state/sentinel_embed_tailnet_fails 2>/dev/null

# 5. Does Hermes config match?
grep -A20 'llama-swap:' ~/.hermes/config.yaml | head -25

# 6. No legacy lmstudio-memory LaunchAgents lingering?
ls ~/Library/LaunchAgents/ | grep -i lmstudio   # should return nothing
```

## Rename blast radius — check every one of these

A rename breaks every caller that pins an id, and they fail in *different*
ways, so a single green check proves nothing about the others:

| Consumer | Where | Symptom when stale |
|---|---|---|
| Watchdog probe | `scripts/watchdog_llama_swap_sentinel.sh` `EMBEDDING_MODEL` default | Discord alert every 5m; the `state/sentinel_embed_*_fails` counters climb |
| Cron job model pins | `cron/jobs.json` `model`/`provider` | job FAILS at agent construction with a **context-window** ValueError, not a 404 (unknown id falls back to the provider-level `context_length: 16384`, below Hermes' 64K minimum) |
| Hindsight memory | `hindsight/hs-run.sh` env + the **running container** | every retain/recall 404s: `Failed to generate batch embeddings`, `Fact extraction failed` |
| Hermes config | `config.yaml → providers.llama-swap.models`, `aux_models.*` | model resolves with wrong/absent context length |
| Any hand-started client | notebooks, `curl` scripts | 404 on the pinned id |

Sweep command:

```bash
grep -rn "studio-[a-z0-9]" --include="*.sh" --include="*.env" --include="*.yaml" \
  --include="*.yml" --include="*.json" --include="*.py" \
  ~/.hermes/scripts ~/.hermes/hindsight \
  ~/.hermes/config.yaml ~/Library/LaunchAgents | grep -v '\.bak'
```

Fix the cron pins through the CLI (it writes the job store correctly):

```bash
hermes cron edit <job_id> --model ms-<model> --provider llama-swap
```

**Pitfall — do not false-positive on `jobs.json` greps.** A raw `grep studio-`
over `cron/jobs.json` matches historical `last_error` text from failed runs
even after `hermes cron edit` fixed the live pin. Check the live fields only:
`grep -o '"model": "[^"]*"' cron/jobs.json | sort | uniq -c`.

## Probe drift troubleshooting

### Watchdog alerting after a migration

Likely cause: probe drift, not model failure. Audit, in order:
- `scripts/watchdog_llama_swap_sentinel.sh` → `EMBEDDING_MODEL` default (and any
  env override where the job runs)
- cron jobs pinning a model id
- Hermes `config.yaml` `providers.llama-swap.api` and `.models`

A `state/sentinel_embed_local_fails` or `sentinel_embed_tailnet_fails` counter
that has climbed is the smoking gun for long-standing drift (a real outage would
be transient). Delete the file, or let the first healthy run clear it — the
script's `strike_reset` does that automatically.

Env overrides beat the script default, so a probe can look healthy in cron and
fail when you run the script by hand (and vice versa). Check both.

### Embedding call returns `upstream command exited prematurely`

Origin pattern: `llama-swap` returned 500 while `llama-server` on 5800 was
healthy. Common causes:
- `llama-swap` model key does not match a model in `config.yaml`
- Port `5800` occupied by a stray hand-started `llama-server` — llama-swap
  can't bind the embedding model (happened 2026-08-09)
- `--parallel` saturation under concurrency
- Request payload too large for the GGUF context path

Fix: `lsof -iTCP:5800` for squatting, verify keys, reduce `--parallel`/queue.

## Recreating consumers (their config is env-declared)

Editing the file is not enough for the Docker consumers — env vars bind at
container creation, so a recreate is required.

### Hindsight

```bash
cd ~/.hermes/hindsight && ./hs-run.sh Hindsight 8890 \
  hindsight-bakeoff-data ms-gemma-4-26b-moe \
  --restart unless-stopped -p 127.0.0.1:9999:9999
```

`hs-run.sh` does `docker rm -f` + `docker run` against the named volume, so data
is preserved. Before recreating, diff the live container's env against the image
to confirm the script carries every run-time var:

```bash
docker inspect <name> --format '{{range .Config.Env}}{{println .}}{{end}}' | sort > /tmp/cur
source <(printf '')  # then comm -23 /tmp/cur <image env> to list live-only vars
```

Verify: `docker logs --since 5m hindsight-bakeoff | grep -c 'no router'` → 0, and
`hindsight_recall` returning real memories.


## Is llama-swap up, what is loaded, and who is calling it (folded from the MBP local-inference-serving skill)

Do these in order; each answers a different question.

1. **Process.** `launchctl list | grep -i llama` (registered job and PID, or `-` if dead) and `pgrep -fl -i llama`. The swap proxy and the `llama-server` child it spawned both show; the child is the actual model process.
2. **Port.** `lsof -nP -iTCP:9292 -sTCP:LISTEN`. Child ports are assigned at load time from 5800 upward and are not stable identifiers; read them from `ps aux | grep llama-server`, never from memory.
3. **Dashboard.** `https://studio.taile85139.ts.net:9292/ui/`. The root 302s there; `/dashboard` and `/webui` are 404s.
4. **Why is it loaded.** In `~/.hermes/llama-swap/config.yaml`, `ttl: 0` means pinned resident by config, not "something is using it". Per-request context is `--ctx-size` divided by `--parallel`. Members of a `swap: true` group evict each other, so a model that serves one call and then reports `unloaded` was evicted, not broken.
5. **Who called it.** Tail `~/.hermes/logs/llama-swap.out.log`; each request logs the client IP, path, status and User-Agent. Confirm the User-Agent before blaming the current session.
6. **Did the restart take.** Compare the file mtime you edited (`stat -f "%Sm" <file>`) with the process start (`ps -p <PID> -o pid,lstart,args`). A PID older than the edit is still running the old code.

Probe reasoning models with a real `max_tokens`; an 8-token probe lands entirely in `reasoning_content` and reads as a dead endpoint.

## Restarting llama-swap on macOS

```bash
launchctl bootout gui/$(id -u) ~/Library/LaunchAgents/ai.llama-swap.plist && \
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/ai.llama-swap.plist
```

**Caveat:** the Hermes gateway process blocks `launchctl bootstrap` from inside
its own process tree (terminal, cron, gateway): `Blocked: launchctl
submit/bootstrap registers a persistent KeepAlive job and is unsafe from inside
the gateway process`. Run it from a separate Terminal.app window or SSH.

Workaround — start it manually:

```bash
/opt/homebrew/bin/llama-swap --config ~/.hermes/llama-swap/config.yaml --listen 127.0.0.1:9292 --watch-config &
```

`--watch-config` polls the config file every 2s, so config edits apply without a
restart (and a restart is needed only to clear state, not to load changes).

## Best Practices

1. **Canonical id source of truth:** `curl /v1/models` on llama-swap first, then
   `providers.llama-swap.models` in `config.yaml` — not memory of prior renames.
2. **Watchdogs use env-variable overrides:** `EMBEDDING_URL` and `EMBEDDING_MODEL`
   override the script defaults. Note the flip side: an override set somewhere in
   the cron environment makes a hand-run of the script disagree with cron.
3. **Port 5800 is single-tenant:** llama-swap allocates `${PORT}` sequentially
   from 5800. A stray `llama-server` squatting 5800 makes the embedding model
   fail to bind and exit in ~290ms. Check before blaming flags.
4. **Embeddings are reachable both locally and over Tailscale.** The watchdog
   requires BOTH to pass: `127.0.0.1:9292` and
   `https://studio.taile85139.ts.net:9292`. `providers.embedding` in
   `config.yaml` uses the tailnet URL. (Earlier versions of this doc claimed
   embeddings were local-only — that was wrong.)
5. **Cron timestamp offset:** `cron/executions.db` and job fields record
   `-05:00` (EST) while the host runs EDT (`-04:00`), so recorded run times read
   one hour behind `date`. Don't misread a post-fix run as pre-fix.
6. **Anything pinned to a swap model id must be re-checked after a rename** —
   the 2026-09 rename left the watchdog, three brief jobs, Hindsight, and
   and Hindsight pointing at dead ids at once, each failing differently. (OpenWebUI was a third such consumer until it was decommissioned 2026-09-23.)

## Related Skills

- `orbstack-sleep-guard` — distinguish guest sleep from service crashes during Docker-backed outages
- `apple-macos-tools` — macOS system management including LaunchAgents
- `mlops/inference/gguf-serving` — GGUF serving lifecycle notes
