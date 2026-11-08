# Authentication Root Cause Analysis

## Issue: X-Hermes-Session-Token vs Authorization: Bearer Mismatch

### Problem
When the Hermes desktop app connects to a remote gateway in multi-profile mode, it sends `X-Hermes-Session-Token` headers for authentication. However, the gateway's `_check_auth` method in `api_server.py` (lines 1245-1254) only accepts `Authorization: Bearer ***` tokens, not the session token header.

### Log Evidence
```
[2026-07-15 09:30:45] ERROR - Invalid API key in request header X-Hermes-Session-Token=...
[2026-07-15 09:30:45] ERROR - Authentication failed for profile "personal"
```

### Fix Path
1. The gateway needs to accept `X-Hermes-Session-Token` headers as valid authentication method
2. OR the desktop app needs to be configured to use `Authorization: Bearer` tokens instead
3. OR the desktop app needs to be set up with proper token configuration for remote gateways

### Solution Implementation
The user's preferred "for once and for all" approach:
1. Set `API_SERVER_KEY` in the gateway environment (as done in our investigation)
2. Configure desktop client to properly authenticate with remote gateways using token auth
3. Verify session isolation works correctly between profiles

This approach addresses the core issue rather than treating it as a series of workarounds.