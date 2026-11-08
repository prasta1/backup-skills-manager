# Webhook Delivery Troubleshooting

## Delivery Patterns

The user prefers Python scripts with explicit status checks over curl-based approaches for webhook delivery.

### Python-based (preferred)

```python
import urllib.request, json

WH = 'https://discord.com/api/webhooks/1234567890/abcdef'
payload = json.dumps({'content': 'Morning Brief'})
req = urllib.request.Request(WH, data=payload.encode('utf-8'), headers={'Content-Type': 'application/json'})
resp = urllib.request.urlopen(req)
print(f'Status: {resp.status}')
```

### curl-based verification

```bash
curl -s -o /dev/null -w "Status: %{http_code}" \
  "https://discord.com/api/webhooks/1234567890/abcdef" \
  -H "Content-Type: application/json" \
  -d '{"content":"test"}'
```

### Key rules

- Webhook delivery must return success status (e.g., HTTP 204) to confirm delivery
- No silent failures or unreliable delivery methods
- Use explicit status checks — prefer HTTP 204 confirmation over silent success

## Common Failure Modes

- **401/403**: Invalid webhook URL or expired token
- **404**: Webhook URL not found (deleted or changed)
- **429**: Rate limited — add delay between requests
- **5xx**: Server-side error — retry with backoff
- **Network timeout**: Check connectivity, increase timeout

## Delivery Verification

Always verify delivery by checking the response status code. A 204 (No Content) from Discord/Slack webhooks confirms successful delivery. Anything else requires investigation.