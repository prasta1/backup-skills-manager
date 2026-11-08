# API Server Session Profile Isolation Fix

## Implementation Steps

### Step 1: Modify the API server to read profile parameter
In `gateway/platforms/api_server.py`, modify the `_handle_list_sessions` method to:

1. Read the `profile` query parameter from the request:
   ```python
   profile = request.query.get("profile")
   ```

2. When a specific profile is requested, use that profile's session database:
   ```python
   if profile and profile != "default":
       # Use the specific profile's session database instead of default
       db = SessionDB(profile=profile)
   ```

### Step 2: Ensure backward compatibility
- If no profile is specified or profile is "default", continue using the default session DB
- This maintains existing behavior for users not relying on profile isolation

### Step 3: Verify the fix works
After applying the patch:
1. Sessions should be properly isolated by profile when using the API server
2. The desktop app should show correct sessions for each profile
3. Default behavior (no profile parameter) remains unchanged

## Expected Outcome

Before fix:
```
GET /api/sessions?profile=personal → returns sessions from default profile
GET /api/sessions?profile=work      → returns sessions from default profile  
```

After fix:
```
GET /api/sessions?profile=personal → returns sessions from personal profile
GET /api/sessions?profile=work      → returns sessions from work profile
```

## Testing Commands
```bash
# Test that API server respects profile parameter
curl -H "Authorization: Bearer your-api-key" "http://localhost:8642/api/sessions?profile=personal"

# Test default behavior (no profile parameter)
curl -H "Authorization: Bearer your-api-key" "http://localhost:8642/api/sessions"
```