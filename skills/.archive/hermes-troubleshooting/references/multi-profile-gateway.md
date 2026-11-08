---
name: multi-profile-gateway
description: Complete guide for multi-profile gateway configuration, session isolation, and OAuth token sync.
version: 1.0.0
author: Hermes Curator
---

# Multi-Profile Gateway Configuration

## When to Use

- Desktop app shows disconnected gateway when switching profiles
- Invalid API key errors on port 8642 after profile switch
- Sessions from one profile appear in another profile
- OAuth tokens diverge across profiles
- Gateway restarts every ~30s due to plugin sidecar crashes

## Problem Families

### 1. Profile Gateway Isolation

**Root cause**: Only the default profile gets a launchd-managed gateway by default.

**Fix**:
```bash
hermes -p personal gateway install --start-now
hermes -p work gateway install --start-now
```

### 2. Session Profile Isolation

**Root cause**: Gateway API server ignores `profile` query parameter in `_handle_list_sessions()`.

**Fix**: Patch `api_server.py` to accept `profile` param, open the correct profile's `state.db`. Add route `GET /api/profiles/sessions`.

### 3. Auth Header Mismatch

**Root cause**: Desktop sends `X-Hermes-Session-Token` but `_check_auth` only accepts `Authorization: Bearer`.

**Fix**: Patch `_check_auth` to accept both. Set `API_SERVER_KEY` in `~/.hermes/.env`.

### 4. OAuth Token Synchronization

**Root cause**: Profile `auth.json` files get stale while shared store has fresh tokens.

**Fix quick**: `hermes --profile work auth add nous --type oauth`
**Fix permanent**: `hermes config set gateway.multiplex_profiles true && hermes gateway restart`

### 5. Photon Sidecar Crash

**Root cause**: Photon sidecar crashes cause gateway restarts every ~30s.

**Fix**: Remove Photon credentials, set `PHOTON_SIDECAR_AUTOSTART=false`, remove stale state files, restart gateway.

## Session Cleanup

`hermes sessions prune` only cleans SQLite. Must also manually remove web UI JSON files and request dumps.

## macOS Tailscale

macOS uses `utun4`, not `tailscale0`. Bind to `0.0.0.0`, not `100.x.x.x`.