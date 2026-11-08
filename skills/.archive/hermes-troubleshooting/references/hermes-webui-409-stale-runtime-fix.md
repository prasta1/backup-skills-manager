---
name: hermes-webui-409-stale-runtime-fix
description: Fix Hermex WebUI 409 on /api/chat/start after gateway.
---

# Hermes WebUI 409 `agent_runtime_stale` — root cause & permanent fix

## Trigger
- Hermex (iOS app, client for `nesquena/hermes-webui`) or the webui chat pane
  drops after you restart the Hermes gateway or update the Hermes Agent.
- `POST /api/chat/start` returns **409** with type `agent_runtime_stale`,
  `retryable: true`. Starting a *new chat does NOT fix it* — only a full webui
  restart does.

## Root cause (the why)
The webui (`com.hermes.webui` → `~/hermes-webui/server.py`, port 8787) runs chat
on its **own in-process agent runtime**, separate from the Hermes gateway
process (`ai.hermes.gateway`, port 8642). On startup the webui captures the agent
checkout's git `HEAD` (`_AGENT_REVISION`). When the gateway restarts / the agent
is updated, on-disk `HEAD` changes while the running webui still holds the old
modules in memory. A deliberate guard (`ensure_agent_runtime_current` in
`api/agent_runtime.py`) refuses every `chat/start` with a 409 to avoid mixing
Python modules from two checkouts. The stale flag is process state, so no
client action clears it — the webui must reload.

Auth (`.sessions.json`, 30-day TTL) and session history survive; only the live
chat pane is blocked.

## The permanent fix: route webui chat through the gateway
Doing this means chat no longer touches the webui's in-process runtime, so the
staleness guard is bypassed by design. Three coordinated edits:

1. **config.yaml** — add a top-level key. Set it via the CLI, never a raw write
   (the agent's file guard blocks direct edits to `~/.hermes/config.yaml`):
   ```bash
   hermes config set webui_chat_backend gateway
   ```
   Note: `webui_chat_backend` is strict — only the exact value `gateway` is
   honored; anything else silently stays on `legacy`.

2. **`~/Library/LaunchAgents/hermes-webui-launch.sh`** — export the gateway-mode
   env vars (the launcher already sources the password from `.webui_password`):
   ```bash
   export HERMES_WEBUI_CHAT_BACKEND=gateway
   export HERMES_WEBUI_GATEWAY_BASE_URL=http://127.0.0.1:8642
   _GWKEY="$(grep -E '^API_SERVER_KEY=' "$HOME/.hermes/.env" | tail -1 | cut -d= -f2- | tr -d ' \r\n')"
   [ -n "$_GWKEY" ] && export HERMES_WEBUI_GATEWAY_API_KEY="$_GWKEY"
   ```
   The webui process env does NOT get the agent's `.env` by default — without
   this key it cannot authenticate to the gateway's API server (port 8642).

3. **Restart the webui** — this both applies the config AND clears current stale
   state:
   ```bash
   launchctl kickstart -k gui/$(id -u)/com.hermes.webui
   ```

## Verify
```bash
# key is valid against the gateway (200 = good, 401 = missing/wrong key)
KEY=$(grep -E '^API_SERVER_KEY=' ~/.hermes/.env | tail -1 | cut -d= -f2- | tr -d ' \r\n')
curl -s -o /dev/null -w '%{http_code}\n' -H "Authorization: Bearer $KEY" http://127.0.0.1:8642/v1/models
```
Then check the webui status (needs the webui password; use a login cookie):
```
GET /api/health/agent  →  gateway_chat: { enabled: true, backend: gateway,
                          base_url_configured: true, api_key_configured: true }
```

## Pitfalls
- **Status readout lies if you only set config.yaml.** The
  `/api/health/agent` `gateway_chat` block reads env vars only and IGNORES
  config.yaml. If webui still reports `legacy` after the config change, set the
  env vars in the launcher (step 2) and restart.
- **Trade-off:** in gateway mode the webui's chats depend on the gateway process
  being up. Covered by launchd `KeepAlive`, but a stopped gateway = no webui chat.
- The 409 message text is: *"Hermes Agent was updated while Hermes WebUI was
  running. Restart Hermes WebUI before retrying this action."* — that's the guard
  working as designed, not a config bug.

## Files
- `~/hermes-webui/api/agent_runtime.py` — `ensure_agent_runtime_current`,
  `AgentRuntimeChangedError`
- `~/hermes-webui/api/gateway_chat.py` — `webui_chat_backend_mode`,
  `webui_gateway_chat_enabled`, `gateway_chat_config_status`
- `~/hermes-webui/api/config.py` — `_get_config_path` (reads active profile home
  `config.yaml` = the same file Hermes Agent uses)
- `~/hermes-webui/api/routes.py` — `_handle_chat_start` (calls
  `_agent_runtime_barrier_response`), line ~22041
- `~/hermes-webui/docs/advanced-chat-setup.md` — the env-var method is documented
  upstream under "Gateway-backed browser chat"
