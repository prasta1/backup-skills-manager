# Webhook Delivery Troubleshooting

## Common Failure Modes

- **401/403**: Invalid webhook URL or expired token
- **404**: Webhook URL not found (deleted or changed)
- **429**: Rate limited — add delay between requests
- **5xx**: Server-side error — retry with backoff
- **Network timeout**: Check connectivity, increase timeout

## Delivery Verification

Always verify delivery by checking the response status code. A 204 (No Content) from Discord/Slack webhooks confirms successful delivery.

## Python delivery (preferred)

```python
import urllib.request, json
WH = 'https://discord.com/api/webhooks/1234567890/abcdef'
payload = json.dumps({'content': 'Brief'})
req = urllib.request.Request(WH, data=payload.encode('utf-8'), headers={'Content-Type': 'application/json'})
resp = urllib.request.urlopen(req)
print(f'Status: {resp.status}')
```

## curl verification

```bash
curl -s -o /dev/null -w "Status: %{http_code}" \
  "https://discord.com/api/webhooks/1234567890/abcdef" \
  -H "Content-Type: application/json" \
  -d '{"content":"test"}'
```
