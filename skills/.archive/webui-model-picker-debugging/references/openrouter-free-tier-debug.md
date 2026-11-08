# OpenRouter Free-Tier Model Fetch Debugging

## Problem Summary
When the Hermes WebUI fails to fetch free-tier models from OpenRouter's API, only 5 fallback models appear in the picker instead of the full set of available free models.

## Diagnostic Commands

### 1. Test OpenRouter API Connectivity
```bash
# Direct test of the API endpoint that's failing
curl -s --max-time 8 https://openrouter.ai/api/v1/models | head -c 200

# If this times out or returns nothing, the host cannot reach OpenRouter
```

### 2. Check WebUI Logs for Errors
```bash
# Look for the specific debug message indicating failure
grep -i "free-tier live fetch unavailable" ~/.hermes/webui.log

# Also check for any HTTP error codes
grep -i "40[0-9]\|50[0-9]" ~/.hermes/webui.log | grep -i openrouter
```

### 3. Verify Network Configuration
```bash
# Test DNS resolution
nslookup openrouter.ai

# Test basic connectivity
telnet openrouter.ai 443
```

## Expected vs Actual Behavior

### Expected (when network works):
- All free-tier OpenRouter models visible in picker
- Models with zero pricing for prompt/completion

### Actual (when network fails):
- Only 5 fallback models visible:
  - Elephant Alpha (free)
  - Owl Alpha (free)
  - Hy3 Preview (free)
  - Nemotron 3 Super (free)
  - Trinity Large Preview (free)

## Root Cause Analysis

The WebUI's model loading process has two phases:
1. **Phase 1**: Fetch curated models with tool support filtering (via hermes_cli)
2. **Phase 2**: Fetch free-tier models unauthenticated from openrouter.ai (fails silently)

When Phase 2 fails, it falls back to the static list in `_FALLBACK_MODELS` (lines 1125-1129 of api/config.py).

This is a silent failure - the user sees only 5 models instead of the full free-tier set, with no clear indication why.

## Troubleshooting Steps

### Immediate Steps:
1. Run the curl test above to confirm network connectivity
2. Check WebUI logs for error messages about openrouter.ai
3. Verify Tailscale/remote access isn't blocking the outbound request

### Long-term Fixes:
1. Configure proper timeout handling for external API calls
2. Add better error reporting to the UI when free-tier fetch fails
3. Consider adding a manual refresh option for model lists