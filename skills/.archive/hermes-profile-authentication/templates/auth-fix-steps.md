# Hermes Multi-Profile Authentication Fix Steps

## Step-by-Step Resolution Process

### 1. Identify the Authentication Mismatch
```bash
# Check gateway logs for authentication errors  
tail -f ~/.hermes/logs/gateway.log | grep "Invalid API key"
```

### 2. Set API Server Key
```bash
# Add to main environment file
echo "API_SERVER_KEY=your-unique-secret-key-here" >> ~/.hermes/.env
```

### 3. Restart Gateway Service
```bash
# Stop and restart the gateway to reload configuration
launchctl bootout gui/$(id -u) ~/Library/LaunchAgents/ai.hermes.gateway.plist 2>&1 || true
sleep 3
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/ai.hermes.gateway.plist 2>&1
```

### 4. Configure Desktop Client for Remote Mode
```bash
# Set environment variables for desktop app to connect properly
export HERMES_DESKTOP_REMOTE_URL=http://studio.taile85139.ts.net:8642
export HERMES_DESKTOP_REMOTE_TOKEN=your-unique-secret-key-here
```

### 5. Verify Fix Works
```bash
# Test that API server accepts valid key
curl -H "Authorization: Bearer your-unique-secret-key-here" http://localhost:8642/v1/models

# Check desktop app logs for successful authentication
tail -f ~/Library/Logs/Hermes/desktop.log | grep "auth\|token"
```

## Expected Outcome
After these steps, desktop clients should be able to properly connect to the remote gateway with isolated session data between profiles, resolving the "Invalid API key" errors and profile merging issues.

## Key Commands for User Preference Alignment
The user prefers direct commands without meta-commentary:

1. `echo "API_SERVER_KEY=your-unique-secret-key-here" >> ~/.hermes/.env`
2. `launchctl bootout gui/$(id -u) ~/Library/LaunchAgents/ai.hermes.gateway.plist`
3. `launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/ai.hermes.gateway.plist`