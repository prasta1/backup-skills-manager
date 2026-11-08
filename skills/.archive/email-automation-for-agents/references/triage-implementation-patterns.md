# Email Triage Implementation Patterns

**Consolidates:** `email-triage-agent` approach (local LLM triage) with the `email-inbox-triage` workflow already in this umbrella.

## Two Triage Approaches

### 1. Local LLM Triage (email-triage-agent pattern)

Use when the user wants AI-powered classification and drafting without cloud LLM calls.

**Setup:**
- Himalaya v2 installed (`brew install himalaya`)
- Gmail App Password in `~/.hermes/.env` as `GMAIL_APP_PASSWORD`
- Local model (e.g., `studio-devstral-24b` via llama-swap)

**Workflow:**
1. **Scan**: Himalaya lists unread envelopes, fetches full message content
2. **Classify**: Local LLM classifies each thread (urgent-reply, reply, action, waiting, reference, noise)
3. **Draft**: Local LLM drafts replies in user's voice, saves as TOML draft files
4. **Stage**: Drafts staged in `~/.hermes/email-drafts/` — NOT sent automatically
5. **Send**: Explicit approval gate — only approved drafts sent via `himalaya message send`

**Commands:**
- `/email-triage-agent run` — scan, classify, draft, stage
- `/email-triage-agent review` — list pending drafts
- `/email-triage-agent send` — send approved drafts (requires explicit approval)

**Pitfalls:**
- Gmail IMAP LIST over large mailboxes is slow — use limit flag
- Himalaya v2 doesn't expand `${VAR}` in config — use `password.command = ["sh", "-c", "echo $GMAIL_APP_PASSWORD"]`
- Large emails may truncate in model context — expected, not a bug

### 2. AgentMail Triage (this umbrella)

Use when the agent needs its own email inbox or cloud LLM is acceptable.

**Setup:**
- Sign up at https://console.agentmail.to
- Install: `pip install agentmail` or `npm install agentmail`

**Workflow:**
Uses AgentMail's WebSocket API for real-time message processing, with drafts staged for user approval.

## Key Differences

| Aspect | Local LLM | AgentMail |
|--------|-----------|-----------|
| Model | Local (offline) | Cloud LLM |
| Inbox | User's Gmail | Agent's own inbox |
| Auth | Gmail App Password | AgentMail API key |
| Cost | One-time hardware | Subscription per inbox |
| Approval | Staged drafts | Staged drafts |

## Common Pattern

Both approaches follow the same pattern: **scan → classify → draft → stage for approval → send (gated)**. The classification taxonomy is identical:

- **urgent-reply** — needs reply within 24h
- **reply** — needs reply but not urgent
- **action** — needs action but no reply
- **waiting** — waiting on sender
- **reference** — keep for reference
- **noise** — no action

The triage workflow (from `email-inbox-triage`):
1. Set inbox scope — account, folders, time window, max threads
2. Retrieve complete threads (earlier unanswered questions live upthread)
3. Classify each thread
4. Draft replies in thread context — answer every question, preserve tone, state uncertainty
5. Present approval batch — no send/delete/archive without approval
6. Apply and verify — read back from provider to confirm

**Pitfalls (shared):**
- Treating unread as important
- Missing earlier unanswered questions in long threads
- Retrying after SMTP succeeded but save-to-Sent failed (causes duplicate mail)
- Claiming inbox zero when pagination or folders were omitted
