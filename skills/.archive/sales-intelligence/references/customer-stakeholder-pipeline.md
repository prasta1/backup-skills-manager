---
name: customer-stakeholder-pipeline
description: "End-to-end pipeline: HubSpot CSV → local markdown → HTML charts → Notion DBs → GitHub Pages"
version: 1.0.0
author: Patrick Ruster
license: MIT
platforms: [linux, macos]
prerequisites:
  env_vars:
    - NOTION_API_KEY
  commands:
    - git
    - gh
    - python3
metadata:
  hermes:
    tags: [crm, stakeholder, notion, github-pages, pipeline, automation]
    homepage: https://github.com/prasta1/stakeholder-charts
---

# Customer Stakeholder Pipeline

Automated pipeline for managing customer stakeholder data from HubSpot CRM through to published GitHub Pages charts, with Notion as the collaboration layer.

## Architecture

```
┌──────────────┐    ┌──────────────────┐    ┌─────────────┐    ┌──────────────┐    ┌────────────────┐
│ HubSpot CSV  │───▶│ Local Markdown   │───▶│ HTML Charts │───▶│ GitHub Pages │───▶│ Stakeholders   │
│ (source)     │    │ (source of truth)│    │ (generated) │    │ (public URL) │    │ (view only)    │
└──────────────┘    └──────────────────┘    └─────────────┘    └──────────────┘    └────────────────┘
       │                    │                    │                    │
       ▼                    ▼                    ▼                    ▼
┌──────────────┐    ┌──────────────────┐    ┌─────────────┐    ┌────────────────┐
│              │    │  Notion DBs      │    │  GitHub     │    │  Notion        │
│              │◀───│  (collaboration) │    │  Actions    │    │  (auto-sync)   │
└──────────────┘    └──────────────────┘    └─────────────┘    └────────────────┘
```

## Directory Structure

```
~/.hermes/projects/customer-accounts/
├── customers/                          # Source of truth (18 account folders)
│   ├── motorola/index.md
│   ├── polar/index.md
│   ├── csem/index.md
│   └── ... (18 total)
├── stakeholder_maps/                   # Generated charts (GitHub Pages source)
│   ├── motorola-stakeholder-map.html
│   └── ... (18 total)
├── scripts/
│   ├── generate_stakeholder_charts.py  # Chart generator
│   ├── upload_to_notion.py             # Notion sync (contacts)
│   └── update_notion_chart_urls.py     # Notion sync (chart URLs)
├── .github/workflows/pages.yml         # GitHub Pages deploy
├── README.md                           # Full documentation
└── .gitignore
```

## Data Schema (index.md)

```yaml
---
name: Motorola Solutions
industry: telecommunications
tsh: Teague
contacts:
  - name: Jane Doe
    role: VP Engineering
    influence: High
    relationship_to_us: Ally
    notes: "Title: VP Engineering; Last activity: 2026-01-15; Sales activities: 42"
notes_links: []
---
```

## Quick Commands

### Daily Workflow
```bash
# 1. Edit contacts
vim customers/motorola/index.md

# 2. Push to deploy
cd ~/.hermes/projects/customer-accounts
git add -A && git commit -m "Update Motorola contacts" && git push
# → GitHub Actions regenerates charts + deploys to Pages
# → Stakeholders see updates at https://prasta1.github.io/stakeholder-charts/
```

### Full Sync (after HubSpot CSV export)
```bash
# 1. Download CSV to ~/Downloads/hubspot-crm-exports-*.csv

# 2. Run sync script (creates/updates all index.md files)
python3 scripts/sync_hubspot_to_markdown.py

# 3. Regenerate charts
python3 scripts/generate_stakeholder_charts.py

# 4. Push contacts to Notion
export NOTION_API_KEY="ntn_..."
python3 scripts/upload_to_notion.py

# 5. Update chart URLs in Notion
python3 scripts/update_notion_chart_urls.py

# 6. Deploy
git add -A && git commit -m "Full sync from HubSpot $(date +%Y-%m-%d)" && git push
```

### Notion-Only Updates
```bash
# If contacts edited in Notion, pull to local (manual for now)
# Then regenerate + deploy
python3 scripts/generate_stakeholder_charts.py
git add -A && git commit -m "Sync from Notion" && git push
```

## Notion Databases

| Database | ID | Purpose |
|----------|-----|---------|
| Customer Stakeholders | `3a70efce-9aed-80fc-8a7d-d68e4f03de78` | 639 contacts, filterable by Account/Influence/Relationship |
| Customer Accounts | `3a70efce-9aed-80a1-b089-000b1fb5128f` | 18 account rows with chart URLs + contact relations |

## Scripts Reference

| Script | Purpose | Key Dependencies |
|--------|---------|------------------|
| `generate_stakeholder_charts.py` | Reads all `customers/*/index.md` → writes `stakeholder_maps/*.html` | pyyaml |
| `upload_to_notion.py` | Pushes contacts from markdown → Notion Customer Stakeholders | NOTION_API_KEY |
| `update_notion_chart_urls.py` | Updates Customer Accounts `Chart URL` property | NOTION_API_KEY |

## GitHub Actions Workflow

File: `.github/workflows/pages.yml`

Triggers: push to main (customers/**, scripts/**, stakeholder_maps/**) + workflow_dispatch

Steps:
1. Checkout
2. Setup Python 3.11
3. Install pyyaml
4. Run `generate_stakeholder_charts.py`
5. Copy `stakeholder_maps/` → `docs/`
6. Upload Pages artifact
7. Deploy to GitHub Pages

Live URL: `https://prasta1.github.io/stakeholder-charts/<account>-stakeholder-map.html`

## Custom Domain (Optional)

```bash
# In GitHub repo Settings → Pages → Custom domain
stakeholders.yourdomain.com

# Add CNAME record:
stakeholders  CNAME  prasta1.github.io
```

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Charts not updating | Check GitHub Actions run; verify `customers/*/index.md` changed |
| Notion sync fails | Verify `NOTION_API_KEY` env var; check database sharing with integration |
| GitHub Pages 404 | Wait 2-3 min after deploy; check Actions log for deploy step |
| Script permission denied | `chmod +x scripts/*.py` |
| Jekyll build error | Ensure workflow uses `actions/upload-pages-artifact@v3` + `actions/deploy-pages@v4` (not Jekyll) |

## Maintenance

**Weekly:**
- [ ] Download fresh HubSpot export → run full sync

**Monthly:**
- [ ] Review influence/relationship assignments
- [ ] Archive stale contacts (no activity > 180 days)

**Quarterly:**
- [ ] Audit Notion database permissions
- [ ] Backup local markdown to git (already done via commits)

## Integration with Hermes

This skill can be invoked from Hermes:
- "Run the stakeholder pipeline sync"
- "Generate charts for Motorola"
- "Push contacts to Notion"
- "Deploy to GitHub Pages"

## Related Skills

- `customer-account-organization` — Account folder structure & contact schema
- `google-workspace` — HubSpot CSV export automation (future)
- `notion` — Notion API operations