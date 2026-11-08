# Photon and Profile Credential Conflicts

## Issue Summary
The user experienced gateway timeout/re-auth cycles due to a combination of:
1. Stale Photon sidecar credentials in `.env` files
2. Credential conflicts between personal and work profiles using the same Telegram bot tokens
3. Stale gateway state files causing persistent phantom platform connections

## Root Causes
- **Photon credentials**: `PHOTON_PROJECT_ID` and `PHOTON_PROJECT_SECRET` were still present in `.env` even though the platform was disabled in config
- **Profile conflicts**: Both `personal` and `work` profiles had Telegram bot tokens that would conflict when the gateway tried to load them
- **Stale state files**: `gateway_state.json` and `channel_directory.json` in profile directories were causing platform adapters to retry endlessly

## Resolution Steps
1. **Clean credential files**:
   - Remove all `PHOTON_*` variables from `.env`
   - Set `PHOTON_SIDECAR_AUTOSTART=false` to prevent sidecar spawning

2. **Fix profile credential conflicts**:
   - Create empty `.env` override files in `personal` and `work` profiles to prevent duplicate Telegram token usage

3. **Clear stale gateway state**:
   - Remove `gateway_state.json` files from profile directories
   - Delete `channel_directory.json` files that were triggering phantom platform connections

4. **Restart gateway cleanly**:
   - Use launchd to properly restart the gateway process with fresh state

## Verification
After applying fixes:
- `ps aux | grep sidecar` should show no processes
- `hermes gateway list` should show stable gateways
- Logs should not contain repeated Photon or sidecar errors
- Desktop app should maintain stable connection without re-auth prompts

## Prevention Tips
- Always check `.env` files for stale credentials when disabling platforms
- Use profile-specific overrides to isolate credential conflicts
- Monitor gateway logs for persistent error patterns that indicate stale state issues