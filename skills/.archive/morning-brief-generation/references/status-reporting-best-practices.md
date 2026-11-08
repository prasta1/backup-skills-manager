# Status Reporting Best Practices

## General Principles
- **Conciseness is key**: The user explicitly prefers "brief but complete" answers
- **No fluff**: Avoid phrases like "just to let you know", "please note", "I hope this helps"
- **Direct communication**: If they ask for "just give me the answer", that's a directive to reduce verbosity
- **Graceful degradation**: When integrations aren't available, acknowledge that clearly rather than failing

## For System Status Reports
1. **Prioritize what matters**: Focus on the most important daily priorities, not every system status
2. **Honor user preferences**: If they've expressed frustration with verbosity, apply that now  
3. **Use structured formatting**: Bullet points for clear organization, not paragraphs
4. **Be explicit about gaps**: When services aren't configured, state that fact clearly rather than trying to work around it
5. **Include actionable steps**: If something is missing, suggest how to fix it

## Channel-Specific Considerations
### Channel-Specific Considerations
#### Slack Webhooks
- Use markdown formatting for good visual hierarchy
- Keep messages under 4000 characters to avoid truncation
- Use emojis for visual cues (🌅 for morning, ✅ for completed tasks)
- Avoid over-formatting that might break in different clients

### Terminal Output
- Use ANSI colors for visual hierarchy (when supported)
- Keep line lengths reasonable for terminal display
- Use clear section headers and bullet points

### Email Delivery
- Use HTML formatting when appropriate for rich display
- Keep subject lines concise but descriptive
- Include proper content-type headers for rendering

## Tone and Style Guidelines  
1. **No forced enthusiasm**: The user dislikes overly reactive responses
2. **No meta-commentary**: Don't explain the process of generating reports - just deliver the result
3. **Clear but brief**: When explaining missing integrations, keep it focused and to the point
4. **Consistent messaging**: If you previously mentioned a feature, don't change how you describe it in subsequent reports

## Failure Handling Patterns
1. **Missing credentials**: "Not configured - set [ENV_VAR] to enable"
2. **Service downtime**: "Service temporarily unavailable"  
3. **Rate limiting**: "Rate limit exceeded - retry in [time]"
4. **No data**: "No items found matching criteria"

## Context Enrichment
- **Use session_search proactively**: Before writing the "Recent context" section, query recent sessions for the user's active topics. This turns stale placeholder text into live, useful context.
- **Continuity signal**: If the same topic appears across multiple days, note it — the user may be mid-project and the brief should reflect that.
- **Synthesize, don't dump**: 1-2 lines of synthesized context is better than a raw session dump. Pick the most relevant work thread from the last 24-48 hours.
- **When sessions are empty**: If session_search returns nothing relevant, omit the "Recent context" section entirely rather than filling it with placeholder text.

## Template for Status Reports
```
🌅 [TITLE] — [DATE]

**Status:** [Brief summary of what's working and what's not configured]

• **Date:** [Formatted date]
• **System:** [Current system context] 
• **To fix:** [Action items to resolve gaps]
• **Recent context:** [Brief summary of recent work]

---

_This is an automated [type] report. Configure [service] for enriched [functionality]._
```