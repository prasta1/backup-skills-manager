# Troubleshooting Guide: Hermes Desktop Authentication

## Common Issues and Resolutions

### 1. Gateway Connection Failures
- **Symptom**: "could not reach this gateway" error in Desktop
- **Root Cause**: HTTPS/TLS mismatch between client and gateway
- **Solution**: Force Desktop to use HTTP instead of HTTPS for connection

### 2. OAuth Redirect URI Mismatch
- **Symptom**: "redirect_uri_mismatch" error during login
- **Root Cause**: Dashboard registered with different redirect URL than Desktop expects
- **Solution**: Re-register dashboard with matching redirect URI format

### 3. TLS Handshake Errors
- **Symptom**: "tlsv1 alert protocol version" in logs
- **Root Cause**: Client-side TLS version incompatibility
- **Solution**: Use HTTP instead of HTTPS if strict TLS isn't required

## Diagnostic Steps

1. Verify Tailscale connectivity from desktop machine:
   ```bash
   tailscale ping studio
   ```

2. Test gateway status endpoint from desktop:
   ```bash
   curl -vk http://100.89.133.43:9119/api/status
   ```

3. Check desktop connection config:
   ```bash
   cat ~/Library/Application\ Support/Hermes/connection.json
   ```

4. Validate dashboard configuration on Studio:
   ```bash
   plutil -p ~/Library/LaunchAgents/ai.hermes.dashboard.plist | grep -E 'host|0.0.0.0'
   ```