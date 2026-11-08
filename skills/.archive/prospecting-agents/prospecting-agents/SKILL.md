---
name: prospecting-agents
description: "Prospecting agents: hunt, score, dedup, push to Notion."
author: Hermes Curator
version: 1.0.0
license: MIT
tags: [prospecting, sales, notion, icp, dedup]
metadata:
  hermes:
    tags: [prospecting, sales, notion, icp, dedup, automation]
---

# Prospecting Agents

## Overview
This umbrella consolidates the family of prospecting agent skills. Each agent follows the same pattern: hunt for prospects using web search/Firecrawl, research each company, score against an ICP (Ideal Customer Profile), dedup against a Notion database, and push qualifying entries — only when explicitly authorized.

## When to Use
- "Find prospects for Edge Impulse"
- "Hunt Vermont businesses for custom CNC work"
- "Push qualifying roles to Notion"
- "Run the prospecting agent for [company]"

## Shared Pattern

All prospecting agents follow the same 6-step procedure:

### 1. Hunt
Search for prospect signals using web search / Firecrawl:
- Job postings (embedded ML, edge AI, firmware ML, etc.)
- Funding announcements (edge AI / IoT / industrial AI, seed–Series C)
- GitHub activity (tflite, ONNX, edge inference, embedded ML keywords)
- Conference speakers/attendees (Embedded World, tinyML Summit, Edge AI Summit)
- News (companies announcing edge AI products or pilots)
- Local business search (Google Maps, Chamber of Commerce directories)

### 2. Research
For each prospect: company overview, HQ location, edge-AI use-case hypothesis, current ML approach, company size/stage, key contact (Head of Eng, CTO, VP Product) + LinkedIn URL, recent news/signals.

### 3. Score (ICP)
Apply the ICP scoring model. Only scores at the threshold go to Notion.

### 4. Dedup via Notion
Query the Notion database by company name. If exists at "Spotted" stage, update; if exists at later stage, skip; if not, create new.

### 5. Push to Notion (writes only when authorized)
Guardrails:
- "dry-run", "check", "research", "find" = read and report only. No writes.
- Scheduled run with "full procedure" = standing authorization to push new prospects
- Deletions NEVER authorized by scheduled runs
- Never update Notion entries speculatively

### 6. Report
Final response carries prospects found/pushed, top highlights, patterns, dedup counts, and blockers. Stored in Hermes run history.

## Agent Variants

### Cuan — Edge Impulse Prospecting
- **Domain:** Edge AI / embedded ML companies
- **Geographic filter:** US and Canada only
- **ICP score:** 5 Fire / 4 Star / 3 Good / 2 Weak / 1 No (only 3+ pushed)
- **Notion DB:** EI Prospecting DB
- **Durable log:** ~/.hermes/prospecting-runs.log
- See `references/cuan.md`

### Lorg — Job Hunting
- **Domain:** CS & Post-Sales Leadership, Operations & Strategy, Strategic Accounts
- **Location:** Remote (US) OR Burlington VT
- **No numeric score** — push iff passes every hard filter
- **Flags:** 🔥 Strong / 👍 Solid / 👀 Marginal
- **Notion DB:** Hunting Gathering DB
- See `references/lorg.md`

### Vega — Peregrine Design Werx Prospecting
- **Domain:** Vermont businesses needing custom CNC woodwork
- **Score:** 1–10 (geography, need fit, scale, reachability)
- **Only surface 5+**
- **Notion DB:** Peregrine Prospects DB
- See `references/vega.md`

## Notion API Pattern
All agents use the same Notion API pattern:
```bash
curl -s -X POST "https://api.notion.com/v1/databases/<db_id>/query" \
  -H "Authorization: Bearer $NOTION_API_KEY" \
  -H "Notion-Version: 2022-06-28" \
  -H "Content-Type: application/json" \
  -d '{"filter":{"property":"Company","title":{"equals":"<company name>"}}}'
```

## References
- `references/cuan.md` — Cuan agent spec (from edge-impulse-kws-setup)
- `references/lorg.md` — Lorg agent spec (v3.5)
- `references/vega.md` — Vega agent spec
