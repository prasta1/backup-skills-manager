#!/bin/bash
# Gateway Restart Script

echo "Stopping Hermes gateway cleanly..."

# Stop the gateway process if running
if pgrep -f "gateway run" > /dev/null; then
    # Use launchctl to properly stop the gateway service
    launchctl bootout gui/$(id -u) ~/Library/LaunchAgents/ai.hermes.gateway.plist 2>/dev/null
    sleep 3
    
    # Kill any remaining gateway processes
    pkill -9 -f "gateway run" 2>/dev/null
    sleep 1
    
    # Kill any lingering photon sidecar processes  
    pkill -9 -f "photon/sidecar" 2>/dev/null
fi

echo "Starting Hermes gateway..."

# Restart the gateway service
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/ai.hermes.gateway.plist 2>/dev/null

echo "Gateway restart initiated. Check status with 'hermes gateway list'"