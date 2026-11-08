---
name: oauth-token-synchronization
description: Synchronize OAuth tokens across Hermes profiles when using shared authentication stores
version: 0.1.0
author: Wren
category: hermes
---

# OAuth Token Synchronization in Hermes

## Problem Context
When using shared OAuth credentials (e.g., Nous) across multiple Hermes profiles, token expiration can cause sporadic authentication failures. This occurs when:
1. The shared store (`~/.hermes/shared/nous_auth.json`) contains fresh tokens
2. Individual profile auth files (`~/.hermes/profiles/*/auth.json`) contain expired/stale tokens
3. The gateway processes read from individual profile files, not the shared store

## Root Cause Analysis
- Token expiration in `work` and `personal` profiles (e.g., 08:11 UTC vs fresh 11:13 UTC)
- `default` profile may have proper tokens but the others don't
- Gateways read profile-specific auth files, not shared store

## Solution Process

### 1. Identify Token Mismatch
```bash
# Check token expiration times in each profile
cat ~/.hermes/profiles/work/auth.json | jq '.providers.nous.expires_at'
cat ~/.hermes/profiles/personal/auth.json | jq '.providers.nous.expires_at'
cat ~/.hermes/shared/nous_auth.json | jq '.expires_at'
```

### 2. Synchronize Tokens from Shared Store
Directly copy tokens from shared store to individual profile files:

```bash
# Sync work profile from shared store
cat ~/.hermes/shared/nous_auth.json | \
  python3 -c "
import json, sys
shared = json.load(sys.stdin)
with open('~/.hermes/profiles/work/auth.json', 'r') as f:
    work = json.load(f)
work.setdefault('providers', {})['nous'] = {
    'access_token': shared['access_token'],
    'refresh_token': shared['refresh_token'],
    'token_type': shared.get('token_type', 'Bearer'),
    'scope': shared.get('scope'),
    'client_id': shared.get('client_id'),
    'portal_base_url': shared.get('portal_base_url'),
    'inference_base_url': shared.get('inference_base_url'),
    'expires_at': shared.get('expires_at'),
    'expires_in': shared.get('expires_in'),
}
with open('~/.hermes/profiles/work/auth.json', 'w') as f:
    json.dump(work, f, indent=2)
print('Work profile synced')
"

# Sync personal profile similarly
cat ~/.hermes/shared/nous_auth.json | \
  python3 -c "
import json, sys
shared = json.load(sys.stdin)
with open('~/.hermes/profiles/personal/auth.json', 'r') as f:
    personal = json.load(f)
personal.setdefault('providers', {})['nous'] = {
    'access_token': shared['access_token'],
    'refresh_token': shared['refresh_token'],
    'token_type': shared.get('token_type', 'Bearer'),
    'scope': shared.get('scope'),
    'client_id': shared.get('client_id'),
    'portal_base_url': shared.get('portal_base_url'),
    'inference_base_url': shared.get('inference_base_url'),
    'expires_at': shared.get('expires_at'),
    'expires_in': shared.get('expires_in'),
}
with open('~/.hermes/profiles/personal/auth.json', 'w') as f:
    json.dump(personal, f, indent=2)
print('Personal profile synced')
"
```

### 3. Restart Gateways to Apply Changes
```bash
# Restart all gateways to reload credentials
launchctl bootout gui/$(id -u) ~/Library/LaunchAgents/ai.hermes.gateway.plist
sleep 2
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/ai.hermes.gateway.plist
```

## User Preferences Alignment
- The user prefers "for once and for all" solutions over incremental fixes
- Direct commands to execute without meta-commentary about why steps are needed
- Minimal explanation unless specifically requested
- Concise, actionable output over process documentation
- Prefers direct, executable solutions over verbose explanations

## Gateway Multiplexing Insight
- In multi-profile setups, gateways may run in multiplex mode (serving all profiles) rather than separate processes
- When gateways are running separately for each profile, they need to be stopped and restarted to reload credentials
- The default gateway can multiplex profiles when `multiplex_profiles: true` is configured in the main config

## Verification Steps
After synchronization:
1. Verify all profiles have matching expiration times:
   ```bash
   cat ~/.hermes/profiles/work/auth.json | jq '.providers.nous.expires_at'
   cat ~/.hermes/profiles/personal/auth.json | jq '.providers.nous.expires_at'
   cat ~/.hermes/shared/nous_auth.json | jq '.expires_at'
   ```

2. Confirm gateways reload credentials by checking their logs or status

## Key Details
- This issue is specific to multi-profile setups using shared authentication stores
- The solution requires direct file manipulation rather than `hermes auth add` commands
- Gateway processes must be restarted to pick up the new credentials
- The shared store contains the most recent valid tokens and should be the source of truth
- In multi-profile setups, gateways may run in multiplex mode (per `multiplex_profiles: true`) rather than as separate processes
- When separate gateway processes exist for each profile, they need to be stopped and restarted to reload credentials

## Troubleshooting
If token synchronization fails:
1. Ensure `~/.hermes/shared/nous_auth.json` exists and has valid tokens
2. Verify that profile directories (`~/.hermes/profiles/work`, `~/.hermes/profiles/personal`) exist
3. Check file permissions on the auth.json files to ensure they're writable
4. For multi-profile setups, check if separate gateway processes are running that need to be stopped

## References
- `references/gateway-multiplexing.md`: Details on gateway multiplexing behavior in Hermes multi-profile setups
- `gateway-multiplexing-in-multiprofile-setup`: Complete skill covering gateway multiplexing in multi-profile setups for OAuth token synchronization

## Templates
- `templates/oauth-token-sync-recipe.md`: Complete step-by-step recipe for OAuth token synchronization in multi-profile setups

## User Preferences Alignment
The user explicitly stated they prefer:
- "For once and for all" solutions over incremental fixes
- Direct commands to execute without meta-commentary about why steps are needed  
- Minimal explanation unless specifically requested
- Concise, actionable output over process documentation
4. Confirm gateway multiplexing behavior - if separate launchd plists exist for each profile, they need to be stopped and restarted