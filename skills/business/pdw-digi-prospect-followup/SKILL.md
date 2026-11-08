---
name: pdw-digi-prospect-followup
description: Follow-up email drafts for local VT business prospects.
license: MIT
metadata:
  author: prasta1
  version: "1.0"
  category: lead-generation
---

# PDW Digital Prospect Follow-Up

## Purpose

Generate follow-up email drafts for local Vermont business prospects after the initial outreach was sent. Produces sequences that re-engage without being pushy, using new angles or triggers.

## When to use this skill

- After the first outreach email was sent and no response received
- When you want to follow up within the 7-14 day window
- When something new has happened at the prospect's business (new review, social post, competitor activity)
- When you need a gentle nudge before going dark

## When not to use this skill

- Less than 4 days since the initial outreach
- The prospect explicitly asked to be removed from future outreach
- The business is no longer relevant or has been disqualified
- For job-search outreach

## Required inputs

- Business name
- Prospect contact name (if discovered)
- Email address used for initial outreach
- Days since initial outreach sent
- Current research context (new review, social post, etc.) — optional but recommended

## Follow-up cadence

1. **Follow-up #1:** 4-5 days after initial outreach (gentle nudge on the original offer)
2. **Follow-up #2:** 7-10 days after follow-up #1 (new angle + urgency)
3. **Follow-up #3:** 2-3 weeks after follow-up #2 (park and revisit; lowest pressure)

## Follow-up templates

### Follow-up #1 (Gentle Nudge)

```
Subject: Re: [original subject] — quick follow-up

[Contact name],

Just circling back on my note from a few days ago about [specific topic]. I know you're busy
running [business type] — I'm just looking for 10 minutes to show you [the mockup / my
suggestions]. Happy to do it over the phone if that's easier.

No pressure at all. If now isn't the right time, just say the word.

Patrick
```

### Follow-up #2 (New Angle)

```
Subject: [New observation / something different]

[Contact name],

I just noticed [something new — a new review, a competitor's site update, a seasonal opportunity].
Made me think of [Business Name] and that [mockup / suggestions] I put together.

[Specific hook tied to the new observation]

Still happy to share it whenever you're ready.

Patrick
```

### Follow-up #3 (Park & Revise)

```
Subject: Checking in

[Contact name],

One last try on this. [Business Name] has [acknowledge something positive — new review, busy season, etc.].
I've got the [mockup / suggestions] ready and I'd love to get your eyes on it.

If now isn't the right time, just let me know — I'll check back in a couple months.

Either way, keep up the great work.

Patrick
```

## Rules

1. Never send more than 3 touches per outreach cycle.
2. Each follow-up must introduce a new element (angle, observation, or value add).
3. Always acknowledge their business positively — even on the final touch.
4. Reference the original outreach date in tracking, not in the email body.
5. Wait for explicit "not interested" before suppressing — never assume.

## Process

1. Confirm days since initial outreach (≥4 days).
2. Determine the follow-up number (1st, 2nd, or 3rd).
3. Check for any new public activity at the business (new reviews, social posts).
4. If there's new activity, use Follow-up #2 template (new angle).
5. If no new activity, use the next sequential template.
6. Keep each follow-up under 100 words (body only).
7. Always close with low-pressure CTA — never a demand.

## Tracking convention

Save follow-up drafts to `Digital/outreach-drafts/` with naming:
`YYYY-MM-DD-[slug]-followup-N.md` (where N is 1, 2, or 3)

Include a tracking note:
`- **Follow-up #N** — [Days since initial outreach] days after initial send on [date]`
