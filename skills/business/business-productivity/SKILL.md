---
name: business-productivity

description: "Productivity platform APIs and sales intelligence tools."
version: 1.0.0
author: Hermes Curator
license: MIT
tags: [productivity, linear, notion, teams, powerpoint, sales, prospecting, market-research, lead-generation]
metadata:
  hermes:
    tags: [productivity, linear, notion, teams, powerpoint, sales, prospecting, market-research, lead-generation]
---

# Business Productivity & Intelligence

This umbrella consolidates API/CLI integrations for productivity platforms (Linear, Notion, Teams, PowerPoint) and sales intelligence workflows (prospecting, qualification, market research, lead management).

Consolidates the former `productivity-platforms` and `sales-intelligence` skills.

## When to Use

- "Update Linear issue ENG-42 to done" → **Linear**
- "Create a Notion page from this markdown" → **Notion**
- "Summarize yesterday's Teams meeting" → **Teams Meeting Pipeline**
- "Create a PowerPoint deck from this outline" → **PowerPoint**
- "Find prospects matching our ICP" → **Sales Prospecting**
- "Research this company" → **Company Research**
- "Score leads against our ideal customer profile" → **Lead Qualification**

## Common Setup

All integrations require API keys in `${HERMES_HOME:-~/.hermes}/.env`.

## Productivity Platforms

### Linear

- Endpoint: https://api.linear.app/graphql (POST)
- Auth: raw API key (no Bearer prefix)
- Python helper: `scripts/linear_api.py`

### Notion

- ntn CLI: shorter syntax, macOS + Linux only
- HTTP + curl: works everywhere
- Notion-Version 2025-09-03 required

### Teams Meeting Pipeline

- Prerequisites: `MSGRAPH_TENANT_ID`, `MSGRAPH_CLIENT_ID`, `MSGRAPH_CLIENT_SECRET`
- Command: `hermes teams-pipeline`
- Graph subscriptions expire in 72 hours — must be renewed

### PowerPoint

- `pip install markitdown[pptx] Pillow defusedxml lxml`
- `brew install libreoffice poppler`
- `npm install pptxgenjs`

## Sales Intelligence

Covers account prioritization, lead qualification, company research, market analysis, data normalization, outreach brief generation, and prospecting agent patterns.

## Cron Jobs

This skill powers the "Brief - Evening" cron job via `scripts/linear_api.py`.

## References

- `references/linear.md` — Linear GraphQL reference
- `references/notion-block-types.md` — Notion block reference
- `references/powerpoint-editing.md` — PowerPoint editing workflow
- `references/powerpoint-pptxgenjs.md` — pptxgenjs tutorial
- `references/sales-intelligence-framework.md` — Sales intelligence framework
- `references/cuan.md` — Cuan prospecting agent spec
- `references/lorg.md` — Lorg job-hunting agent spec
- `references/vega.md` — Vega prospecting agent spec
- `references/company-target-list.md` — Company target list builder
- `references/market-research.md` — Market research dataset analysis
- `references/b2b-lead-qualification.md` — Lead qualification against ICP

## Scripts

- `scripts/linear_api.py` — Zero-dependency Linear GraphQL CLI (cron)

## Assets

- `assets/powerpoint-LICENSE.txt` — PowerPoint skill license