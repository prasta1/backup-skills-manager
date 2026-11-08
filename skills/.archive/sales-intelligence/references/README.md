# Customer Stakeholder Pipeline

Complete workflow for managing customer stakeholder data from HubSpot CRM → local markdown → HTML charts → Notion databases → GitHub Pages.

## Overview

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐     ┌──────────────┐     ┌──────────────────┐
│  HubSpot CSV    │ ──▶ │  Local Markdown  │ ──▶ │  HTML Charts    │ ──▶ │   Notion     │ ──▶ │  GitHub Pages  │
│  (source)       │     │  (source of      │     │  (stakeholder   │     │  (sharing &   │     │  (public URL)  │
│                 │     │   truth)         │     │   maps)         │     │   collab)     │     │                │
└─────────────────┘     └──────────────────┘     └─────────────────┘     └──────────────┘     └──────────────────┘
```

## Components

### 1. Local Markdown (`customers/*/index.md`)
- **Source of truth** for all stakeholder data
- YAML frontmatter with structured `contacts` array
- 18 customer accounts, ~599 contacts

### 2. HTML Charts (`stakeholder_maps/*.html`)
- Auto-generated from markdown
- Dark theme, grouped by influence (High/Medium/Low)
- Responsive grid layout, color-coded influence bars

### 3. Notion Databases
| Database | ID | Purpose |
|----------|-----|---------|
| Customer Stakeholders | `3a70efce-9aed-80fc-8a7d-d68e4f03de78` | 639 contacts, filterable by Account/Influence/Relationship |
| Customer Accounts | `3a70efce-9aed-80a1-b089-000b1fb5128f` | 18 rows, linked to contacts via relation, chart URLs |

### 4. GitHub Pages
- **URL:** `https://prasta1.github.io/stakeholder-charts/`
- Auto-deploys on push to `main`
- Password protection via Netlify/Vercel if needed

## Quick Start

### Prerequisites
```bash
export NOTION_API_KEY="ntn_..."
```

### Daily Workflow
```bash
# 1. Edit contacts in customers/*/index.md
# 2. Regenerate charts
python3 scripts/generate_stakeholder_charts.py

# 3. Push to Notion (optional)
python3 scripts/upload_to_notion.py

# 4. Update chart URLs in Notion
python3 scripts/update_notion_chart_urls.py

# 5. Deploy to GitHub Pages
git add -A && git commit -m "Update stakeholders" && git push
```

## Scripts

| Script | Purpose |
|--------|---------|
| `generate_stakeholder_charts.py` | Reads all `customers/*/index.md` → writes `stakeholder_maps/*.html` |
| `upload_to_notion.py` | Pushes contacts from markdown → Notion Customer Stakeholders |
| `update_notion_chart_urls.py` | Updates Notion Customer Accounts with GitHub Pages chart URLs |

## Data Schema (index.md)

```yaml
contacts:
  - name: "Jane Doe"
    role: "VP Engineering"
    influence: "High"
    relationship_to_us: "Ally"
    notes: "Title: VP Engineering; Last activity: 2026-01-15; Sales activities: 42"
```

### Influence Levels
| Level | Criteria |
|-------|----------|
| High | C-suite, VP, Director, Head of, GM, CTO, CEO |
| Medium | Senior, Lead, Architect, Principal, Manager, Distinguished, Expert |
| Low | Individual contributors, Junior, Intern, Student (unless activity ≥30) |

### Relationship Levels
| Level | Criteria |
|-------|----------|
| Ally | Customer/In Progress/Nurture lifecycle; or >15 sales activities |
| Warm | 5-15 sales activities |
| Neutral | New, Educational Community, <5 activities |
| Blocker | Disqualified, Do Not Contact |
| Marketing | Marketing contact status |

## GitHub Pages Deploy

1. Repo: `prasta1/stakeholder-charts` (public)
2. Workflow: `.github/workflows/pages.yml` (see `references/github-pages-workflow.yml`)
3. URL: `https://prasta1.github.io/stakeholder-charts/`
4. Auto-deploys on push to `main` touching `customers/**/index.md` or `scripts/generate_stakeholder_charts.py`

## Notion Integration

### Setup
1. Create integration at `notion.so/my-integrations`
2. Share both databases with integration
3. Add `NOTION_API_KEY` to environment

### Database Properties

**Customer Stakeholders:**
- Name (title)
- Account (select, 18 options)
- Role (rich_text)
- Influence (select: High/Medium/Low)
- Relationship (select: Ally/Neutral/Warm/Blocker/Marketing)
- Last Activity (date)
- Sales Activities (number)
- Notes (rich_text)

**Customer Accounts:**
- Name (title)
- Account (select, 18 options)
- Chart URL (url)
- Chart File (files)
- Contact Count (number)
- TSH (rich_text)
- Contacts (relation → Customer Stakeholders)

## Maintenance

### Weekly
- [ ] Download fresh HubSpot export
- [ ] Run `scripts/sync_hubspot_to_markdown.py` (TODO)
- [ ] Regenerate charts
- [ ] Push to Notion

### Monthly
- [ ] Review influence/relationship assignments
- [ ] Archive stale contacts (no activity >180 days)
- [ ] Verify Notion relations intact

### Quarterly
- [ ] Rotate NOTION_API_KEY
- [ ] Audit Notion database permissions
- [ ] Test GitHub Pages deploy manually

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Chart generation fails | Check `index.md` YAML syntax; ensure `contacts:` array exists |
| Notion upload 400 | Verify property IDs match; share database with integration |
| GitHub Pages 404 | Wait 2-3 min after deploy; check `docs/` has `.html` files |
| Relation limit (100) | Motorola has 307 contacts; only first 100 linked in Notion |

## Extending

### Add New Account
1. Add folder in `customers/<slug>/index.md` with frontmatter
2. Add slug to `SLUG_MAP` in `generate_stakeholder_charts.py`
3. Add Account select option in both Notion databases
4. Run generation + upload

### Add Custom Field
1. Add property to Notion database
2. Add field to `index.md` frontmatter
3. Update `upload_to_notion.py` to include new field
4. Update chart template if displaying

## Files in This Skill

| Path | Purpose |
|------|---------|
| `scripts/generate_stakeholder_charts.py` | Main chart generator |
| `scripts/upload_to_notion.py` | Notion contact upload |
| `scripts/update_notion_chart_urls.py` | Notion chart URL sync |
| `references/github-pages-workflow.yml` | GitHub Actions workflow template |