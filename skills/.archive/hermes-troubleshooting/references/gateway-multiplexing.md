# Gateway Multiplexing in Hermes

## Understanding the Behavior

In multi-profile Hermes setups, gateways can run in two modes:

1. **Multiplex Mode**: A single gateway process (`PID 31794`) that serves all profiles when `multiplex_profiles: true` is configured in the main config
2. **Separate Processes**: Individual gateway processes for each profile (e.g., `work` and `personal`) that run as separate launchd services

## Key Observations from the Session

### Default Gateway Behavior
- The default gateway runs as a multiplexer that already serves all profiles (PID 31794)
- It uses the shared `~/.hermes/shared/nous_auth.json` for all profiles
- This is the preferred configuration when `multiplex_profiles: true` is set

### Separate Profile Gateways
- Work and personal profiles were running separate gateway processes (PIDs 1049 and 31773)
- These were causing token synchronization issues because they were using outdated credentials
- They needed to be stopped and allowed to run under the multiplexer instead

## Management Commands

### Check Gateway Status
```bash
hermes gateway status
```

### Stop Separate Profile Gateways
```bash
# For work profile
launchctl bootout gui/$(id -u) ~/Library/LaunchAgents/ai.hermes.gateway-work.plist 2>&1 || true

# For personal profile  
launchctl bootout gui/$(id -u) ~/Library/LaunchAgents/ai.hermes.gateway-personal.plist 2>&1 || true
```

### Restart Main Gateway to Apply Changes
```bash
# Restart the main multiplexer gateway
launchctl bootout gui/$(id -u) ~/Library/LaunchAgents/ai.hermes.gateway.plist 2>&1 || true
sleep 2
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/ai.hermes.gateway.plist 2>&1
```

## Verification

After changes:
1. Verify all profiles have synchronized tokens from the shared store
2. Confirm the main gateway is running (PID 31794) with `multiplex_profiles: true`
3. Check that no separate profile gateway processes exist