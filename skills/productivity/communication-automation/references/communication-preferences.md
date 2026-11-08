# Communication Preferences & Status Reporting

**Consolidates:** User communication style preferences, delivery patterns, and status reporting best practices.

## User Preference Notes

- Prefers "brief but complete" answers
- No over-explanation or forced enthusiasm
- Dislikes verbosity and overly reactive responses
- Values accuracy over agreeableness
- Prefers 'for once and for all' solutions over incremental fixes
- Prefers direct command-line solutions over process descriptions
- For webhook delivery: Python scripts with explicit status checks
- Webhook delivery must return HTTP 204 confirmation

## Status Report Structure

```
🌅 [TITLE] — [DATE]

**Status:** [Brief summary of what's working and what's not configured]

• **Date:** [Formatted date]
• **System:** [Current system context]
• **To fix:** [Action items to resolve gaps]
• **Recent context:** [Brief summary of recent work]

---

_This is an automated status report. Configure missing integrations for enriched reports._
```

## Delivery Patterns

### Python webhook delivery (preferred)

```python
import urllib.request, json

WH = 'https://discord.com/api/webhooks/1234567890/abcdef'
payload = json.dumps({'content': 'Status Brief'})
req = urllib.request.Request(WH, data=payload.encode('utf-8'), headers={'Content-Type': 'application/json'})
resp = urllib.request.urlopen(req)
print(f'Status: {resp.status}')
```

### curl verification

```bash
curl -s -o /dev/null -w "Status: %{http_code}" \
  "https://discord.com/api/webhooks/1234567890/abcdef" \
  -H "Content-Type: application/json" \
  -d '{"content":"test"}'
```

## Best Practices

- Signal over noise: focus on what matters
- Graceful degradation: acknowledge missing integrations clearly
- Distinguish "nothing configured" from "nothing to do"
- Use session_search for recent context enrichment
- Report watchdog script drift as config gaps, not service outages
