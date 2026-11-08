---
name: hermes-agent-troubleshooting
description: Troubleshoot Hermes gateway, Tailscale access, and remote connectivity issues
version: 0.1.0
author: Wren
platforms: [macos, linux]
---

# Hermes Troubleshooting

## Profile Gateway Status Behavior

### Problem
When users switch between Hermes profiles (e.g., `personal`, `work`), the desktop app or TUI may show "disconnected gateway" warnings even though the profiles are properly configured.

### Diagnosis
```bash
# Check all profile gateway statuses
hermes gateway list

# Check if a specific profile has a running gateway
### Real-World Context
For more details on this specific case, see `references/profile-gateway-behavior.md` which documents how the user's profiles were set up and why the behavior was actually correct, not a regression.

## User Preference Alignment
The user prefers to understand what they're seeing rather than have a "new behavior" explanation. They explicitly said they prefer "for once and for all" solutions over incremental fixes, which means they want to understand why something is working as designed rather than being treated as a bug.

## Key Details
- The `default` profile has a launchd service running its gateway — that's the PID 46272 you see
- The other profiles have no gateway because they were just set up and have no messaging platform tokens configured
- The gateway is a per-profile service that handles messaging platforms (Telegram, Discord, etc.) and cron jobs
- If you want gateways for other profiles, install them per-profile:
  ```bash
  hermes -p personal gateway install --start-now
  hermes -p work gateway install --start-now
  ```
- If those profiles don't have their own Telegram/Discord bots configured, there's nothing for the gateway to do
- Chatting across profiles in the desktop app or TUI works fine without it

### User Preference Alignment
The user explicitly said they prefer "for once and for all" solutions over incremental fixes, which means they want to understand why something is working as designed rather than being treated as a bug. They also prefer direct commands to execute without meta-commentary about why these steps are needed, and minimal explanation unless specifically requested.

## User Preference Alignment
The user prefers to understand what they're seeing rather than have a "new behavior" explanation. They explicitly said they prefer "for once and for all" solutions over incremental fixes, which means they want to understand why something is working as designed rather than being treated as a bug.

## Dashboard Basic Auth Login Issues

### Problem
The Hermes dashboard has basic authentication enabled but with an empty password, preventing login via desktop app. The desktop app authenticates against the plugin-based dashboard auth system, not the old plaintext basic-auth field.

### Diagnosis
```bash
# Check if dashboard basic auth is configured with empty password
grep -A 5 "basic_auth:" ~/.hermes/config.yaml

# Check if the dashboard is running with public bind
launchctl list | grep -i hermes

# Check dashboard logs for auth failures
grep -i "auth\\|password" ~/.hermes/logs/dashboard.error.log | tail -20
```

### Solution
The desktop app is hitting the public dashboard bind, which has basic-auth enabled with username `patrick` but no password set. The desktop app authenticates against the plugin-based dashboard auth system, not the old plaintext basic-auth field. The fix involves setting up a proper password provider:

```bash
# Run the interactive dashboard setup to configure password auth (this ensures proper scrypt hashing and session secret)
hermes dashboard register --username prasta --password admin

# Restart the dashboard service to reload providers
launchctl bootout gui/$(id -u) ~/Library/LaunchAgents/ai.hermes.dashboard.plist
sleep 3
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/ai.hermes.dashboard.plist
```

### Key Details
- The dashboard requires a registered password provider with proper scrypt hash and session secret, not just plaintext config fields
- The desktop app authenticates against the plugin-based dashboard auth system, not the old plaintext field
- After successful login, the desktop client should remember credentials automatically
- When upgrading Hermes and hitting auth issues, check that dashboard providers are properly registered via the `hermes dashboard register` command

## API Server Authentication Issue

### Problem Summary
When switching to `personal` or `work` profiles, chat fails because the API server on port 8642 rejects requests with "Invalid API key". The gateway multiplexer is correctly configured (`gateway.multiplex_profiles: true`), but the API server auth is missing.

### Root Cause Analysis
1. With `gateway.multiplex_profiles: true`, the default gateway (PID 30953) serves all profiles - there's one shared API server on port 8642
2. The API server requires authentication via `API_SERVER_KEY` (line 923 in `api_server.py`: `os.getenv("API_SERVER_KEY", "")`)
3. Neither the main `.env` nor the profile `.env` files have `API_SERVER_KEY` set
4. The desktop/TUI chat connects to this API server, not directly to the gateway

### Diagnosis Commands
```bash
# Check if API_SERVER_KEY is configured in main .env
grep "API_SERVER_KEY" ~/.hermes/.env

