#!/bin/bash
# WebUI Model Picker Debug Script

echo "=== Hermes WebUI Model Picker Debug ==="

# Check if WebUI is running
if ! pgrep -f "hermes.*webui\|WebUI" > /dev/null; then
    echo "⚠️  WebUI is not currently running"
    exit 1
fi

# Test OpenRouter API connectivity
echo "Testing OpenRouter API connectivity..."
curl -s --max-time 8 https://openrouter.ai/api/v1/models | head -c 50 > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "✅ OpenRouter API is reachable"
else
    echo "❌ OpenRouter API is NOT reachable (network or DNS issue)"
fi

# Check WebUI logs for free-tier fetch errors
echo "Checking WebUI logs for free-tier fetch errors..."
if grep -q "free-tier live fetch unavailable" ~/.hermes/webui.log; then
    echo "⚠️  Free-tier fetch failed - falling back to static models"
    echo "   This indicates network issues or API access problems"
fi

# Show current model count (if auth available)
echo "Checking model endpoint..."
curl -s -H "Authorization: Bearer $(cat ~/.hermes/.webui_password 2>/dev/null || echo 'unknown')" http://127.0.0.1:8787/api/models 2>/dev/null | grep -c '"id"' 2>/dev/null || echo "Cannot fetch model count (auth required)"