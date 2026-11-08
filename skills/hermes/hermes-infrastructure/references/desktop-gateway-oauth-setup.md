# Hermes Desktop Gateway OAuth Setup

**Consolidated from:** `Hermes Desktop Gateway OAuth Setup` (bundled skill)

> **Not currently active** (as of 2026-09-12): the `studio.taile85139.ts.net:9119` remote is decommissioned — nothing listens on :9119 and Hermes Desktop is configured local-only (`connections.json` has a single `local` connection). This doc is kept as the how-to for re-enabling remote access.

## Overview

Setting up remote Hermes Desktop authentication with a self-hosted gateway using OAuth via Nous Portal. Handles Tailscale-based setups, redirect URI mismatches, and TLS issues specific to macOS environments.

## Prerequisites

- Self-hosted Hermes gateway with `hermes dashboard register` configured
- Desktop on client machine reachable via Tailscale
- OAuth via Nous Portal for authentication

## When to Use

- "Desktop can't reach gateway"
- "redirect_uri_mismatch" during login
- TLS handshake errors on macOS

## Common Issues and Fixes

### Gateway Connection Failures

**Symptom**: "could not reach this gateway" in Desktop.
**Root Cause**: HTTPS/TLS mismatch between client and gateway.
**Fix**: Force Desktop to use HTTP instead of HTTPS for connection — edit `connection.json` to use `http://` instead of `https://`.

### OAuth Redirect URI Mismatch

**Symptom**: "redirect_uri_mismatch" error during login.
**Root Cause**: Dashboard registered with different redirect URL than Desktop expects.
**Fix**: Re-register dashboard with matching redirect URI format:
```bash
hermes dashboard register --name studio --redirect-uri "http://studio.taile85139.ts.net:9119/auth/callback"
```

### TLS Handshake Errors

**Symptom**: "tlsv1 alert protocol version" in logs.
**Root Cause**: Client-side TLS version incompatibility.
**Fix**: Use HTTP instead of HTTPS if strict TLS isn't required. Ensure dashboard binds to `0.0.0.0`.

## Troubleshooting Flow

1. Verify Tailscale connectivity: `tailscale ping studio`
2. Test gateway status: `curl -vk http://100.89.133.43:9119/api/status`
3. Inspect desktop `connection.json`: `cat ~/Library/Application\ Support/Hermes/connection.json`
4. Validate dashboard config: `plutil -p ~/Library/LaunchAgents/ai.hermes.dashboard.plist | grep -E 'host|0.0.0.0'`