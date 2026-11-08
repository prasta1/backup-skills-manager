# Gateway API Session Profile Fix - Implementation Details

## Complete Implementation Steps

### 1. Locate the Method to Modify
File: `gateway/platforms/api_server.py`
Method: `_handle_list_sessions()` (lines 1860-1887)

### 2. Current Implementation (Before Fix)
```python
def _handle_list_sessions(self, request):
    limit = int(request.query.get("limit", 20))
    offset = int(request.query.get("offset", 0))
    source = request.query.get("source", "local")
    include_children = request.query.get("include_children", "false").lower() == "true"
    
    # This always uses the default session DB regardless of profile requested
    session_db = SessionDB()
    
    # ... rest of method implementation ...
```

### 3. Fixed Implementation (After Patch)
```python
def _handle_list_sessions(self, request):
    limit = int(request.query.get("limit", 20))
    offset = int(request.query.get("offset", 0))
    source = request.query.get("source", "local")
    include_children = request.query.get("include_children", "false").lower() == "true"
    
    # NEW: Read profile parameter and use appropriate session DB
    profile = request.query.get("profile")
    if profile and profile != "default":
        session_db = SessionDB(profile=profile)
    else:
        session_db = SessionDB()
    
    # ... rest of method unchanged ...
```

### 4. Testing Approach
After applying the fix:
1. Restart the gateway server (`hermes gateway run`)
2. Observe that desktop app session lists now properly show profile-specific sessions
3. Verify no existing functionality is broken (requests without `profile` parameter still work)

### 5. Alternative Fix Paths
If the SessionDB class doesn't support profile parameter:
1. Create a helper function to get session DB by profile name  
2. Modify the path resolution to use `~/.hermes/profiles/{profile}/state.db` directly
3. Or add a new parameter to SessionDB constructor

### 6. Expected Behavior After Fix
- Request: `GET /api/sessions?profile=personal&limit=20`
- Returns: Sessions from `~/.hermes/profiles/personal/state.db`  
- Request: `GET /api/sessions?profile=work&limit=20`
- Returns: Sessions from `~/.hermes/profiles/work/state.db`
- Request: `GET /api/sessions?limit=20` (no profile)
- Returns: Sessions from default `~/.hermes/state.db` (backward compatible)

This is a minimal, targeted fix that addresses the exact root cause of the session duplication issue.