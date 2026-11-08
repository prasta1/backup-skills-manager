# Communication Style & Delivery Preferences

**Consolidates:** `concise-communication-session-notes.md` (absorbed from `concise-communication`), `morning-brief-delivery.md` (delivery patterns). General class-level principles are also captured in `status-reporting-best-practices.md`.

## User Preference Notes

- The user prefers "brief but complete" answers.
- They do not want over-explanation or forced enthusiasm.
- If they say "just give me the answer", that's a directive to reduce verbosity.
- "Prefers concise, direct responses without fluff. Dislikes verbosity and overly reactive responses. Values accuracy over agreeableness. Prefers 'for once and for all' solutions over incremental fixes."
- The user expects the final result or answer to be delivered directly. No meta-commentary or process description is needed unless explicitly requested.
- Strong preference for direct command-line solutions over process descriptions — "just give me the bash command" rather than explanations of why it works.

## Session Observations

In a session, the user explicitly corrected framing in a cover letter for a technical support role at Temporal. The session demonstrated:

1. Direct alignment between job requirements and personal experience
2. Technical role framing over business/CS spin ("technical support leader" vs "customer success growth")
3. Concrete mapping of job requirements to specific experience points
4. Concise, factual presentation over fluff or forced enthusiasm

The user corrected the original letter to shift from "Head of Global Customer Success" to "technical support leader", replacing expansion/QBR language with "operating system" and "support systems", and shifting from CS growth framing to technical support systems building.

This pattern reinforces a clear preference for:
- Avoiding spin that makes content sound generic
- Focusing on technical requirements matching personal experience
- Using direct, concrete framing over business/CS expansion language

## Profile Collapse Preference

The user explicitly requested a collapse from a multi-profile setup to a single `default` profile to eliminate duplication and maintain "machine hygiene." They preferred a "for once and for all" solution over incremental fixes. This establishes a hard preference for a consolidated, non-redundant configuration and memory structure.

## Delivery Patterns

The user prefers direct, terminal-oriented delivery with explicit status confirmation:

### Python over curl for webhook delivery
Python scripts with proper error handling and logging are preferred.

```python
import urllib.request, json

WH = 'https://discord.com/api/webhooks/1234567890/abcdef'
payload = json.dumps({'content': 'Morning Brief'})
req = urllib.request.Request(WH, data=payload.encode('utf-8'), headers={'Content-Type': 'application/json'})
resp = urllib.request.urlopen(req)
print(f'Status: {resp.status}')
```

### curl-based verification pattern
```bash
curl -s -o /dev/null -w "Status: %{http_code}" \
  "https://discord.com/api/webhooks/1234567890/abcdef" \
  -H "Content-Type: application/json" \
  -d '{"content":"test"}'
```

### Key rules
- Explicit status checks required — prefer HTTP 204 confirmation over silent success
- No silent failures or unreliable delivery methods

## General Principles (class-level)

1. Lead with the answer or action; provide reasoning only if asked or essential for correctness.
2. Avoid filler phrases like "I think", "just to let you know", "please note".
3. Use bullet points or tables for structured data; avoid long paragraphs.
4. If user expresses frustration with verbosity, immediately shorten subsequent replies.
5. Honor user's preferred tone: direct, minimal pleasantries, no forced enthusiasm.
6. When automating updates (e.g. cron jobs), ensure all messages are concise and high-signal.
