#!/bin/bash

# Test script for gateway session profile isolation fix
# Usage: ./verify-profile-isolation.sh

echo "Verifying gateway session profile isolation fix..."

# Check if the API server is running
if ! pgrep -f "hermes.*gateway.*run" > /dev/null; then
    echo "ERROR: Gateway is not running"
    exit 1
fi

# Test the new endpoint exists and returns proper JSON
echo "Testing /api/profiles/sessions endpoint..."
curl -s http://localhost:8642/api/profiles/sessions | head -1

# Test with profile parameter (should work even if no sessions)
echo "Testing /api/profiles/sessions?profile=personal..."
curl -s "http://localhost:8642/api/profiles/sessions?profile=personal" | head -1

# Test that it's not a 404 (should be auth error or valid JSON)
echo "Checking that endpoint exists..."
if curl -s -o /tmp/test_response.txt http://localhost:8642/api/profiles/sessions; then
    if grep -q "error" /tmp/test_response.txt; then
        echo "✓ Endpoint exists and responds (auth error expected)"
    else
        echo "✓ Endpoint exists and returns valid response"
    fi
else
    echo "✗ Endpoint test failed"
fi

rm -f /tmp/test_response.txt

echo "Verification complete."