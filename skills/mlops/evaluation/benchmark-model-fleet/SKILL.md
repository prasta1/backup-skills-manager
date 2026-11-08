---
name: benchmark-model-fleet
description: Benchmark LLM speed, vision, quality and scatter plots.
version: 0.2.0
author: Hermes
categories: [mlops, evaluation]
tags: [Benchmarking, LLM, Visualization, Matplotlib]
---

# Model Fleet Benchmark & Visualization

Benchmark a fleet of llama-swap-hosted models — coding speed, vision performance, quality scoring, and scatter plot generation. Originally built to audit and right-size a 171 GB model fleet down to 110 GB (recovering 61 GB) while mapping speed × quality trade-offs.

**What it does**: Run coding/vision benchmarks against a llama-swap endpoint, compute quality scores via deterministic pattern matchers, and land one reviewable row per (run × machine × family × model) in a single Notion table — plus native Notion chart/KPI views over that table, and the per-machine frontier scatter uploaded into Notion. Ranked tables still print to stdout; matplotlib PNGs and the PDF remain available but are opt-in.

**Where results are reviewed**: the Notion table, `Fleet Benchmark Results`, under the `Model Benchmarking` page. Replaces a review surface that was ~40 flat CSVs plus ~13 PNGs and a PDF per run.

**What it does NOT do**: Manage model lifecycle (loading, removal, disk cleanup). That's handled by separate llama-swap config operations. This skill only benchmarks, scores, visualizes, and reports.

**Key dependency**: llama-swap running with an OpenAI-compatible API (default `llama-swap-studio` = `http://127.0.0.1:9292`), matplotlib installed (`pip3 install matplotlib`). stdlib otherwise.

## When to Use

- Audit a model fleet's speed/quality tradeoffs before deletions
- Compare thinking vs non-thinking model variants
- Benchmark vision models (mmproj) with consistent image input
- Review results across runs in one sortable table (the Notion sink)
- Generate scatter plots showing deleted models greyed-out alongside active ones
- Produce ranked tables for reporting to stakeholders

## Prerequisites

- llama-swap running: `llama-swap :9292` (OpenAI-compatible endpoint). Verify with `scripts/discover_endpoints.py`.
- matplotlib: `pip3 install matplotlib`
- A test image for vision benchmarks, **paired with its rubric**: `scripts/test_image_user.png` + `prompts/vision_user.py` (default), or `scripts/test_image_workshop.png` + `prompts/vision_grounded.py`. The benchmark sends base64 data URIs, not URLs — llama-swap mmproj requires `data:image/png;base64,...`. **Do not use the legacy `scripts/test_image.png`** — it is a grey placeholder with a caption, not a photograph.
- Knowledge of model names as served by llama-swap (e.g. `ms-qwen3-coder-30b`) — or just run `run_interactive.py`, which reads them from the endpoint.

## How to Run

### Interactive (preferred)

`scripts/run_interactive.py` asks six questions before spending any GPU time —
which machine, what you want to measure, which models, how hard, where results
land, and a final confirm. It then drives the whole pipeline including the merge
step that is easy to forget.

```bash
python3 scripts/run_interactive.py              # interview, then run
python3 scripts/run_interactive.py --dry-run    # show the plan, run nothing
python3 scripts/run_interactive.py --preset vision
```

Every answer defaults to the cheap/safe option. `--non-interactive --profile
<profile.json>` replays a saved run for cron. **Use this unless you have a
specific reason not to** — a full `--all-models` coding sweep is ~2 hours on this
hardware, and the interview is what stops that from happening when you only
wanted to check two models.

### Manual

All scripts live in `scripts/`; run them from the skill root.

```bash
# 1. See what's live and what model ids each endpoint serves
python3 scripts/discover_endpoints.py --models

# 2. Run coding benchmarks (built-in coding prompts; requires --models or --all-models)
python3 scripts/benchmark.py --models ms-qwen3-coder-30b ms-devstral-24b
python3 scripts/benchmark.py --all-models          # every LLM the endpoint reports

# 3. Run vision benchmarks (uses scripts/test_image.png by default)
#    (models are unloaded after each benchmark by default; pass --no-unload to keep them resident)
python3 scripts/benchmark.py --vision --models ms-qwen3-vl-8b ms-glm-4.6-vision
python3 scripts/benchmark.py --models ms-qwen3-coder-30b --no-unload   # keep loaded after
python3 scripts/benchmark.py --vision --models ms-qwen3-vl-8b ms-glm-4.6-vision

# 4. Push into the Notion table — one row per run x machine x family x model.
#    This is the review surface; --all backfills every run dir it finds.
python3 scripts/push_to_notion.py --results-dir ~/.hermes/benchmark_results/run-X
python3 scripts/push_to_notion.py --all
python3 scripts/push_to_notion.py --all --dry-run     # show the rows, write nothing
python3 scripts/push_to_notion.py --views-only        # reconcile charts/KPIs only

# 5. Generate consolidated ranked report (rankings are PER MACHINE, see below)
python3 scripts/generate_final_report.py --results-dir ~/.hermes/benchmark_results
python3 scripts/generate_final_report.py --results-dir ~/.hermes/benchmark_results \
    --model-config <dir>/model-config.json --out <dir>/report.txt
# --combined  one table across all machines instead

# 6. OPT-IN: scatter plots + the PDF (uses references/model-config.json)
python3 scripts/generate_scatter.py --results-dir ~/.hermes/benchmark_results
# multi-machine fleet: one set of plots per box as well
python3 scripts/generate_scatter.py --results-dir ~/.hermes/benchmark_results \
    --model-config <dir>/model-config.json --per-machine
```

Plots: `scatter_coding.png`, `scatter_vision.png`,
`scatter_coding_efficiency.png`, plus `..._mac_studio_m3_ultra.png` /
`..._macbook_pro_m5.png` variants under `--per-machine`. `--combined-only`
suppresses the all-machines set.

The same run also writes **`scatter_plots.pdf`** — a document, not just a pile of
images: a cover page, a table of contents with real page numbers, a per-machine
summary page, then every chart as its own page. It is on by default; `--no-pdf`
restores PNG-only output. Pages are native vector, so a 12-page report is ~90 KB.
Every page shares the chart paper size (15.5×10.5 in); the text pages lay out in
an A4-width column aligned with the chart titles.

**Reading the output.** Per-machine speed × quality plots (and vision, when it is
rubric-graded) draw the **Pareto frontier**: a dashed staircase through the
models nothing else beats on both axes, with the beaten region shaded and its
models dimmed. That is the keep list. The combined plot skips it — a frontier
across machines would rank the hardware. The PDF summary page lists the same
frontier per machine (computed from the same rows as the chart), and for a group
spanning machines shows no speed-derived line at all, only best quality. The
text report opens each machine with a matching `VERDICT` block and marks
frontier rows `◆` in the coding table; it reads the CSVs rather than
model-config.json, so its frontier can differ from the PDF's by a model where
the two sources disagree on a score.

Results land in `~/.hermes/benchmark_results/` (override with `--results-dir`):
- `coding_bench_<timestamp>.csv` / `vision_bench_<timestamp>.csv` — raw per-model results. **These are the data layer**, not the review surface: the merge, the plots and the ranked report all read them, so they stay.
- `model-config.json` — pipeline state written by the merge, also not a review artifact.
- ranked tables printed to stdout by `generate_final_report.py`
- the **Notion table** — the review surface (see below). This is where a run is meant to be read.
- `scatter_coding.png`, `scatter_vision.png`, `scatter_coding_efficiency.png`, `scatter_plots.pdf` — **only with `--plots`** (or by running `generate_scatter.py` directly)

## The Notion table (the review surface)

`Fleet Benchmark Results`, under the `Model Benchmarking` page. One row per
**(run × machine × family × model)** — a run dir's ~40 CSVs collapse to a couple
of dozen sortable rows, and every run ever pushed lives in the same table, so one
model can be followed across runs.

Columns: Model, **Model Family**, **Base Architecture**, Machine, Family (the
TASK family — coding / vision / tool_calling), Type, Run, Date, Speed tok/s,
Quality, Chars, Size GB, tok/s per GB, Frontier, **Retired**, Prompts, Rows,
Errors, Endpoint, Run Dir, plus a `Key` of `run|machine|family|model` that makes
the push idempotent — re-pushing after a scorer fix corrects rows in place
instead of duplicating the run.

**Two classification axes, deliberately not one.** `Model Family` is read from
the model id — the line whoever built it named — and is id-grounded on purpose,
because an id saying `hermes` or `kat-coder` does not state what its weights are.
`Base Architecture` is read from the artifact instead: `general.architecture` in
the model's own GGUF. The two disagree in the interesting cases, which is the
whole point: `ms-kat-coder-v2.5` is family `kat` and architecture `qwen35moe` —
a fact no amount of reading the id would give you.

`Retired` is the human-facing name for a flag the pipeline still stores as
`deleted`; see the pitfall below for why only the label moved.

**Aggregation matches `generate_final_report.py`**, so the table and the report
cannot disagree: speed is the mean of per-prompt `median_tok_s` over non-error
rows (0 tok/s excluded — that is a failed call, not a slow model), quality is the
mean over non-error rows with a genuine 0.0 **kept**, and `Frontier` uses the same
`pareto()` over (speed, quality) computed **per (machine, family)** — a fleet-wide
frontier would rank the hardware, not the models.

