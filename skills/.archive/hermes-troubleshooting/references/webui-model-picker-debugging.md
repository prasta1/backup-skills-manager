---
name: webui-model-picker-debugging
description: Debug and resolve issues with model picker visibility in Hermes WebUI, particularly missing free-tier OpenRouter models
version: 0.1.0
author: Wren
platforms: [macos, linux]
---

# Hermes WebUI Model Picker Debugging

## Overview

This skill provides systematic debugging for issues where models don't appear in the WebUI model picker, particularly focusing on OpenRouter free-tier models that fail to load due to network or configuration issues.

## Problem Patterns

### Free-Tier Models Not Visible in Picker

The WebUI uses a two-stage model list building process:
1. **Curated live catalog** - via `hermes_cli.models.fetch_openrouter_models()` with tool-support filtering
2. **Free-tier augmentation** - unauthenticated fetch to `openrouter.ai/api/v1/models` for free models

If stage 2 fails (network timeout, DNS issues, or API errors), the picker falls back to static `_FALLBACK_MODELS` list containing only 5 OpenRouter free models.

### Root Cause Investigation

**Primary suspect**: Network connectivity to `openrouter.ai` from the WebUI host.

**Secondary suspects**:
- Timeout configuration for external API calls
- Local DNS resolution issues
- Firewall/proxy blocking the request

## Diagnostic Steps

### 1. Check WebUI Logs for Free-Tier Fetch Failures
```bash
# Look for the debug log indicating free-tier fetch failure
grep -i "openrouter.*free.*tier\|free-tier.*live.*fetch" ~/.hermes/webui.log
```

### 2. Test Direct API Access
```bash
# Test if the host can reach OpenRouter's API endpoint
curl -s --max-time 8 https://openrouter.ai/api/v1/models | head -c 200
```

### 3. Examine WebUI Model Endpoint Response
```bash
# Get raw model list from the WebUI (will need auth)
curl -H "Authorization: Bearer <token>" http://127.0.0.1:8787/api/models
```

### 4. Verify Provider Configuration
```bash
# Check if OpenRouter provider is properly configured
hermes config get providers.openrouter
```

## Troubleshooting Solutions

### Solution 1: Network Access Fix
If the direct API test fails, the issue is likely network connectivity from the host to `openrouter.ai`.

**Resolution steps**:
1. Check DNS resolution:
   ```bash
   nslookup openrouter.ai
   ```

2. Test HTTP connectivity:
   ```bash
   telnet openrouter.ai 443
   ```

3. If behind a corporate firewall, configure proxy settings or request access to the domain.

### Solution 2: Configuration Adjustment (Code-Level)
If network issues can't be resolved immediately, the code can be adjusted to make the free-tier fetch more resilient.

### Solution 3: Use Fallback Models
When the free-tier fetch fails, only 5 models appear:
- Elephant Alpha (free)
- Owl Alpha (free) 
- Hy3 Preview (free)
- Nemotron 3 Super (free)
- Trinity Large Preview (free)

These are visible in the picker but may not be the user's preferred models.

## Common Pitfalls

### Pitfall 1: Silent Failures
The free-tier fetch uses a 8-second timeout but doesn't show detailed errors in the UI. Users may think the models just don't exist.

### Pitfall 2: Misunderstanding Fallback Behavior
The WebUI shows the fallback list of 5 free models instead of all available free models when the live fetch fails.

### Pitfall 3: Assumption About Network Connectivity
Users may not realize that network issues in the WebUI environment can block model availability.

## Best Practices

### For Developers/Operators
1. Monitor WebUI logs for free-tier fetch errors
2. Implement proper network resilience in model fetching logic
3. Ensure fallback behavior is clearly documented and tested

### For Users
1. Verify network connectivity to external APIs from the WebUI host
2. Check that the WebUI logs show any error messages about model fetching
3. Consider alternative providers if OpenRouter integration is problematic

## References

- WebUI config code: `api/config.py` line ~6704 (OpenRouter free-tier handling)
- Free-tier model list: `_FALLBACK_MODELS` in `api/config.py` lines 1125-1129