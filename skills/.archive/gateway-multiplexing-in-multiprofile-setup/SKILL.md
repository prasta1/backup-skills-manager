---
name: gateway-multiplexing-in-multiprofile-setup
description: Handle gateway multiplexing behavior in multi-profile Hermes setups to resolve OAuth token synchronization issues
version: 0.1.0
author: Wren
category: hermes
---

# Gateway Multiplexing in Multi-Profile Hermes Setups

## Problem Context
In multi-profile Hermes setups, gateways may run in either multiplex mode or separate processes, causing OAuth token synchronization issues when profiles have stale tokens but the shared store has fresh ones. This is a separate issue from session listing, but both affect multi-profile functionality.

## Root Cause Analysis
- When `multiplex_profiles: true` is configured, a single gateway process serves all profiles
- Separate launchd plists for individual profiles (e.g., `work`, `personal`) can cause token synchronization problems
- Gateway processes read profile-specific auth files, not the shared store
- The default gateway can multiplex profiles but separate processes don't get updated credentials

## Solution Process

### 1. Identify Gateway Mode
```bash
# Check current gateway status and multiplexing configuration
hermes gateway status
grep "multiplex_profiles" ~/.hermes/config.yaml
```

### 2. Stop Separate Profile Gateways (if they exist)
```bash
# For work profile
launchctl bootout gui/$(id -u) ~/Library/LaunchAgents/ai.hermes.gateway-work.plist 2>&1 || true

# For personal profile  
launchctl bootout gui/$(id -u) ~/Library/LaunchAgents/ai.hermes.gateway-personal.plist 2>&1 || true
```

### 3. Ensure Main Gateway Runs Multiplexed
```bash
# Verify main gateway config includes multiplexing
grep "multiplex_profiles" ~/.hermes/config.yaml

# Restart main gateway to ensure it's running multiplexed
launchctl bootout gui/$(id -u) ~/Library/LaunchAgents/ai.hermes.gateway.plist 2>&1 || true
sleep 2
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/ai.hermes.gateway.plist 2>&1
```

### 4. Verify Synchronized Tokens Across All Profiles
```bash
# Check all profiles have matching token expiration times
cat ~/.hermes/profiles/work/auth.json | jq '.providers.nous.expires_at'
cat ~/.hermes/profiles/personal/auth.json | jq '.providers.nous.expires_at'
cat ~/.hermes/shared/nous_auth.json | jq '.expires_at'
```

## Session Listing Issue (Separate but Related)
The session listing issue is a different problem that affects profile isolation. When the desktop app makes requests like:
```
GET /api/sessions?profile=personal&limit=20
```

The gateway API server ignores the `profile` parameter and returns sessions from the default profile, causing all profiles to show identical session lists.

## Key Details
- The session listing issue is a separate root cause from OAuth token sync issues
- Both are relevant to multi-profile Hermes setups but require different fixes
- Session listing fix needs to modify the API server in `gateway/platforms/api_server.py`  
- OAuth sync fix requires ensuring proper gateway multiplexing configuration and process management

## Authentication Issue (New Findings)

During investigation of multi-profile session merging issues, we identified a critical authentication mismatch:

### Root Cause
When the Hermes desktop app connects to a remote gateway (Mac Studio) in multi-profile mode, it sends `X-Hermes-Session-Token` headers for authentication. However, the gateway's `_check_auth` method in `api_server.py` (lines 1245-1254) only accepts `Authorization: Bearer ***` tokens, not the session token header.

This mismatch causes "Invalid API key" errors in logs and prevents proper session isolation between profiles.

### Fix Implementation
1. Set an API server key in the gateway environment:
```bash
echo "API_SERVER_KEY=your-secret-key-here" >> ~/.hermes/.env
```

2. Configure the desktop client to use token authentication when connecting to remote gateways

### Updated Fix Details
The actual fix was applied to `gateway/platforms/api_server.py` in the `_check_auth` method to accept both:
- `Authorization: Bearer ***` (standard token auth)  
- `X-Hermes-Session-Token` (desktop app local mode header)

This allows the gateway to properly authenticate desktop connections that send session tokens instead of just Bearer tokens.

## Troubleshooting
If gateway behavior persists:
1. Confirm `multiplex_profiles: true` is set in the main config
2. Ensure no separate launchd plists for individual profiles exist
3. Restart the main gateway to reload all credentials

## Verification Steps
After applying changes:
1. Verify single gateway process (PID 31794) is running multiplexed
2. Confirm no separate profile gateway processes exist
3. Verify all profiles have synchronized token expiration times from shared store
After applying changes:
1. Verify single gateway process (PID 31794) is running multiplexed
2. Confirm no separate profile gateway processes exist
3. Verify all profiles have synchronized token expiration times from shared store