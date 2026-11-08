# Morning Brief Examples

## Example 1: No Integrations
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

## Example 2: Partial Integration  
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

## Example 3: Full Integration
```
🌅 **Morning Brief — Wednesday, July 15, 2026**

**Status:** Full integration with Google Calendar and Linear API. Today's events and tasks are included.

• **Date:** Wednesday, July 15, 2026 — Day 15 of July
• **Calendar Events:** 
  - Team Standup (9:00 AM - 10:00 AM)
  - Product Review (2:00 PM - 3:00 PM)
• **Tasks:** 
  - Complete dashboard UI design (Priority: High)
  - Update documentation for API v3 (Priority: Medium)
• **Recent context:** Last seen working on customer account management (HubSpot CRM import), Hermes config triage, and MoA preset tuning

---

_This is an automated morning brief. Configure Google Calendar + Linear for enriched daily summaries._
```