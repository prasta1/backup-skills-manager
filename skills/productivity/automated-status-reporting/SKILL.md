---
name: automated-status-reporting
description: "Generate and deliver system status briefs."
version: 1.0.0
author: Hermes Curator
license: MIT
tags: [status-reporting, automation, system-monitoring, webhook-delivery, infrastructure-health, delta-reports]
metadata:
  hermes:
    tags: [status-reporting, automation, system-monitoring, webhook-delivery, infrastructure-health, delta-reports]
---

# Automated Status Reporting

Generate and deliver concise, actionable status reports for system health and daily priorities to external services (Discord, Slack, email, terminal). Consolidates the former `morning-brief-generation` skill.

## When to Use

- "Send me a morning status brief to Slack"
- "What's the system health today?"
- "Check if any cron jobs failed"
- "Compare current state to morning brief"
- "Probe embedding pipeline and LM Studio endpoints"

## Core Pattern for Status Reporting

### 1. Configuration Detection

- Check what integrations are available (Google Calendar, Linear, etc.)
- If services aren't configured, note that in the report but don't fail
- Handle partial configuration gracefully

### 2. Context Enrichment (before writing)

- Use `session_search` to find the user's recent active topics
- Query memory for job search, project names, recurring themes
- Synthesize 1-2 lines of actual recent context
- If the user has been working on the same topic for multiple days, note the continuity

### 3. Content Structure

```
🌅 [TITLE] — [DATE]

[STATUS: Brief summary of what's working and what's not configured]

• **Date:** [Formatted date]
• **System:** [Current system context]
• **To fix:** [Action items to resolve gaps]
• **Recent context:** [Brief summary of recent work]

---

_This is an automated status report. Configure missing integrations for enriched reports._
```

### 4. Infrastructure Health Probe (optional enrichment)

Probe ambient services for issues the user should know about:

- **Embedding pipeline**: Verify the endpoint responds. Check whether the watchdog script still points at the current routing.
- **Cron job health**: Scan for `error` or `failed` jobs, especially delivery-enabled ones.
- **Watchdog script drift**: Hardcoded URLs, model names, and port numbers are fragile.

### 5. Delivery Patterns

- **Webhooks**: JSON payload to Slack/Discord webhooks with markdown formatting
- **Email**: Python's `smtplib` or terminal mail command
- **Terminal**: Display directly as formatted text

Webhook delivery must return success status (HTTP 204) — no silent failures.

### 6. Handling Different Scenarios

- **Complete integration**: Full status with events and tasks
- **Partial integration**: Show what's working, note what's missing
- **No integration**: Clear explanation that no data sources are available
- **Watchdog script in error but service healthy**: Note stale config, not a service outage

### User Preference Notes

The user prefers brief but complete answers without forced enthusiasm. Direct command-line solutions, explicit delivery confirmation, and "for once and for all" solutions over incremental fixes.

**Full consolidated reference:** `references/communication-preferences.md`

## Delta / Check-In Reports

Some status reports are **deltas** — follow-up pulses that compare against a prior report and report only what changed.

**Pattern:** Read baseline → re-check same sources → report only changes → flag unavailable sources clearly.

Reference: `references/delta-status-checking.md` (absorbed from `morning-brief-generation`)

## Infrastructure Health Probes

**Embedding pipeline:**
```bash
curl -sf -m 8 -H 'Content-Type: application/json' \
  -d '{"model":"Qwen3-Embedding-4B-GGUF","input":"ping"}' \
  http://127.0.0.1:1234/v1/embeddings 2>&1 | head -c 400
```

**LM Studio / llama.cpp:**
```bash
curl -sf -m 6 http://100.89.133.43:1234/v1/models 2>&1 | head -c 200
```

**Cron job health:**
```bash
hermes cron list
```

**Port inventory:**
```bash
bash ~/.hermes/scripts/port-inventory.sh
```

Reference: `references/infrastructure-probes.md` (absorbed from `morning-brief-generation`)

## LLM Digest Repo Manager

```bash
python3 ~/.hermes/scripts/llm_digest.py --add-repo org/repo
python3 ~/.hermes/scripts/llm_digest.py --remove-repo org/repo
python3 ~/.hermes/scripts/llm_digest.py --list-repos
```

Reference: `references/llm-digest-repo-manager.md` (absorbed from `morning-brief-generation`)

## Webhook Delivery

**Python (preferred for error handling):**

```python
import urllib.request, json

WH = 'https://discord.com/api/webhooks/1234567890/abcdef'
payload = json.dumps({'content': 'Status Brief'})
req = urllib.request.Request(WH, data=payload.encode('utf-8'), headers={'Content-Type': 'application/json'})
resp = urllib.request.urlopen(req)
print(f'Status: {resp.status}')
```

**curl verification:**
```bash
curl -s -o /dev/null -w "Status: %{http_code}" \
  "https://discord.com/api/webhooks/1234567890/abcdef" \
  -H "Content-Type: application/json" \
  -d '{"content":"test"}'
```

## References

- `references/communication-preferences.md` — User communication style, delivery patterns, preference notes
- `references/status-reporting-best-practices.md` — Best practices for system status reporting and tone
- `references/webhook-delivery-troubleshooting.md` — Webhook delivery patterns and troubleshooting
- `references/delta-status-checking.md` — Delta/check-in status reports
- `references/infrastructure-probes.md` — Probe commands for embedding pipelines, LM Studio, cron health
- `references/llm-digest-repo-manager.md` — Manage GitHub repo list for daily LLM digest cron job
- `references/morning-brief-examples.md` — Example status reports for various integration states
