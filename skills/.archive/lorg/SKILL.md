---
name: lorg
description: "Lorg — job-opportunity hunter: poll the ATS watch list, filter against Patrick's three role tracks, push qualifying roles to the Hunting Gathering Notion DB."
version: 3.2.0
author: patrick
platforms: [macos]
prerequisites:
  env_vars: [NOTION_API_KEY]
metadata:
  hermes:
    tags: [JobSearch, Notion, ATS, Prospecting]
---

# Lorg — Job Hunting (spec v3.5, ported from NanoClaw 2026-07-26)

Ported from `~/nanoclaw/groups/lorg/CLAUDE.local.md` (spec v3.2, June 10 2026). NanoClaw plumbing removed: no chat messages of any kind — Notion is the only external output; the run summary is the agent's final response (Hermes run history). Auth is `Authorization: Bearer *** (see `notion` skill), not the old onecli placeholder.

**v3.3 (2026-08-02):** Track B repurposed Product → Operations & Strategy; Track A widened with Professional Services / Implementation / Enablement / Education + AI-infra function tokens (Forward Deployed / Solutions / Deployment / Applied / DevRel, leadership only); comp floor A/B lowered $170K → $150K base; Security/Cyber un-blocked for leadership lanes (still barred from Solutions-Engineering titles). Cron prompt still references "spec v3.2" — soft reference, no behavior gate.

**v3.4 (2026-08-02):** Removed the per-run load of `~/.hermes/lorg-connections.csv` (4,088-row LinkedIn export was a context/token burner). Warm-intro matching from the personal network is deferred to a bounded approach — see Linear DEV-351. The CSV file is retained on disk for that work.

**v3.5 (2026-08-02):** Archived the write-only observability sinks — stopped writing `~/.hermes/prospecting-runs.log` (shared heartbeat) and the Agent Run Log Notion DB `32d0efce` (audit; DB left intact, writes stopped), and retired the `~/.hermes/lorg-observations.md` journal. Only the Hunting Gathering DB remains as output; the run summary is now the agent's final response. Observability/memory redesign tracked in Linear DEV-354.

## Guardrails (permanent — origin: 2026-05-07 incident)

**Never push to Notion, delete from Notion, or write to any external system unless explicitly instructed in the current run's prompt.** A scheduled run whose prompt says so is the standing authorization to push new qualifying roles and refresh Spotted rows. Deletions are NEVER authorized by a scheduled run. If in doubt: log and skip.

## 1. Target criteria

Three tracks; match seniority + function pattern within ~5 tokens; tag every pushed role with its track. Overlap → higher-priority track, note overlap. Leadership roles are domain-transferable — a strong CS / ops / strategy leader qualifies across domains unless a track note says otherwise.

**Track A — CS & Post-Sales Leadership (priority 1).** Seniority: VP, SVP, Senior Director, Head of, Director (only with strong function match), Chief (CCO). Function: Customer Success/CS, Customer Operations/CS Ops, Customer Experience/CX, Account Management, Post-Sales, Professional Services, Implementation, Onboarding, Customer Delivery, Enablement, Customer Education, Adoption, Customer Outcomes/Value. AI-infra flavors (same seniority gate): Forward Deployed (Engineering), Solutions / Solutions Engineering / Solutions Architecture, Deployment, Customer/Field Engineering, Applied, Developer Relations/DevRel. Hard pass: IC titles (CSM, individual FDE/SE/AM/TAM, etc.).

**Track B — Operations & Strategy (priority 2, complements CS).** Three families, all leadership unless noted:
- *Revenue/GTM Ops:* VP/Head/Director RevOps, Revenue Operations, GTM Operations, Customer Operations, Sales Operations.
- *Strategy:* Chief of Staff (to CRO/CCO/CEO), Customer Strategy, Customer Transformation, GTM Strategy, Business Operations/BizOps, Transformation.
- *Customer-facing Product (narrowed):* Senior/Staff/Principal/Lead/Group PM or Director/Head of/VP Product — only if domain = AI/ML AND a customer or platform angle is present (Voice-of-Customer, Platform, Customer, Adoption, Technical, API, Data, Infrastructure). Hard pass: APM; consumer/growth/feature PM with no customer or platform angle. Borderline angle → flag 👀 Marginal.

**Track C — Strategic Accounts (priority 3, opportunistic).** Strategic/Enterprise/Named/Major Account Manager, Account Director (enterprise), Director of Strategic Accounts, Customer/Revenue Lead. Hard pass: SMB/mid-market, SDR/BDR, pure new-logo roles.

**Stage:** Seed dropped (log "stage mismatch"). Series A: Track A only for Head/Director titles; fine for B/C. B/C/D/E+/Public: all tracks.

**Domains (priority):** 1 AI/ML tooling · 2 Hardware/IoT · 3 Industrial tech · 4 Connected-Vehicle/Mobility · 5 Additive manufacturing · 6 Developer tools.

**Location:** Remote (US) OR Burlington VT area (incl. hybrid VT).

**Comp floor:** Tracks A/B $150K base (or $230K OTE if only OTE shown). Track C: $230K OTE floor, no base floor. Undisclosed comp: push with Comp Type = Unknown, never drop.

