---
name: company-target-list
description: "Build a prioritized company list for job searches."
version: 1.0.0
author: patrick
tags: [job-search, prospecting, research]
---

# Company Target List Builder

## Purpose
Research and compile a prioritized list of companies for a job search into a durable markdown file. Surface hiring signal, fit assessment, and outreach strategy. Save to ~/.hermes/lists/ for later reference.

## Trigger
User asks to build or update a company list for job searching, prospecting, or outreach. Examples: "Pull me companies in X space I should apply to", "Build a target list for Y roles".

## Steps
1. Clarify scope — What role title(s)? What industry/space? What stage (Seed–C)? What location/remote preference? What comp floor? Ask if not stated.
2. Research — Run 3–5 parallel web searches covering funding data, job boards, and company directories. Use web_search in parallel for funding/company lists, job board listings, and company career pages.
3. Filter & tier — Sort into tiers: Tier 1 (active hiring, strong fit), Tier 2 (good fit, no CS listing yet), Tier 3 (broader fit).
4. Write file — Save to ~/.hermes/lists/<search-topic>-targets.md with header, each company entry (name, what they do, stage, funding, hiring signal, URLs), application strategy notes at the bottom, sources cited.
5. Proactive next step — After saving, ask about detailed job specs or outreach list.

## Conventions
- File naming: ~/.hermes/lists/<slug>-targets.md
- Format: Markdown with headers, bullet points for details, blockquotes for URLs
- Always include hiring signal and comp floor check ($200K+ for Patrick)
- Tiers are the organizing principle — dont dump a flat list