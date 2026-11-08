# API Server Authentication Issue

## Problem Summary
When switching to `personal` or `work` profiles, chat fails because the API server on port 8642 rejects requests with "Invalid API key". The gateway multiplexer is correctly configured (`gateway.multiplex_profiles: true`), but the API server auth is missing.

## Root Cause Analysis
1. With `gateway.multiplex_profiles: true`, the default gateway (PID 30953) serves all profiles - there's one shared API server on port 8642
2. The API server requires authentication via `API_SERVER_KEY` (line 923 in `api_server.py`: `os.getenv("API_SERVER_KEY", "")`)
3. Neither the main `.env` nor the profile `.env` files have `API_SERVER_KEY` set
4. The desktop/TUI chat connects to this API server, not directly to the gateway

## Diagnosis Commands
```bash
# Check if API_SERVER_KEY is configured in main .env
grep "API_SERVER_KEY" ~/.hermes/.env

# Check if API_SERVER_KEY is configured in profile .env files
grep "API_SERVER_KEY" ~/.hermes/profiles/personal/.env 2>/dev/null || echo "No personal .env"
grep "API_SERVER_KEY" ~/.hermes/profiles/work/.env 2>/dev/null || echo "No work .env"

# Test API server authentication
curl -H "Authorization: Bearer invalid-key" http://localhost:8642/v1/models
```

## Fix Steps
1. Add an API key to authenticate the desktop app:
```bash
# Add to ~/.hermes/.env (the main profile's .env)
echo 'API_SERVER_KEY=your-secret-key-here' >> ~/.hermes/.env

# Then restart the gateway
launchctl bootout gui/$(id -u) ~/Library/LaunchAgents/ai.hermes.gateway.plist
sleep 3
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/ai.hermes.gateway.plist
```

2. Configure the desktop app to use the same key in its API configuration.

## Verification
After applying the fix, verify:
```bash
# Test that API server accepts valid key
curl -H "Authorization: Bearer your-secret-key-here" http://localhost:8642/v1/models

# Test that desktop app can connect
# (Check desktop app logs for successful authentication)
```

## Key Details
- The desktop app connects to the API server endpoint, not the direct gateway
- Authentication is required for all API server requests (even health checks)
- The same API key must be used in both the .env file and desktop app config