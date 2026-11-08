---
name: sales-intelligence
description: "Sales prospecting, qualification, market research, company research, lead management."
author: Hermes Curator
version: 1.1.0
license: MIT
tags: [sales, prospecting, qualification, research, market-analysis]
metadata:
  hermes:
    tags: [sales, prospecting, qualification, research, market-analysis, lead-generation]
---

# Sales Intelligence Toolkit

## Overview
This umbrella consolidates sales intelligence, customer research, prospecting workflows, market research, and lead generation. Covers account prioritization, lead qualification, company research, market analysis, data normalization, outreach brief generation, and prospecting agent patterns.

## When to Use
- "Find prospects matching our ICP"
- "Research this company"
- "Score leads against our ideal customer profile"
- "Normalize company names in this list"
- "Segment this lead list"
- "Generate an outreach brief"
- "Classify this persona"
- "Review for duplicate records"
- "Build a target list for job searches"
- "Analyze this dataset for market patterns"

## Skill Inventory

| Skill | Purpose | Status |
|---|---|---|
| hermes/sales-intelligence | Unified framework (this skill) | umbrella |
| prospecting-agents | Prospecting agent patterns (Cuan, Lorg, Vega) | absorbed |
| company-target-list | Job search target list builder | absorbed |
| market-research | Company dataset analysis | absorbed |
| b2b-lead-qualification | Lead qualification against ICP | absorbed |
| company-data-normalization | Normalize company names, domains, data | absorbed |
| company-research | Company research methodology | absorbed |
| company-research-workflow-planner | Research scope and ICP definition | absorbed |
| company-segmentation | Commercial segment assignment | absorbed |
| lead-list-analysis | Analyze lead list quality | absorbed |
| lead-list-segmentation | Segment lead lists by criteria | absorbed |
| lead-research-workflow-planner | Lead research planning | absorbed |
| outreach-brief-generator | Generate outreach briefs | absorbed |
| partner-qualification | Partner candidate evaluation | absorbed |
| prospect-list-cleanup | Clean and normalize prospect data | absorbed |
| territory-segmentation | Assign territories | absorbed |
| account-prioritization | Prioritize target accounts | absorbed |
| automated-customer-alerts | Proactive customer health monitoring | absorbed |
| competitor-research | Monitor competitors for material news | absorbed |
| customer-account-organization | Organize customer accounts markdown system | absorbed |
| customer-meeting-prep | Generate meeting briefs and agendas | absorbed |
| customer-stakeholder-pipeline | End-to-end pipeline: HubSpot → markdown → HTML → Notion → Pages | absorbed |
| deal-forecasting | Analyze HubSpot deal pipeline, calculate forecasts | absorbed |
| renewal-pipeline-reports | Weekly renewal pipeline tracking | absorbed |
| productivity-product-price-monitor | Watch prices; alert on target | absorbed |
| research-competitor-news-monitor | Watch companies for material news | absorbed |
| account-prioritization | Prioritize target accounts | absorbed |
| candidate-qualification | Evaluate candidate against job description | absorbed |
| persona-classification | Classify buyer personas | absorbed |
| duplicate-record-review | Identify duplicate records | absorbed |
| directory-research-planner | Directory research planning | absorbed |
| job-title-normalization | Standardize job titles | absorbed |

## Core Workflows

### 1. Company Research Workflow
1. Define research scope and ICP (company-research-workflow-planner, directory-research-planner)
2. Identify target accounts
3. Research each company (company-research)
4. Normalize data (company-data-normalization, job-title-normalization)
5. Segment companies (company-segmentation)
6. Prioritize accounts (account-prioritization)

### 2. Lead Qualification Workflow
1. Evaluate candidate against job description (candidate-qualification) or ICP (b2b-lead-qualification, supplier-qualification, partner-qualification)
2. Score fit and experience
3. Classify persona (persona-classification)
4. Generate outreach brief (outreach-brief-generator)

### 3. Lead List Management
1. Analyze list quality (lead-list-analysis)
2. Clean up and normalize data (prospect-list-cleanup)
3. Segment into commercial segments (lead-list-segmentation)
4. Review for duplicates (duplicate-record-review)
5. Assign territories (territory-segmentation)

### 4. Market Research (absorbed from market-research)
Analyze datasets of companies or profiles to identify market patterns, dominant categories, gaps, and emerging trends. Use when the user provides a larger dataset and wants segments, gaps, and patterns. See `references/market-research.md`.

### 5. Prospecting Agent Pattern (absorbed from prospecting-agents)
Each prospecting agent follows the same 6-step pattern: Hunt, Research, Score (ICP), Dedup via Notion, Push to Notion (writes only when authorized), Report.

**Agent Variants:**
- **Cuan** — Edge AI / embedded ML companies, US and Canada only. ICP score: 5 Fire / 4 Star / 3 Good / 2 Weak / 1 No (only 3+ pushed). Notion DB: EI Prospecting DB.
- **Lorg** — Job hunting (CS & Post-Sales Leadership, Operations, Strategic Accounts; Remote US or Burlington VT). No numeric score — push iff passes every hard filter. Flags: fire Strong / thumbsup Solid / eyes Marginal.
- **Vega** — Vermont businesses needing custom CNC woodwork. Score: 1-10. Only surface 5+.

**Shared Notion API pattern:** All agents use curl to query Notion databases and push qualifying entries.

**References:** `references/cuan.md`, `references/lorg.md`, `references/vega.md`

### 6. Company Target List (absorbed from company-target-list)
Build a prioritized company list for job searches. Research and compile a list of companies with hiring signals, fit assessment, and outreach strategy. Save to ~/.hermes/lists/ for later reference.

**Procedure:**
1. Clarify scope — role title(s), industry/space, stage (Seed-C), location/remote, comp floor
2. Research — Run 3-5 parallel web searches covering funding data, job boards, company directories
3. Filter & tier — Sort into Tier 1 (active hiring, strong fit), Tier 2 (good fit, no listing), Tier 3 (broader fit)
4. Write file — Save to ~/.hermes/lists/<search-topic>-targets.md
5. Proactive next step — Ask about detailed job specs or outreach list

**Reference:** `references/company-target-list.md`

## Data Normalization Subskills
- job-title-normalization — Standardize job titles to role, seniority, department
- company-data-normalization — Normalize company names, industries, domains, locations
- duplicate-record-review — Identify likely duplicate profiles or companies

## File Locations
All sales intelligence skills use Notion databases as their primary output target.

## References
- `references/sales-intelligence-framework.md` — Unified workflow framework
- `references/cuan.md` — Cuan prospecting agent spec
- `references/lorg.md` — Lorg job-hunting agent spec
- `references/vega.md` — Vega prospecting agent spec
- `references/company-target-list.md` — Company target list builder
- `references/market-research.md` — Market research dataset analysis
- `references/b2b-lead-qualification.md` — Lead qualification against ICP
- `references/company-data-normalization.md` — Normalize company data
- `references/company-research.md` — Company research methodology
- `references/company-research-workflow-planner.md` — Research planning
- `references/company-segmentation.md` — Commercial segment assignment
- `references/lead-list-analysis.md` — Lead list quality analysis
- `references/lead-list-segmentation.md` — Lead list segmentation
- `references/lead-research-workflow-planner.md` — Lead research planning
- `references/outreach-brief-generator.md` — Outreach brief generation
- `references/partner-qualification.md` — Partner candidate evaluation
- `references/prospect-list-cleanup.md` — Prospect data cleanup
- `references/territory-segmentation.md` — Territory assignment
