# Infrastructure Health Probes

Specific probe commands for common services during briefs. These are environment-aware — adapt endpoints and model names to the actual routing.

## Embedding Pipeline

**Probe the configured endpoint (the one the app actually uses, not the watchdog):**
```bash
curl -sf -m 8 -H 'Content-Type: application/json' \
  -d '{"model":"Qwen3-Embedding-4B-GGUF","input":"ping"}' \
  http://127.0.0.1:1234/v1/embeddings 2>&1 | head -c 400
```

**Expected response:** A JSON object with `data[0].embedding` containing a vector array.

**Check the watchdog probe script for stale config:**
```bash
cat ~/.hermes/scripts/watchdog_llama_swap_sentinel.sh
```

**Red flags:** Hardcoded `localhost:8082`, `bge-m3`, or any endpoint/model that no longer matches the actual routing. Look for `EMBEDDING_URL` and `EMBEDDING_MODEL` fallbacks in the script's `:-` defaults.

## LM Studio / llama.cpp

**Check model availability:**
```bash
curl -sf -m 6 http://100.89.133.43:1234/v1/models 2>&1 | head -c 200
```

**Note:** This endpoint is on the Studio's tailnet IP — may be unreachable from cron sessions running on the MBP or through the OpenRouter provider.

## Cron Job Health

**List all jobs with their last status:**
```bash
hermes cron list
```

Flag any job with `last_status: error` — especially delivery-enabled ones.

## Port Inventory

**Scan the stack at once:**
```bash
bash ~/.hermes/scripts/port-inventory.sh
```

The scan probes the llama-swap **proxy** (:9292) plus the gateway (:8642). The
webui (:8787) probe was removed 2026-09-27 when that service was retired, and
mnemosyne (:8765) was removed 2026-10-01 when Mnemosyne was retired outright —
no start mechanism remains, so a listener there is unknown, not an outage. It
does **not** watch upstream model ports.

**Why upstream ports are not watched:** llama-swap substitutes `${PORT}` at
model start and the config pins nothing, so upstream numbers are not stable
identities. A hardcoded upstream list goes stale silently and then reports
false outages (that is exactly what happened: 5803 labelled "gemma-4-26B alt"
was serving gemma-4-12B, and 5804 — marked critical — no longer existed).

**What to trust:**
- The critical section: proxy reachable with a non-empty model list, gateway, a
  live embeddings call, and the daily driver registered as `ms-gemma-4-26b-moe`.
- Drift: LM Studio on a random high port instead of 1234 is **drift**, note it
  and move on — it is not an outage.
- Known-inactive by design (never a failure): unsloth-studio :8888 (launchd job
  disabled) and syncthing :22000 (retired, app-launched only). Keep this list
  tight — retired every turn means retired from the list too: a service whose
  start mechanism is deleted can never come back, so watching it is pure noise.
  (54329 / `paperclip-db` was removed from the sweep entirely on 2026-10-07:
  Paperclip is fully retired, the `paperclipai` binary is gone, and nothing
  launches it. It was historically tombstoned as `honcho-postgres` until
  2026-10-01, then listed in `OWNED_UP` as Paperclip's embedded Postgres —
  both placements are now obsolete. Never re-add it.)
- Launchd jobs on our own labels with a nonzero last-exit status — a real flag.

**On-demand models** (`ttl: 900`) unload when idle. DOWN is their normal steady
state, not a failure, and a cold-load probe would stall the brief. Leave backend
liveness to the 5-minute Health watchdog.

## Common Failure Patterns

| Pattern | Likely Cause | Fix Direction |
|---------|-------------|---------------|
| Embedding watchdog errors but service is healthy | Watchdog script hardcodes old URL/model | Update the script's fallback defaults |
| Calendar returns nothing | No `google_token.json` | Run Google OAuth setup |

## Pitfalls

- **Do not** assume the watchdog script's target URL is correct — always verify it against the actual routing in `.env` and `config.yaml`
- **Do not** report a container as "down" when the watchdog script is the one that's wrong — the probe may be testing a dead endpoint while the service is healthy on a different port
- **Do not** flag `watchdog-embedding-probe` errors as a service outage without reading the script first