Two deliberate omissions:

- **No frontier for vision.** Vision tok/s is unreliable by this skill's own
  measure (1.4–80.8 tok/s for one model across prompts). A frontier drawn on an
  unreliable axis invites a false conclusion; on vision, read Quality.
- **`vision_quality` is not imported from model-config.json.** A row records what
  *that run* measured. `vision_quality` is a fleet-view concept (a later run
  superseding a scorer fix), and importing it into a historical row would misdate
  it.

Where it lives: `references/notion.json` holds the database and data source ids,
written by `--init`; nothing is hardcoded. The script runs **headless against the
integration token** (`NOTION_API_KEY` in `~/.hermes/.env`) — a skill script has no
MCP session, so the Notion MCP tools are not available to it. The parent page must
be shared with that integration or every call 404s.

**Views**: `push_to_notion.py` reconciles a script-owned set on every push —
`Quality by Model` and `Quality by Model Family` (bars), one
`Speed by Model · <machine>` bar PER MACHINE, `Family mix` (donut), three KPI
number tiles, `By Model Family` (a board), and the `Latest run` / `Frontier only`
tables. A view the script never created is invisible to it and stays untouched, so
hand-made views are always safe. `--views-only` reconciles without pushing rows.

**The REST API CAN do views.** An earlier version of this file claimed it could
not; that was wrong. `POST /v1/views`, `PATCH /v1/views/{id}` and
`DELETE /v1/views/{id}` all work, `chart` and `dashboard` are valid view types,
and the wire shape can be learned by reading back a view created elsewhere. The
MCP is a convenience, not a requirement — nothing about views needs a session.

`notion_views.py` owns them. There is **no endpoint that lists a database's
views** (`GET /v1/databases/{id}/views` is `invalid_request_url`), so idempotency
cannot come from enumerating them — it comes from the `views` registry in
`references/notion.json`. A recorded id that 404s on PATCH was deleted in the UI,
so it is recreated. A view the script never created is invisible to it and stays
untouched, so hand-made views are always safe. `--views-only` reconciles without
pushing rows.

**Speed charts are per machine, deliberately.** A speed chart spanning both boxes
would rank the hardware and read as a model comparison — the same rule the report
and the plots follow. Quality IS comparable across machines, so `Quality by
Model` stays global. The per-machine set is built from the table's own `Machine`
select options, **not** from `endpoints.json`: the registry lists each box twice
(local + tailnet, tailnet + loopback) and `_host_label` renders one box as both
`Mac Studio M3 Ultra` and `Mac Studio`, which produced a duplicate speed chart per
machine, one of them permanently empty.

**Dashboard rows cannot be set by the API.** A `dashboard` view can be created and
`type: "dashboard"` is accepted, but `configuration` is rejected for it —
`configuration.type` allows only table/board/calendar/timeline/gallery/list/map/
form/chart. So a dashboard comes back empty and arranging it is a one-time drag in
the UI.

**The frontier scatter is uploaded, not left on disk.** Notion cannot draw a
scatter, and that chart is the skill's central visual, so a single-run push
renders the per-machine coding scatters into a temp dir and uploads them into the
`Model Benchmarking` page as image blocks. Captions read `◆ <run> · <machine>` and
are checked before upload, so re-pushing a run is a no-op rather than a duplicate.
The temp dir is removed afterwards — no chart is left beside the CSVs.
`--no-charts` skips it; `--all` skips it by default, because backfilling 18 runs
would stack dozens of images on the page.

## The Grist table (second sink, same rows)

`Fleet Benchmark Results` — <https://docs.getgrist.com/doc/tBbZvcesAundEsKyK9w9BY>.
Same rows as Notion, same `Key`, fed by the **same aggregation**: the transform is
IMPORTED from `push_to_notion.py`, not reimplemented, so the two sinks cannot
drift. `scripts/diff_sinks.py` proves it by reading both live and diffing
key-for-key (219 keys × 19 fields, clean).

Why a second sink exists: **Grist shows charts on every plan, including Free**
(Notion caps Free at one *visible* chart), and Grist has a **native Scatter
Plot**, which Notion cannot draw on any plan — the reason the frontier scatter
has to be rendered in matplotlib and uploaded as an image over there.

Grist API facts, each one verified against the live API rather than assumed:

- **`PUT .../tables/{t}/records` takes `{require, fields}`** — declarative upsert
  matched on `require`. Idempotency is the API's own job here, unlike Notion's
  emulated query-then-patch.
- **A "fresh" doc is NOT empty.** It ships with `Table1` carrying three blank
  formula columns (`A`, `B`, `C`), and the API has no table-delete. So `--init`
  RENAMES `Table1` to `Results` instead of creating a sibling and orphaning it,
  and deletes the placeholders only while they still look like placeholders.
- **A `Choice` column accepts and STORES an out-of-list value but does not add it
  to the list.** The row keeps the value; the column's `choices` do not grow, so
  that value would render without a legend entry forever. `sync_choices()` unions
  what it is about to write into `widgetOptions` on every push, in ONE PATCH.
- **Table and column ids are not labels.** `speed_tok_s` carries the label
  `Speed tok/s`. Records are written by id, never by label.
- **`PATCH .../tables/{t}/columns` takes the column id in the BODY**, while
  `DELETE .../columns/{colId}` takes it in the PATH. Conflating them 404s.
- **DateTime columns store epoch seconds.** `to_epoch()` reads a run's naive
  local timestamp as local, not UTC — UTC would shift every September run 4 hours.
- `scripts/grist_client.py` holds the transport; `references/grist.json` holds the
  doc/table ids. Both mirror the Notion pair on purpose.

**Charts are declared, not dragged.** `scripts/grist_views.py` reconciles eleven:
per machine the current frontier scatter, the current fleet scatter, the current
tool-calling scatter, the frontier speed bar and a vision quality bar, plus two
global ones (quality by model, quality by model family). The action API has
no "make a chart" action, so configuring one means rewriting its
`_grist_Views_section_field` rows and setting `chartType`/`title` on the section.

**Renaming a spec orphans its page; there is no rename path.** A spec is matched
to its page by NAME, and `unclaimed_chart_page()` only adopts a page whose chart
section has no `chartType` yet (the unconfigured probe pages). So changing a
spec's `name` does not move the existing page: it creates a new one and leaves the
old one behind, still holding its chart. Rename by hand first (PATCH
`_grist_Views.name`), or delete the old page and accept the recreation. Removing a
page takes two actions in order: `["RemoveViewSection", sectionRef]` then
`["RemoveRecord", "_grist_Views", viewRef]`, and the stale key must be dropped
from `references/grist.json` or the registry keeps pointing at a page that is
gone.

**Every chart pins one task family, `Latest`, and not-`Retired`.** A filter is per
column, so `Latest` alone still leaves one row per (machine × family × model): a
model measured in coding, vision and tool_calling plots three times under one
name. And `Frontier` is computed over every measurement ever taken, not over the
latest ones, so a frontier chart without `Latest` replays each run. Measured
before the fix: the Studio "Current fleet" scatter drew 41 points for 22 models,
the Studio frontier scatter 23 points for 8 (`ms-kat-coder-v2.5` five times). The
`Family` pin is not cosmetic either — `Frontier` is computed per
(machine × family), so a chart mixing families superimposes several frontiers on
one speed axis and puts vision speeds (the axis this skill calls unreliable) next
to coding ones. `coding` is pinned because it is the canonical family and the
only one with a row for every live model on both boxes. Result: 18 points on
"Current fleet · Studio", 19 on the MacBook one, 3 on each frontier scatter —
and the 3 IS the current coding frontier, the same list the report's VERDICT
block prints.

**Density, and the `Latest` flag.** The 219 rows are only **54 distinct model
ids** — 92% are a repeat measurement of a model already in the table, and one id
appears in 12 separate runs. So an unfiltered scatter is a labelled hairball.
Two row fields fix that, both computed batch-level in
`push_to_notion.mark_latest()` and carried by BOTH sinks: `Frontier` (pareto over
speed×quality per machine+family) and **`Latest`** (newest measurement per
machine × family × model — 86 of 219 rows; 65 once retired models are excluded).
Frontier answers "what is the tradeoff curve", Latest answers "what is current".
Speed is compared per machine either way, because tok/s measures the hardware as
much as the model.

`Latest` is a row field rather than a chart trick on purpose: it makes "present
state" a filter usable by any widget, and the two sinks stay identical because
one function computes it. It is derived from the run's own date with run-id
tie-breaking, so it is deterministic rather than filesystem-order dependent.

**Page names and descriptions are reconciled too.** The raw-data page a fresh doc
calls `Table1` is renamed **`All results`** — renaming a page changes the label
only, the table id stays `Results`, so every chart binding and filter keeps
working. Every view also carries a description saying what it answers and what it
filters, reconciled from `DESCRIPTIONS` so a description cannot drift from the
chart it describes.

**Tag colours are data, not code.** `references/family-colors.json` holds one
colour per model family, reconciled into each Choice column's
`widgetOptions.choiceOptions` (the tag's fill and text colour). Colours are
**sampled, not chosen by eye**: fetch each publisher's own mark (HF org avatar,
GitHub org avatar, or their favicon), drop near-white / near-black / desaturated
pixels, histogram the rest by hue in 10-degree bins, average the dominant bin,
then lift it to a readable mid-tone.

