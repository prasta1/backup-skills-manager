---
name: job-search-pipeline
description: 'Scan, rank, and review career-ops pipeline results.'
tags: []
related_skills: []
---

# job-search-pipeline

Operate a career-ops-style job search pipeline end to end: scan for new roles, rank pending URLs, interpret funnel stats, and maintain a review cadence.

## When to load

Load this skill when the user asks to:
- run or review a career-ops-style job search pipeline
- fold scan results into their job search workflow
- interpret pipeline stats, rankings, or reports
- establish a search cadence around the tool
- update cv.md tool inventory so gap analysis reflects real experience

## Where these commands run

The career-ops checkout lives on the **MacBook**, not the Studio: `~/Projects/forks/fork-career-ops`.
Hermes runs on the Studio, so every `node ...` command below needs the SSH form:

```bash
ssh macbook 'cd ~/Projects/forks/fork-career-ops && node <script> <args>'
```

Run it bare from the Studio and it fails on a missing script, or silently operates on the wrong
directory. Confirm the checkout is still where expected before a long run:

```bash
ssh macbook 'ls -d ~/Projects/forks/fork-career-ops'
```

**Discord surface:** `#search-jobs` (id `1521128702040211486`) in The Abyss, shared with job-search
alerts. career-ops requests and replies land there. The bot is already a member of that guild.

## Core workflow

1. **Scan** — find new roles
   - `node scan.mjs` for configured companies
   - `node scan-ats-full.mjs` for broad ATS sweep
2. **Rank** — annotate pending entries in `data/pipeline.md`
   - `node rank-pipeline.mjs --limit N`
   - Default batch size is 20; set `--limit` to the full backlog size. Runs over ~20 should be launched with `background=true` and `notify=true`, then summarized after completion rather than polling.
   - After changing `cv.md` facts/tools/narrative, rerank before relying on fit scores; a fresh scan plus full rerank is the preferred end-to-end refresh.
3. **Stats** — quick health check
   - `node stats.mjs --summary`
   - 0 applications with 0% advance rate means no decisions yet, not a broken funnel.
4. **Act** — move high-ranked targets into the tracker
   - Write TSV additions in `batch/tracker-additions/<num>-<slug>.tsv` and run `node merge-tracker.mjs` to promote evaluated pipeline entries into `data/applications.md`.
   - Do not use `node add-entry.mjs` for tracker promotion — that helper inserts into `cv.md`, not the applications tracker.
   - TSV column order is strict for the safety check: `num, date, company, role, status, score, pdf, report, notes`. Swapped score/status causes merge-tracker to skip the row as a possible column swap.
   - `node followup-seed.mjs <appNum>` after each application.
   - Before interviews, review `interview-prep/story-bank.md` and any company reports in `reports/*`

5. **Prepare** — generate application artifacts for active targets
   - Resolve the bundle root with `node application-artifacts.mjs --report N --company NAME --role ROLE --init`
   - Save the live JD into `output/<bundle>/jd/current.md`; leave `previous.md` empty unless comparing JDs
   - Optional gap check before drafting: `node jd-skill-gap.mjs <jd-path> --summary`
   - Build a compact tailored-CV JSON payload and write it to `/tmp/cv-<candidate>-<company>.json`
   - Resolve the template path with `node cv-templates.mjs resolve cv`
   - Build HTML: `node build-cv-html.mjs <payload> <bundle>/cv/tailored/v001/cv.html <resolved-template>`
   - Fact gate before PDF: `node verify-cv-facts.mjs <html-path>`
   - Render PDF: `node generate-pdf.mjs <html-path> <pdf-path> --format=letter --report=N`
   - ATS prefill summary: `node prepare-application.mjs --url <apply_url> --pdf <pdf-path>`
   - Stop at prefill; do not submit. Review location/remote constraints first.

## Cadence

- **Daily**: scan + stats
- **After each application**: followup-seed
- **Weekly** (15 min): stats + analyze-patterns + upskill + detect-reposts + rejection-latency
- **Before interviews**: review `interview-prep/story-bank.md` and any company reports in `reports/`
- **Monthly**: funnel-velocity + process-quality + salary-gap

## Weekly review commands

| Goal | Command |
|------|---------|
| Advance/rejection patterns | `node analyze-patterns.mjs --summary` |
| Skill gaps vs cv.md | `node upskill.mjs --summary` |
| Ghost jobs/reposts | `node detect-reposts.mjs --summary` |
| Slow/no-response recruiters | `node rejection-latency.mjs --summary` |
| Interview friction | `node process-quality.mjs --summary` |
| Stage timing drift | `node funnel-velocity.mjs --summary` |

## Key outputs

- `data/pipeline.md` — ranked pending URLs with fit scores
- `data/applications.md` — active tracker
- `reports/*.md` — company evaluation reports
- `data/status-log.tsv` — append-only transition ledger
- `cv.md` — source of truth for facts, skills, tools, and quantified claims used by evaluation and ranking

## Session notes

See `references/scan-ranking-workflow.md` for the latest run details and target shortlist.

## Pitfalls

- Ranking is opt-in and batched. The first run only ranks 20 entries; the backlog requires explicit re-runs with `--limit`.
- The scanner respects `data/blacklist.md` and `portals.yml` filters. If yields look low, check title/location filters before assuming a portal is broken.
- "Agent/WebSearch handoff" lines in scan output are not failures — they are fallback searches for companies without a zero-token ATS provider. Treat them as noise unless the user wants full coverage.
- Derived files (`interview-prep/story-bank.md`, `reports/*.md`) supply phrasing and narrative, not quantified facts. Any number from a derived file must trace to `cv.md` or carry a provenance marker.
- The Go dashboard requires a real TTY. `npm run serve:dashboard` will fail inside non-TTY sessions; run it directly in Terminal instead.
- `cv.md` is gitignored by design. Do not attempt to commit it; backing it up belongs in the user's separate config/backup strategy.
- If the user asks for tool/stack inventory, the canonical place to record it is `cv.md` under the **Skills** section. Add bullets by category — e.g. CRM, AI/Dev Tooling, Fabrication — so `upskill.mjs` can exclude known tools from the gap map.
- If `node openrouter-runner.mjs evaluate <url>` fails with 401s across free models, do not block on report generation. Instead: add tracker rows in `data/applications.md` via TSV additions + `node merge-tracker.mjs`, create artifact directories with `node application-artifacts.mjs --init`, and generate reports later when the eval path is restored.
- Tracker additions must use TSV in `batch/tracker-additions/`, never direct edits to `data/applications.md` for new entries. merge-tracker owns insertion, dedup, and sort order.
- When the user asks to move ranked pipeline entries into the tracker, the correct path is TSV additions + merge, not `add-entry.mjs`.
- Background ranking runs should be checked by process absence and then by reading `data/pipeline.md` or `node stats.mjs --summary`, not by polling the background process itself.
- Check location/remote constraints before generating artifacts. A role marked Hybrid or On-site with a stated location preference can still be a hard mismatch against a remote-only candidate; confirm intent before drafting a tailored CV or prefill form.
- `generate-pdf.mjs` warns when the rendered CV exceeds the page budget but still reports/indexes the PDF by default. Treat 3-page output as a draft, not a final submission-ready artifact; trim lower-priority bullets and rerender before attaching.