# Check if API_SERVER_KEY is configured in profile .env files
grep "API_SERVER_KEY" ~/.hermes/profiles/personal/.env 2>/dev/null || echo "No personal .env"
grep "API_SERVER_KEY" ~/.hermes/profiles/work/.env 2>/dev/null || echo "No work .env"

# Test API server authentication
curl -H "Authorization: Bearer invalid-key" http://localhost:8642/v1/models
```

### Fix Steps
1. Add an API key to authenticate the desktop app:
```bash
# Add to ~/.hermes/.env (the main profile's .env)
echo 'API_SERVER_KEY=your-secret-key-here' >> ~/.hermes/.env

# Then restart the gateway
launchctl bootout gui/$(id -u) ~/Library/LaunchAgents/ai.hermes.gateway.plist
sleep 3
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/ai.hermes.gateway.plist
```

2. Configure the desktop app to use the same key in its API configuration.

### Verification
After applying the fix, verify:
```bash
# Test that API server accepts valid key
curl -H "Authorization: Bearer your-secret-key-here" http://localhost:8642/v1/models

# Test that desktop app can connect
# (Check desktop app logs for successful authentication)
```

### Key Details
- The desktop app connects to the API server endpoint, not the direct gateway
- Authentication is required for all API server requests (even health checks)
- The same API key must be used in both the .env file and desktop app config

### Updated Context
Note that in addition to API key configuration, the gateway now properly supports cross-profile session isolation through `/api/profiles/sessions` endpoint. This resolves issues where the desktop app would show merged sessions from all profiles instead of isolated ones.

For detailed diagnostics of this specific case, see `references/api-server-authentication-issue.md` which documents the exact error conditions and fix steps applied.

## Session TTL Configuration Issues

### Problem
Hermes dashboard basic auth with `session_ttl_seconds: 0` causes frequent login prompts and session breakage during gateway restarts.

### Diagnosis
```bash
# Check for problematic session TTL setting in config
grep -A 10 "basic_auth:" ~/.hermes/config.yaml | grep session_ttl_seconds
```

### Solution
The `session_ttl_seconds: 0` setting in the dashboard basic_auth config causes access tokens to expire every 60 seconds (minimum enforced by code), which breaks during gateway restarts that occur every ~30 minutes. The fix is to either:

1. Remove the setting entirely (recommended) or
2. Set it explicitly to a longer value like 43200 (12 hours):

```bash
# Option 1: Remove the setting entirely (recommended)
hermes config set dashboard.basic_auth.session_ttl_seconds ""
```

### User Preference Alignment
The user prefers "for once and for all" solutions over incremental fixes, direct commands to execute without meta-commentary about why steps are needed, and minimal explanation unless specifically requested.
# Option 2: Set to 12h explicitly
hermes config set dashboard.basic_auth.session_ttl_seconds 43200

# Then restart the gateway to apply changes
launchctl bootout gui/$(id -u) ~/Library/LaunchAgents/ai.hermes.gateway.plist
sleep 3
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/ai.hermes.gateway.plist
```

### Real-World Fix Applied
In one case, the user encountered a login loop where dashboard authentication was failing every ~60 seconds due to `session_ttl_seconds: 0` in their config. The fix was:

