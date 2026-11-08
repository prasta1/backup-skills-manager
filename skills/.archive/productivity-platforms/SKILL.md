---
name: productivity-platforms
description: "Linear, Notion, Teams, and PowerPoint API/CLI integrations."
version: 1.0.0
author: Hermes Curator
license: MIT
tags: [productivity, linear, notion, teams, powerpoint, api-integration]
metadata:
  hermes:
    tags: [productivity, api, integrations, linear, notion, teams, powerpoint]
---

# Productivity Suite Integrations

This umbrella skill consolidates API/CLI client integrations for productivity platforms: Linear (issue tracking), Notion (docs/databases), Microsoft Teams (meeting pipeline), and PowerPoint (presentation documents). Each section below is a distinct integration — pick the one matching the request.

## Skill Inventory

| Subskill | Purpose | Status |
|---|---|---|
| linear (absorbed) | Linear issue/project management via GraphQL + Python helper | absorbed |
| notion (absorbed) | Notion API via ntn CLI or curl + block types reference | absorbed |
| teams-meeting-pipeline (absorbed) | Teams meeting summaries, Graph webhooks, CLI pipeline | absorbed |
| powerpoint (absorbed) | PowerPoint creation/editing via pptxgenjs + XML manipulation | absorbed |

## When to Use

- "Update Linear issue ENG-42 to done" -> **Linear**
- "Create a Notion page from this markdown" -> **Notion**
- "Summarize yesterday's Teams meeting" -> **Teams Meeting Pipeline**
- "Create a PowerPoint deck from this outline" -> **PowerPoint**

## Common Setup

All four integrations require:
- API keys stored in ${HERMES_HOME:-~/.hermes}/.env
- terminal tool for CLI/curl execution
- python3 for helper scripts (stdlib-only where possible)

### Credential reference

| Integration | Env var | Source |
|---|---|---|
| Linear | LINEAR_API_KEY | Linear Settings -> Account -> Security -> Personal API keys |
| Notion | NOTION_API_KEY | Notion -> My Integrations -> create integration |
| Teams | MSGRAPH_TENANT_ID, MSGRAPH_CLIENT_ID, MSGRAPH_CLIENT_SECRET | Azure AD app registration |
| PowerPoint | (none for open-source tools) | n/a |

## Linear (absorbed from `linear`)

Manage Linear issues, projects, and teams via the GraphQL API using curl, or use the bundled Python CLI for ergonomic one-liners. cron=yes — powers the "Brief - Evening" cron job.

### Setup

1. Get a personal API key from Linear Settings > Account > Security & access > Personal API keys.
2. Set LINEAR_API_KEY in ${HERMES_HOME:-~/.hermes}/.env

### API Basics

- Endpoint: https://api.linear.app/graphql (POST)
- Auth header: Authorization with the raw key (no "Bearer" prefix)
- All requests are POST with Content-Type: application/json

Base curl pattern:
```bash
curl -s -X POST https://api.linear.app/graphql \
  -H "Authorization: $LINEAR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"query": "{ viewer { id name } }"}' | python3 -m json.tool
```

### Python helper script

Use scripts/linear_api.py for zero-dependency one-liners:
```bash
python3 scripts/linear_api.py whoami
python3 scripts/linear_api.py list-teams
python3 scripts/linear_api.py get-issue ENG-42
python3 scripts/linear_api.py get-document 38359beef67c
python3 scripts/linear_api.py raw 'query { viewer { name } }'
```
Subcommands: whoami, list-teams, list-projects, list-states, list-issues, get-issue, search-issues, create-issue, update-issue, update-status, add-comment, list-documents, get-document, search-documents, raw. Run with --help for flags.

### Workflow States & Pagination

6 state types: triage, backlog, unstarted, started, completed, canceled. To change an issue's status, query workflow states first to get the stateId UUID. Priority: 0=None, 1=Urgent, 2=High, 3=Medium, 4=Low. Relay-style cursor pagination with first: N (max 250). Rate limits: 5,000 req/hr, 3M complexity points/hr.

**Full GraphQL reference:** references/linear.md

## Notion (absorbed from notion)

Talk to Notion two ways. Same integration token works for both.

ntn CLI: Notion official CLI. Shorter syntax, one-line file uploads. macOS + Linux only.
HTTP + curl: works everywhere including Windows. Default fallback.

### Setup

1. Create an integration at notion.so/my-integrations
2. Copy the API key (starts with ntn_ or secret_)
3. Store in .env: NOTION_API_KEY=your_key
4. Share target pages/databases with the integration in Notion.

### Install ntn

npm install --global ntn

Skip ntn login:
export NOTION_API_TOKEN=$NOTION_API_KEY
export NOTION_KEYRING=0

### API Basics

Notion-Version 2025-09-03 required on all HTTP requests. ntn handles this. Databases called data sources.

### Common Operations

Read page as Markdown: ntn api v1/pages/{page_id}/markdown
Create page from Markdown: ntn api v1/pages parent[page_id]=xxx markdown=content
Query a database: ntn api v1/data_sources/{id}/query filter[property]=Status
File uploads: ntn files create < photo.png

**Block types reference:** references/notion-block-types.md

## Teams Meeting Pipeline (absorbed from teams-meeting-pipeline)

Use this skill whenever the user asks about Microsoft Teams meeting summaries, transcripts, recordings, action items, Graph subscriptions, or any operational question about the Teams meeting pipeline.

Everything operator-facing is a hermes teams-pipeline subcommand run via the terminal tool.

### Prerequisites

Verify these are set in .env:
- MSGRAPH_TENANT_ID
- MSGRAPH_CLIENT_ID
- MSGRAPH_CLIENT_SECRET

If any are missing, direct the user to the Azure app registration guide.

### Command reference