**Hard no's:** Health Tech, Legal Tech, and any title containing "Account Executive" (per Patrick, Jul 3 2026 — "Director of Strategic Accounts" / "Strategic Account Manager" still qualify). **Security/Cybersecurity:** allowed for Track A CS/PS/AM/TAM leadership and all of Track B; NOT for Solutions / Sales Engineering titles in security (needs hands-on domain credibility Patrick lacks). Out-of-scope domains: hard-filter silently.

## 2. Sources

**Primary — CORE watch list (every run):** `~/.hermes/lorg-watchlist.md` (v-versioned header; 56 companies with ATS endpoints; Hermes-owned copy of the NanoClaw original). Poll each company's board; only title/location/comp/hard-no filters need to run (stage/domain known per row). `needs-resolve` endpoints: find the ATS via the careers page and cache the working URL back into the file. First-appearance dedup: per-company set of seen Job URLs; re-appearing roles are silent skips. Weekly (Monday) run: flag companies dry 60+ days and dead endpoints.

**Secondary — discovery sweep (Monday runs only):** keyword search for net-new companies. ATS board search (Greenhouse/Lever/Ashby, Wellfound, YC), LinkedIn Jobs, Built In, Getro VC portfolio boards (General Catalyst 222, Accel 8672, Insight 246, Primary 1124 — API 406s intermittently, don't block). Bias to 👍/🔥; promote genuinely strong companies to the watch list.

**Recency:** posted within 30 days; missing post date is not a skip.

## 3. Qualify & flag

No numeric score — a role pushes iff it passes every hard filter. Exactly one Priority flag, first matching rule: 👀 Marginal (weak title match, or a Track B customer-facing-PM role with only a borderline customer/platform angle) · 🔥 Strong (canonical title + top-tier domain: AI/ML, Hardware/IoT, Mobility) · 👍 Solid (everything else). Comp visibility and post date never affect the flag.

## 4. Notion write spec

Target: 🏹 Hunting Gathering DB `3270efce-9aed-8042-b972-fe082819bb56`. Dedup query by Job URL (then also check Company + Title):

```bash
curl -s -X POST "https://api.notion.com/v1/databases/3270efce-9aed-8042-b972-fe082819bb56/query" \
  -H "Authorization: Bearer $NOTION_API_KEY" -H "Notion-Version: 2022-06-28" -H "Content-Type: application/json" \
  -d '{"filter":{"property":"Job URL","url":{"equals":"<job posting url>"}}}'
```

Existing row Spotted + fresher posting → PATCH the row. Otherwise duplicate → skip and log. Insert via `POST /v1/pages` with parent `3270efce-9aed-8042-b972-fe082819bb56`.

Required fields on every insert — Company (title) · Company URL (url) · Title (rich_text, exact as posted) · Job URL (url, direct apply URL) · Role Track (select: `A · CS Leadership/Ops` | `B · Ops & Strategy` | `C · Strategic Accounts`) · **Date Spotted** (date, run date — the live column is `Date Spotted`, NOT the old spec's "Date Found") · Stage (always `Spotted`, never `Passed`) · Originator (select: `Lorg` | `Poke` | `Automation` | `Hermes`) · ICP Score (number: 🔥→5, 👍→3, 👀→1) · Funding Stage (select: `Seed` | `A` | `B` | `C` | `D` | `E+` | `Public` | `Unknown`) · Company Domain (select: `AI/ML` | `Hardware-IoT` | `Industrial` | `Additive` | `DevTools` | `Mobility` | `Other`) · Comp Type (select: `Base` | `OTE` | `Total` | `Unknown`) · Headcount (number, best estimate) · Source (rich_text, exact source URL + note if ATS blocked) · V (rich_text — the version header of `~/.hermes/lorg-watchlist.md` at push time, e.g. "v1.4").

Notes field: ≤2 sentences of qualitative color. **Retired fields — never write:** Raw Score, Score Breakdown, Comp Min/Max, Reports To, Location Type, Metadata, Application Date, Last Contact, Originated From Signal, Signal Type, Remote, Date Posted. Live columns `Product Type` and `Stage Reason` exist but Lorg does not write them — leave untouched.

## 5. Process rules

**Stale role maintenance (Monday runs):** Spotted rows >45 days by Date Spotted — URL resolves → no change; 404/gone → PATCH Stage to Expired (authorized as part of the scheduled run).

The run's final response carries the counters (watched / pushed by track / skipped / dropped / blockers) and top picks — stored in Hermes run history, not sent anywhere.
## 6. Run procedure

1. Poll watch list (resolve+cache `needs-resolve` endpoints). 2. Monday only: discovery sweep. 3. Verify each qualifying job URL is live (HTTP 200) — skip dead links. 4. Enrich (funding, headcount, reporting line, news, domain fit). 5. Flag per §3. 6. Dedup + push per §4/§5. 7. Monday only: stale-role pass. 8. Report: final response carries run counters + top picks (Hermes run history).

## Operational notes (hard-won)

- Lever/Ashby block plain fetch (403/empty) — use web search (`site:jobs.ashbyhq.com`) for those.
- Greenhouse: use job-boards.greenhouse.io directly.
- **Dover boards (app.dover.com/jobs/*) are JS-only SPAs — a static fetch reads as an empty/dead board.** Motorq logged dead for 15 runs until a browser check found 15 live roles (Jul 10 2026). Never trust a static-fetch zero on Dover; verify with a browser tool or note "Dover — needs browser check" in the report.
- Getro API 406s intermittently — try, don't block.

## Out of scope

No outreach, no application submission, no salary/interview research.
