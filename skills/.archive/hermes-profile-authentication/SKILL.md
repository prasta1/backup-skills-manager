---
name: hermes-profile-authentication
description: Resolve authentication issues in multi-profile Hermes setups with gateway connections
version: 0.1.0
author: Wren
category: hermes
---

# Hermes Profile Authentication Issues

## Problem Context
When using multi-profile Hermes setups with a remote gateway (e.g., Mac Studio as the gateway), users may experience authentication failures where desktop clients cannot properly connect to the gateway due to header mismatch issues.

## Root Cause Analysis

### Authentication Mismatch Issue
The Hermes desktop application authenticates to gateways using two mechanisms:
1. **Local mode**: Uses `HERMES_DASHBOARD_SESSION_TOKEN` for authentication
2. **Remote mode**: Sends either:
   - Token auth: `X-Hermes-Session-Token` header (as used in desktop app's local mode)
   - OAuth auth: Session cookies + WebSocket ticket

However, the Hermes gateway API server (`api_server.py`) only validates `Authorization: Bearer ***` tokens (lines 1245-1254), not the `X-Hermes-Session-Token` header.

This mismatch causes "Invalid API key" errors in gateway logs and prevents proper session isolation between profiles when connecting from desktop clients.

### Fix Implementation
The actual fix was applied to `gateway/platforms/api_server.py` in the `_check_auth` method to accept both:
- `Authorization: Bearer ***` (standard token auth)  
- `X-Hermes-Session-Token` (desktop app local mode header)

This allows the gateway to properly authenticate desktop connections that send session tokens instead of just Bearer tokens.

## Verification Commands

After applying fixes:

```bash
# Test that API server accepts valid key
curl -H "Authorization: Bearer your-secret-key-here" http://localhost:8642/v1/models

# Check gateway logs for authentication success
tail -f ~/.hermes/logs/gateway.log | grep -i "auth\|token"
```

## Troubleshooting Checklist

- [ ] API_SERVER_KEY is set in `~/.hermes/.env`  
- [ ] Desktop client configured to use token auth for remote connections
- [ ] Gateway multiplex_profiles is enabled in config.yaml
- [ ] No separate launchd processes for individual profiles
- [ ] Desktop app can successfully connect to gateway without "Invalid API key" errors

## User Preference Alignment

The user explicitly prefers:
- "For once and for all" solutions over incremental fixes
- Direct commands to execute without meta-commentary about why steps are needed  
- Minimal explanation unless specifically requested

This skill provides the complete, final solution for multi-profile authentication issues rather than treating it as a series of incremental troubleshooting steps.