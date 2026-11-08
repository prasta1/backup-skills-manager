# Gateway Multiplexing Behavior Analysis

## Background

The user experienced a behavioral change in Hermes where profile switching was no longer working seamlessly. This was due to the introduction of the `gateway.multiplex_profiles` feature.

## Change in Behavior

### Before (v2.x and earlier):
- Each profile ran its own independent gateway process
- Default profile had launchd service, others required manual setup
- Profile switching was less seamless due to separate gateway processes

### After (v3.x+ with multiplexing):
- Single gateway process can serve all profiles
- Behavior change was not well-documented as a breaking change
- Previously working seamless switching required explicit configuration

## Technical Details

### Profile Gateway Architecture:
- Default profile: Launchd service (PID 46272)
- Other profiles: Independent processes requiring manual installation
- Desktop app requires running gateway per profile for messaging platforms

### Root Cause of User Issue:
The `gateway.multiplex_profiles` setting was set to false (default), causing each profile to require its own gateway process, breaking the seamless switching that users were accustomed to.

## User Impact

Users experienced:
1. "Disconnected gateway" warnings when switching between profiles
2. Expected behavior of seamless profile switching was broken  
3. Need to manually install gateways for each individual profile
4. Regression from previous version where one gateway served all profiles

## Solution Pathways

### Immediate Fix:
1. Enable multiplexing: `hermes config set gateway.multiplex_profiles true`
2. Restart gateway: `hermes gateway restart`

### Alternative Manual Fix:
1. Install gateways per profile: `hermes -p personal gateway install --start-now`
2. Verify with: `hermes gateway list`

## Key Takeaway

This represents a behavioral change in Hermes that was not properly communicated to users who relied on seamless cross-profile switching. The multiplexing feature provides the old behavior but requires explicit configuration to enable.