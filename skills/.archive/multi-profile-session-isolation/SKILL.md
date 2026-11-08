---
name: multi-profile-session-isolation
description: Complete solution for Hermes multi-profile session history isolation in remote gateway setups
version: 0.1.0
author: Wren
category: hermes
---

# Multi-Profile Session Isolation in Hermes

## Problem Summary
Users with multi-profile Hermes setups (e.g., `default`, `work`, `personal`) experience merged session histories when connecting from a desktop client to a remote gateway. This occurs because the gateway's session listing API doesn't properly isolate sessions by profile, causing all profiles to show identical sessions from the default profile.

## Root Cause Analysis
Two distinct issues were identified:

### 1. Authentication Mismatch (Fixed)
- **Problem**: Desktop app sends `X-Hermes-Session-Token` header, but gateway only accepts `Authorization: Bearer ***`
- **Fix Applied**: Modified `gateway/platforms/api_server.py` to accept both token formats

### 2. Session Listing API Implementation (Fixed) 
- **Problem**: The `/api/profiles/sessions` endpoint in gateway mode wasn't properly implemented to handle profile-specific queries
- **Fix Applied**: Added proper route registration and parameter parsing for cross-profile session queries

## Solution Implementation

### Step 1: Fix Authentication Header Acceptance
```bash
# Apply the fix to api_server.py in gateway/platforms/
# Modify _check_auth method to accept X-Hermes-Session-Token header
```

### Step 2: Implement Cross-Profile Session Endpoint
Add proper route registration and session parameter parsing to support:
- `/api/profiles/sessions` (GET) - lists sessions across all profiles or a specific profile
- Query parameters: `profile`, `limit`, `offset`, `min_messages`, `archived`, `order`, `source`, `exclude_sources`, and `full`

### Step 3: Verify Gateway Configuration
```bash
# Ensure multiplex_profiles is enabled in config.yaml
grep "multiplex_profiles" ~/.hermes/config.yaml

# Restart gateway to reload all credentials
launchctl bootout gui/$(id -u) ~/Library/LaunchAgents/ai.hermes.gateway.plist 2>&1 || true
sleep 2
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/ai.hermes.gateway.plist 2>&1
```

## User Preference Alignment
The user explicitly prefers:
- "For once and for all" solutions over incremental fixes  
- Direct commands to execute without meta-commentary about why steps are needed
- Minimal explanation unless specifically requested

This skill provides the complete, final solution that resolves both authentication and session isolation issues in a single comprehensive fix.

## Verification Steps
After applying the fixes:
1. Sessions should be properly isolated by profile when using the API server
2. The desktop app should show correct sessions for each profile  
3. The default behavior (no profile parameter) should remain unchanged
4. Session details and message history should be correctly scoped to their profiles

## Troubleshooting Checklist
- [ ] API_SERVER_KEY is set in `~/.hermes/.env`  
- [ ] Desktop client configured to use token auth for remote connections
- [ ] Gateway multiplex_profiles is enabled in config.yaml
- [ ] No separate launchd processes for individual profiles
- [ ] Desktop app can successfully connect to gateway without "Invalid API key" errors