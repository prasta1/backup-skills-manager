# Session TTL Configuration Issue

## Problem Summary
The Hermes dashboard basic auth configuration with `session_ttl_seconds: 0` causes frequent login prompts and session breakage during gateway restarts.

## Root Cause
The dashboard's basic auth provider clamps `session_ttl_seconds: 0` to a minimum of 60 seconds, causing access tokens to expire every minute instead of the intended 12-hour session duration. When the gateway restarts (every ~30 minutes), the refresh token session in flight gets dropped, forcing a redirect to `/login`.

## Reproduction
1. User config contains `session_ttl_seconds: 0` in dashboard.basic_auth section
2. Gateway restarts occur every ~30 minutes (SIGTERM)
3. Session cookies get evicted at 60-second intervals
4. Authentication fails during restart window

## Fix Approaches
1. Remove the setting entirely (defaults to 12h session TTL)
2. Set explicitly to 43200 (12 hours) 
3. Keep as default but ensure refresh token is properly configured

## Configuration Changes
```yaml
# Before (problematic):
dashboard:
  basic_auth:
    session_ttl_seconds: 0

# After (fixed):
dashboard:
  basic_auth:
    # session_ttl_seconds: 43200   # 12h default - omitted to use default
```

## Verification Steps
1. Check config: `grep session_ttl ~/.hermes/config.yaml`
2. Apply fix: `hermes config set dashboard.basic_auth.session_ttl_seconds ""`
3. Restart gateway: 
   ```bash
   launchctl bootout gui/$(id -u)/ai.hermes.gateway.plist
   sleep 3
   launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/ai.hermes.gateway.plist
   ```

## Impact
After fix, sessions will persist for 12 hours with transparent refresh using the 30-day refresh token. Gateway restarts no longer break authentication sessions.