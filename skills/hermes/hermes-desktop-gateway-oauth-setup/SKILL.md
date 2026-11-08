---
name: hermes-desktop-gateway-oauth-setup
version: 1.0.0
description: Guide for setting up remote Hermes Desktop authentication with self-hosted gateway using OAuth via Nous Portal.
---

# Hermes Desktop Gateway OAuth Setup

> **Active again (2026-10-15)**: the dashboard is re-enabled and reachable over MagicDNS at `https://studio.taile85139.ts.net:9119` (tailnet-only via `tailscale serve --https 9119`). OAuth (Nous Portal) is the auth provider. See the "Re-enabling remote dashboard access" section below for the exact recipe.

## Overview
This skill guides the user through setting up remote Hermes Desktop authentication with a self-hosted gateway using OAuth via the Nous Portal. It handles Tailscale-based setups, redirect URI mismatches, and TLS issues specific to macOS environments.

## Prerequisites
- A self-hosted Hermes gateway (e.g., on Studio Mac) with `hermes dashboard register` configured
- The desktop is running on a client machine (e.g., MacBook Pro) that can reach the gateway over Tailscale
- OAuth is set up via Nous Portal for authentication

## Common Issues and Fixes

### Issue 1: Desktop Shows "Could Not Reach Gateway"
**Symptom**: Desktop app fails to connect with error "could not reach this gateway".
**Root Cause**: Likely due to HTTPS host mismatch or TLS handshake failure on the client side (MacBook).

**Fix**:
1. On the MacBook, ensure `connection.json` uses HTTP instead of HTTPS:
   ```bash
   python3 -c "
   import json
   from pathlib import Path
   p = Path.home() / 'Library/Application Support/Hermes/connection.json'
   data = json.loads(p.read_text())
   if isinstance(data.get('remote'), dict):
       data['remote']['url'] = 'http://studio.taile85139.ts.net:9119'
   p.write_text(json.dumps(data, indent=2) + '\n')
   "
   ```
2. Restart Hermes Desktop.

### Issue 2: OAuth Redirect URI Mismatch
**Symptom**: "redirect_uri_mismatch" error when logging in.
**Root Cause**: Dashboard was registered with a different redirect URI than what the desktop app attempts to use.

**Fix**:
1. On Studio, re-register dashboard with correct redirect URI matching client expectations:
   ```bash
   hermes dashboard register --name studio --redirect-uri "http://studio.taile85139.ts.net:9119/auth/callback"
   ```
2. Ensure dashboard plist binds to `0.0.0.0` (not just `127.0.0.1`).
3. Restart dashboard:
   ```bash
   launchctl bootout gui/$(id -u)/ai.hermes.dashboard || true
   launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/ai.hermes.dashboard.plist
   ```

### Issue 3: TLS Handshake Failures
**Symptom**: Desktop fails to authenticate with error like "tlsv1 alert protocol version".
**Root Cause**: Client-side TLS version incompatibility between Desktop and the gateway endpoint.

**Fix**:
1. Use HTTP instead of HTTPS if the redirect is not strictly required.
2. Force the dashboard to bind publicly (`0.0.0.0`) and ensure `PUBLIC_URL` matches what Desktop attempts to reach.

## Re-enabling remote dashboard access (2026-10-15 recipe)

To expose the Hermes dashboard over MagicDNS for phone access (tailnet-only, HTTPS, OAuth-gated):

1. **Serve the port tailnet-only**: `tailscale serve --bg --https 9119 http://127.0.0.1:9119` (verify with `tailscale serve status`).
2. **Set the public URL** so the Host-header check accepts the MagicDNS name AND the auth gate engages: `hermes dashboard register --redirect-uri "https://studio.taile85139.ts.net:9119/auth/callback"` — this idempotently updates the Portal OAuth client and writes `HERMES_DASHBOARD_PUBLIC_URL` to `.env`.
3. **Enable the nous auth provider** — it is often in `plugins.disabled` (was disabled 2026-08-26). `hermes plugins enable dashboard_auth/nous`. Without it the dashboard refuses to bind with "no auth providers are registered".
4. **Run the dashboard under launchd** so it survives reboots (a dashboard started from a desktop terminal dies with the session). Model the plist on `ai.hermes.gateway.plist` (osascript wrapper, `hermes dashboard --no-open`, KeepAlive SuccessfulExit=false, HERMES_HOME set).
5. **Restart**: `launchctl kickstart -k gui/$(id -u)/ai.hermes.dashboard`.

Verify: `curl -sI https://studio.taile85139.ts.net:9119/` → 302 to `/auth/login?provider=nous`; `/api/sessions` → 401 unauthenticated; `/auth/login?provider=nous` → 302 to `portal.nousresearch.com/oauth/authorize?...redirect_uri=https%3A%2F%2Fstudio.taile85139.ts.net%3A9119%2Fauth%2Fcallback`.

Pitfall: the desktop app runs its OWN headless backend (random port, e.g. 63814) — it does not depend on the 9119 dashboard, so restarting the dashboard is safe. The dashboard's children (tui_gateway.entry etc.) are its own in-process chat gateway.

## Troubleshooting Flow

1. Confirm Tailscale connectivity:
   ```bash
   tailscale ping studio
   ```

2. Verify gateway reachability via HTTP:
   ```bash
   curl -vk http://100.89.133.43:9119/api/status
   ```

3. On the desktop, inspect `connection.json`:
   ```bash
   cat ~/Library/Application\ Support/Hermes/connection.json
   ```

4. For OAuth to function properly, ensure the dashboard is registered with:
   - Public URL matching client expectations (`studio.taile85139.ts.net:9119`)
   - Correct redirect URI format (e.g., `http://studio.taile85139.ts.net:9119/auth/callback`)
   - Bound to `0.0.0.0` in launch agent

## Final Notes
- The desktop app only supports OAuth or static token auth for remote gateways.
- If the gateway is running with basic auth (`auth_required: true`), the desktop app must be able to authenticate via OAuth or token.
- Ensure DNS resolution for `studio.taile85139.ts.net` works from the desktop machine.