1. Set the session TTL to empty (unset) to use default 12-hour session duration:
   ```bash
   hermes config set dashboard.basic_auth.session_ttl_seconds ""
   ```

2. Restart the gateway:
   ```bash
   launchctl bootout gui/$(id -u) ~/Library/LaunchAgents/ai.hermes.gateway.plist
   sleep 3
   launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/ai.hermes.gateway.plist
   ```

This resolved the login loop that occurred every ~30 minutes when gateway services were restarting.

### Key Details
- The dashboard's basic auth provider clamps `session_ttl_seconds: 0` to minimum 60 seconds
- This causes access tokens to expire too frequently, breaking session persistence during gateway restarts  
- Setting it to a longer value (12h default) or removing the setting entirely resolves the login loop
- The refresh token (30-day lifetime) will handle transparent authentication for 30 days after initial login

### User Preference Alignment
When troubleshooting networking issues, the user prefers:
- Direct commands to execute (no meta-commentary about why these steps are needed)
- Minimal explanation unless specifically requested
- Actionable output over process documentation

The user explicitly said they prefer "for once and for all" solutions over incremental fixes, which means they want to understand why something is working as designed rather than being treated as a bug. They also prefer direct commands to execute without meta-commentary about why these steps are needed, and minimal explanation unless specifically requested.

1. Remove the setting entirely (recommended) or
2. Set it explicitly to a longer value like 43200 (12 hours):

```bash
# Option 1: Remove the setting entirely (recommended)
hermes config set dashboard.basic_auth.session_ttl_seconds ""

# Option 2: Set to 12h explicitly
hermes config set dashboard.basic_auth.session_ttl_seconds 43200

# Then restart the gateway to apply changes
launchctl bootout gui/$(id -u) ~/Library/LaunchAgents/ai.hermes.gateway.plist
sleep 3
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/ai.hermes.gateway.plist
```

### Real-World Fix Applied
In one case, the user encountered a login loop where dashboard authentication was failing every ~60 seconds due to `session_ttl_seconds: 0` in their config. The fix was:

1. Set the session TTL to empty (unset) to use default 12-hour session duration:
   ```bash
   hermes config set dashboard.basic_auth.session_ttl_seconds ""
   ```

2. Restart the gateway:
   ```bash
   launchctl bootout gui/$(id -u) ~/Library/LaunchAgents/ai.hermes.gateway.plist
   sleep 3
   launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/ai.hermes.gateway.plist
   ```

This resolved the login loop that occurred every ~30 minutes when gateway services were restarting.

### Key Details
- The dashboard's basic auth provider clamps `session_ttl_seconds: 0` to minimum 60 seconds
- This causes access tokens to expire too frequently, breaking session persistence during gateway restarts  
- Setting it to a longer value (12h default) or removing the setting entirely resolves the login loop
- The refresh token (30-day lifetime) will handle transparent authentication for 30 days after initial loginid -u) ~/Library/LaunchAgents/ai.hermes.gateway.plist
```

### Real-World Fix Applied
In one case, the user encountered a login loop where dashboard authentication was failing every ~60 seconds due to `session_ttl_seconds: 0` in their config. The fix was:

1. Set the session TTL to empty (unset) to use default 12-hour session duration:
   ```bash
   hermes config set dashboard.basic_auth.session_ttl_seconds ""
   ```

2. Restart the gateway:
   ```bash
   launchctl bootout gui/$(id -u) ~/Library/LaunchAgents/ai.hermes.gateway.plist
   sleep 3
   launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/ai.hermes.gateway.plist
   ```

This resolved the login loop that occurred every ~30 minutes when gateway services were restarting.

### Key Details
- The dashboard's basic auth provider clamps `session_ttl_seconds: 0` to minimum 60 seconds
- This causes access tokens to expire too frequently, breaking session persistence during gateway restarts  
- Setting it to a longer value (12h default) or removing the setting entirely resolves the login loop
- The refresh token (30-day lifetime) will handle transparent authentication for 30 days after initial login

## Web UI 400 Auth Callback vs. Live Dashboard

### Problem
A user reports “Hermes is hitting a 400,” but the web UI on `127.0.0.1:8787` actually returns `302 -> /login` and appears healthy. The 400 is coming from a different auth surface: the dashboard OAuth callback at `/auth/callback`, not the running web UI.

### Diagnosis
```bash
# Probe the running web UI directly
curl -sS --max-time 5 http://127.0.0.1:8787/ -D - -o /dev/null | head -20

