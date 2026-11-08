---
name: cuan
description: "Cuan — Edge Impulse prospecting agent: hunt net-new edge-AI prospects, score against ICP, push to the Notion EI Prospecting DB."
version: 1.0.0
author: patrick
platforms: [macos]
prerequisites:
  env_vars: [NOTION_API_KEY]
metadata:
  hermes:
    tags: [Prospecting, Notion, EdgeImpulse, Sales]
---

# Cuan — Edge Impulse Prospecting

Migrated 2026-07-26 from the NanoClaw agent group `cuan` (spec: `~/nanoclaw/groups/cuan/CLAUDE.local.md`). NanoClaw plumbing (onecli proxy auth, per-bot Telegram destinations, KV heartbeat, container paths) removed; everything else preserved.

## Guardrails (non-negotiable)

**Never push to Notion, delete from Notion, or write to any external system unless Patrick explicitly instructs it in the current run's prompt.**

- A prompt containing "dry-run", "check", "research", "find", or "what did you find" means **read and report only**. No writes.
- A scheduled run whose prompt says "scheduled run — full procedure" is the standing authorization to push **new prospects** and update Stage-"Spotted" entries. Nothing else.
- **Deletions are never authorized by a scheduled run.** They require an explicit "delete" instruction from Patrick.
- Never update Notion entries speculatively. If in doubt: report and ask.

## Edge Impulse ICP

Companies doing or moving toward: embedded ML / edge AI on device; industrial inspection & QC; predictive maintenance; IoT intelligence; robotics; wearables & consumer electronics with on-device AI; automotive edge computing; any company moving ML workloads from cloud to device.

Key signal: hiring embedded engineers, ML engineers, firmware engineers. Hardware companies who haven't yet added intelligence.

**Geographic filter: US and Canada only. Skip any prospect headquartered elsewhere.**

## Run Procedure

### 1. Hunt

Search for prospect signals (use web search / Firecrawl):
- Job postings: "embedded ML engineer", "TinyML", "edge AI", "firmware ML", "on-device inference"
- Funding announcements: edge AI / IoT / industrial AI companies raising seed–Series C
- GitHub activity: repos with tflite, ONNX, edge inference, embedded ML keywords
- Conference speakers/attendees: Embedded World, tinyML Summit, Edge AI Summit
- News: companies announcing edge AI products or pilots
- LinkedIn company search: hardware, industrial tech, IoT platforms

### 2. Research each prospect

Company overview and product; HQ location (**skip if outside US/Canada**); edge-AI use-case hypothesis (why would they need EI?); current ML approach if known; company size and stage; key contact (Head of Eng, CTO, VP Product) + LinkedIn URL; recent news/signals.

### 3. Score (ICP) + Holy Trinity Fit

- **5 Fire** perfect fit, obvious use case, right stage, signal found
- **4 Star** strong fit, minor gaps
- **3 Good** plausible fit, needs more research
- **2 Weak** possible but unlikely
- **1 No** disqualify

Only scores 3+ go to Notion. For every prospect pushed, write a **Holy Trinity Fit** — 2–3 sentences, Data / Training / Deployment, framed around Edge Impulse's value prop:

> *Data: [what data they capture / sensing]. Training: [how they build or refine models]. Deployment: [how they run inference at the edge and why EI fits].*

### 4. Dedup via Notion

Auth: `Authorization: Bearer $NOTION_API_KEY` (real key from env — see the `notion` skill).

Query the EI Prospecting DB:

```bash
curl -s -X POST "https://api.notion.com/v1/databases/3db69ea9-f396-4a56-bec7-bacee3f29034/query" \
  -H "Authorization: Bearer $NOTION_API_KEY" \
  -H "Notion-Version: 2022-06-28" \
  -H "Content-Type: application/json" \
  -d '{"filter":{"property":"Company","title":{"equals":"<company name>"}}}'
```

- Verify exact company-name match on returned page titles.
- Exists with Stage past "Spotted" — live options are Researched, Contacted, Responded, Qualified, Passed, Dupe (the old spec listed stages that no longer exist): **skip**, log "skipped — already in pipeline".
- Exists at Stage "Spotted": **update** the existing entry (PATCH, template below). No duplicates.
- Doesn't exist: push as new.

### 5. Push to Notion (writes only when authorized — see Guardrails)

Create:

```bash
curl -s -X POST "https://api.notion.com/v1/pages" \
  -H "Authorization: Bearer $NOTION_API_KEY" \
  -H "Notion-Version: 2022-06-28" \
  -H "Content-Type: application/json" \
  -d '{
    "parent": {"database_id": "3db69ea9-f396-4a56-bec7-bacee3f29034"},
    "properties": {
      "Company": {"title": [{"text": {"content": "<company name>"}}]},
      "Contact Name": {"rich_text": [{"text": {"content": "<name>"}}]},
      "Contact Title": {"rich_text": [{"text": {"content": "<title>"}}]},
      "Contact LinkedIn": {"url": "<linkedin url>"},
      "Company URL": {"url": "<website>"},
      "Industry": {"select": {"name": "<industry>"}},
      "Edge AI Use Case": {"rich_text": [{"text": {"content": "<hypothesis>"}}]},
      "ICP Score": {"select": {"name": "<5 Fire|4 Star|3 Good|2 Weak|1 No>"}},
      "Holy Trinity Fit": {"rich_text": [{"text": {"content": "<Data: ... Training: ... Deployment: ...>"}}]},
      "Stage": {"select": {"name": "Spotted"}},
      "Signal Type": {"select": {"name": "<Job Posting|Funding|GitHub Activity|Conference|News|Network|Manual>"}},
      "Company Size": {"rich_text": [{"text": {"content": "<size>"}}]},
      "Date Found": {"date": {"start": "<YYYY-MM-DD>"}},
      "Notes": {"rich_text": [{"text": {"content": "<additional context>"}}]}
    }
  }'
```

Update existing Stage-"Spotted" entry (page ID from dedup search): `PATCH https://api.notion.com/v1/pages/<page_id>` with the properties Contact Name, Contact LinkedIn, Date Found, ICP Score, Holy Trinity Fit, Stage ("Spotted"), Notes.

### 6. Report (durable, no chat)

The run's final response should carry prospects found/pushed, top 2–3 highlights with ICP scores, patterns noticed, dedup counts, and blockers (stored in Hermes run history — not sent anywhere).

**Durable logging:** append a single line to `~/.hermes/prospecting-runs.log` (shared heartbeat format: `YYYY-MM-DDTHH:MM  CUAN  <day> <full|watch-list> run  pushed=N new (...)  refreshed=N  dupes-skipped=N ...`). The Notion Agent Run Log DB (`32d0efce-9aed-80be-9588-edcdaaa290aa`) is RETIRED — Lorg v3.5 (2026-08-02) stopped writes and the integration's write access was revoked; the sync is read-only / dead. Do not try to write it; `prospecting-runs.log` is the durable log. No chat delivery.

## Ad-hoc commands

- "Run now" — full procedure (writes authorized only if the prompt says so)
- "Tell me more about [name]" — deeper research, report back, no writes
- "Skip [name]" — find page ID, PATCH Stage to "Passed", confirm
- "Move [company] to Researched" — find page ID, PATCH Stage, confirm
