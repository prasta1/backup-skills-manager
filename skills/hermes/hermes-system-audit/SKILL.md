---
name: hermes-system-audit
description: "Use when Patrick runs a Hermes self-audit or optimization."
version: 1.0.0
license: MIT
author: Ionga
tags: [hermes, audit, optimization, performance, memory, skills, tokens, verification]
metadata:
  hermes:
    tags: [hermes, audit, optimization, performance, memory, skills, tokens, verification]
---

# Hermes System Audit (four-prompt master framework)

Patrick pasted this master prompt on 2026-10-13: four audit/optimization prompts for the
whole Hermes installation. The execution rule at the end of the source document is
**"RUN THESE INDIVIDUALLY STEP BY STEP"** — run ONE phase at a time, in order, never all
four in a single turn. Each phase gates its changes on approval.

## When to Use

- "Run the system audit" / "audit and optimize" / "learn this as a skill" (the source doc)
- Comprehensive health check of the Hermes install, performance/token audit, memory+skills
  cleanup, or independent verification of previously claimed optimizations.
- NOT for a single reported infra fault — that is the `triage` skill; NOT for general Hermes
  troubleshooting — that is `hermes-infrastructure`.

## How to Run (one phase per session, in order)

The four reference files contain the verbatim prompts. Load the phase's file and execute it:

1. `references/phase1-complete-system-audit.md` — system discovery + deep performance audit +
   intelligence/learning review + safe optimization + validation + final report (score /100).
2. `references/phase2-memory-skills-cleanup.md` — memories, USER.md/MEMORY.md/SOUL.md, skills,
   skill references, session retrieval; Hermes Curator dry-run comparison; consolidation
   strategy with before/after inventory and estimated token savings.
3. `references/phase3-speed-token-efficiency.md` — task-execution analysis, model/context/
   reasoning/tool-selection audit, benchmark before/after, highest-impact optimizations first.
4. `references/phase4-verification-challenge.md` — skeptical re-audit of earlier phases;
   every improvement claim gets evidence or is labeled unverified; final prioritized roadmap.

## Guardrails (from the source prompts — non-negotiable)

- **Backup first, then verify the backup is recoverable**, before any modification.
- Only low-risk, reversible improvements without explicit approval. No permanent deletes, no
  provider switches, no weakened security, no altered critical automation, no removed working
  integrations without Patrick's explicit approval.
- Destructive/higher-risk changes: produce a proposed change list with exact targets, reasons,
  expected benefits, risks, and rollback procedures — then wait for approval.
- Measure a baseline before each change; after it, verify the component, run functional tests,
  compare against baseline, check regressions, and roll back anything that causes problems.
- Never claim an optimization succeeded unless it has been verified. No positive
  self-assessment padding; distinguish confirmed findings from assumptions and label guesses
  as guesses.
- Phase 4 runs with an adversarial stance: assume the earlier audit overlooked problems, and
  check for changes that improved one metric while degrading another.
- Phase 1's final report must include: health score /100 with a scoring rubric, findings
  ranked by severity, confirmed vs suspected, files/configs/skills needing attention, safe
  improvements completed, changes requiring approval, measured improvements, remaining
  security/reliability risks, recommended long-term maintenance practices.

## Environment-specific notes (Mac Studio)

- Diagnose with real commands and real output, never assume configuration works because it
  exists: `hermes doctor`, read `~/.hermes/config.yaml`, `curl -s 127.0.0.1:9292/v1/models`,
  `cronjob_manage`/`~/.hermes/cron/jobs.json`, `launchctl list`, `git -C ~/.hermes status`,
  session store sizes, `du` on caches.
- `MEMORY.md` is capped at 12,000 chars and refuses adds at 100% (see `hermes-infrastructure`
  for format rules — canonical `\n§\n` separators, never "organize" into sections).
- `~/.hermes` is a git backup repo: **never** `git clean -xfd` there (14+ GB of credentials
  and source would be destroyed). Name explicit paths for any cleanup.
- Memory streamlining is a *procedure lesson*: corrections to an agent's own mistakes belong
  in skills, not in memory; memory holds only verified, task-independent facts.
- `ms-bge-m3-1024` is a LIVE dependency of the daily Gmail Triage cron — do not flag it as
  cruft in a fleet audit.
- Studio runs on branch `local` of hermes-agent (carries ~40 private patches) — "behind"
  update-check messages are a branch artifact, not a network fault (see `hermes-infrastructure`).
- **Smoke-test gateways leak RAM if the sandbox can't auth.** A `hermes-audit-adapted` smoke run
  spawns one `gateway run --quiet --idle-exit` per session under `~/.local/state/hermes-audit-adapted/runs/<run>/home/`.
  If the sandbox can't reach Nous Portal (AuthError: not logged in), each gateway hits a transient
  agent failure, persists a message, and parks in a wait state that never counts as idle — so
  `--idle-exit` never fires and the gateways stay orphaned (PPID 1) at ~265 MB each. A single smoke
  session can leave 100+ of them (~22 GB). After any audit run, check `pgrep -f "gateway run --quiet"`
  and kill strays by exact command line + sandbox cwd (never `pkill` broadly — the production gateway
  runs `gateway run --external-supervisor` and must be spared). SIGTERM won't take them (parked in a
  wait state); go straight to SIGKILL. Clean up the `runs/` dirs too once the gateways are gone.
- Phase 2 mentions "built-in Hermes Curator in dry-run mode when available": run it dry first
  (when it exists on this install), compare its findings against independent inspection, and
  prefer reversible archiving over deletion.

## References

- references/phase1-complete-system-audit.md
- references/phase2-memory-skills-cleanup.md
- references/phase3-speed-token-efficiency.md
- references/phase4-verification-challenge.md

Related skills: `hermes-infrastructure` (deep gotchas: memory format, gateway exits, backup
repo, MCP auth), `triage` (single reported fault), `automated-status-reporting` (status briefs).
