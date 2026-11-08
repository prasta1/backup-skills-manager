# Infrastructure Health Probes

Specific probe commands for common services during morning briefs. These are environment-aware — adapt endpoints and model names to the actual routing.

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
cat ~/.hermes/scripts/watchdog_embedding.sh
```

**Red flags:** Hardcoded `localhost:8082`, `bge-m3`, or any endpoint/model that no longer matches the actual routing. Look for `EMBEDDING_URL` and `EMBEDDING_MODEL` fallbacks in the script's `:-` defaults.

## LM Studio / llama.cpp

**Check model availability:**
```bash
curl -sf -m 6 http://100.89.133.43:1234/v1/models 2>&1 | head -c 200
```

**Expected response:** A JSON array of available models.

**Note:** This endpoint is on the Studio's tailnet IP — may be unreachable from cron sessions running on the MBP or through the OpenRouter provider.

## Cron Job Health

**List all jobs with their last status:**
```bash
hermes cron list
```

Flag any job with `last_status: error` — especially delivery-enabled ones (Morning Brief, Midday Check, Open Source Update, Apple Card check, Weekly Cruft Check).

## Port Inventory

**Scan all watched ports at once:**
```bash
bash ~/.hermes/scripts/port-inventory.sh
```

**Watched ports and their significance:**
- `9292` (llama-swap proxy) — critical; the routing layer for all local inference
- `5800` (bge-m3 embeddings) — critical; embedding pipeline backend
- `5804` (gemma-4-26B daily driver) — critical; the always-loaded resident model
- `5803` (gemma-4-26B alt) — alternate instance, not critical
- `8642` (hermes CLI gateway) — critical; the gateway serve endpoint
- `8787` (hermes-webui) — critical; WebUI server
- `1234` (LM Studio UI) — critical; expected port. If DOWN but a high port (e.g. 41343) is listening, that's a **drift**, not a failure
- `5810` (Qwen3.6 35B A3B) — on-demand model; DOWN is normal when idle (TTL unload), but if it's been down for hours and was expected to be running, it's a routing gap

**Drift detection:** LM Studio frequently drifts from 1234 to a random high port. Always check `lsof -iTCP:1234 -sTCP:LISTEN -P -n` and compare with `lsof -iTCP -P -n | grep -i 'lm'` to catch this.

**Key insight:** Qwen on 5810 being down is the silent killer — model routing falls back to the daily driver without any visible error. This is exactly what the port inventory script catches.

## Common Failure Patterns

| Pattern | Likely Cause | Fix Direction |
|---------|-------------|---------------|
| Embedding watchdog errors but service is healthy | Watchdog script hardcodes old URL/model | Update the script's fallback defaults |
| Calendar returns nothing | No `google_token.json` | Run Google OAuth setup |

## Pitfalls

- **Do not** assume the watchdog script's target URL is correct — always verify it against the actual routing in `.env` and `config.yaml`
- **Do not** report a container as "down" when the watchdog script is the one that's wrong — the probe may be testing a dead endpoint while the service is healthy on a different port
- **Do not** flag `watchdog-embedding-probe` errors as a service outage without reading the script first — it's the most common stale-config source