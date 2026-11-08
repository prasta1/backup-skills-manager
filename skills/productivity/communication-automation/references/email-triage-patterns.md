# Email Triage Patterns (absorbed from email-triage-agent)

## Workflow

1. **Scope** — set account, folders, time window, max threads to bound the queue
2. **Retrieve** — fetch complete threads (earlier unanswered questions live upthread)
3. **Classify** — urgent-reply, reply, action (no reply), waiting, reference, noise
4. **Draft** — reply in thread context, answer every question, preserve tone, state uncertainty
5. **Stage** — no send/delete/archive without explicit approval
6. **Verify** — read back from provider to confirm delivery

## Staged Draft Approval Pattern

- Drafts saved as TOML files with `approved = false` flag
- A send-gate script is the ONLY thing that sends — deterministic, no LLM
- Approval flow: `approve <file>` sets `approved = true`, then `send` dispatches only approved drafts

## Pitfalls

- Treating unread as important
- Missing earlier unanswered questions in long threads
- Retrying after SMTP succeeded but save-to-Sent failed (causes duplicate mail)
- Gmail IMAP sometimes doesn't expose `\Unseen` flag — fall back to "not Seen"
