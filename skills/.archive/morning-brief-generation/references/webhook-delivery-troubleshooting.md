# Slack Webhook Delivery Troubleshooting

When delivering morning briefs or other system status reports via Slack webhooks, the following patterns are observed in user behavior:

## Delivery Reliability

1. **Expected Success**: HTTP 204 responses are acceptable confirmation of delivery
2. **Silent Failures Are Unwanted**: The user explicitly stated they do not want silent failures or unreliable delivery methods
3. **Explicit Status Checks**: They prefer Python scripts with checks over curl-based approaches to ensure proper error handling and logging

## Common Issues & Resolutions

### 403 Forbidden Errors
- **Root Cause**: Invalid webhook URL or token, or permissions issues
- **Solution**: Verify the webhook URL and ensure it's valid and not expired

### HTTP Status Verification
- **Method**: Use `curl -w "Status: %{http_code}"` or Python's `urllib.request` to capture the actual response code
- **Check**: Ensure status code is 204 (success) rather than a 4xx or 5xx error

### Command-Line Delivery Pattern
```bash
curl -s -o /dev/null -w "Status: %{http_code}" \
  "https://discord.com/api/webhooks/1234567890/abcdef" \
  -H "Content-Type: application/json" \
  -d '{"content":"test"}'
```

## Python Delivery Pattern
```python
import urllib.request, json

WH = 'https://hooks.slack.com/services/YOUR/WEBHOOK/URL'
payload = json.dumps({'content': 'Morning Brief'})
req = urllib.request.Request(WH, data=payload.encode('utf-8'), headers={'Content-Type': 'application/json'})
resp = urllib.request.urlopen(req)
print(f'Status: {resp.status}')
```

## Logging and Validation

The user prefers that all delivery methods return confirmation status codes (like 204) to validate success, and they do not want to receive "just the command" without a confirmation that it actually executed.