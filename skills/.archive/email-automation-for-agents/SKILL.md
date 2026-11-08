---
name: email-automation-for-agents
description: "Email automation for AI agents and inbox triage."
author: Hermes Curator
version: 1.1.0
license: MIT
tags: [email, agentmail, himalaya, imap, smtp, automation]
metadata:
  hermes:
    tags: [email, agentmail, himalaya, imap, smtp, automation, inbox-triage]
---

# Email Automation for AI Agents

## Overview
This umbrella covers giving AI agents their own email inboxes (AgentMail), reading the user's personal email via terminal clients (Himalaya), and systematic inbox triage. It consolidates the email cluster of skills.

## Skill Inventory

| Skill | Purpose | Status |
|---|---|---|
| `agentmail` (absorbed) | AgentMail SDK reference — inboxes, messages, threads, attachments, drafts, pods, WebSockets, webhooks, error handling (TypeScript + Python examples) | absorbed |
| `himalaya` | IMAP/SMTP terminal email client | connector (absorbed) |
| `email-inbox-triage` | Thread-aware inbox prioritization and reply drafting | workflow (absorbed) |
| `email-for-ai-agents` | Comprehensive email automation guide | absorbed |
| `himalaya-gmail-setup` | Himalaya Gmail config with App Password support | absorbed |
| `agentmail-cli` | AgentMail CLI for programmatic email | absorbed |
| `agentmail-mcp` | AgentMail MCP server for AI assistants | absorbed |
| `agentmail-toolkit` | AgentMail integration with TypeScript/Python frameworks | absorbed |

## Quick Start

### Agent-owned email (AgentMail)
Use AgentMail when you need the agent to have its own email address to send/receive emails autonomously. This is NOT for reading the user's personal email.

**Setup:**
1. Sign up at https://console.agentmail.to (free tier: 3 inboxes, 3,000 emails/month)
2. Install: npm install agentmail (Node) or pip install agentmail (Python)
3. The MCP server provides tool access — requires Node.js 18+

### Personal email (Himalaya)
Use Himalaya when you need to read the user's personal email via terminal.

**Gmail setup:**
1. Generate an App Password in Google Account settings
2. Configure with the template: templates/gmail-configuration.toml
3. Alias Gmail's non-standard folders ([Gmail]/Sent Mail -> Sent, etc.)

## Workflows

### Inbox Triage Workflow (absorbed from email-inbox-triage)
Turn a mailbox into a bounded queue of decisions. This owns thread-aware prioritization and reply policy.

**Procedure:**
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
- Claiming inbox zero when pagination or folders were omitted

### Himalaya CLI Reference (absorbed from himalaya)
Himalaya is a CLI email client that lets you manage emails from the terminal using IMAP, SMTP, Notmuch, or Sendmail backends. Configuration file at ~/.config/himalaya/config.toml. Use `himalaya envelope list`, `himalaya message read`, `himalaya template send` (pipe stdin for non-interactive sending). Folder aliases use `folder.aliases.X` (plural) syntax in v1.2.0+. See `references/configuration.md` and `references/message-composition.md`.

**Installation:**
- macOS: `brew install himalaya`
- Linux: `curl -sSL https://raw.githubusercontent.com/pimalaya/himalaya/master/install.sh | PREFIX=~/.local sh`
- Or via cargo: `cargo install himalaya --locked`

## References
- `references/gmail-configuration.md` — Gmail App Password setup
- `references/agent-email-patterns.md` — architecture patterns
- `references/email-for-ai-agents.md` — comprehensive guide
- `references/email-inbox-triage.md` — full triage workflow from email-inbox-triage skill
- `references/configuration.md` — Himalaya config file setup + IMAP/SMTP authentication
- `references/message-composition.md` — MML syntax for composing emails
- `references/himalaya-gmail-setup.md` — Himalaya Gmail setup guide (absorbed)
- `references/agentmail-cli.md` — AgentMail CLI reference (absorbed)
- `references/agentmail-mcp.md` — AgentMail MCP server setup (absorbed)
- `references/agentmail-toolkit.md` — AgentMail framework integration (absorbed)
- `references/agentmail-webhooks.md` — AgentMail webhook API reference (absorbed from agentmail skill)
- `references/agentmail-websockets.md` — AgentMail real-time WebSocket notifications (absorbed from agentmail skill)

## Templates
- `templates/gmail-configuration.toml` — Himalaya Gmail config template
