# Agent Email Patterns

## Overview

AgentMail provides agent-owned email inboxes. Himalaya provides access to the user's personal email. Both can be used within communication automation workflows.

## AgentMail

### Setup
1. Sign up at https://console.agentmail.to
2. Install: `pip install agentmail` or `npm install agentmail`
3. The MCP server provides tool access — requires Node.js 18+

### Use Cases
- Agent needs its own email address to send/receive emails autonomously
- NOT for reading the user's personal email

### Architecture Patterns

1. **Agent inbox per task**: Create a throwaway inbox for each autonomous workflow
2. **Persistent agent inbox**: Long-lived inbox for ongoing agent operations
3. **Thread-based processing**: Process email threads with context preservation

Free tier: 3 inboxes, 3,000 emails/month.

## Himalaya

### Gmail Setup
1. Generate an App Password in Google Account settings
2. Configure with the template: `templates/gmail-configuration.toml`
3. Alias Gmail's non-standard folders ([Gmail]/Sent Mail -> Sent, etc.)

Installation:
- macOS: `brew install himalaya`
- Linux: `curl -sSL https://raw.githubusercontent.com/pimalaya/himalaya/master/install.sh | PREFIX=~/.local sh`

Configuration at `~/.config/himalaya/config.toml`.
Folder aliases use `folder.aliases.X` (plural) syntax in v1.2.0+.

Use `himalaya envelope list`, `himalaya message read`, `himalaya template send` (pipe stdin for non-interactive sending).

## Inbox Triage

Turns a mailbox into a bounded queue of decisions. Thread-aware prioritization and reply policy.

**Procedure:**
1. Set inbox scope — account, folders, time window, max threads
2. Retrieve complete threads (earlier unanswered questions live upthread)
3. Classify each thread: urgent reply, reply, action without reply, waiting, reference, noise
4. Draft replies in thread context — answer every question, preserve tone, state uncertainty
5. Present approval batch — no send/delete/archive without approval
6. Apply and verify — read back from provider to confirm

**Full reference:** `references/triage-implementation-patterns.md`

## Delivery Patterns

**Python over curl preferred** for webhook delivery with explicit status checks.

```python
import urllib.request, json
WH = 'https://discord.com/api/webhooks/1234567890/abcdef'
payload = json.dumps({'content': 'Brief'})
req = urllib.request.Request(WH, data=payload.encode('utf-8'), headers={'Content-Type': 'application/json'})
resp = urllib.request.urlopen(req)
print(f'Status: {resp.status}')
```

**Key rule:** Webhook delivery must return success status (HTTP 204). No silent failures.

**Full reference:** `references/communication-preferences.md`