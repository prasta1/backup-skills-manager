# Gateway Plugin Crash Troubleshooting

## Problem
Users experiencing continuous gateway timeouts and re-authentication prompts due to plugin crashes (particularly Photon sidecar failures).

## Diagnosis
When the gateway experiences frequent restarts or timeouts, check for:
1. Plugin processes that crash repeatedly
2. Authentication errors in the plugin logs
3. Gateway logs showing fatal plugin adapter errors

### Key diagnostic commands:
```bash
# Check gateway status and active processes
hermes gateway list
ps aux | grep "gateway run"
ps aux | grep "photon/sidecar"

# Check recent gateway error logs for plugin crashes
tail -50 ~/.hermes/logs/gateway.error.log | grep -i "photon|fatal|crash"
```

## Solution
The most common cause is a misconfigured plugin (especially Photon) that keeps crashing and forcing gateway restarts.

### Steps to fix:
1. **Identify the problematic plugin** - Look for error messages in logs like "SIDECAR_CRASHED" or "inbound stream dropped"
2. **Remove problematic credentials** - If using Photon, remove the `PHOTON_*` variables from `.env`
3. **Disable the plugin in config** - Ensure `platforms.photon.enabled: false` and `plugins.disabled: platforms/photon`
4. **Restart the gateway cleanly**
5. **Verify no sidecar processes remain**

### Example fix:
```bash
# Remove Photon credentials from .env
sed -i '' '/PHOTON_/d' ~/.hermes/.env

# Verify plugin is disabled in config
grep -A2 "platforms.photon" ~/.hermes/config.yaml

# Restart gateway cleanly
launchctl bootout gui/$(id -u) ~/Library/LaunchAgents/ai.hermes.gateway.plist 2>/dev/null
sleep 3
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/ai.hermes.gateway.plist 2>/dev/null
```

### Key Details:
- Gateway crashes caused by plugin sidecar failures can appear as timeout/re-auth issues
- The gateway will keep restarting every ~30 seconds if a plugin keeps crashing
- Plugin credentials can persist in `.env` even when disabled in config
- Ensure both environment variables and configuration are properly cleared
- Stale gateway_state.json files can cause phantom platform connections to retry endlessly
- Profile credential conflicts (e.g., Telegram bot tokens) can trigger gateway instability

## Real-World Fix Applied
In this case, the user was experiencing repeated gateway restarts every 30 seconds due to:
1. A Photon sidecar attempting to connect with invalid credentials (PHOTON_PROJECT_ID/SECRET)
2. The sidecar crashing with `401` errors on `/inbound`
3. This forcing the gateway to restart repeatedly, causing timeout and re-auth prompts
4. Credential conflicts between personal/work profiles creating additional instability

The solution involved:
1. **Complete credential cleanup**: Removing `PHOTON_*` environment variables from `.env`
2. **Configuration verification**: Confirming the platform config had proper disablement (`platforms.photon.enabled: false` and `plugins.disabled: platforms/photon`)
3. **Stale state cleanup**: Removing `gateway_state.json` and `channel_directory.json` files in profile directories that were triggering phantom platform connections
4. **Profile credential isolation**: Creating empty `.env` override files in `personal` and `work` profiles to prevent Telegram token conflicts
5. **Clean gateway restart**: Using launchd to properly restart the gateway process with fresh state

This resolved the continuous timeout/re-auth cycles that were making the desktop app unusable.

## Additional Troubleshooting Tips
When troubleshooting gateway instability:
- Check for `gateway_state.json` files in profile directories that may have cached platform states
- Look for stale `channel_directory.json` files that trigger phantom platform connections
- Verify environment variables in `.env` files (not just config.yaml) - credentials can persist there
- Use `hermes gateway list` to confirm all gateways are properly running
- Monitor logs with `tail -f ~/.hermes/logs/gateway.error.log` to catch ongoing reconnection attempts

## Scripted Restart
For a complete clean restart, use the included gateway restart script:
```bash
# Make executable if needed
chmod +x ~/.hermes/skills/hermes/gateway-plugin-crash-troubleshooting/scripts/gateway-restart.sh

# Run the clean restart
~/.hermes/skills/hermes/gateway-plugin-crash-troubleshooting/scripts/gateway-restart.sh
```

This script:
1. Removes stale gateway state files in all profile directories
2. Stops any existing gateway processes cleanly
3. Restarts the gateway using launchd to ensure proper state management