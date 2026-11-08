# Status Reporting Best Practices

## Key Principles

- **Conciseness is key**: The user prefers "brief but complete" answers
- **No fluff**: Avoid phrases like "just to let you know", "please note"
- **Direct communication**: If they ask for "just give me the answer", reduce verbosity
- **Graceful degradation**: When integrations aren't available, acknowledge clearly rather than failing
- **Signal over noise**: Focus on what's important for the user's day, not all system information
- **Follow user preference**: Brief, direct format without over-explanation or forced enthusiasm

## Content Structure

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

## Handling Different Scenarios

- **Complete integration**: Full status with events and tasks
- **Partial integration**: Show what's working, note what's missing
- **No integration**: Clear explanation that no data sources are available
- **Integration present but empty**: When a task source returns data but all items are inactive (e.g., all Linear issues canceled), report the actual state — "all 25 assigned items are canceled" is more useful than "no active tasks". Distinguish between "nothing configured" and "nothing to do."
- **Watchdog script in error but service healthy**: When a watchdog probe reports failure but the underlying service responds fine, the probe script's hardcoded URL is stale. Note this as a config gap, not a service outage.

## Channel-Specific Considerations

### Slack/Discord Webhooks
- Use markdown formatting for good visual hierarchy
- Keep messages under 4000 characters to avoid truncation
- Use emojis for visual cues (🌅 for morning, ✅ for completed tasks)
- Explicit status checks — prefer HTTP 204 confirmation over silent success

### Email Delivery
- Use HTML formatting when appropriate for rich display
- Keep subject lines concise but descriptive
- Include proper content-type headers for rendering

### Terminal Output
- Use ANSI colors for visual hierarchy (when supported)
- Keep line lengths reasonable for terminal display
- Use clear section headers and bullet points

## User Preference Notes

- Prefers "brief but complete" answers
- No forced enthusiasm or overly reactive responses
- Values accuracy over agreeableness
- Prefers 'for once and for all' solutions over incremental fixes
- Prefers direct command-line solutions over process descriptions
- Webhook delivery must return success status (HTTP 204)

## Failure Handling Patterns

1. **Missing credentials**: "Not configured - set [ENV_VAR] to enable"
2. **Service downtime**: "Service temporarily unavailable"
3. **Rate limiting**: "Rate limit exceeded - retry in [time]"
4. **No data**: "No items found matching criteria"

## Context Enrichment

- **Use session_search proactively**: Before writing the "Recent context" section, query recent sessions for the user's active topics
- **Continuity signal**: If the same topic appears across multiple days, note it — the user may be mid-project
- **Synthesize, don't dump**: 1-2 lines of synthesized context beats a raw session dump
- **When sessions are empty**: If session_search returns nothing relevant, omit the "Recent context" section entirely