# Distinguish dashboard callback failures from web UI failures
grep -E 'missing_pkce_cookie|login_failure|login_success' ~/.hermes/logs/dashboard-auth.log | tail -20

# Identify which process owns which port
lsof -i :8787 -sTCP:LISTEN -n -P
lsof -i :9119 -sTCP:LISTEN -n -P
```

### Key Distinctions
- `127.0.0.1:8787` — running web UI / desktop Electron backend, auth via `hermes_session` cookie + password/OIDC
- `127.0.0.1:9119` — legacy dashboard backend, PKCE cookie flow, `/auth/callback` 400 on missing `hermes_session_pkce`
- Desktop Hermes app auth errors may originate from the dashboard callback path even when the web UI is fine

### Fix Pattern
- Do not treat a reported “400” as proof the web UI is down — verify the port/process first.
- If `8787` returns `302 -> /login`, the UI is healthy; the failure is elsewhere in the OAuth round trip.
- If `9119` logs `missing_pkce_cookie`, the failure is the dashboard callback, not the web UI.
- If both are broken, choose one root-cause path; do not restart both blindly.

### Reference
See `references/web-ui-400-auth-callback.md` for the exact log signatures and code paths involved.

## Dashboard/Web UI Partial-Outage Diagnosis

### Problem
`127.0.0.1:3334` is unreachable, but launchd still shows `com.hermes.webui` running. Restarting `ai.hermes.dashboard` blindly can leave the apparent outage unchanged.

### Diagnosis
```bash
# 1. Check whether anything is listening on the expected port
curl -sS --max-time 5 http://127.0.0.1:3334/ -o /dev/null -w '%{http_code}\n'

# 2. Inspect launchd states for dashboard + webui
launchctl print gui/$(id -u)/ai.hermes.dashboard 2>/dev/null | tail -40
launchctl print gui/$(id -u)/com.hermes.webui 2>/dev/null | tail -60

# 3. If needed, find the real backend listener
lsof -i :9119 -sTCP:LISTEN -n -P 2>/dev/null
ps -p <PID> -o pid,command,start_time
```

### Common Pattern
- `ai.hermes.dashboard` → `job state: exited`
- `com.hermes.webui` → `job state: running`
- legacy dashboard backend → still bound on `9119` and serving traffic

### Fix Pattern
- Do **not** restart `ai.hermes.dashboard` while another backend owns `9119`.
- If a live backend already exists above the dead service, delete or replace the dead service rather than stacking another restart.
- Verify the actual reachable UI path from the live process/port before declaring the web UI down.

### Key Details
- logs may show repeated bind errors on `9119` even while a dashboard process is still running as the owner
- web UI build logs showing `--skip-build` reuse of `...web_dist` are normal and not evidence of failure
- prefer one diagnosis pass and one corrective action over repeated bootout/bootstrap cycles

### Reference
See `references/web-ui-400-auth-callback.md` for the exact log signatures and code paths involved.

## Dashboard/Web UI Partial-Outage Diagnosis
When troubleshooting networking issues, the user prefers:
- Direct commands to execute (no meta-commentary about why these steps are needed)
- Minimal explanation unless specifically requested
- Actionable output over process documentation

The user explicitly said they prefer "for once and for all" solutions over incremental fixes, which means they want to understand why something is working as designed rather than being treated as a bug. They also prefer direct commands to execute without meta-commentary about why these steps are needed, and minimal explanation unless specifically requested.