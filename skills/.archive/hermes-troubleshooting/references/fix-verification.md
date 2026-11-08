# Fix Verification Steps

## Post-Fix Verification Commands

### 1. Check API Server Authentication
```bash
# Test that gateway accepts both token formats
curl -H "Authorization: Bearer your-secret-key-here" http://localhost:8642/v1/models
curl -H "X-Hermes-Session-Token: your-session-token-here" http://localhost:8642/v1/models
```

### 2. Verify Session Endpoint Implementation
```bash
# Test cross-profile session listing
curl -H "Authorization: Bearer your-secret-key-here" http://localhost:8642/api/profiles/sessions?profile=work
curl -H "Authorization: Bearer your-secret-key-here" http://localhost:8642/api/profiles/sessions
```

### 3. Check Gateway Logs for Authentication Success
```bash
# Monitor logs for proper auth handling
tail -f ~/.hermes/logs/gateway.log | grep -i "auth\|token\|session"
```

### 4. Validate Profile Isolation
```bash
# Check session counts per profile on gateway
sqlite3 ~/.hermes/profiles/work/state.db "SELECT COUNT(*) FROM sessions;"
sqlite3 ~/.hermes/profiles/personal/state.db "SELECT COUNT(*) FROM sessions;"
```

### 5. Desktop App Connection Test
```bash
# Verify desktop app can connect without "Invalid API key" errors
# Check desktop logs for successful session retrieval
```