---
name: customer-account-organization
description: Organize customer accounts in a structured, scalable markdown-based system with dashboard automation.
version: 0.1.0
author: Hermes Agent
tags: [customer-success, note-taking, organization, productivity]
---

# Customer Account Organization

## Purpose
Create a durable, portable customer account structure that supports both human and automated access — ideal for CRM-free workflows where markdown files are the source of truth.

## Principles
- Use plain markdown with YAML frontmatter for maximum portability.
- Avoid app-specific formats like Tolaria's schema until the user actually needs it.
- Build a folder structure that scales — one subfolder per customer.
- Keep the dashboard script in the root so it can scan all accounts.
- Let users build out templates in the markdown files as needed.

## Stakeholder Mapping
Use the `contacts` frontmatter field to maintain an editable stakeholder map per account. Populate `name`, `role`, `influence`, `relationship_to_us`, and `notes` as you discover people. The dashboard and any renderer should treat missing values as unknown/blank.

## Org-Chart Rendering
Because contact data lives in the same `index.md` as account data, you can regenerate any stakeholder visual from the same source of truth whenever the contact list changes.

## Workflow
1. **Create directory structure**:
   - `customers/` root folder
   - One subfolder per customer (e.g., `customers/polar-electro/`)
   - Each customer has an `index.md` with YAML frontmatter
   - `_meta.yaml` holds aggregate data for scripts or dashboards

2. **Define frontmatter schema**:
   - `name`: full customer name
   - `industry`: sector or vertical
   - `tsh`: AE/primary account executive
   - `customer_since`: YYYY-MM-DD
   - `renewal`: YYYY-MM-DD (renewal date)
   - `arr`: estimated annual recurring revenue
   - `health`: green/yellow/red/unknown
   - `risk_factors`: list of risks or delays
   - `expansion_signals`: key indicators for growth
   - `last_touch`: YYYY-MM-DD (last customer interaction)
   - `next_touch_due`: YYYY-MM-DD (due date for next touch)
   - `contacts`: structured list of stakeholders for org-chart mapping
     - `name`: full name
     - `role`: job title or accountability
     - `influence`: low | medium | high
     - `relationship_to_us`: ally | neutral | blocker | unknown
     - `notes`: last context, cadence, personal detail
   - `notes_links`: wikilinks to related notes or meetings

3. **Build dashboard script**:
   - Parses all `index.md` files
   - Scores accounts by urgency (renewal date, overdue touch)
   - Renders a weekly view of top priority accounts
   - Outputs readable text or structured JSON

## Pitfalls
- Using app-specific formats (e.g. Tolaria, Obsidian) before the user has a need for them.
- Overcomplicating the file structure with nested folders or JSONs.
- Not keeping dashboard logic in a single script that can be reused across tools or apps.
- Ignoring the user’s preference for concise, direct output.
- Not handling empty or malformed date fields in CSV imports gracefully.
- Failing to handle data inconsistencies (e.g., blank future-touch fields, missing contact fields) in the dashboard logic.
- **Not validating property IDs before use in API requests.** Notion's DB schema allows for custom properties that are not present in all pages, leading to 400 errors if the IDs are missing or invalid.

## References
- See `references/customer-account-template.md` for a sample account file.
- See `references/customer-dashboard-example.md` for a dashboard output example.
- See `scripts/customer-dashboard.py` for the dashboard logic.
- See `references/customer-seed-csv-processing.md` for details on CSV import workflows.