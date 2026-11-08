---
name: hermes-multi-profile-gateway
description: "Multi-profile gateway: multiplexing, session, token, auth."
author: Hermes Curator
category: hermes
tags: [gateway, multi-profile, multiplexing, session-isolation, oauth, authentication]
---
# Hermes Multi-Profile Gateway Setup

## Overview
Class-level guide to configuring and troubleshooting multi-profile Hermes gateways. Covers gateway multiplexing, session isolation, OAuth token synchronization, and API server authentication.

## When to Use
- Profile switching shows "disconnected gateway"
- Sessions from one profile appear in another
- "Invalid API key" errors after profile switch
- OAuth tokens expire in some profiles but not others
- Gateway keeps restarting every ~30s

## Core Problems & Solutions

### 1. Gateway Multiplexing
**Problem:** Separate per-profile gateway processes run independently; tokens diverge.
**Fix:** Enable single-process multiplexing:
```bash
hermes config set gateway.multiplex_profiles true
hermes gateway restart
```
Verify: `hermes gateway list` → one PID serving all profiles.

**Stop separate per-profile gateways (if they exist):**
```bash
launchctl bootout gui/$(id -u) ~/Library/LaunchAgents/ai.hermes.gateway-work.plist 2>&1 || true
launchctl bootout gui/$(id -u) ~/Library/LaunchAgents/ai.hermes.gateway-personal.plist 2>&1 || true
```

**Verify synchronized tokens:**
```bash
cat ~/.hermes/profiles/work/auth.json | jq '.providers.nous.expires_at'
cat ~/.hermes/profiles/personal/auth.json | jq '.providers.nous.expires_at'
cat ~/.hermes/shared/nous_auth.json | jq '.expires_at'
```

### 2. API Server Profile Isolation
**Problem:** Desktop sends `GET /api/sessions?profile=personal` but API server returns default-profile sessions.
**Fix:** The `/api/profiles/sessions` endpoint must respect the `profile` query parameter and open the correct `state.db`.
**Key file:** `gateway/platforms/api_server.py` — `_handle_list_sessions()` must read `profile` from query and use `SessionDB(profile=profile)`.

### 3. OAuth Token Synchronization
**Problem:** Shared store has fresh tokens; individual profile `auth.json` files have expired tokens.
**Fix:** Sync from shared store to profile files:
```bash
cat ~/.hermes/shared/nous_auth.json | jq '.expires_at'
cat ~/.hermes/profiles/work/auth.json | jq '.providers.nous.expires_at'
cat ~/.hermes/profiles/personal/auth.json | jq '.providers.nous.expires_at'
```
Copy tokens from shared store into each profile's `auth.json` under `.providers.nous`.

### 4. API Server Authentication Mismatch
**Problem:** Desktop sends `X-Hermes-Session-Token` header but gateway's `_check_auth` only accepts `Authorization: Bearer`.
**Fix:** Patch `gateway/platforms/api_server.py` `_check_auth` to accept both headers. Set `API_SERVER_KEY` in `~/.hermes/.env`.

## Subsections
- [Gateway Multiplexing](#1-gateway-multiplexing)
- [API Server Session Profile Fix](#2-api-server-profile-isolation)
- [OAuth Token Synchronization](#3-oauth-token-synchronization)
- [Profile Gateway Behavior](#profile-gateway-lifecycle)
- [Plugin Crash Troubleshooting](#plugin-crash-troubleshooting)

### 1. Gateway Multiplexing
In multi-profile setups, gateways may run in either multiplex mode or separate processes, causing OAuth token synchronization issues. When `multiplex_profiles: true` is configured, a single gateway process serves all profiles.

**Identify mode:**
```bash
hermes gateway status
grep "multiplex_profiles" ~/.hermes/config.yaml
```

### 2. API Server Session Profile Fix
The `_handle_list_sessions()` method in `gateway/platforms/api_server.py` must read the `profile` query parameter and route session queries to the correct profile database.

**Changes made to `api_server.py`:**
1. Added route: `("GET", "/api/profiles/sessions", self._handle_profiles_sessions)`
2. Enhanced query parameter parsing: `limit`, `offset`, `min_messages`, `archived`, `order`, `profile`, `source`, `exclude_sources`, `full`
3. Added error handling for invalid parameters and missing profiles

**Verification:**
- Sessions properly isolated by profile
- Desktop app shows correct sessions per profile
- Default behavior unchanged (no profile parameter)

### 3. OAuth Token Synchronization
Token sync for multi-profile setups using shared authentication stores. Sync from shared store (`~/.hermes/shared/nous_auth.json`) to profile files (`~/.hermes/profiles/*/auth.json`).

**Restart gateways to apply:**
```bash
launchctl bootout gui/$(id -u) ~/Library/LaunchAgents/ai.hermes.gateway.plist
sleep 2
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/ai.hermes.gateway.plist
```

### Profile Gateway Lifecycle
Each Hermes profile runs its own independent gateway process for messaging platforms (Telegram, Discord) and cron jobs. The gateway is only started for the default profile by default.

**Install gateways for other profiles:**
```bash
hermes -p personal gateway install --start-now
hermes -p work gateway install --start-now
```

### Plugin Crash Troubleshooting
Gateway crashes from plugin sidecar failures (particularly Photon). Symptoms: continuous timeouts, re-authentication, gateway restart every ~30s.

**Diagnosis:**
```bash
hermes gateway list
ps aux | grep "gateway run"
ps aux | grep "photon/sidecar"
tail -50 ~/.hermes/logs/gateway.error.log | grep -i "photon|fatal|crash"
```

**Fix:**
1. Remove Photon credentials: `sed -i '' '/PHOTON_/d' ~/.hermes/.env`
2. Disable: `platforms.photon.enabled: false` + `plugins.disabled: platforms/photon`
3. Remove stale state: `gateway_state.json`, `channel_directory.json` in profile dirs
4. Clean restart via launchd

### References
- `references/multiplexing-behavior.md`
- `references/photon-sidecar-crash-log-excerpt.md`
- `references/api-server-authentication-issue.md`
- `references/session-listing-bug.md`
- `references/gateway-multiplexing.md`
- `references/oauth-token-sync-recipe.md`
- `references/authentication-root-cause-analysis.md`
- `templates/oauth-token-sync-recipe.md`
- `templates/gateway-multiplexing-config.yaml`
- `templates/fix-implementation.md`
- `references/fix-verification.md`
- `scripts/gateway-restart.sh`
- `scripts/verify-multiplexing.sh`