Three families have **no brand colour to sample at all** — OpenAI, Nous Research
and Liquid AI use deliberately monochrome marks — so they are labelled `assigned`
rather than passed off as brand colours. And several brands are genuinely the same
blue (qwen, deepseek, granite, muse, bonsai), so a **budgeted** separation pass
nudges only what actually collides: capped at 20 degrees and never below 0.50
value. An earlier uncapped pass is the cautionary tale — it dragged DeepSeek's blue
to magenta and IBM's to green, destroying the brand identity the colours exist to
carry. Per-family provenance (`sampled` / `shifted` / `assigned`) is recorded in
the file so nothing is misrepresented.

**Section filters live in `_grist_Filters`, NOT on the section.**
`ViewSectionRec` builds its row filter from
`recordSet(this, docModel.filters, "viewSectionRef")`: a filter is a row of
`_grist_Filters {viewSectionRef, colRef, filter, pinned}` where `filter` is the
FilterSpec JSON (`{"included": [true]}`, `{"included": ["Mac Studio M3 Ultra"]}`).
`_grist_Views_section.filterSpec` also exists and looks exactly like the right
place for this. The client ignores it — writing it is a **silent no-op**, so a
"filtered" chart quietly displays everything.

**The field list IS the axis config — and the arity differs by chart type.** From
`ChartView.chartTypes`:

| chart type | fields | why |
|---|---|---|
| `bar`, `line`, `area` | **2**: X, Y | `basicPlot(series)` plots `series.slice(1)` against `series[0]` |
| `scatter` | **3**: LABEL, X, Y | `scatter()` calls `basicPlot(series.slice(1), {text: series[0].values})` |
| `pie`, `donut` | 2: labels, values | labels are field[0] |

Give a scatter only two fields and `basicPlot` receives a single series, slices
*that* away, and renders an **empty chart with no error anywhere** — silently
broken, which is exactly how it shipped the first time. `plan_config()` now
raises on a wrong arity rather than letting it through.

Traps, all of which failed silently and cost real debugging:

