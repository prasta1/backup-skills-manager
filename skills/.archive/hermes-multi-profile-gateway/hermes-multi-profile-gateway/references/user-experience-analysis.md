# Profile Gateway Behavior Analysis

This document analyzes the user's experience with Hermes profile gateway behavior and the root cause of their reported issue.

## User Experience

The user reported:
1. Previously seamless profile switching between `personal` and `work` profiles was broken
2. Desktop app showed "disconnected gateway" warnings when switching profiles
3. The behavior was not expected and worked out of the box before

## Root Cause Analysis

The issue stems from a behavioral change in Hermes where:
- `gateway.multiplex_profiles` setting defaults to false (v3.x+)
- Previously, one gateway served all profiles seamlessly  
- Now, each profile requires its own gateway process unless multiplexing is enabled

## Configuration Fix

### For Seamless Operation:
```bash
# Enable multiplexing to restore old behavior
hermes config set gateway.multiplex_profiles true

# Restart gateway to apply changes  
hermes gateway restart
```

### For Individual Profile Gateways:
```bash
# Install gateways for specific profiles (if not using multiplexing)
hermes -p personal gateway install --start-now
hermes -p work gateway install --start-now
```

## Key Insights

1. **Breaking Change**: The multiplexing feature introduced a behavioral regression that was not properly communicated
2. **User Preference**: User explicitly preferred "for once and for all" solutions over incremental fixes
3. **Expected Workflow**: Previously, switching between profiles was seamless without separate gateway processes
4. **Configuration Impact**: The default behavior changed, requiring explicit user action to restore previous workflow

This analysis confirms that the fix for the user's issue was properly identified and addressed.