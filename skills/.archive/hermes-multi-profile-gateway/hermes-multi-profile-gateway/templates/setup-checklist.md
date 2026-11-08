# Multi-Profile Hermes Setup Checklist

## System Configuration Requirements

### Gateway Setup (Mac Studio)
1. Ensure `multiplex_profiles: true` in config.yaml
2. Set API_SERVER_KEY in ~/.hermes/.env:
   ```bash
   echo "API_SERVER_KEY=your-secret-key-here" >> ~/.hermes/.env
   ```
3. Restart gateway process:
   ```bash
   launchctl bootout gui/$(id -u) ~/Library/LaunchAgents/ai.hermes.gateway.plist 2>&1 || true
   sleep 2
   launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/ai.hermes.gateway.plist 2>&1
   ```

### Desktop Client (MacBook Pro)
1. Configure remote gateway connection in Settings → Gateway
2. Ensure Tailscale connectivity to studio.taile85139.ts.net:9119
3. Clear stale OAuth session state if needed:
   ```bash
   rm -rf ~/Library/Application\ Support/Hermes/Session\ Storage/
   rm -rf ~/Library/Application\ Support/Hermes/IndexedDB/
   ```

## Troubleshooting Steps

### Authentication Issues
If desktop shows "Invalid API key" errors:
1. Verify API_SERVER_KEY is set in gateway environment
2. Check that desktop is using token authentication for remote connections  
3. Ensure gateway is running multiplexed mode (not separate profile processes)

### Session Isolation Issues
If all profiles show same sessions:
1. Verify `/api/profiles/sessions` endpoint is properly implemented
2. Check that query parameters are parsed correctly for profile filtering
3. Confirm sessions from each profile database are properly isolated

### Connectivity Problems
If desktop can't connect:
1. Ensure Tailscale is running and studio.taile85139.ts.net resolves correctly
2. Check that port 9119 is accessible from MBP (dashboard server)
3. Verify no firewall rules blocking the connection