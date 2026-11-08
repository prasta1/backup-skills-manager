---
name: morning-brief-generation
description: Generate and deliver concise system status briefs to external services like Slack
version: 0.3.0
author: Hermes Agent
tags: [status-reporting, automation, productivity, system-monitoring]
---

# Morning Brief Generation

## Purpose
Create and deliver concise, actionable status reports for system health and daily priorities to external services (Discord, Slack, email). This skill handles the full lifecycle of generating and sending status reports in a variety of formats and channels.

## Key Principles
- **Tailor to the channel**: Slack vs email vs terminal output
- **Handle missing integrations gracefully**: When services aren't configured, report that fact clearly rather than failing
- **Prioritize signal over noise**: Focus on what's important for the user's day, not all system information
- **Follow user preference**: Convey status in brief, direct format without over-explanation or forced enthusiasm

## Core Pattern for Status Reporting

### 1. Configuration Detection
When preparing a status report:
- Check what integrations are available (Google Calendar, Linear, etc.)
- If services aren't configured, note that in the report but don't fail
- Handle partial configuration (e.g., only one of Google or Linear available) gracefully

### 2. Context Enrichment (before writing)
Before composing the report, enrich the "Recent context" section with real session history:
- Use `session_search` with a query about the user's recent active topics (or browse recent sessions) to find what they were working on
- Query for the user's job search, project names, or recurring themes from memory
- Synthesize 1-2 lines of actual recent context — never use stale placeholder text
- If the user has been working on the same topic for multiple days, note the continuity

### 3. Content Structure
The report should follow this structure:
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

### 3.5 Infrastructure Health Probe (optional enrichment)

Beyond calendar and tasks, probe ambient services for issues the user should know about. Report findings as brief bullet points in the existing structure, not a separate section:

- **Embedding pipeline**: Verify the endpoint responds. Check whether the watchdog script that probes it still points at the current routing — stale URL targets are a common failure pattern when routing changes (LM Studio → llama.cpp, tanker decommissioning) but the probe scripts are not updated.
- **Cron job health**: Scan for any `error` or `failed` jobs, especially delivery-enabled ones. Report the fix direction, not just the symptom.
- **Watchdog script drift**: Hardcoded URLs, model names, and port numbers in watchdog scripts are fragile. When a probe script errors consistently, read the script to see what it's targeting — the failure may be a stale config, not a broken service.

### 4. Handling Different Scenarios
- **Complete integration**: Full status with events and tasks
- **Partial integration**: Show what's working, note what's missing  
- **No integration**: Clear explanation that no data sources are available
- **Integration present but empty**: When a task source returns data but all items are inactive (e.g., all Linear issues canceled), report the actual state — "all 25 assigned items are canceled" is more useful than "no active tasks". Distinguish between "nothing configured" and "nothing to do."
- **Watchdog script in error but service healthy**: When a watchdog probe reports failure but the underlying service responds fine, the probe script's hardcoded URL is stale. Note this in the brief as a config gap, not a service outage.

### 5. Delivery Patterns
- **Webhooks**: Send JSON payload to Slack webhooks with appropriate formatting (markdown)
- **Email**: Use Python's `smtplib` or send via terminal with mail command
- **Terminal**: Display directly as formatted text

## User Preference Notes
- The user prefers "brief but complete" answers.
- They do not want over-explanation or forced enthusiasm.
- When services aren't configured, they prefer clear acknowledgment of that fact rather than trying to work around it.
- They explicitly stated: **"Prefers concise, direct responses without fluff. Dislikes verbosity and overly reactive responses. Values accuracy over agreeableness. Prefers 'for once and for all' solutions over incremental fixes."**
- **When applying this skill in response to a user's request, the user expects the final result or answer to be delivered directly. No meta-commentary or process description is needed unless explicitly requested.**
- **User has strong preference for direct command-line solutions over process descriptions** - they prefer "just give me the bash command" rather than explanations of why it works.
- **For webhook delivery, they prefer Python scripts with explicit status checks over curl-based approaches** to ensure proper error handling and logging.
- **Webhook delivery must return success status (e.g., HTTP 204) to confirm delivery** - they do not want silent failures or unreliable delivery.

## Examples

### Example 1: No Integrations
```
🌅 **Morning Brief — Wednesday, July 15, 2026**

**Status:** Calendar and task sources are not configured in this profile — no Google Calendar token or Linear API key found. Morning brief data is limited as a result.

• **Date:** Wednesday, July 15, 2026 — Day 15 of July
• **System:** Hermes default profile is active; work and personal profiles exist but aren't configured with calendar/task integrations
• **To fix:** Set up Google Workspace (run `gsetup --auth-url`) and/or Linear (set `LINEAR_API_KEY`) to enable full briefs
• **Recent context:** Last seen working on customer account management (HubSpot CRM import), Hermes config triage, and MoA preset tuning

---

_This is an automated morning brief. Configure Google Calendar + Linear for enriched daily summaries._
```

### Example 2: Partial Integration  
```
🌅 **Morning Brief — Wednesday, July 15, 2026**

**Status:** Google Calendar configured but Linear integration missing. Brief includes calendar events but not task list.

• **Date:** Wednesday, July 15, 2026 — Day 15 of July
• **System:** Hermes default profile with Google Calendar access, Linear not configured
• **To fix:** Set `LINEAR_API_KEY` in environment to enable task integration
• **Recent context:** Last seen working on customer account management (HubSpot CRM import), Hermes config triage, and MoA preset tuning

---

_This is an automated morning brief. Configure Linear for enriched task summaries._
```

## References
- `references/status-reporting-best-practices.md` — Best practices for system status reporting and tone consistency
- `references/morning-brief-examples.md`
- `references/morning-brief-delivery.md` — User preference notes on webhook delivery, concise format, and terminal-first status reporting (absorbed from concise-communication).
- `references/concise-communication-session-notes.md` — Session-specific user preference notes and communication style observations (absorbed from concise-communication). — Example formats and templates for various integration states
- `references/webhook-delivery-troubleshooting.md` — Slack webhook delivery patterns, HTTP status verification, and common failure modes
- `references/delta-status-checking.md` — Delta/diff-based follow-up reports (midday checks, afternoon pulses, evening wraps): compare against a prior report and report only what changed
- `references/infrastructure-probes.md` — Specific probe commands for Honcho, embedding endpoints, llama.cpp, Docker containers, and cron job health during briefs
- `references/llm-digest-repo-manager.md` — Manage the GitHub repo list for the daily LLM digest cron job (absorbed from llm-digest-repo-manager)