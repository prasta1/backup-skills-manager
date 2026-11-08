# Infrastructure Health Probes

Specific probe commands for common services during briefs.

## Embedding Pipeline

```bash
curl -sf -m 8 -H 'Content-Type: application/json' \
  -d '{"model":"Qwen3-Embedding-4B-GGUF","input":"ping"}' \
  http://127.0.0.1:1234/v1/embeddings 2>&1 | head -c 400
```

## LM Studio

```bash
curl -sf -m 6 http://100.89.133.43:1234/v1/models 2>&1 | head -c 200
```

## Cron Job Health

```bash
hermes cron list
```

## Port Inventory

```bash
bash ~/.hermes/scripts/port-inventory.sh
```

## Watched Ports

- `9292` (llama-swap proxy) — critical
- `5800` (bge-m3 embeddings) — critical
- `5804` (gemma-4-26B daily driver) — critical
- `8642` (hermes CLI gateway) — critical
- `8787` (hermes-webui) — **retired 2026-09-27**, launchd job disabled, no longer probed
- `1234` (LM Studio UI) — critical

## Common Failure Patterns

| Pattern | Likely Cause | Fix Direction |
|---------|-------------|---------------|
| Watchdog errors but service healthy | Stale probe script URL/model | Update script defaults |
| Calendar returns nothing | No `google_token.json` | Run Google OAuth setup |