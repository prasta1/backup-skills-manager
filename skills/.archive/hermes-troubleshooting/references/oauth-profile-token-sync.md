---
name: oauth-profile-token-sync
version: 1.0.0
description: Handling OAuth token synchronization issues between Hermes profiles
---

# OAuth Profile Token Sync

## Problem Summary

When users have multiple Hermes profiles (e.g., `work` and `default`) configured with the same OAuth provider (like Nous), they may encounter intermittent "need OAuth" messages. This happens because each profile's auth.json can get out of sync with the shared store or main profile.

## Root Cause

The system's `_merge_shared_nous_oauth_state()` function attempts to sync tokens from the shared store, but this only works when the runtime detects expired tokens in the profile. If a profile has stale tokens (e.g., work profile with an already-expired token from 3 hours ago), it won't auto-sync even when the shared store has fresh tokens.

## Solution

### Quick Fix - Sync Individual Profile
```bash
hermes --profile work auth add nous --type oauth
```

This reads fresh tokens from the shared store and updates the work profile's auth.json.

### Long-term Fix - Enable Multiplexing
```bash
# Enable multiplexing for seamless cross-profile operation  
hermes config set gateway.multiplex_profiles true
hermes gateway restart
```

This allows one gateway to serve all profiles with shared credentials, eliminating profile-specific token issues.

## When This Happens

1. User creates multiple profiles (e.g., `work`, `personal`)
2. All profiles use the same OAuth provider (e.g., Nous)
3. Tokens are refreshed in one profile but not others
4. The gateway shows "need OAuth" when tokens expire in specific profiles

## User Preference Alignment

The user explicitly stated they prefer "for once and for all" solutions over incremental fixes. This approach provides a complete fix that addresses the root cause rather than just patching symptoms.

## Verification Steps

1. Check token expiration in each profile:
   ```bash
   hermes --profile work auth list
   hermes --profile default auth list
   ```

2. Compare expiration times - if one is much older than others, that's the problem profile.

3. Apply fix and verify:
   ```bash
   hermes --profile work auth add nous --type oauth
   ```

## Best Practices

- Use `gateway.multiplex_profiles` setting for seamless multi-profile operation
- Regularly verify that all profiles have synchronized OAuth tokens
- Enable multiplexing to avoid profile-specific authentication issues entirely