- **A newly created chart section already has TWO default fields on it** (the
  table's first two columns). They must be re-pointed or removed — appending
  yields a chart with four series. Always re-read the live fields after a create.
- **`read_views()` is a snapshot.** Renaming or creating a page invalidates it, so
  re-read after any such change, and track which page an adopt consumed — without
  that, every spec in the loop adopts the same page.
- **Filters go in `_grist_Filters`, not `filterSpec`** (see above).
- Removing a page takes **two** actions in order: `["RemoveViewSection", ref]`,
  then `["RemoveRecord", "_grist_Views", viewRef]`. There is no `RemoveView`.

## Scatter report artifacts — read this before trusting one

`generate_scatter.py` reads the **fleet** `model-config.json` and the pooled
results, NOT the run directory you hand it. Verified: pointed at a vision-only run
dir it produced a 284 KB *coding* scatter without complaint. So every PNG in a
`report/` dir is a picture of the fleet **at the moment the script ran**, filed
under whichever run was current. One filed in `fleet/2026-09-21_studio/report/` is
titled "2 Oct 2026" and has an mtime eleven days after its run.

These are therefore **not per-run snapshots**. A scatter sitting beside a run's
CSVs does not mean that run produced that data, and two runs can carry
byte-identical charts.

`_empty()` now **writes nothing** and says why. It used to emit a placeholder PNG
("Nothing to plot — no … results for these models") so callers globbing
`scatter_*.png` would always find something. That promise was a bug with two
costs: seven error screens accumulated across report dirs and had to be found and
deleted by hand, and `notion_views.frontier_images()` globs `scatter_coding*.png`
— so a vision-only run uploaded error screens **into Notion as frontier charts**.
Skipping is truthful and fixes the upload in the same stroke.

**Running it from an agent shell: clear PYTHONPATH first.** This shell exports
`PYTHONPATH` pointing at a **python3.14 venv** while the interpreter is 3.9, so
`import matplotlib` dies in PIL (`cannot import name '_imaging'`). Use
`env -u PYTHONPATH python3 generate_scatter.py …`. Environment-level, predates any
script edit — but it means this script silently cannot run from here without that.

## Quick Reference

| Command | Purpose |
|---------|---------|
| `scripts/discover_endpoints.py` | Probe all registered endpoints, list live ones + model ids |
| `scripts/benchmark.py` | Coding/vision benchmark, writes CSV. **The canonical benchmark.** |
| `scripts/run_interactive.py` | **Interactive front-end** — asks what to measure before spending GPU time |
| `scripts/build_model_config.py` | Merge CSVs + on-disk GGUF sizes into model-config.json. **Reconciles against the llama-swap config** — ids no machine can load are marked `deleted`, not silently kept |
| `scripts/generate_scatter.py` | Matplotlib scatter plots (speed×quality, vision, efficiency) **+ `scatter_plots.pdf`** (cover, contents, summary, all charts). Opt-in — the Notion table is the default review surface |
| `scripts/push_to_notion.py` | **Notion sink** — one row per (run × machine × family × model), upserted. `--init` creates the table, `--all` backfills every run dir, `--views-only` reconciles just the views |
| `scripts/notion_client.py` | Notion REST transport + `references/notion.json` state, shared by the sink and the view manager |
| `scripts/notion_views.py` | **Native views** (charts, KPIs) reconciled on each push, and the frontier scatter render + upload into Notion |
| `scripts/grist_sink.py` | **Grist sink (second destination)** — same rows, same `Key`. `--init` creates the doc+table, `--all` backfills, `--check` reads back and diffs against the source runs |
| `scripts/grist_client.py` | Grist REST transport + `references/grist.json` state |
| `scripts/diff_sinks.py` | **Cross-sink diff** — reads Notion and Grist live and compares every key and field. Read-only; the guard against the two sinks drifting |
| `scripts/grist_views.py` | **Declarative Grist charts** — reconciles 7 per-machine charts (4 frontier + 2 "current fleet" scatters) by rewriting section fields, chartType, and `_grist_Filters` rows. `--list`, `--dry-run`. Idempotent |
| `scripts/probe_grist_chain.py` | Throwaway-doc probe of the Grist primitive chain (create → schema → upsert → idempotency), deleting the doc after. Run it before trusting a new API assumption |
| `scripts/model_family.py` | **Classification**: family from the model id, base architecture from the GGUF. Also the stdlib GGUF metadata reader, and the ssh bridge that reads the MacBook's weights from here |
| `scripts/head_to_head.py` | **Pairwise head-to-head** — two models, Hermes-shaped tasks, ground truth derived from live artifacts. Accuracy + token cost + latency. Answers "should A replace B"; `benchmark.py` answers the fleet question |
| `scripts/generate_final_report.py` | Consolidated ranked tables |
| `scripts/prompts.py` | Built-in coding prompts + quality scorers |
| `prompts/judgment.py` | **Reasoning family** — 7 quality-discrimination prompts (agentic coding, math, multi-step logic, debugging, instruction following, structured output, practical reasoning). Ported from Claude Code's `benchmark-models` harness; run with `--max-tokens 2048` |
| `prompts/vision_user.py` | **Grounded vision rubric** — the one to use (`--prompts-file`) |
| `prompts/vision_grounded.py` | Second grounded rubric, for `test_image_workshop.png` |
| `references/vision_ground_truth_user.json` | Verified ground truth for `test_image_user.png` |
| `references/vision_ground_truth.json` | Verified ground truth for `test_image_workshop.png` |
| `test_vision_user.py` / `test_vision_rubric.py` | Rubric unit tests — run after ANY scorer change |
| `references/endpoints.json` | Endpoint registry (llama-swap, LM Studio, oMLX, mlx_lm, Ollama, vLLM) |
| `references/model-config.json` | Model metadata — **generated by build_model_config, not hand-edited** |
| `references/benchmark-methodology.md` | Full methodology docs |

**Key API endpoints**:
- `POST http://127.0.0.1:9292/v1/chat/completions` — completion request
- `GET http://127.0.0.1:9292/v1/models` — list available models

**Endpoints**: `--endpoint` takes a registry name from `references/endpoints.json` (`llama-swap-studio`, `llama-swap-studio-tailnet`, `llama-swap-mbp`, `lm-studio`, `omlx`, `mlx-lm`, `ollama`, `vllm`) or a full URL. Default is `llama-swap-studio`. Run `scripts/discover_endpoints.py` first — most endpoints are down at any given time, which is expected. A dead endpoint fails preflight in <0.1s instead of retrying 30x per call, and ids the server does not serve are skipped with a warning.

**Auth**: endpoints that require a key (e.g. oMLX) set an `api_key` field in `endpoints.json` — `file:/path/to.json#/json/pointer` (read from a JSON file), `env:VARNAME`, or a literal. Both `discover_endpoints.py` and `benchmark.py` send it as a Bearer header. oMLX serves on **:8010** (settings.json `server.port`), not 8000, and requires its key.

**Task families**: `--prompts-file prompts/<family>.py` swaps the rubric. CSVs are named after the family so runs do not collide. Deterministic scoring is best for sql_generation (queries are executed against an in-memory SQLite and result sets compared), excellent for structured_extraction / tool_calling / instruction_following, good for web_frontend and data_analysis, and impossible for summarization or creative writing — do not fake those with pattern matchers. `prompts/judgment.py` is the REASONING family: 7 quality-discrimination prompts (agentic coding / math / multi-step logic / debugging / strict instruction following / structured output / practical reasoning) ported from the old Claude Code `benchmark-models` harness. It uses `--max-tokens 2048` (the prompts ask for real code) and its rubrics have defined correct answers, so scores are ground-truth checks. Its tests: `scripts/test_judgment.py`.

## Procedure

1. **Verify llama-swap is running**: `python3 scripts/discover_endpoints.py` — confirm `llama-swap-studio` is UP and note the model ids. llama-swap loads models on-demand, so first requests may take time (retry on 503).

2. **Prepare test image** (for vision benchmarks): a PNG at `scripts/test_image.png`. The benchmark reads it as base64 and sends `data:image/png;base64,...` — llama-swap mmproj does NOT fetch URLs.

3. **Edit `references/model-config.json`**: List every model to benchmark with its metadata:
   ```json
   [{"name": "ms-qwen3-coder-30b", "size_gb": 16, "type": "MoE", "deleted": false}]
   ```
   Fields: `name` (llama-swap model ID), `size_gb` (for bubble size + efficiency), `type` (MoE/Vision/Standard/Embeddings for coloring), `deleted` (grey X marker on plots), plus `coding_spd`/`quality`/`vision_spd`/`vision_chars` (results go here after benchmarking). This is the single source of truth for plots and reports.

   **In practice you should not hand-edit this — `build_model_config.py` generates it** (step 4 below), and the merge now sets `deleted` itself. Hand-edits are overwritten on the next merge, and a hand-edited file is how stale ids survived here for weeks.

   **Staleness rule.** The merge's name universe is the union of *every* CSV ever written, and nothing ever removes a name — so a model that was benchmarked once, then pruned or renamed, would otherwise stay forever, rendered as a LIVE bubble. `reconcile()` prevents that: an id survives only if the local llama-swap config declares it, or it carries a prefix owned by another machine (derived from `endpoints.json` + which prefixes this config actually declares). Everything else gets `deleted: true` + `not_loadable: true` — greyed on the plots, left out of every frontier and marked `deleted` in the report's rankings, and kept as an audit trail. Run with `--no-reconcile` to opt out.

4. **Run coding benchmarks**: `python3 scripts/benchmark.py --models <id> ...` (or `--all-models`). For each model: 1 warmup + 3 timed runs per prompt (`--runs` and `--limit-prompts` adjust this). Median tok/s is recorded. Quality is scored by the rubric's pattern matchers; a prompt with **no** scorer falls back to 0.8, which is a placeholder, not a measurement — treat any model relying on it as unscored.

5. **Run vision benchmarks**: `python3 scripts/benchmark.py --vision --prompts-file prompts/vision_user.py --image-path scripts/test_image_user.png --models <id> ...`. **Always pass `--prompts-file` and the matching `--image-path`** — see the Vision rubric section below for why the default is not trustworthy.

6. **Generate final report**: `python3 scripts/generate_final_report.py` consolidates all CSVs into ranked tables, one section per machine plus a cross-machine comparison.

7. **Push to the Notion table**: `python3 scripts/push_to_notion.py --all` against a populated table (add `--root` if the runs live outside `~/.hermes/benchmark_results`). Idempotent — re-run it any time, including after a scorer fix, and rows are corrected rather than duplicated. **`--results-dir <one dir>` is only safe against an EMPTY table** — `prune()` treats the pushed batch as the whole publish set, so a single-run push archives every other row and mis-flags `latest` in the same stroke (see the pitfall below). To add one new run to a populated table: rename any exploratory arms `_superseded-…` so discovery skips them, then push `--all`.

8. **Optional — scatter plots + PDF**: `python3 scripts/generate_scatter.py --results-dir <dir>`. Plots are saved as `scatter_coding.png`, `scatter_vision.png`, `scatter_coding_efficiency.png`; `scatter_plots.pdf` collects them behind a cover, table of contents and summary page. Pass `--model-config` to override the default `references/model-config.json`. Add `--per-machine` for a per-box set. Pass `--no-pdf` for PNGs only. Nothing in the default flow produces these any more — `run_interactive.py` needs `--plots`.

## Vision benchmarking — read this before trusting a vision number

**The old vision path scored nothing and must not be used.** `benchmark.py`
passed `scorers = None` for vision, so every model took the 0.8 unscored default
and the only real signal was `quality_chars` — a character count of the response.
A model that padded its answer scored higher, so the axis rewarded verbosity and
invention. Worse, the test image was a flat grey rectangle with a caption printed
on it, so every score was measuring hallucination against a blank.

Two grounded rubrics now exist, each paired with an image whose contents are
verified in a `references/vision_ground_truth*.json`:

| rubric | image | use |
|--------|-------|-----|
| `prompts/vision_user.py` | `scripts/test_image_user.png` | **default choice** — real photo, genuinely ambiguous |
| `prompts/vision_grounded.py` | `scripts/test_image_workshop.png` | generated scene, 3 people / workshop |

```bash
python3 scripts/benchmark.py --vision \
  --prompts-file prompts/vision_user.py \
  --image-path scripts/test_image_user.png \
  --models ms-qwen3-vl-8b ms-glm-4.6-vision \
  --runs 1 --enable-thinking false \
  --results-dir ~/.hermes/benchmark_results/vision-$(date +%Y%m%d)
```

**Rubric and image are a matched pair.** `benchmark.py` warns when the image does
not match the rubric's recorded ground truth, because a scorer verified against
one picture is meaningless on another. If you swap the image, re-verify it and
rewrite the ground-truth JSON in the same change.

What makes `vision_user.py` discriminate (the first rubric gave every model
1.00, which ranks nothing):

- **negative existence** — "how many are wearing a red top?" The answer is
  **zero**. Her top is light, so a model pattern-matching light→a-colour says 1
  and is wrong.
- **spatial trap** — "the person on the far left". There is no person there; the
  horse is. The only person stands on the right.
- **small object** — the cat is bottom-corner and occluded by the fence.
- **calibration** — two background elements are genuinely ambiguous. Hedging or
  listing plausible readings scores; confident fabrication does not. This is the
  axis a character count structurally cannot express.

**After changing any scorer, run `python3 test_vision_user.py` and
`test_vision_rubric.py`.** Both must pass. The scorers are regex-heavy and have
a history of silently returning `None` (treated as a low score) when a phrasing
is not covered — see the pitfalls below.

- **Rank vision by the rubric, never by character count — in the report too, not
  just the plot.** The plot was fixed to use `vision_quality` while
  `generate_final_report.py` still sorted by `quality_chars`, so the two
  artifacts ranked the same models differently. Sorting by speed put
  `ms-ministral-3-3b` at #1 (97.5 tok/s, 0.50 quality) and `mb-qwen3-vl-8b` at
  #9 (36.4 tok/s, 1.00). On the rubric, qwen3-vl-8b is #1 and ministral-3-3b is
  #13th. Chars stay as a diagnostic column only. The report reads
  `vision_quality` from model-config.json so a scorer fix applied via
  `--vision-results-dir` is honoured instead of being silently reverted.

**Treat vision tok/s as unreliable.** Measured medians on this box ranged from
1.4 to 80.8 tok/s for the same model across prompts, with completion tokens
swinging 94→512. The quality axis is the trustworthy part of a vision run.

## Results are reported PER MACHINE — do not flatten them

`generate_final_report.py` and `generate_scatter.py` split everything by the
machine that produced it. This is not cosmetic. **tok/s is only comparable
within one box**: the Studio's 151 tok/s and the MBP's 16 tok/s on the same
task are a fact about the hardware, not the model. A single combined ranking
puts `mb-smollm3-3b` (91.9 tok/s, quality 0.65) at #2 overall, above
`ms-gemma-4-12b` (51.8 tok/s, quality 0.35) — implying the 3B laptop model is
the better coder, when within each machine the ordering is different. Each box
also serves a different roster, so a merged table implies comparisons that do
not exist.

Machine identity comes from `scripts/machines.py`, keyed on the `endpoint`
column already in every CSV (measured fact), falling back to the `id_prefix`
in `references/endpoints.json` for rows that lack one. Adding a machine means
adding a prefixed endpoint entry — no code change. Note `load_machines()`
yields `(url, (name, prefix))`; destructure both halves, or the prefix length
comes back as the URL length and every id loses its first two characters.

Two useful consequences:

- **Per-machine rankings answer "which model should this box use".**
- **The cross-machine table answers "why does the same model differ".** It
  strips the prefix so `ms-devstral-24b` and `mb-devstral-24b` line up as one
  model on two boxes. That is the only genuinely cross-hardware comparison
  available, and it is where quantization and runtime differences show up:
  qwen3-vl-8b scored 0.75 coding / 0.88 vision on the Studio and 0.80 / 1.00
  on the MBP, while qwen3.8-27b-swift1.5 collapsed from 0.80 / 0.88 to
  0.50 / 0.62. NOT a quant difference — verified 2026-10-03: both hosts run
  byte-identical Q4_K_M + F16 mmproj (SHA256-matched), identical llama.cpp
  0.5.0 binary, and identical perception (both place the woman right of the
  horse). The gap is a real, unexplained host-level execution difference
  (M3 Ultra vs M5): the MBP deterministically fails the spatial_left trap
  (0.0 x5) while the Studio passes under every MTP recipe (1.0 x5). Same
  family as the documented MTP-throughput inversion between hosts. The
  laptop should not be trusted for this spatial task.

## Pitfalls

- **`POST /v1/databases` accepts a `properties` map and silently drops it.** In
  the 2025-09-03 API the container and its columns are different objects: the
  database is created with `POST /v1/databases`, and the columns are added with
  `PATCH /v1/data_sources/{data_source_id}`. Getting this wrong does **not** fail
  at creation — the database looks fine, and then every row insert fails with
  `Model is not a property that exists`, which reads like a payload bug rather
  than a schema one. And a database may hold exactly one title property, so the
  default `Name` is **renamed** (`{"Name": {"name": "Model"}}`), never re-added
  as a new `title`.

- **A Notion filename regex that demands microseconds hides half the history.**
  Microseconds were appended to CSV names to stop two concurrent sweeps
  colliding, so every run before that carries only `<YYYYMMDD>_<HHMMSS>`. A
  discovery pattern requiring the microsecond group silently skipped the whole
  of September (8 of 10 `fleet/` bundles). Make it optional, and check the
  discovered run count against `ls` before pushing.

- **Count the rows you pushed against the rows you can read back.** A push that
  reports `created N` proves nothing about the table's contents. Query the data
  source and compare the total, then push again and confirm `created 0`. The
  first real backfill here reported 219 created / 0 failed while the database had
  no columns at all — the error was only visible because the rows were read back.

- **Notion rate-limits at ~3 requests/second and does not fail loudly.** The
  client here throttles to one write per 0.34 s and honours `Retry-After` on a
  429; dropping the throttle to go faster mostly produces 429s and a slower
  total. A ~220-row backfill takes about 2.5 minutes, which is the floor, not a
  bug.

- **The Notion sink cannot use the Notion MCP.** Skill scripts run headless in
  cron and from a terminal; there is no MCP session. Auth is the integration
  token from `~/.hermes/.env`, and the parent page must be shared with that
  integration — otherwise every call 404s on a page that plainly exists.

- **A compound view filter is written `{"and": [...]}` — not the shape the API
  returns.** Read-back gives `{"type": "group", "operator": "and", "filters": [...]}`,
  and posting that back is rejected with a wall of `body.filter.or should be
  defined / body.filter.and should be defined / body.filter.title ...`. Writes
  accept `{"and": [...]}`, `{"or": [...]}`, or a bare property filter. A single
  filter stays flat: `{"property": <id>, "checkbox": {"does_not_equal": true}}`.

- **View writes take `property_id`, never the property name.** Sending
  `property_name` fails with `body.configuration.x_axis.property_id should be
  defined`. The ids are opaque ("g:\\i" for Quality, "GEuD" for Deleted) and
  cannot be derived from names — but they ARE stable per data source, so the same
  id shows up whether you read it from a table view or a chart's y-axis.

- **A view's configuration only exposes property ids if you ask for them.** A
  view created bare reads back as just `{"type": "table"}` with no properties at
  all, so it cannot be used to discover the id map. Create the probe view WITH an
  explicit `configuration.properties` array naming every property and the server
  echoes back `property_id`/`property_name` for all of them — which both verifies
  a shipped map and re-discovers it after a database is recreated.
  `resolve_property_ids()` does exactly this, once, and caches the result.

- **`GET /v1/databases/{id}/views` does not exist** (`invalid_request_url`), so
  views cannot be listed. Anything that has to be idempotent across runs —
  reconciliation, "don't re-upload this chart" — must key off local state or a
  marker it can read back (a caption, a recorded id). Enumerating the database's
  views is not an option.

- **Ordered validation hides the real requirement.** `POST /v1/views` reports only
  the FIRST failing check, so a body can look like it fails on `configuration`
  when it is really missing `database_id`. A create needs `database_id` (placement)
  *and* `data_source_id`; if a call starts complaining about
  `Exactly one of database_id, view_id, or create_database`, the rest of the body
  was already accepted.

- **A chart's `x_axis` requires `sort`.** Omitting it gives
  `body.configuration.x_axis.sort should be defined`. And a `number` chart reads
  its measure from `value`, not `y_axis` — passing `y_axis` is accepted silently
  and the chart quietly reports `count` instead of the average or sum you asked
  for. Read the view back and check.

- **Notion file upload is multipart, and a raw PUT "succeeds" as a 400.** The flow
  is `POST /v1/file_uploads` -> multipart `POST` to the returned `upload_url` with
  a file part named `file` -> reference the id in a block. Sending raw bytes
  instead returns HTTP 400 `has an invalid status of pending` — which reads like a
  state problem rather than an encoding one.

- **An uploaded image is attached to a PAGE, and pages' blocks are listable.** The
  frontier scatters go on the parent page with a `◆ <run> · <machine>` caption,
  and the caption set is read back before uploading so a re-push does not stack
  duplicates. Blocks are listable even though views are not.

- **`groupBy` is SILENTLY DROPPED on a table view.** Post it at the view level
  (it is a sibling of `name`/`filter`/`sorts`, not part of `configuration`) and
  the call succeeds — the view then reads back `groupBy: null`. No error, no
  warning. A board accepts the same field. So the API can only group BOARDS;
  grouping a table is a one-click UI action, and `By Model Family` is a board for
  that reason rather than for any design preference.

- **A renamed property breaks a name-keyed cache; a NEW one is invisible to it.**
  The property-id map in `references/notion.json` is keyed by property NAME, so
  `Deleted` → `Retired` left a stale key and every lookup of `Retired` missed.
  Adding `Model Family` was worse: the cache was *valid*, just incomplete, so the
  new column was never looked up and the spec raised KeyError. The fix is to
  compare the cache against the live schema (`GET /data_sources/{id}` returns
  property NAMES) before trusting it, not to trust it because it exists.

- **Adding a column and renaming another in the SAME request collides.** A patch
  containing both `{"Deleted": {"name": "Retired"}}` and a new `{"Retired": {...}}`
  is ambiguous and fails. `ensure_schema()` skips adding any name that appears as
  a rename target. Worth knowing before hand-writing a schema migration.

- **Base architecture comes from the artifact, never from the id.** The GGUF's
  `general.architecture` is evidence; inferring a base from a model name is how
  you label a Qwen model as a Llama one. `ms-kat-coder-v2.5` reads `qwen35moe`.
  When no GGUF is reachable the cell is left BLANK — blank means "not verified",
  and roughly a third of the historical rows are blank because those models are
  retired (not in any config, so no path) or came from MLX/oMLX runs that never
  had a GGUF. Never fill those in by guessing.

- **The `gguf` pip package is a different version on each Mac.** The Studio's
  copy reads fine; the MacBook's raises `AttributeError` on the same call. A
  dependency that behaves differently on the two hosts of a two-machine fleet is
  worse than no dependency, so `model_family.py` parses the GGUF header with
  struct instead — identical everywhere, no install, and ~4s for 19 models
  because it stops as soon as it has the keys it wants and never walks the
  tokenizer vocabulary.

- **The MacBook's GGUFs are readable from the Studio over ssh, and that is how
  their architectures get filled in.** Its config holds `/Users/prasta/Models/...`
  paths that resolve only on that box, so `remote_arch_map()` pipes
  `model_family.py` itself over ssh and runs it there — nothing has to be
  installed on the far side. A failure returns `{}`, so a sleeping laptop leaves
  those rows unverified instead of breaking the push. `--no-arch` skips it.

- **"Retired" on the table, `deleted` in the pipeline — on purpose.** The column
  was renamed for the reader; the JSON field was NOT, because `deleted` is
  written into every `model-config.json` on disk and read by four scripts plus
  `--carry-forward`. A half-migrated rename is the exact failure the "merge's
  name universe never shrinks" pitfall already describes: if a reader is missed,
  retired models silently stop being marked. Only the label a human reads moved.
  The same applies to the strings in `generate_scatter`/`generate_final_report`/
  `reconcile()`, which still say "deleted".

- **`_`-prefixed directories are archive markers, not runs.** `fleet/_superseded-mixed-pile`
  and `_archive-pre-skill` hold measurements that were replaced on purpose.
  Discovery skips any path component starting with `_` or `.`; without that rule
  they land in the table looking exactly like live results. This is also the way
  to keep an exploratory arm OUT of the table while leaving it on disk as an
  audit trail: rename it `_superseded-<what>` and it stops being a run.

- **`push_to_notion.py --results-dir <one run>` ARCHIVES the whole table.**
  `prune(api, state, {r["key"] for r in all_rows})` takes the pushed batch as the
  complete publish set, so a single-run push marks every other row stale and
  archives it — and `mark_latest()` is batch-level for the same reason, so
  `latest` would flag only that run. Verified 2026-11-04: against a 230-row
  table it would have archived all but 2 rows. Use `--all` on a populated table;
  reserve `--results-dir` for an empty one. `grist_sink.py` carries the same
  hazard, except its prune is a hard `RemoveRecord` rather than Notion's
  reversible `archived: true`. Before any large push, snapshot the key→page_id
  map (`existing_keys()`) so a prune stays reversible.

- **The 512-token default confounds EVERY model whose reasoning budget is
  ≥ 512 — and it misgrades partially, not just down to 0.00.** `benchmark.py`
  defaults to `--max-tokens 512`. A model served with `--reasoning-budget N`
  where N ≥ 512 cannot finish deliberating inside that budget, and the scorer
  (`text = msg.get("content") or msg.get("reasoning_content", "")`) then grades
  whatever fragment exists — the reasoning preamble standing in for the answer.
  Measured 2026-11-04 on `mb-qwen3.6-coder-27b` (served `--reasoning-budget
  1500`): **0.55 at 512, 0.80 at 2048, 0.85 at 4096** — the first budget where
  every prompt reached `finish_reason: stop`. Same weights, same prompts, same
  box; the sinks carried 0.55 as the fleet's current measurement because the
  harness's own default was the confound, not the model. It read as "the
  dedicated coder is worse at coding than a general MoE", which is false.

  Before trusting any low quality score, diff the served `--reasoning-budget`
  (or the model's observed reasoning output) against the `--max-tokens` the run
  used, and confirm `finish_reason == "stop"` on EVERY prompt at the budget you
  chose — `length` means you are still measuring a truncation. 2048 is not
  automatically enough; this coder needed more than it. A model that reasons
  can also need 4-8x the default the harness assumes.

- **Two concurrent sweeps silently destroy one CSV.** CSV names are
  `<prefix>_<timestamp>.csv`; two runs launched together start their first model
  in the same second, so the names collide and the slower process OVERWRITES
  the faster one's file. A two-machine sweep lost a full 4-prompt coding result
  (rows present in the log, absent from every CSV). Names now carry
  microseconds. If you run two machines at once, still diff the model count in
  the CSVs against the model count in the logs before trusting the merge.

- **`adjustText` can fling a label off-canvas and `bbox_inches='tight'` will
  follow it there.** One escaped label turned a 15.5x10.5in figure into
  66x12,440in and a 116 MB PNG that never finished writing. `_resolve_labels`
  now leaves in-bounds labels alone and pulls escaped ones back beside their own
  marker — do NOT snap them all to the nearest edge, which stacks every escaped
  label into one unreadable corner. All savefig calls go through `_savefig()` so
  dpi and pad live in one place. PDF chart pages do NOT use the tight bbox: they
  save at the fixed 15.5×10.5in figure size (tight_layout fits the content), so
  every page in the document is the same size.

- **adjustText 1.x silently ignores the 0.x keyword names.** `expand_points`,
  `expand_text`, `lim`, `precision` and `autoalign` raise no error — they are
  swallowed — so labels were barely de-overlapped and piled on top of each
  other. `_resolve_labels` uses the 1.x names (`expand`, `force_text`,
  `force_static`, `iter_lim`, `ensure_inside_axes`). Check
  `inspect.signature(adjust_text)` before tuning it.

- **A fixed y-axis floor hides the models a fleet audit exists to find.** The
  coding plot was clamped at `ylim(0.55, …)`, so every model scoring below 0.55
  (ms-nuextract3, the granite family, ms-trinity, ms-gemma-4-12b — 9 Studio
  models) was silently off the chart. The floor now follows the data.

- **Do not trust a vision model's description of label layout.** Two reads of a
  correct 28-label plot both reported "all labels stacked in the top-right
  corner, unreadable." Measuring the rendered text extents showed 16 overlapping
  pairs out of 378 and ZERO labels outside the axes — the plot was fine and the
  reads were wrong; 28 leader lines just look like a wall when skimmed. Verify
  geometry numerically (`get_window_extent`) before "fixing" a layout.

- **The Homebrew python has no `adjustText`, and pip is PEP-668 blocked.** Use a
  throwaway venv (`python3.14 -m venv /tmp/benchvenv && pip install matplotlib
  numpy adjustText`) rather than `--break-system-packages`.

  Re-measured 2026-10-27, and the original wording was wrong about *which*
  interpreter: this is a Homebrew-python problem, not a general one.
  `/opt/homebrew/bin/python3` (3.15) has matplotlib 3.11.2 but no adjustText, and
  its pip refuses with PEP 668. **`/usr/bin/python3` (3.9.6 — what `python3`
  resolves to) has BOTH matplotlib 3.9.4 and adjustText 1.4.0**, and rendering
  works. So plots and the Notion chart upload run fine through `sys.executable`.
  The claim that the default python "cannot import matplotlib at all" was false;
  check which interpreter you are actually on before reaching for a venv.

- **A PDF summary that averages across machines contradicts the skill's own
  rule.** The summary page first printed "All Machines — 197.1 GB on disk" and a
  combined mean tok/s. Both were wrong: only one host's models carry `size_gb`,
  so the total silently covered 23 of 41 models, and averaging tok/s across
  hardware is exactly the comparison the per-machine split exists to prevent.
  Partial totals now print as `197.1 GB across 16 sized`, and any group spanning
  machines gets its speed average suppressed with a note. The same rule covers
  every speed-derived line — "Fastest", best tok/s/GB and the frontier are all
  hidden for a mixed group; only quality is ranked there. When adding a summary
  number, ask which subset it actually covers before printing it.

- **`matplotlib.backends.backend_pdf` is not an attribute until you import it.**
  `matplotlib.use('Agg')` does not load the PDF backend, so
  `matplotlib.backends.backend_pdf.PdfPages` raises AttributeError. Use
  `from matplotlib.backends.backend_pdf import PdfPages`.

- **`global X` at module level is a SyntaxError, not a no-op.** Resetting a
  module counter inside an `if __name__ == '__main__':` block must be a plain
  assignment — the block IS module scope, so adding `global` there fails with
  "name is assigned to before global declaration".

- **A blank PDF page is worse than no page.** A group with no vision or
  efficiency data still writes a placeholder PNG (existing behaviour worth
  keeping), but those must be passed `pdf=None` — otherwise a 12-page report
  carries four empty pages. Page numbers in the contents are assigned from a
  plan that skips those axes, so the two stay consistent.

- **The merge's name universe never shrinks — reconcile it or you get ghosts.**
  `read_rows` globs `{prefix}_*.csv` with no recency window and unions every
  distinct model name found, so a model benchmarked once and later pruned or
  renamed lives in `model-config.json` forever. `deleted` was hardcoded `False`
  and nothing ever set it `True`, which made the grey-X "deleted" rendering in
  `generate_scatter.py` permanently dead code: a pruned 8B sat at rank #2 on the
  coding chart at 134.8 tok/s for weeks, indistinguishable from a real model.
  11 such ghosts accumulated. `reconcile()` now decides from the llama-swap
  config, and `--carry-forward` stops a partial run shrinking a 41-row fleet
  file to the 2 models it just touched.

- **Never infer "this prefix is local" from the URL.** `endpoints.json` has
  `llama-swap-mbp-loopback` at `127.0.0.1:8999` carrying prefix `mb-`, so a
  loopback-means-local test classifies the MacBook's entire roster as local and
  marks all 14 `mb-*` models deleted on the Studio — silently dropping a whole
  machine's results. Derive it from the config instead: a prefix is local iff
  this host's config declares a key carrying it. That is self-consistent on both
  boxes, where the URL is not.

- **Two files claimed to be the source of truth.** `run_interactive.py` wrote the
  merge to `<results_dir>/model-config.json` while `generate_scatter.py` and
  `generate_final_report.py` both default to reading
  `references/model-config.json`. Nothing reconciled them, so the interactive
  path — the documented preferred one — never updated the file the charts read.
  The two files now have separate jobs. **`<run>/model-config.json` is the run
  view**: built from that run's CSVs only, and what that run's plots and report
  read. **`references/model-config.json` is the fleet view**: the latest known
  value per model per field across every run. The interactive flow writes the
  run view, then folds the run into the fleet view with `--carry-forward`. Only
  the built-in coding family folds in, because `--family` writes its scores
  into the coding fields. Carry-forward fills the fields a run did not measure
  from the previous fleet row, so a vision-only run cannot wipe coding scores.

- **Skipping `build_model_config.py` silently re-plots the PREVIOUS run.** The
  plotting scripts read `references/model-config.json` and never read the CSVs.
  A fresh benchmark that skips the merge produces confident plots of old numbers.
  `run_interactive.py` does the merge for you; if you run the steps by hand, do
  not skip it. It also needs `--family <prefix>_bench` for a non-default rubric
  (default `coding_bench`), or it globs nothing and merges an all-null config.

- **`from prompts import <family>` does not work.** `scripts/prompts.py`
  *shadows* the `prompts/` directory of the same name, so that import resolves to
  the module file and raises ImportError. Load families by path via
  `parse_prompts_file()`, as `benchmark.py` now does internally.

- **A model advertised by llama-swap can still be unloadable.** Two models
  (`ms-qwopus3.8-27b-flash`, `ms-qwen3.5-4b-mtp`) appeared in `/v1/models` but
  returned HTTP 500 on every request: their GGUF symlinks had been created with
  backslash-escaped paths (`/Users/macstudio\.hf\/...`), so the link target was
  a literal, non-existent filename. `ls -la` on the model dir and
  `[ -e "$path" ]` per target will find it; `build_model_config.py` reports
  `!! GGUF path broken` and a 0.0 GB size as a signal. The weights were present
  the whole time — no re-download needed, just `ln -sfn` with unescaped paths.

- **A two-machine fleet breaks the size merge.** `build_model_config.py` stats
  GGUF paths from the config of whichever host runs it, so a Studio-side merge
  reports every `mb-*` model as 0.0 GB with `broken_paths` — the paths live on
  the MBP. Measure sizes on the host that holds the weights and pass
  `--extra-sizes <json>` (map of `{id: {size_gb, broken: []}}`); local entries
  always win. Without this the efficiency plot has every remote model at zero
  size.

- **`--model` in a prose comment reads as a broken GGUF path.** The size
  scraper takes the token after `--model`/`-m`/`--mmproj`; a config comment
  containing that literal word yields a bare word like `wired`, which then gets
  reported as a missing file. Paths are filtered on containing `/`. A
  `!! GGUF path broken` flag on a model that just benchmarked cleanly is this
  bug, not a real missing file — confirm with `ls` before re-downloading
  anything.

- **A fresh vision run used to write NO `vision_quality`, so the vision scatter
  silently ranked by character count.** `build_model_config.py` computed
  `vision_quality` only inside `if args.vision_results_dir:`, and no default flow
  (`run_interactive.py` included) passes that flag — it exists for superseding a
  scorer fix. So the ordinary vision run left the field absent, and
  `generate_scatter.py`'s `graded = any(vision_quality is not None)` fell through
  to `vision_chars`: the verbosity axis this skill exists to replace, on the
  exact run a human is reading. Fixed — the field is now computed from the
  primary dir's own `vision_bench` CSVs, and `--vision-results-dir` still
  supersedes them. Verify after any change here: a run's `model-config.json` must
  carry `vision_quality` for every model that has vision rows, with no flag.
- **`generate_scatter.py` grouped machines by id prefix, inventing a phantom
  "Unassigned models" group.** It called `machine_for_model` (prefix match) on
  model-config entries, which carry no endpoint — so `sushi`, which deliberately
  has no `ms-` prefix, matched nothing and the Studio's largest model was plotted
  under a group that is not a box (and split the PDF/plot set in two).
  `machines.group_rows` and `push_to_notion` had always resolved by the CSV's
  `endpoint` column (measured fact); the plots now do too, falling back to the
  prefix only for entries with no rows. Symptom to watch for: a per-machine run
  reporting one more group than there are machines.
- **A row measured through a prefix-less endpoint can never be assigned to a box.**
  `machines.load_machines()` keeps only registry entries that declare an
  `id_prefix`, on the reasoning that those are the ones describing a served model
  roster, so `lm-studio` (127.0.0.1:1234) and `omlx` (127.0.0.1:8010) are dropped
  and every row from them lands in `Machine = 'unassigned'` — even though both
  entries already carry `host: Mac Studio (local)`, and the URL is the grouping
  key `machine_for_endpoint` is supposed to use. Six such rows came from one
  September run dir, four already retired, and the two live ones
  (`kat-coder-v2.5-dev-mtp`, `qwen3-coder-30b-a3b-instruct`) are served by
  neither config, so they showed up Frontier-flagged on the global bar charts
  with no box attached. An explicit `machine` field on a prefix-less registry
  entry, honoured by `machine_for_endpoint`, is the fix — not another filter.
- **`NO_FRONTIER_FAMILIES` was keyed on a string `family_of()` never returns.**
  The constant held `{"vision_bench"}` but `CSV_RE` strips the `_bench_` suffix,
  so `family_of()` yields `"vision"` — the guard never fired and the Notion
  table marked a Pareto frontier on vision rows, the one axis the module
  docstring says cannot carry one (vision tok/s swings 1.4–80.8 for a single
  model). Silent: no error, just a frontier flag on the wrong family. Any set
  keyed on a `family_of()` result must match the stripped name.
- **A rubric that gives every model 1.00 ranks nothing.** The first grounded
  vision rubric scored 1.00 across the board because the scene (3 people, 3
  prominent objects) was too easy: the ground truth was unambiguous *and*
  trivial. Difficulty has to come from somewhere real — a photo with occlusion,
  attribute-filtered counting, a spatial trap, and genuinely ambiguous elements.
  Verify discrimination with a deliberately weaker model before trusting a
  ranking.

- **Keep scorers on a 0–1 scale with no weight juggling.** Two bugs in a row came
  from weighting: letting each prompt's ceiling be its own axis weight (a perfect
  answer scored 0.20 on one prompt, 0.35 on another), then "fixing" it by
  dividing by the weight without multiplying first (scores of 2.86 and 5.00).
  Write each specific scorer to return 0–1 and use it directly. The weights in
  the ground-truth JSON document priority for a human reader; they are not
  arithmetic.

- **`score_debugging_duplicates` penalizes the correct list-based fix.** Its "fix correct" check requires `return list(set(` in the code, but the right fix for unhashable items is to drop the set entirely (a `seen` list + `dict.fromkeys`/`return duplicates`). Both LFM2.5 builds produced exactly that correct fix and scored 0.4 — a scorer artifact, not a reasoning failure. When a model scores low on this prompt, read the actual output before trusting the number: a correct unhashable-safe rewrite that abandons `set()` is the model being right, not wrong.
  `prompts/vision_user.py` binds a count to a colour word, so a bare `0, 0` or
  `none / none` returned None and scored 0.00 — while a verbose `Red: 0 /
  Blue: 0` scored 1.00 for the identical fact. The prompt says "Give a number
  for each. If there are none, say none", so terseness IS compliance. glm-4.6v
  and gemma-4-12b lost 0.25 each before a positional fallback was added (bind
  numbers in asked order when no colour anchor exists, only when the count
  matches the number of colours). General rule: when a scorer returns None,
  re-read the PROMPT before blaming the model — and verify with a live probe,
  not the CSV, because a 0.00 next to a short `quality_chars` is the tell.

- **A 0.00 quality with a full 512-token completion is a budget artifact, not
  a bad answer.** R1-style models emit `reasoning_content` and leave `content`
  empty; `benchmark.py` reads `content` first and only falls back to
  `reasoning_content`. Confirm by probing the endpoint directly and comparing
  `content_chars` vs `reasoning_chars` in the raw response. Raising
  `--max-tokens` does NOT help if the template ignores `enable_thinking: false`
  —  on `mb-deepseek-r1-32b` at 512 tokens: content 0 chars, reasoning 2228.

- **Never compare a model WITH a reasoning cap to one WITHOUT.** Measured
  2026-10-28: qwen3.5-4b uncapped against a 1.7B at `--reasoning-budget 256`
  read as 15/19 vs 17/19 with a 2x token gap. Both capped: 17/19 vs 16/19 — the
  conclusion was backwards. Diff the two `cmd:` lines side by side first; a flag
  on one arm only invalidates the run and nothing in the output says so. The
  check is worth running for its own sake: it found that
  `ms-qwen3.5-4b-mtp` had NO cap and was burning 1500-3000 reasoning tokens on
  trivial prompts into empty content.

- **A substring grader can pass a confidently WRONG answer.** A count question
  graded `expected in content` passed a model answering 24 instead of 22, because
  its rambling enumeration happened to list a "22" among thirty model names. For
  numeric answers: require a SHORT reply (reject >80 chars as `rambling`), extract
  integers and require exactly one match, and keep `rambling` distinct from
  `missing` and `empty` in the reason string. `scripts/head_to_head.py` does this.

- **Re-run every failing item at 2-3x the token budget before scoring it.**
  `finish_reason: length` with empty `content` is exhaustion, not capability; a
  `length` reply with an answer buried in prose is a real and worse finding
  (no stopping discipline); a clean `stop` with a wrong answer is the only
  genuine capability miss. Any model emitting `reasoning_content` first is
  exposed to all three.

- **Pairing numbers to colours by distance is wrong.** In "1 person in a red top
  and 0 wearing blue", the `0` is *closer* to "red" (14 chars) than red's own `1`
  is (18). Nearest-overall sends both halves of "nobody in red and nobody in
  blue" to red. Anchor on the colour words and cut the text at them, then bind
  each number to the region it falls in. Also: a bare "no" is a zero count, a
  lookahead window must be wide enough to contain a whole colour word (24 chars
  clipped "blue" to "blu"), and "zero people in red" is a colour count while
  "only one person in the image" is a headcount.

- **Streaming endpoints inflate tok/s if elapsed is measured before the body read**: oMLX (and any SSE/chunked server) sends headers before the body finishes streaming. If `elapsed` is captured on entering the `urlopen` context (before `resp.read()`), it under-measures time and tok/s balloons (a 27B MLX model read as 255 tok/s when the real number was 34). Measure elapsed AFTER `resp.read()` completes. llama-swap buffers the full body so it was unaffected, but the fix is correct for every endpoint.
- **Qwen3 thinking models**: When `max_tokens=512`, Qwen3 thinking models put all output in `reasoning_content` and leave `content` empty — quality scores show 0.0. Fix: raise `--max-tokens`. **`--enable-thinking=false` is NOT a reliable fix** — it is inert against a model whose server cmd carries `--jinja` + `--reasoning-budget`. Measured 2026-11-04: the two arms of `mb-qwen3.6-coder-27b` produced byte-identical `completion_tokens` (2048/1479/1834/2048) and identical scores, so the second arm was a no-op rather than a control. Verify the flag did something before treating two arms as two data points — diff `completion_tokens` between them; identical counts mean the request flag was ignored and the reasoning budget is server-side only.
- **Vision URL vs base64**: llama-swap mmproj API does not support URL image fetching. URL-based image inputs fail with errors. Always use `data:image/png;base64,...`.
- **On-demand model loading**: llama-swap swaps models in on first request. Retry on HTTP 503/502/504 with 5s delay, up to 30 attempts.
- **4B models are deceptively fast**: Tiny models (qwen3-4b, phi4-mini) hit 110+ tok/s but quality is capped at 0.80 — speed without capability. Compare quality, not just speed.
- **Deleted model labels overlap**: On coding plot, the three 110+ tok/s 4B models cluster near each other. Use vision or efficiency plot for clearer separation.
- **Legend placement**: One row above the plot, right-aligned opposite the subtitle (`loc='lower right', bbox_to_anchor=(1.0, 1.008)`), listing only the types present. Inside the axes it covered the top-left corner — where a slow, high-quality model plots and where the frontier starts.
- **Embeddings in the config**: `model-config.json` includes bge embedding/reranker entries (`type: "Embeddings"`). They plot as grey diamonds; they are not benchmarked (no coding/vision scores).

- **A Grist chart can render STALE label text against fresh points.**
  Symptom: the label drawn next to a dot belongs to another row, so a reader
  reads a number off a point that is not that model. Measured on the live doc: the
  text `ms-hermes-4-14b` was drawn centred on the dot for a different
  model at 136.7 tok/s, while its own dot at 53.9 tok/s carried another model's
  name — and the same chart printed `ms-hermes-4.3-36b` on the dot at 211.8 tok/s
  whose own row is 5.62. The dots are in their true places (their (speed, quality)
  coordinates match the table's per-quality row counts exactly, and the x scale
  measured 6.45 px per tok/s from the chart's own tick labels), so it is the text
  array that is misaligned. No ordering of the rows reproduces the permutation:
  id order, reverse id, alphabetical, quality-then-speed, speed desc, run order,
  the unfiltered 293-row column, and every fixed offset of each of those were all
  tested against 21 label/point pairs and none exceed chance. **A page reload
  cleared it**: all four sampled points then read correctly, so this is a STALE
  CLIENT RENDER, not a data or config fault. Reload before investigating, and
  still never take a number from a chart label when the table has it. Verify
  geometry instead of eyeballing: dot centres as connected components of the
  series colour, x calibrated from the tick labels (`x_px = a + b*value`), each
  text block read with a VL model.

- **A model retired on the OTHER box never gets marked Retired.** `reconcile()`
  treats an id carrying a remote prefix as "absent from this host's config by
  design, not stale", so a Studio-side merge keeps every `mb-*` id live after the
  MacBook has dropped it. Verified: `mb-hermes-4-14b` is in neither llama-swap
  config — its weights are gone from both machines — and a fresh merge still
  writes `deleted: false` for it, purely because of its prefix. Retirement only
  propagates for ids this host's own config declares. A peer-reported retire list
  in the `--extra-sizes` shape (there is already `mbp-sizes.json` measured on the
  MacBook) is the missing piece; until it exists, a dead laptop model keeps a
  live row, and any chart filtered on `Retired` still shows it.

## Verification

```bash
# Verify all scripts run cleanly
python3 scripts/generate_scatter.py --output-dir /tmp/skill_test --results-dir /dev/null
python3 scripts/generate_final_report.py --model-config references/model-config.json

# Verify the Notion sink without writing anything
python3 scripts/push_to_notion.py --all --dry-run     # prints the rows it would send

# Verify the views reconcile (dry run lists would-create / would-update)
python3 scripts/push_to_notion.py --views-only --dry-run

# Verify classification: family from the id, architecture from the GGUF
python3 test_model_family.py
python3 scripts/model_family.py --families ms-kat-coder-v2.5 ms-hermes-4-14b
python3 scripts/model_family.py --emit-arch-map ~/.hermes/llama-swap/config.yaml \
    --only ms-qwen3-14b
```

A **blank `Base Architecture` is not a failure.** It means no GGUF was reachable,
which is the expected state for a retired model (absent from every config, so
there is no path to read) and for MLX/oMLX runs that never had a GGUF. About a
third of the historical rows are blank for exactly those reasons. Blank means
"not verified"; filling one in from the model name is the thing this column
exists to avoid.

Views and charts are idempotent by a different test than rows: run the real
command twice and the second pass must report `updated` (never `created`) for
every view, and `0 uploaded, N already on the page` for the charts. A view that
keeps getting recreated means its recorded id is wrong in
`references/notion.json`.

For a real push, verify by **reading the table back** rather than trusting the
push's own count: query the data source, compare the total against `--dry-run`,
and push twice — the second run must report `created 0, updated N`. A table that
was created without its columns still accepts the push attempt and fails every
row, so a green run is not evidence on its own.

Check that `scatter_coding.png`, `scatter_vision.png`, and `scatter_coding_efficiency.png` are created with:
- Legend as one row above the plot, top right
- Deleted models as grey X markers with grey labels
- Model name annotations on active model markers (uniform size; type is shape + colour)
- Per-machine speed × quality: dashed frontier staircase, beaten models dimmed,
  subtitle reading `N models · K on the frontier`
- The lowest-scoring model is on the chart, not below the y-axis

Check `scatter_plots.pdf` exists and its page count matches the printout
(`N pages: 3 front matter + M charts`).

**Verify the front matter by looking at it, not by reading the .pdf.** Text
overlap and page-number drift are invisible in the file itself and there is no
PDF renderer on this box (`pdftoppm`, `mutool`, `gs`, Quartz all absent). Render
the pages straight to PNG through the same code path the PDF uses:

```bash
python3 scripts/generate_scatter.py --results-dir <dir> \
    --model-config references/model-config.json --per-machine \
    --preview-pages /tmp/fm
```

Then inspect `/tmp/fm/page1.png` (cover), `page2.png` (contents), `page3.png`
(summary) with `vision_analyze`. `--preview-pages` reuses the same group plan
and the same page functions as the real run, so what you inspect is what the
PDF contains — and it prints the last chart page so you can confirm the contents
entries land inside the document.

Do not "fix" a layout from a vision read alone. Two reads of a correct 28-label
plot both reported it as a stacked mess; measuring the rendered text extents
showed 16 overlapping pairs out of 378 and zero labels outside the axes. Confirm
geometry numerically before changing spacing.

---

Load methodology details on demand:
`skill_view(name='benchmark-model-fleet', file_path='references/benchmark-methodology.md')`

Load the pairwise head-to-head protocol on demand (use before any two-model
decision; it carries the three traps that produced a wrong verdict once):
`skill_view(name='benchmark-model-fleet', file_path='references/pairwise-head-to-head-protocol.md')`

Load the optimization-comparison layer on demand:
`skill_view(name='benchmark-model-fleet', file_path='references/optimization-comparisons.md')`

Load Qwen3.8-27B-specific sweep config on demand:
`skill_view(name='benchmark-model-fleet', file_path='references/qwen38-27b-sweep-paths.md')`

## lm-evaluation-harness Benchmarking

For evaluating LLMs on academic benchmarks (MMLU, GSM8K, HumanEval, HellaSwag, TruthfulQA, ARC, WinoGrande), use the EleutherAI lm-evaluation-harness — the industry standard used by HuggingFace and major labs. Full task reference and API/distributed/custom-task guides live in the archived `evaluating-llms-harness` skill under `~/.hermes/skills/.archive/`.

### Quick setup

```bash
pip install lm-eval
```

### Core reasoning benchmarks

- MMLU (Massive Multitask Language Understanding) — 57 subjects, multiple choice
- GSM8K — Grade school math word problems
- HellaSwag — Common sense reasoning
- TruthfulQA — Truthfulness and factuality
- ARC (AI2 Reasoning Challenge) — Science questions

### Code benchmarks

- HumanEval — Python code generation (164 problems)
- MBPP (Mostly Basic Python Problems) — Python coding

### Backend options

- **HuggingFace**: standard, slower
- **vLLM**: 5-10x faster with PagedAttention

### Common issues

- **Slow evaluation:** use vLLM backend, reduce num_fewshot to 0, or evaluate subset of MMLU (mmlu_stem)
- **Out of memory:** use --batch_size 1 or load_in_8bit=True
- **HumanEval not executing code:** pip install human-eval and use --allow_code_execution
- **Different results than reported:** verify num_fewshot count and exact task name

### When to use vs benchmark-model-fleet

- Use **lm-evaluation-harness** when: benchmarking on academic standards (MMLU, GSM8K), comparing model quality with standardized prompts, reporting reproducible metrics
- Use **benchmark-model-fleet** (this skill) when: auditing a local model fleet for speed/quality tradeoffs, right-sizing deployments, generating scatter plots of model performance

## References

- `references/vision-benchmark-protocol.md`: vision run protocol, ranking rules, oMLX endpoint quirks (moved from MEMORY.md 2026-10-01)
