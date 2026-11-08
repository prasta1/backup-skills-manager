---
name: nanoclaw-to-hermes-cutover
description: Replace NanoClaw orchestration with Hermes as the single runtime for agents, messaging, cron, memory, and model routing.
---

# NanoClaw to Hermes Cutover

Use when migrating from NanoClaw orchestration to Hermes as the single runtime for local agents, messaging, cron, memory, and model routing.

## Trigger
User wants to replace NanoClaw with Hermes, or is evaluating whether to consolidate.

## Phases

### Phase 0 — Inventory
List what NanoClaw does today:
- Per-agent Telegram/Discord adapter wiring
- Agent groups and isolation model
- Container lifecycle, restart, orphan cleanup
- Cron/scheduled tasks, compaction commands
- Memory health scans, session digests
- Model overrides and routing rules
- Custom slash commands (`/status`, `/models`, `/compact`, `/logs`, `/errors`, `/resources`, agent triggers)

### Phase 1 — Hermes profile/gateway prep
- Confirm Hermes profiles match desired separation (business, work, learning)
- Verify gateway is reachable on Tailscale from MBP and DGX Spark
- Confirm local providers are reachable from Hermes runtime
- Verify Telegram/Discord channels are connected at gateway level

### Phase 2 — Provider routing
Map NanoClaw model paths to Hermes providers:
- Local chat/coding → llama.cpp Ministral (`127.0.0.1:52292`) or host-bridged alias
- Vision → LM Studio (`localhost:1234`) until Hermes vision path is validated
- Embeddings → llama.cpp embedding server (`127.0.0.1:52291`)
- Main chat → Anthropic cloud unchanged
- Add these as named providers in Hermes config

### Phase 3 — Agent migration
- For each NanoClaw agent group, create or reuse a Hermes profile/session config
- Move CLAUDE.md, skills, and personalities into profiles
- Move NanoClaw cron jobs into Hermes cron jobs
- Move memory-health and session-digest cron jobs into Hermes

### Phase 4 — Slash commands and bot behavior
- Port NanoClaw slash commands to Hermes equivalents
- Agent trigger commands map to Hermes cron or manual session wakes
- `/restart` becomes gateway restart or profile reload

### Phase 5 — Data cutover
- Session state: map inbound/outbound polling to Hermes session model
- Qdrant memory: reuse existing Qdrant if schema is compatible
- If NanoClaw SQLite schema is custom, write a read-only bridge or importer
- Scheduled tasks/task_run_logs: migrate into Hermes cron or task DB

### Phase 6 — Stop NanoClaw
- Stop NanoClaw host and Docker containers
- Reclaim container disk space
- Disable NanoClaw launchd service
- Keep repo and `.env` as backup until Hermes is stable

## Verification Checklist
- [ ] Each agent group can send/receive on Telegram and Discord
- [ ] Local chat routes to llama.cpp Ministral, not LM Studio
- [ ] Vision still reaches LM Studio
- [ ] Embeddings hit llama.cpp `:52291`
- [ ] Status-style checks show correct services
- [ ] Cron jobs run and deliver on schedule
- [ ] No orphan containers or routing bugs in Hermes logs

## Risk Log
- Per-agent Docker isolation is lost; use Hermes session isolation if needed
- Custom NanoClaw adapter logic may need rebuild as Hermes skills/plugins
- Memory migration may need a one-time backfill from NanoClaw SQLite to Hermes memory
