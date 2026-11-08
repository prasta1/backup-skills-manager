---
name: communication-automation
description: "Automated email, messaging, and status delivery."
version: 1.0.0
author: Hermes Curator
license: MIT
tags: [email, messaging, status-reports, webhook-delivery, automation, inbox-triage]
metadata:
  hermes:
    tags: [email, messaging, status-reports, webhook-delivery, automation, inbox-triage]
---

# Communication Automation

This umbrella covers automated communication workflows: agent-owned email management (AgentMail), personal email via terminal clients (Himalaya), inbox triage, and status report delivery to external services (Slack, Discord, email, terminal).

Consolidates the former `email-automation-for-agents` and `automated-status-reporting` skills.

## When to Use

- "Agent needs its own email inbox to send/receive emails autonomously"
- "Read the user's personal email via terminal"
- "Triage my inbox: classify threads and draft replies"

## Agent-Owned Email (AgentMail)

Use AgentMail when the agent needs its own email address.

**Setup:**
1. Sign up at https://console.agentmail.to
2. Install: `pip install agentmail` or `npm install agentmail`

**Reference:** `references/agent-email-patterns.md`, `references/agentmail-mcp.md`, `references/agentmail-cli.md`, `references/agentmail-toolkit.md`, `references/agentmail-webhooks.md`, `references/agentmail-websockets.md`

## Personal Email (Himalaya)

Use Himalaya when reading the user's personal email via terminal.

**Gmail setup:**
1. Generate an App Password in Google Account settings
2. Configure with `templates/gmail-configuration.toml`
3. Alias Gmail's non-standard folders

**Reference:** `references/configuration.md`, `references/message-composition.md`, `references/himalaya-gmail-setup.md`

## Inbox Triage Workflow (absorbed from email-inbox-triage)

Turn a mailbox into a bounded queue of decisions:

1. Set inbox scope — account, folders, time window, max threads
2. Retrieve complete threads (earlier unanswered questions live upthread)
3. Classify each thread: urgent reply, reply, action without reply, waiting, reference, noise
4. Draft replies in thread context — answer every question, preserve tone, state uncertainty
5. Present approval batch — no send/delete/archive without approval
6. Apply and verify — read back from provider to confirm

**Pitfalls:**
- Treating unread as important
- Missing earlier unanswered questions in long threads
- Retrying after SMTP succeeded but save-to-Sent failed (causes duplicate mail)

**Reference:** `references/triage-implementation-patterns.md` for both local LLM and AgentMail triage approaches

## Status Report Delivery

Generate and deliver concise status reports to external services.

**Reference:** `references/status-reporting-best-practices.md`, `references/communication-preferences.md`, `references/webhook-delivery-troubleshooting.md`, `references/delta-status-checking.md`, `references/infrastructure-probes.md`

## Templates

- `templates/gmail-configuration.toml` — Himalaya Gmail config template

## References

- `references/agent-email-patterns.md` — Architecture patterns for agent email
- `references/email-for-ai-agents.md` — Comprehensive guide to agent email infrastructure
- `references/email-inbox-triage.md` — Full triage workflow
- `references/configuration.md` — Himalaya config + IMAP/SMTP auth
- `references/message-composition.md` — MML syntax for composing emails
- `references/himalaya-gmail-setup.md` — Gmail setup guide
- `references/agentmail-cli.md` — AgentMail CLI reference
- `references/agentmail-mcp.md` — AgentMail MCP server setup
- `references/agentmail-toolkit.md` — AgentMail framework integration
- `references/agentmail-webhooks.md` — AgentMail webhook API
- `references/agentmail-websockets.md` — AgentMail WebSocket notifications
- `references/triage-implementation-patterns.md` — Local LLM vs AgentMail triage comparison
- `references/status-reporting-best-practices.md` — Status report tone and structure
- `references/communication-preferences.md` — User communication style preferences
- `references/webhook-delivery-troubleshooting.md` — Webhook delivery patterns
- `references/delta-status-checking.md` — Delta/check-in reports
- `references/infrastructure-probes.md` — Probe commands for system health
