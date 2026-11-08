# Desktop Authentication Issue: Plugin-Based Auth vs Old Plaintext

## Problem Summary
When the Hermes desktop app attempts to authenticate with the dashboard, it hits a mismatch between:
1. The desktop app's expectation of the old plaintext basic-auth field
2. The new plugin-based dashboard auth system that requires proper provider registration

## Root Cause
In June 2026, Hermes introduced a security hardening that replaced the old plaintext dashboard basic-auth with a plugin-based system. The desktop app now authenticates against registered password providers rather than the old `password_hash` field.

## Example Error Pattern
```
Invalid Host header. Dashboard requests must use the hostname the server was bound to.
```

## Reproduction
1. Desktop app configured to bind to `studio.taile85139.ts.net`
2. Dashboard running with basic auth but no password set (empty `password_hash` field)
3. Desktop app attempts to authenticate using old auth method instead of new plugin system

## Fix Pattern
1. Use `hermes dashboard register --username prasta --password admin` to set up proper provider
2. Restart the dashboard service to reload providers  
3. Desktop app should now authenticate correctly with new password provider

## Key Point
The desktop application's authentication logic changed to require the plugin-based auth system, not just plaintext fields. Users who updated after June 2026 but didn't properly re-register their dashboard auth will hit this exact error pattern.