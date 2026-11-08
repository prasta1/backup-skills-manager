# Tailscale Remote Backend Setup

## Desktop Gateway Connection
The Hermes desktop app uses `gateway.proxy_url` (not providers) for remote backend access. Configure:

```yaml
gateway:
  proxy_url: https://studio.taile85139.ts.net
  proxy_key: <API_SERVER_KEY>  # or set HERMES_DESKTOP_REMOTE_URL/_TOKEN env vars
```

Or in desktop Settings → Gateway:
1. Select "Remote" mode
2. URL: `https://studio.taile85139.ts.net`
3. Sign in (OAuth) or save token

**Note**: Tailscale serve proxies `https://<host>.ts.net` to the local gateway. The gateway must be running locally on the backend machine (port 8642). Start with `hermes gateway` or configure launchd.

## Session Expiry Handling
OAuth-based remote gateway sessions expire. The error "Your remote gateway session has expired. Sign in again" indicates the desktop client needs re-authentication via Settings → Gateway. For Tailscale setups:
1. Verify gateway is accessible: `curl -sk https://<host>.ts.net/health`
2. Re-authenticate in desktop app Settings → Gateway → Sign in

## Server Binding Configuration
The gateway binds to `127.0.0.1` by default. For Tailscale access:
- **Option A**: Use `tailscale serve --bg 8642` on the backend machine (HTTPS automatically)
- **Option B**: Set `API_SERVER_HOST: 0.0.0.0` in gateway config to bind externally

## Configuration Pattern
When running Hermes client on one machine (e.g., MacBook) and backend on another (e.g., Mac Studio):

```yaml
providers:
  lmstudio-studio:
    api_key: no-key-required
    base_url: http://studio.taile85139.ts.net:1234/v1
    default_model: google/gemma-4-26b-a4b-qat
    name: 'LMS: MacStudioUltra'
    request_timeout_seconds: 300
```

## Model ID Format
Server returns model IDs in OpenAI format (e.g., `google/gemma-4-26b-a4b-qat`). Do NOT add prefixes like:
- ❌ `gemma-4-26b-a4b-it-qat-mlx`
- ✅ `google/gemma-4-26b-a4b-qat`

## Verification
```bash
# From client machine, verify connectivity:
curl -s http://<host>.ts.net:1234/v1/models | jq -r '.data[].id'

# Test a model directly:
curl -s http://<host>.ts.net:1234/v1/chat/completions \
  -X POST -H "Content-Type: application/json" \
  -d '{"model": "<exact-model-id>", "messages": [{"role":"user","content":"test"}], "max_tokens":5}'
```

## Gateway Expose Commands
On the backend machine (Mac Studio):
```bash
# Expose gateway via Tailscale (HTTPS on port 443)
tailscale serve --bg 8642

# Verify exposure
tailscale serve status

# Test from client
curl -sk https://studio.taile85139.ts.net/v1/models
```