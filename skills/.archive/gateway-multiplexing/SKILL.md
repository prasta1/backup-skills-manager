---
name: gateway-multiplexing
description: Configure Hermes gateway to multiplex profiles for seamless cross-profile operation
version: 0.1.0
author: Wren
---

# Hermes Gateway Multiplexing

## Problem Summary

Users are experiencing a behavioral change where profile switching in the Hermes desktop app no longer works seamlessly. When switching between profiles like `personal` or `work`, the desktop app shows "disconnected gateway" warnings even though all profiles are properly configured.

## Root Cause

This behavior is due to the `gateway.multiplex_profiles` setting being disabled (default false). When multiplexing is off:
- Each Hermes profile runs its own independent gateway process
- Only the **default** profile has a launchd service running its gateway (e.g., PID 46272)
- Other profiles must be explicitly installed and started to serve their own messaging platforms

## Solution: Enable Multiplexing

Enable the `gateway.multiplex_profiles` feature to allow a single gateway process to serve all profiles:

```bash
# Enable multiplexing for all profiles in one gateway
hermes config set gateway.multiplex_profiles true

# Restart the gateway to apply changes
hermes gateway restart
```

## When This Fixes Profile Switching Issues

This approach restores the previous behavior where:
- A single gateway process handles all profiles
- Profile switching in the desktop app works seamlessly without separate gateway processes
- Users don't need to install gateways for each individual profile manually

## User Preference Alignment

The user explicitly stated they prefer "for once and for all" solutions over incremental fixes. They want to understand why something is working as designed rather than being treated as a regression.

## Key Details

- The `gateway.multiplex_profiles` feature is off by default (False)
- When enabled, one gateway process serves all profiles
- This eliminates the need for separate launchd services per profile
- The behavior was working in previous versions before this setting changed

## Configuration Best Practices

1. **Enable multiplexing for seamless operation:**
   ```bash
   hermes config set gateway.multiplex_profiles true
   ```
## User Preference Alignment

The user explicitly stated they prefer "for once and for all" solutions over incremental fixes. They want to understand why something is working as designed rather than being treated as a regression.

## Key Details

- The `gateway.multiplex_profiles` feature is off by default (False)
- When enabled, one gateway process serves all profiles  
- This eliminates the need for separate launchd services per profile
- The behavior was working in previous versions before this setting changed

## Real-World Scenario

In one case, the user experienced:
- Profile switching in desktop app was broken
- New `personal` and `work` profiles showed "disconnected gateway" warnings  
- Gateway processes were running only for the default profile (PID 46272)
- The fix was enabling `gateway.multiplex_profiles` to restore seamless profile switching

## Comparison with Old Behavior

**Before multiplexing was introduced**: 
- One gateway process per profile (default + named)
- Profile switching required separate gateway processes
- Desktop app worked fine once all gateways were installed

**After multiplexing was introduced**:
- Single gateway process can serve multiple profiles
- Profile switching works seamlessly without separate processes  
- Requires explicit enabling of `gateway.multiplex_profiles` to restore old behavior

This change was likely introduced in newer Hermes versions but wasn't documented as a breaking change to the user's workflow.