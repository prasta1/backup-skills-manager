#!/bin/bash
# Verify gateway multiplexing configuration and status

echo "=== Gateway Multiplexing Status ==="

# Check if multiplexing is enabled
if grep -q "multiplex_profiles: true" ~/.hermes/config.yaml; then
    echo "✓ multiplex_profiles is enabled"
else
    echo "✗ multiplex_profiles is NOT enabled"
fi

# Check active gateways
echo ""
echo "=== Active Gateways ==="
hermes gateway list

# Check session TTL setting
echo ""
echo "=== Session TTL Configuration ==="
grep -A5 "basic_auth:" ~/.hermes/config.yaml | grep session_ttl_seconds

echo ""
echo "=== Gateway Process Status ==="
ps aux | grep "hermes.*gateway" | grep -v grep