- validate — config snapshot, run first after any change
- token-health — Graph token status
- token-health --force-refresh — force fresh token acquisition
- list — recent meeting jobs
- list --status failed — only failed jobs
- show <job-id> — full detail of one job
- run <job-id> — replay a stored job
- fetch --meeting-id <id> — dry-run: resolve meeting + transcript without persisting
- subscriptions — current Graph webhook subscriptions

### Subscription management

hermes teams-pipeline subscribe --resource communications/onlineMeetings/getAllTranscripts --notification-url URL --client-state STATE
hermes teams-pipeline renew-subscription <sub-id> --expiration ISO
hermes teams-pipeline delete-subscription <sub-id>
hermes teams-pipeline maintain-subscriptions
hermes teams-pipeline maintain-subscriptions --dry-run

### Decision tree

- Meeting summary missing? Start with list --status failed, then show <job-id>. If no job exists, check subscriptions.
- Setup working? validate, then token-health, then subscriptions.
- Re-run meeting X? list to find job ID, run <job-id>. If fails, show <job-id> + fetch --meeting-id.

### Critical pitfall: Graph subscriptions expire in 72 hours

Microsoft Graph caps webhook subscriptions at 72 hours and will NOT auto-renew. Without maintain-subscriptions scheduled (cron or systemd, 12-hour interval), meeting notifications silently stop after 3 days.

### Other pitfalls

- Transcript not available yet: Teams takes 2-5 minutes after meeting ends to generate the transcript artifact.
- Delivery mode mismatch: Check platforms.teams.extra.delivery_mode and matching target config.
- Graph app permissions: Token may acquire but Graph API calls return 401/403 if admin consent not re-granted after adding permissions.
- macOS Tailscale binding: macOS uses utun4, not tailscale0. Do not bind HTTP server to 100.x.x.x.

## PowerPoint (absorbed from powerpoint)

Create, read, and edit PowerPoint decks — from-scratch generation with pptxgenjs, template-based editing via direct XML manipulation, speaker notes, charts, and design QA.

### When to Use

Any time a .pptx or .potx file is involved: creating slide decks, reading content, editing existing presentations, combining/splitting slides, working with templates, layouts, speaker notes, or comments.

### Prerequisites

pip install markitdown[pptx] Pillow defusedxml lxml
brew install libreoffice poppler (macOS)
npm install pptxgenjs

### Quick Reference

| Task | Approach |
| Create a new deck | Write a pptxgenjs script — see references/powerpoint-pptxgenjs.md |
| Edit an existing deck | unzip, edit ppt/slides/slideN.xml, zip |
| Read content | markitdown deck.pptx (one block per slide) |

### Scripts

| Script | What it does |
| scripts/thumbnail.py deck.pptx [prefix] | Labeled grid of every slide for picking layouts |
| scripts/add_slide.py unpacked/ slide2.xml [--after slideN.xml] | Duplicate a slide with all package bookkeeping |
| scripts/clean.py unpacked/ | Delete orphaned slides, media, rels |
| scripts/office/validate.py deck.pptx [--original src.pptx] | Schema, relationship, content-type, chart checks |
| scripts/office/soffice.py --headless --convert-to pdf deck.pptx | LibreOffice wrapper |

### Design System

Color palettes: Midnight Executive, Forest & Moss, Coral Energy, Warm Terracotta, Ocean Gradient, Charcoal Minimal, Teal Trust, Berry & Cream, Sage Calm, Cherry Bold. See full table in references/powerpoint-editing.md.

Typography: Safe fonts (Arial, Calibri, Cambria, Times New Roman, Courier New, Bookman Old Style, Century Schoolbook). Never default to Aptos. Headers 36-44pt bold, body 14-16pt.

### QA (Required)

1. Content QA: markitdown output.pptx — check for missing content, typos, leftover placeholders.
2. File QA: python scripts/office/validate.py output.pptx --original src.pptx
3. Visual QA: Convert to images, inspect every slide with vision_analyze.

### pptxgenjs gotchas

- Set pres.layout before adding slides. Canvas is 10 x 5.625 inches (not 13.3 wide).
- Hex colors: never use #, never 8 digits. Use transparency 0-100 for translucency.
- Never reuse option objects across add* calls.
- Shadow offset must be >= 0. Use angle 270 for upward shadows.
- charSpacing, not letterSpacing.
- bullet: true on each item, never literal bullet character.
- One new pptxgen() per output file.
- dataLabelPosition on stacked charts: use ctr, inEnd, or inBase (never outEnd).
- Never reorder children of p:presentation element.

**Full guides:** references/powerpoint-editing.md, references/powerpoint-pptxgenjs.md
**License:** assets/powerpoint-LICENSE.txt

## References

- references/linear.md — Full Linear GraphQL query and mutation reference (absorbed from linear)
- references/notion-block-types.md — Notion block creation/reading reference with JSON examples (absorbed from notion)
- references/powerpoint-editing.md — Template-based editing workflow and design system (absorbed from powerpoint)
- references/powerpoint-pptxgenjs.md — pptxgenjs tutorial and API guide (absorbed from powerpoint)

## Templates

(none)

## Scripts

- scripts/linear_api.py — Zero-dependency Linear GraphQL CLI (absorbed from linear; used by cron jobs)
- scripts/thumbnail.py — PowerPoint slide grid generator (absorbed from powerpoint)
- scripts/add_slide.py — PowerPoint slide duplication with bookkeeping (absorbed from powerpoint)
- scripts/clean.py — PowerPoint orphaned-part cleanup (absorbed from powerpoint)
- scripts/office/ — Full Office Open XML validation, packing, and schema tooling (absorbed from powerpoint)

## Assets

- assets/powerpoint-LICENSE.txt — PowerPoint skill license (absorbed from powerpoint)
