---
name: hermes-webui-operations
description: Operate and troubleshoot Hermes Web UI on macOS.
trigger: Deploy, reach, harden, or troubleshoot the Hermes Web UI on macOS.
version: 1.0.0
license: MIT
author: Hermes Curator
metadata:
  hermes:
    tags: [webui, troubleshooting, ops, launchd, tailscale]
---

# Hermes Web UI Operations

## Delivery model

- Treat the web UI as a tailnet-served app.
- Default listen address: 127.0.0.1.
- Reachability from other devices is provided by Tailscale serve, not by binding the Python server to a Tailscale IP.

## macOS Tailscale binding quirk

macOS Tailscale uses utun4, not tailscale0. Do not attempt to bind the HTTP server directly to a 100.x.x.x address. Verify with:

    ifconfig | grep 100.

Expect utun4 active with the Studio tailnet IP.

## Launchd service wiring

- plist label: com.hermes.webui
- launch script: ~/Library/LaunchAgents/hermes-webui-launch.sh
- env vars: HERMES_WEBUI_HOST, HERMES_WEBUI_PORT, HERMES_WEBUI_PASSWORD

## Class-level Debugging Patterns

### 409 agent_runtime_stale on /api/chat/start

**Problem:** Hermex (iOS app) or webui chat pane drops after gateway restart or agent update. POST /api/chat/start returns 409 agent_runtime_stale, retryable: true. Starting a new chat does NOT fix it - only a full webui restart does.

**Root cause:** The webui runs its own in-process agent runtime, separate from the gateway process. On startup it captures git HEAD. When the agent is updated, the running webui holds stale modules in memory. A guard refuses every chat/start to avoid mixing checkouts.

**Fix: route webui chat through the gateway.** Three coordinated edits:
1. hermes config set webui_chat_backend gateway
2. Export env vars in the launcher (HERMES_WEBUI_CHAT_BACKEND=gateway, HERMES_WEBUI_GATEWAY_BASE_URL=http://127.0.0.1:8642, HERMES_WEBUI_GATEWAY_API_KEY from .env)
3. Restart the webui process

**Verify:**
KEY from .env API_SERVER_KEY; curl -H "Authorization: Bearer $KEY" http://127.0.0.1:8642/v1/models
Then check GET /api/health/agent for gateway_chat: { enabled: true, backend: gateway, ... }

**Pitfalls:**
- Health endpoint reads env vars only, ignores config.yaml
- Gateway mode means webui depends on gateway being up
- 409 message is a guard working as designed, not a config bug

### Model picker not showing free-tier OpenRouter models

**Problem:** WebUI model picker missing free-tier OpenRouter models.

**Root cause:** Two-stage model list building. Stage 2 (free-tier fetch to openrouter.ai/api/v1/models) fails silently and falls back to _FALLBACK_MODELS (5 models only).

**Diagnosis:**
grep -i "openrouter.*free.*tier|free-tier.*live.*fetch" ~/.hermes/webui.log
curl -s --max-time 8 https://openrouter.ai/api/v1/models | head -c 200
hermes config get providers.openrouter

**Fix:** Ensure host network connectivity to openrouter.ai. Configure proxy or request firewall access if blocked.

### Duplicate "default" profiles in WebUI

When the profile selector shows two entries named default:
1. Check on-disk layout for both ~/.hermes config and ~/.hermes/profiles/default present.
2. Inspect backend row builders in ~/projects/hermes-webui/api/profiles.py: _build_profile_rows_fast, list_profiles_api, _row.
3. Look for logic that adds base home as synthetic default AND enumerates profiles/default as distinct row.
4. Fix at API layer by de-duping on resolved home path or normalized identity.
5. Do not rename or delete directories until backend cause is confirmed.

### Dashboard/Web UI partial-outage diagnosis

**Problem:** A URL/port is unreachable, but the service still shows as running.

**Pattern:** A dead service and a live backend may share a port. Diagnose first, then take corrective action.

### Web UI 400 auth callback vs. live dashboard

**Problem:** User reports 400, but web UI on 8787 returns 302 to /login and appears healthy.

**Distinctions:**
- 127.0.0.1:8787 - running web UI, auth via hermes_session cookie
- 127.0.0.1:9119 - legacy dashboard backend, PKCE flow, /auth/callback 400 on missing hermes_session_pkce

## References

- references/WEBSERVER_BINDING.md - Tailscale binding quirks
- references/PROFILE_LIST_DEDUPE.md - duplicate profile fix
- references/openrouter-free-tier-debug.md - model picker debugging
- references/api-server-authentication-issue.md - gateway API server auth
