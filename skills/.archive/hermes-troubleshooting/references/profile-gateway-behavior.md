---
name: profile-gateway-behavior
description: Understanding and managing Hermes profile gateway behavior for seamless cross-profile operation
version: 0.1.0
author: Wren
---

# Hermes Profile Gateway Behavior

## Problem Summary

When users switch between Hermes profiles (e.g., `personal`, `work`), the desktop app or TUI may show "disconnected gateway" warnings even though the profiles are properly configured.

## Root Cause

Each Hermes profile runs its own independent gateway process that handles messaging platforms (Telegram, Discord) and cron jobs. The gateway is only started for the **default** profile by default (e.g., PID 46272 you see).

## Solution

This behavior is actually correct and expected. To make other profiles work with the desktop app:

1. **Install gateways for specific profiles:**
   ```bash
   hermes -p personal gateway install --start-now
   hermes -p work gateway install --start-now
   ```

2. **Verify the gateways are running:**
   ```bash
   hermes gateway list
   ```

## Key Details

- The `default` profile has a launchd service running its gateway — that's the PID you see for default (e.g., 46272)
- The other profiles have no gateway because they were just set up and have no messaging platform tokens configured
- The gateway is a per-profile service that handles messaging platforms (Telegram, Discord, etc.) and cron jobs
- If you want gateways for other profiles, install them per-profile with `--start-now` to ensure they're running
- If those profiles don't have their own Telegram/Discord bots configured, there's nothing for the gateway to do
- Chatting across profiles in the desktop app or TUI works fine without it

## User Preference Alignment

The user explicitly said they prefer "for once and for all" solutions over incremental fixes, which means they want to understand why something is working as designed rather than being treated as a bug. They also prefer direct commands to execute without meta-commentary about why these steps are needed, and minimal explanation unless specifically requested.

## Real-World Example

In one case, the user encountered this exact scenario:
- They had created new `personal` and `work` profiles
- The desktop app showed "disconnected gateway" warnings when switching to these profiles
- The fix was to properly install and start gateways for those specific profiles using the `--start-now` flag

However, there was also a behavioral change in newer Hermes versions where the `gateway.multiplex_profiles` setting was introduced. When enabled, a single gateway can serve all profiles, restoring the seamless switching that existed before.

## Alternative Solution: Enable Multiplexing

For users who want to restore the old seamless profile switching behavior:

```bash
# Enable multiplexing for all profiles in one gateway
hermes config set gateway.multiplex_profiles true

# Then restart the gateway to apply changes
hermes gateway restart
```

This approach eliminates the need for separate gateways per profile while restoring the previous behavior.

## Configuration Best Practices

1. **Use `--start-now`** when installing gateways for non-default profiles to ensure they're immediately running
2. **Verify with `hermes gateway list`** that all desired gateways are showing as running
3. **Avoid the default `--no-start-now`** when installing for new profiles, as it leaves them in a stopped state

This approach ensures that each profile's desktop app context has access to its own gateway for messaging platforms, making cross-profile operation seamless.