---
name: pdw-digi-prospect-research
description: Prospect research for outreach and site-build dossiers.
license: MIT
metadata:
  author: prasta1
  version: "1.0"
  category: lead-generation
---

# PDW Digital Prospect Research

## Purpose

Produce a general prospect dossier for a local business before outreach, follow-up, or a site conversation. This is the upstream research step for the rest of the PDW stack.

## When to use this skill

- Before cold outreach when no verified research file exists
- When refreshing prospect intel before a follow-up sequence
- When preparing for a site-build conversation with a prospect
- When the outreach skill says "do web_extract first" and there's no structured output yet

## When not to use this skill

- The business is non-local or outside the target region without local relevance
- The business explicitly asked to be removed from outreach
- For job-search outreach
- When a current research file already exists and only one field needs updating — update that field instead of regenerating everything

## Required inputs

- Business name
- Business location (city/town, state)
- Business URL if known; if not, search terms to identify the correct site

## Output

Save a markdown dossier to `Digital/prospect-research/YYYY-MM-DD-[business-slug]-research.md`.

Use this structure:

```
# [Business Name] — Prospect Research

**Date:** YYYY-MM-DD
**Status:** Draft / Complete
**Research URL:**

## Business Overview

## Online Presence

## Contact Intelligence

## Reviews & Reputation

## Local Position

## Site Observations

## Outreach Angles

## Site-Build Notes

## Follow-Up Notes

## Evidence & Sources

## Gaps & [VERIFY] Items

## Research Notes
```

## Research procedure

### 1. Identify the business

Confirm the official homepage, Google Business Profile, and primary contact page. If the business has no website, note that explicitly and use search/social results instead.

### 2. Gather business overview

Record what the business is, who it serves, hours, ownership/team if public, and any recent public activity. Label assumptions as `guessing` or `unverified`.

### 3. Map online presence

Homepage, contact page, about page, menu/services page, Google Business Profile, Instagram/Facebook/other social, review profiles. Note what's missing or weak.

### 4. Extract contact intelligence

Name, title, email, phone, contact form, preferred contact path if obvious, owner/manager names if public. If email is not found, say so and note where it should be.

### 5. Capture reviews and reputation

Pull review counts, average ratings, recent review themes, complaint themes, owner responses if any. Attribute every number to a source.

### 6. Assess local position

Competitors in the same town or nearby. What this business does differently, better, or worse. Seasonal factors. Local events or references they already use.

### 7. Record site observations

Mobile experience, speed/load behavior, booking/path to purchase, navigation clarity, content quality, visual impression, accessibility red flags, SEO basics. Tie each observation to a verified source or mark it `unverified`.

### 8. Draft outreach angles

Write 2-4 specific angles Patrick could use in outreach or follow-up, tied to verified facts from this dossier. Do not write the outreach email here — that's the outreach skill's job.

### 9. Note site-build relevance

If this business becomes a build prospect, note personality cues, palette/visual hints, photo assets, local references, and anything that would inform a proposal.

### 10. Track evidence and gaps

Every factual claim needs a source link or explicit `guessing` / `unverified` label. Maintain a `[VERIFY: what]` list for items the owner would need to confirm.

## Rules

1. Never invent facts, quotes, reviews, or observations.
2. Label guesses explicitly: `guessing`, `unverified`, or `[VERIFY: what]`.
3. Attribute numbers and quotes to sources.
4. Do not send anything — research only.
5. If research turns up almost nothing usable, say so plainly and ask what to target instead of padding the dossier.
6. Keep the dossier reusable: it should serve outreach, follow-up, and site-build without major rework.
7. Use plain markdown; no unnecessary formatting.

## Tracking convention

Save research files to `Digital/prospect-research/` with naming:
`YYYY-MM-DD-[business-slug]-research.md`

If the same business is researched again, append a dated update section instead of overwriting the original file.

## Cross-skill references

- `pdw-digi-prospect-outreach` — uses this dossier as source material
- `pdw-digi-prospect-followup` — draws new angles and triggers from updates here
- `pdw-local-business-website` — uses Site-Build Notes and personality cues from this dossier
