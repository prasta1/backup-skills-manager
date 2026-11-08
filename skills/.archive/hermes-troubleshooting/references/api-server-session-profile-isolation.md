---
name: api-server-session-profile-isolation
description: Fix API server session listing to respect profile parameter for multi-profile Hermes setups
version: 0.1.0
author: Wren
category: hermes
---

# API Server Session Profile Isolation Fix

## Problem Summary
In multi-profile Hermes setups, the gateway's API server (`:8642`) ignores the `profile` query parameter when listing sessions, causing all profiles to show the same sessions from the default profile instead of their own.

## Root Cause Analysis
The `_handle_list_sessions()` method in `gateway/platforms/api_server.py` (lines 1860-1887) only reads `limit`, `offset`, `source`, and `include_children` from the request but never reads or respects the `profile` query parameter. It always uses the default session database (`SessionDB()`), which points to the current process's state.db — always the default profile.

This happens because:
1. The desktop application sends `GET /api/sessions?profile=personal` 
2. But the gateway API server doesn't parse or use the `profile` parameter
3. It always returns sessions from the default profile's database (which is why they appear duplicated across all profiles)

The fix involves ensuring that when a specific profile is requested, the session database connection uses that profile's state.db file instead of the default one.

## Root Cause
The `_handle_list_sessions()` method in `gateway/platforms/api_server.py` (lines 1860-1887) only reads `limit`, `offset`, `source`, and `include_children` from the request but never reads or respects the `profile` query parameter. It always uses the default session database (`SessionDB()`), which points to the current process's state.db — always the default profile.

## Solution
Patch `gateway/platforms/api_server.py` to:
1. Read the `profile` query parameter from the request
2. If profile is specified and different from default, open that profile's session database instead of the default one
3. Maintain backward compatibility for requests without the profile parameter

## Fix Steps
1. Modify `_handle_list_sessions()` to check for `profile` in request query parameters
2. When a specific profile is requested, use that profile's session database instead of default 
3. The fix should be minimal and only affect the session listing logic

## User Preference Alignment
The user prefers "for once and for all" solutions over incremental fixes, direct commands to execute without meta-commentary about why steps are needed, and minimal explanation unless specifically requested.

This skill captures the complete fix approach for the session isolation issue. The user's preference is to have a definitive solution that works correctly rather than a temporary workaround or partial fix.

## Fix Implementation
To properly fix the session listing in gateway mode, modify `gateway/platforms/api_server.py`:

1. In the `_handle_list_sessions()` method (around lines 1860-1887):
   - Read `profile` parameter from request query: 
     ```python
     profile = request.query.get("profile")
     ```
   - When `profile` is specified and not the default, load that profile's session DB:
     ```python
     if profile and profile != "default":
         session_db = SessionDB(profile=profile)
     else:
         session_db = SessionDB()
     ```

2. Ensure the SessionDB class supports profile parameter or create a wrapper that does

3. The fix should be minimal and only affect the session listing logic, maintaining backward compatibility for existing requests without profile parameters.

This ensures that when desktop app makes requests like:
```
GET /api/sessions?profile=personal&limit=20
```

The gateway will correctly return sessions from the personal profile's state.db instead of the default one.
- This is a session isolation bug affecting the API server's multiplexing capability  
- The desktop app sends `profile` query parameters but they're ignored by the API server
- Sessions are properly stored in per-profile state.db files, but the API server doesn't know how to read from them
- The fix requires modifying the session database lookup logic in the API server to respect the profile parameter

## Implementation Details
The fix requires modifying `gateway/platforms/api_server.py` in the `_handle_list_sessions()` method (lines 1860-1887) to:

1. Read the `profile` parameter from the request query string
2. If a specific profile is requested, use that profile's session database instead of the default one
3. Maintain backward compatibility for requests without a profile parameter (default behavior)

## Verification
After applying the fix:
1. Sessions should be properly isolated by profile when using the API server
2. The desktop app should show correct sessions for each profile
3. The default behavior (no profile parameter) should remain unchanged

## References
- `gateway/platforms/api_server.py` lines 1860-1887
- Session database path: `~/.hermes/profiles/<profile>/state.db`