---
name: gateway-session-profile-isolation
description: Complete solution for cross-profile session isolation in Hermes gateway mode
version: 0.1.0
author: Wren
category: hermes
---

# Gateway Session Profile Isolation

## Problem Summary
In multi-profile Hermes setups running in gateway mode, the desktop application and TUI show merged sessions from all profiles instead of properly isolated sessions for each profile. This occurs because the gateway's API server doesn't support cross-profile session access.

## Root Cause
The Hermes gateway in multiplexed mode only had basic session listing capabilities but lacked the comprehensive cross-profile session handling needed by the desktop app. Specifically:
1. The `/api/profiles/sessions` endpoint didn't exist in gateway mode
2. Per-session endpoints (`/api/sessions/{id}/messages`) didn't respect profile context
3. Session database access was tied to the default profile, not individual profiles

## Solution Overview
Complete implementation of cross-profile session handling in the gateway's API server that:
1. Adds `/api/profiles/sessions` endpoint supporting profile parameter
2. Updates all session endpoints to properly handle cross-profile access  
3. Maintains backward compatibility for existing usage patterns

## Implementation Details

### Key Changes in `gateway/platforms/api_server.py`:

1. **New cross-profile session database access method**:
   ```python
   def _open_session_db_for_profile(self, profile: Optional[str]):
       """Open a SessionDB for read paths, optionally for another profile.
   
       ``profile`` None/empty → this process's own ``state.db`` (the common,
       single-profile case). A named profile opens that profile's on-disk
       ``state.db`` directly so the gateway can serve cross-profile reads
       (transcripts, detail) without spawning that profile's backend.
       """
       from hermes_state import SessionDB
       if not profile:
           return self._ensure_session_db()
       from hermes_cli import profiles as profiles_mod
       name = profile.strip() or "default"
       home = profiles_mod.get_profile_dir(name)
       return SessionDB(db_path=Path(home) / "state.db", read_only=True)
   ```

2. **New unified session listing endpoint**:
   ```python
   async def _handle_profiles_sessions(self, request: "web.Request") -> "web.Response":
       # Handles /api/profiles/sessions with optional profile parameter
       # Returns sessions from all profiles or specific profile as needed
   ```

3. **Enhanced session access methods**:
   ```python
   def _get_existing_session_or_404(self, session_id: str, profile: Optional[str] = None) -> tuple[Optional[Dict[str, Any]], Optional["web.Response"]]:
       db = self._open_session_db_for_profile(profile)
   ```

### Endpoints Added/Enhanced:
- `GET /api/profiles/sessions` - Cross-profile session listing with optional `profile` parameter
- `GET /api/sessions/{session_id}/messages` - Per-session message history with profile context
- `GET /api/sessions/{session_id}` - Session details with profile context

## Verification
After applying the fix:
1. Desktop app shows separate session lists for each profile
2. TUI session switching works correctly across profiles  
3. Session details and message history are properly scoped to their source profiles
4. Default behavior (no profile parameter) remains unchanged

## User Preference Alignment
The user prefers "for once and for all" solutions over incremental fixes, direct commands to execute without meta-commentary about why steps are needed, and minimal explanation unless specifically requested.

## References
- `gateway/platforms/api_server.py` lines 1311-1329, 1855-1862, 1906-2021, 2079-2085, 2131-2138
- Session database path: `~/.hermes/profiles/<profile>/state.db`