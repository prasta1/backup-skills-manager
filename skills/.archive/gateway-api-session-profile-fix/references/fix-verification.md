# Multi-Profile Session Isolation Issue

## Summary
The Hermes desktop app was showing identical session lists across all profiles because the gateway API server (`:8642`) ignores the `profile` query parameter in session listing requests.

## Environment Details
- Running in gateway mode (`hermes gateway run`)
- Desktop app configured to connect to `:8642` API endpoint
- Multiple profiles exist: personal, work, larp
- Session databases properly stored in `~/.hermes/profiles/<profile>/state.db`

## Root Cause
When desktop app makes session listing requests like:
```
GET /api/sessions?profile=personal&limit=20&offset=0&source=local
```

The gateway API server (`gateway/platforms/api_server.py`) was only reading:
- `limit`
- `offset` 
- `source`
- `include_children`

But completely ignoring the `profile` parameter, so it always returned sessions from the default profile's database.

## Fix Applied
Modified `gateway/platforms/api_server.py` in `_handle_list_sessions()` method (lines 1860-1887) to:
1. Read `profile` parameter from request query string
2. When profile is specified and not "default", use that profile's session database
3. Maintain backward compatibility for requests without profile parameter

## Verification Results
After applying fix:
- `GET /api/sessions?profile=personal` now returns personal profile sessions
- `GET /api/sessions?profile=work` now returns work profile sessions  
- `GET /api/sessions` (no profile) still returns default profile sessions
- Desktop session lists now properly isolate by profile

This resolves the multi-profile session isolation issue in gateway mode setups.