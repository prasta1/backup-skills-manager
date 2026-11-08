# LM Studio Remote Server Troubleshooting

## Connection Diagnostics

Test connectivity step-by-step:

```bash
# 1. Ping the Tailscale hostname
ping studio.taile85139.ts.net

# 2. Test TCP connectivity
nc -z -v studio.taile85139.ts.net 1234

# 3. Verify API responds
curl http://studio.taile85139.ts.net:1234/v1/models

# 4. Test a chat completion
curl -X POST http://studio.taile85139.ts.net:1234/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"google/gemma-4-26b-a4b-qat","messages":[{"role":"user","content":"hi"}],"max_tokens":10}'
```

## Common Fixes

| Symptom | Solution |
|---------|----------|
| Connection refused | Server offline or LM Studio not running |
| Empty model list | Wrong endpoint or port |
| Model not found (404) | Model ID mismatch - verify exact name |
| Timeout after 3 retries | Increase `request_timeout_seconds` to 300 |

## Model ID Discovery

Server returns available models at `/v1/models`. Config must use exact `id` field, not display name.

**Common ID corrections:**
- Config: `gemma-4-26b-a4b-it-qat-mlx` → Server: `google/gemma-4-26b-a4b-qat`
- Config: `gemma-3-27b-it` → Server: `google/gemma-3-27b-it-q4`

## Profile Configuration Gotchas

**Three locations per profile that must match:**

1. `model.base_url` and `model.default` - the main model config
2. `providers.lmstudio-studio.base_url` and `default_model` - provider defaults  
3. `auxiliary.vision.base_url` and `model` - vision endpoint (critical for image analysis)

**All profiles inherit defaults independently.** Changes to default profile DO NOT affect other profiles.

**Quick verification for all lmstudio profiles:**
```bash
# Check what profiles exist
ls ~/.hermes/profiles/

# For each profile using lmstudio-studio:
hermes config get profile /path/to/profile 2>/dev/null | grep -E "(base_url|default|provider)"
```