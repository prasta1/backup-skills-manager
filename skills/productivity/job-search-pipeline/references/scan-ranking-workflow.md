# Scan → Rank → Stats batch

## 2026-08-31 session

- Tool inventory pass added/expanded bullets in `cv.md`: AI Infrastructure & Tooling, Analytics, Fabrication/Design, Knowledge/Research, Automation/Integration.
- Pricing-model detail added under Edge Impulse experience in `cv.md`: seat-based + compute-consumption hybrid.
- `node scan.mjs` returned 118 new offers, then a follow-up run returned 1 new offer after rerank.
- `node rank-pipeline.mjs` ranked 20 of 119 pending entries by default; a second full run ranked the remaining 79.
- `node stats.mjs --summary` showed 60 tracked entries, 0 applied, undefined advance rate — expected early state.

## Top-ranked targets from this batch

- Lovable: AI Scaled Customer Success Programs — 4.7/5
- Runway: AI Engagement Manager — 4.5/5
- Sierra: Agent Strategist — 4.4/5
- LangChain: Account Manager, Renewals & Expansion (West Coast) — 4.4/5
- RunPod: Director, Revenue Operations — 4.2/5
- Travelperk: Director of Go-to-Market Engineering (Revenue Operations) — 4.2/5
- Pigment: Business Development Manager — 4.0/5
- Legora: AI Enablement Manager — 4.0/5
- Later: VP Partnerships — 4.0/5

## Operational notes

- After changing `cv.md` facts/tools/narrative, rerank before relying on fit scores.
- For backlog ranking, use `node rank-pipeline.mjs --limit 200`. Runs over ~20 entries should be launched with `background=true` and `notify=true`.
- OpenRouter evaluation path may fail with 401 across free models in some environments; that blocks report generation, not local pipeline ranking.
- `node stats.mjs --summary` is the fastest single-command health check after any scan or rank pass.
- Scan output includes "Agent/WebSearch handoff" lines for companies without API providers. These are fallback searches, not errors.
- `cv.md` is gitignored by design; don't attempt to commit it.

## Eval-blocked local prep pattern

- When `node openrouter-runner.mjs evaluate <url>` fails with 401s across all free models, do not block on report generation.
- Instead: add tracker rows in `data/applications.md`, then create artifact directories with `node application-artifacts.mjs --report N --company NAME --role ROLE --init`.
- Generate reports later when the eval path is restored.
