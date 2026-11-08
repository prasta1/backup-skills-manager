# Session Listing Bug Analysis

## Issue Summary
When using the Hermes desktop app with multiple profiles, session listing via the API server (`:8642`) ignores the `profile` query parameter, causing all profiles to show sessions from the default profile.

## Root Cause Details
The `_handle_list_sessions()` function in `gateway/platforms/api_server.py` only reads these query parameters:
- `limit`
- `offset` 
- `source`
- `include_children`

It never reads or respects the `profile` parameter, so it always opens the default session database regardless of what profile was requested.

## Debugging Steps Taken
1. Confirmed that sessions are properly stored in per-profile state.db files (`~/.hermes/profiles/personal/state.db`, `~/.hermes/profiles/work/state.db`)
2. Verified that the desktop app sends `profile` query parameters in API requests
3. Confirmed that all profile sessions return the same IDs (from default profile)
4. Identified that `gateway/platforms/api_server.py` lines 1860-1887 need modification to handle the profile parameter

## Fix Location
File: `gateway/platforms/api_server.py`
Method: `_handle_list_sessions()` (lines 1860-1887)
Specific change needed: Add profile parameter reading and session DB selection logic