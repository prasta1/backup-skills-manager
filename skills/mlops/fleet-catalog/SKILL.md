---
name: fleet-catalog
description: Generate a derived catalog of the served model fleet.
version: 0.1.0
author: Hermes
platforms: [macos]
metadata:
  hermes:
    tags: [LlamaSwap, Inventory, Fleet, Provenance]
---

# Fleet Catalog Generator

Build a queryable inventory of every model llama-swap serves, derived mechanically from `config.yaml` plus the latest benchmark CSVs. One source of truth, one generated artifact, zero hand-maintained copies.

**What it does**: parses every llama-swap config (Studio + MacBook when its home share is mounted), stats every model on disk, resolves group and capability, folds in the most recent benchmark numbers AND per-model usage from the activity logs, and emits `catalog.json` + a flat `catalog.md` table + a self-contained `catalog.html` viewer (sortable, filterable, offline) + a `catalog-widget.html` fragment for the Hermes `::preview` frame.

**What it does NOT do**: rename anything, edit `config.yaml`, or make judgment calls. Every field is either read from the config, measured from disk, or marked `null`. It is a mirror, not an editor.

**Key dependency**: `config.yaml` (source of truth), Python stdlib + `pyyaml`. No network. The MacBook config is read from `/Volumes/prasta/.hermes/llama-swap/config.yaml` only while that share is mounted; when it is not, the MacBook fleet is skipped with a warning (never a failure).

## When to Use

- "What do I actually have, and what is it for?"
- "Which models are vision-capable and which are embeddings?" (capability)
- "What is the disk cost of the fleet, per model?"
- "Is anything broken?" — missing GGUFs, orphans, broken symlinks, image
  ghosts (LFS stubs), config inconsistencies. The rename is one past instance
  of this, not the whole question.
- "What optimizations are available, executed on, and left untouched for
  tuning?" — per-model enabled/available/untouched buckets, plus a fleet-wide
  tuning view.
- Before pruning, deleting, or reordering the ondemand list.
- Any time you are about to hand-copy a model id into a second file.

Do **not** use it to change the fleet. It is deliberately read-only.

## Scope: text LLMs AND image models

The catalog answers the same five questions for two fleets:

- **Text LLMs** (llama-swap served) — derived from `config.yaml`, rich fields
  (ctx, params, quant, arch, bench, usage).
- **Image models** (ComfyUI on the Studio, Unsloth on the MacBook) — derived
  from the model directories on disk (no config file exists for them).
  Fields: id, host, backend, role (DiT/TE/VAE), size, censored, steps,
  optimizations. Ghosts (LFS stubs registered but not on disk) are the
  image-analog of orphans.

Image models are scanned offline from known directories
(`IMAGE_MODEL_DIRS`); the MacBook's HF-cache sizes are measured over ssh
because the SMB mount cannot read HF-cache symlinks (EINVAL). `censored` is
only asserted when the filename says so (uncensored/abliterated/heretic/nsfw
→ false); otherwise it is null — the catalog never guesses.

## Optimizations (tuning view)

Each model carries an `optimizations` object with three buckets:
`enabled` (what's on, from config or the filename), `available` (what the
family/hardware supports), `untouched` (available minus enabled — ready for
tuning). The curated capability map lives in `references/optimizations.md`
and is the single place to add an optimization; the catalog just reads it.
The HTML and markdown both render a fleet-wide tuning table (every model,
text + image, with its three buckets).

## Prerequisites

- `~/.hermes/llama-swap/config.yaml` exists.
- `python3` with `pyyaml` (`python3 -c "import yaml"`).
- Benchmark CSVs in `~/.hermes/benchmark_results/` are optional; results columns fill in when present.

## How to Run

Invoke through the `terminal` tool:

```bash
python3 scripts/fleet_catalog.py                 # write catalog.json + catalog.md + catalog.html + catalog-widget.html
python3 scripts/fleet_catalog.py --check         # exit 1 if anything is wrong, write nothing
python3 scripts/fleet_catalog.py --out-dir "/some/other/dir"   # override OUT_DIR_DEFAULT
python3 scripts/fleet_catalog.py --no-bench      # skip CSV merge, isolate config problems
python3 scripts/fleet_catalog.py --open          # also open catalog.html in the default browser
```

**Where the output goes.** All four artifacts land in `OUT_DIR_DEFAULT` — the
iCloud Hermes infra folder:

```bash
OUT="/Users/macstudio/Library/Mobile Documents/com~apple~CloudDocs/Hermes/infra/fleet-catalog"
```

That is the Studio's local path. It is the **same iCloud folder** Patrick sees
on the MacBook as `/Users/prasta/Library/Mobile Documents/com~apple~CloudDocs/
Hermes/infra/fleet-catalog` — one Apple ID, one synced folder, two local
paths. Write the Studio path and the catalog appears on the other devices on
its own; never write a second copy somewhere else to "make it visible".

**Quote `OUT` in every shell command.** The path contains spaces and the
literal tildes in `com~apple~CloudDocs`, so an unquoted reference word-splits.
`~/.hermes/outputs/fleet-catalog` is retired — it was moved here wholesale on
2026-10-28, so anything still pointing at it fails with `No such file or
directory`.

**Every reader resolves `catalog.json` from this one path** — never a private
copy: `models/docs/gen_dashboard.py` (the dashboard's served section, drift-
checked weekly) and this skill's sibling `llama-benchy-quick-bench`
(`scripts/benchy_interactive.py`, annotating models with ctx/size). Repointing
the generator without repointing them is what breaks the weekly drift check.

**Ephemeral output (the point of a run):** run with `--open`. After
generating, the script launches `catalog.html` — the STANDALONE page with
full sort/filter interactivity — in the default browser via `open`, so
the catalog opens in a real browser as the last step of the run. The
`--open` flag is explicit, never the default: the weekly cron validation
and anything else that calls the generator as a side effect must not pop
a browser window (explicitly override with `--open` only when a human
wants the page in front of them).

In-session, you may additionally mirror the page with an absolute-path
directive on its own line — the standalone page, not the widget:

```
::preview{file="/Users/macstudio/Library/Mobile Documents/com~apple~CloudDocs/Hermes/infra/fleet-catalog/catalog.html"}
```

The in-chat preview is the static mirror; the browser open is the full
interactive viewer. Use the absolute path above verbatim; the frame
resolves relative paths against the session cwd, which can differ.
**Never preview `catalog-widget.html`** — the widget is the app-themed
fragment for `::preview` frames and will render with the app theme, not
the paper design. The frame injects its theme before the page's styles,
and the page's own styles override it, so `catalog.html` always renders
as the approved paper design (verified against the app's srcdoc
construction, 2026-10-24). If a preview ever looks app-themed, the wrong
file was framed. The durable artifacts (`catalog.json` / `catalog.md`)
still land in `--out-dir` for anything downstream; the HTML itself is
disposable and never hand-edited.
`--check` is the one to wire into a cron or pre-commit habit: it validates without writing, so it can run on every config edit.

## Quick Reference

| Flag | Default | Notes |
|------|---------|-------|
| `--config` | `~/.hermes/llama-swap/config.yaml` | Studio source of truth |
| `--mb-config` | `/Volumes/prasta/.hermes/llama-swap/config.yaml` | MacBook config (skipped when share unmounted) |
| `--no-mb` | off | Skip the MacBook config even when mounted |
| `--results-dir` | `~/.hermes/benchmark_results` | Benchmark CSVs |
| `--activity` | `~/.hermes/llama-swap/activity.sqlite` | Studio activity log; MacBook's is added when mounted |
| `--out-dir` | `OUT_DIR_DEFAULT` (iCloud `Hermes/infra/fleet-catalog`) | Where catalog files land; hold the path in `$OUT` and quote it |
| `--check` | off | Validate only, write nothing, exit 1 on problems |
| `--no-bench` | off | Skip CSV merge |
| `--strict` | off | Treat warnings as failures |
| `--open` | off | Open `catalog.html` in the default browser after writing; explicit, never default (cron-safe), no-op with `--check` |

Emits `catalog.json` (full records), `catalog.md` (sortable table), `catalog.html` (self-contained interactive viewer — inline CSS/JS, no CDN, works offline; sort columns, filter by host/capability, search), and `catalog-widget.html` (a FRAGMENT for the Hermes `::preview` frame — uses the app's theme vars, no `<html>/<head>/<body>` wrappers, inline JS that runs in the preview context).

Catalog fields: `id`, `host` (`studio`/`macbook`), `display_name`, `groups`, `persistent`, `gguf_path`, `gguf_resolved` (MacBook paths translated to the `/Volumes/prasta` mount), `gguf_exists`, `gguf_size_gb`, `mmproj_path`, `mmproj_size_gb`, `vision`, `ctx_size`, `parallel`, `spec_type`, `ttl`, `quant`, `params_total_b`, `params_active_b`, `arch` (`moe`/`dense`), `capabilities` (list), `capability` (first), `tokenizer`, `tokenizer_source`, `bench`, `has_bench`, `usage` (`requests`, `input_tokens`, `output_tokens`, `last_used`), `has_usage`, `description`.

## Procedure

1. **Run `--check` first** on any config edit. It reports missing GGUFs, orphan group members, and models absent from every group, without writing.

2. **Read `catalog.md` for the fleet view** — sorted by capability then size. This is the file to read when deciding what to keep.

3. **Use `catalog.json` for anything programmatic.** It is the artifact downstream tools should read instead of re-parsing `config.yaml` or re-typing an id.

4. **Re-run after every config edit.** The catalog is disposable. Never hand-edit it; if a field is wrong, the config or the disk is wrong.

5. **Wire `--check` into the rename workflow.** The `ms-*` rename broke four downstream systems because copies had drifted. A catalog regenerated in the same commit makes the drift visible immediately.

## Dashboard generator

`/Users/macstudio/models/docs/gen_dashboard.py` derives the served section of `dashboard.html` from `catalog.json` + GGUF headers, so the served list cannot drift from the config. It reads `catalog.json` from `OUT_DIR_DEFAULT` — the same iCloud path the generator writes, one copy, no fallback. It filters to `host == "studio"` — the dashboard is the Studio's served fleet; MacBook rows never appear there or trigger drift. Run `python3 gen_dashboard.py --check` (validate) or `python3 gen_dashboard.py` (write). The not-served inventory, HTML shell, and narrative notes live in `dashboard.template.html` (hand-maintained); the served entries are spliced in at the `/*__SERVED_MODELS__*/` marker.

Field sourcing: ctx/params/quant/gb come from the ENRICH map (curated display values — model-max ctx, accurate quant, model-size gb, rounded params); ctx/params/arch fall back to the GGUF header via gguf-py; quant/gb/x/vision/mtp/srv/grp/ttl come from catalog.json. The catalog's `ctx_size` is the SERVING context, not the model max, and its quant/params are config-name heuristics — never use them for the dashboard's display fields. gguf-py Field values are always in `parts[-1]` (string bytes for strings, scalar for ints).

Drift is auto-checked weekly: the Infra Weekly Report cron (job 8df9559db27a, Mon 8am) runs `cruft-check-report.sh` whose `_sec_drift` section calls both `fleet_catalog.py --check` and `gen_dashboard.py --check` under `/usr/bin/python3` (has pyyaml; `--check` needs no gguf). Both must exit 0 or the report flags `!!`. `gen_dashboard.py --check` deliberately does NOT build entries (no GGUF reads) — keep it that way or the cron output gets numpy DeprecationWarnings.

## Pitfalls

- **An unmounted MacBook share silently truncates the catalog.** With
  `/Volumes/prasta` gone, the MacBook config is skipped and the run writes a
  Studio-only `catalog.json` over a fuller one — the skip shows up in
  `problems[]` but the run still exits 0. Guard a run you intend to keep with
  `--check --strict` first: the skip counts as a warning, so strict exits 1
  while the share is down. (Hit 2026-10-28: a 36-model catalog was replaced by
  a 22-model one.) The fix is to mount the share and re-run, not to hand-merge.

- **The output moved to iCloud; every consumer has to move with it.** The
  four artifacts live in `OUT_DIR_DEFAULT` (iCloud `Hermes/infra/fleet-catalog`)
  as of 2026-10-28, and `~/.hermes/outputs/fleet-catalog` no longer exists.
  When the generator's `--out-dir` default changes, grep for the old path and
  repoint every reader in the same pass — `models/docs/gen_dashboard.py` and
  `llama-benchy-quick-bench/scripts/benchy_interactive.py` both read
  `catalog.json` by absolute path. `gen_dashboard.py --check` fails hard
  (`FileNotFoundError`) on a missing catalog, which is exactly how the weekly
  Infra drift check would break; `benchy_interactive.py` degrades silently to
  no annotations, which is worse, because the bench still runs.

- **A broken symlink and a missing file need different fixes and look identical to `os.path.isfile`.** The generator distinguishes them and prints `BROKEN SYMLINK` with the target. None are in that state right now, but this is the failure mode that recurs: backslash-escaped targets (`/Users/macstudio\.hf\/hub/...`) produce a link that `ls -la` looks fine and `[ -e ]` says is dead. Fix with `ln -sfn` using forward slashes, then confirm by reading bytes *through* the link, not just resolving it.

- **A directory-backed engine is NOT a missing GGUF.** `--model` pointing at a model directory (the sushi MLX pack, `/Users/macstudio/.sushi/models/...`) is valid; `os.path.isfile()` alone flags it as `gguf missing on disk` and fails `--check`. The existence test must be `isfile() or isdir()` (fixed 2026-10-07). Before that fix, `--check` passed only because sushi post-dated the last catalog regen.
- **A directory-backed engine also needs a real size.** `os.path.getsize` on a directory returns the directory entry size, so sushi reported `0` until `file_size_gb` learned to sum a directory recursively (2026-10-23). It now reports the measured 64.8 GiB.

- **Capability is derived from the id and group only, never the description.** Prose carries provenance and decisions, not taxonomy. An earlier version matching the description called gemma-4-26b-moe a "code" model and gpt-oss-20b an "extraction" model. If a capability looks wrong, the id is the thing to change, not the classifier.
- **`arch` is read from the GGUF header; the id and the override list are only a fallback.** `gguf_arch()` parses `general.architecture` and `<arch>.expert_count` straight out of the metadata KV block, so it is a measurement and it outranks every name heuristic. `ARCH_OVERRIDES` now covers only entries whose weights cannot be read: directory-backed engines and files absent on the reading host. Three bugs have lived in this one bullet. An `ARCH_OVERRIDES.get("", ...)` lookup silently dropped every override, so gpt-oss-20b and sushi reported `dense`. The name-derived path called `ms-kat-coder-v2.5` and `ms-laguna-xs-2.1` dense (both are 256-expert MoE, `qwen35moe` and `laguna`), and called `ms-qwen3.5-4b-mtp` MoE when its header has no `*.expert_count` field at all — "MTP" is a multi-token-prediction head, not an expert layout. Never add a *name* to the override list without reading the header first.

- **The GGUF metadata type enum starts at UINT8 = 0.** Prepending a sentinel type (a `NONE = 0` ahead of the real values) shifts every constant by one and desyncs the KV walk. It fails as a `MemoryError` on a garbage `read()` length rather than as a clean parse error, so it reads like corrupt weights instead of an off-by-one. `gguf_arch()` uses the spec enum directly and is stdlib-only on purpose: the weekly cron runs `--check` under `/usr/bin/python3` (3.9, pyyaml but no gguf-py or numpy), so giving it a real dependency would break the drift check. For the same reason it reads raw bytes instead of using gguf-py, where `int(field.parts[field.data[-1]])` raises `TypeError` on a multi-element array and a bare `except` turns that into a silent wrong answer.

- **`null` means unknown, not zero.** Param counts come from filename and description heuristics. Gemma 4 E4B reports `params_total_b: null` with `params_active_b: 4` because the total is genuinely not stated anywhere. Do not fill these in by hand; a wrong number here is worse than a missing one. `references/derivations.md` lists every known null and why.

- **A digit in an id does not mean parameter count.** `ms-granite-4.2-3b` is a dense 3B; `ms-gemma-4-e4b` is 4B *active* out of a larger MoE; `ms-qwen3.5-4b-mtp` is the same shape. This is the one real naming defect in the fleet. The catalog separates `params_total_b` from `params_active_b` so the ambiguity is visible instead of baked into the key.

- **A model in `models:` but in no group is unreachable.** llama-swap will not serve it, but the GGUF still occupies disk. `--check` flags this as an orphan.

- **Benchmark columns are per-CSV, not per-model.** A model absent from the newest CSVs shows `bench: null` even though older runs exist. The catalog takes the newest CSV that mentions each model, not the newest CSV overall.

- **Benchmark CSVs live in subdirectories, so the search must be recursive.** Runners write `<results_dir>/<run>/raw/*.csv`. A flat `glob("*.csv")` finds zero files and silently nulls `bench` for the entire fleet with no error — the run still exits 0. `load_bench` uses `rglob` and skips any path containing `_superseded`. If every `tok_s`/`qual` column goes blank at once, suspect the glob before suspecting the fleet.

- **Sizes are the GGUF on disk, not the advertised model size.** A Q4 quant of a 27B lands near 16 GB. The catalog reports measured bytes; the description's "(16.8GB)" prose is ignored.

- **The catalog is not a lockfile.** Deleting it loses nothing. That is the point.

- **Derive capabilities from the model id and group only.** Free-text descriptions in `config.yaml` produce false positives (`ms-gemma-4-26b-moe` was classified `code` from its description).
- **Retired is not broken.** `ms-qwopus3.8-27b-flash` and `ms-qwen3.5-4b-mtp` were removed from the llama-swap config (Qwopus on 2026-10-01); an earlier note blaming escaped-backslash symlinks was wrong. On a model 404, read `curl -s 127.0.0.1:9292/v1/models` before suspecting disk.
- **A full standalone HTML page does not run in the `::preview` frame.** The preview frame is a widget context: it injects the app's theme vars and expects a fragment — no `<html>/<head>/<body>` wrappers, no own background/font/margins. A full document with a trailing `<script>` renders its buttons but the JS never attaches. Use `catalog-widget.html` for `::preview`; keep `catalog.html` for opening in a browser.
- **A WAL-mode sqlite is not a single file.** The MacBook's `activity.sqlite` is WAL-mode and actively written; copying only the `.sqlite` yields an inconsistent snapshot that sqlite refuses to open (`unable to open database file`). Copy the `-wal` and `-shm` alongside (2026-10-23). The Studio's own log is read in place, so this only bites the SMB-hosted MacBook copy.
- **`--check` first.** `python3 scripts/fleet_catalog.py --check` validates the fleet (missing GGUFs, orphans, broken links) before generating `catalog.json`/`catalog.md`.

## Verification

```bash
python3 scripts/fleet_catalog.py --check
```

Pass condition: exit 0, and a line reading `N models, 0 missing gguf, 0 orphans`. A non-zero exit names the offending ids.

`--check` covers config and disk integrity only; it does not validate the benchmark merge. A green check with an all-blank `tok_s` column is a failed verification, not a pass. Confirm the merge separately: 14 of 19 models carry `bench` as of 2026-10-03. The five legitimate gaps are the 4 embeddings (never benchmarked, not throughput-bound) and `ms-nemotron-3.5-lightning-30b`, which was only ever benchmarked as the distinct MacBook build `mb-nemotron-omni-30b` — its numbers are not transferable across host, quant, and weights.

Current state (2026-10-28): **exit 0 with the MacBook share mounted** — `36 models (36 in groups), 0 missing gguf, 0 orphans` (2026-10-24, Studio + MacBook); **Studio-only** `22 models (22 in groups), 0 missing gguf, 0 orphans` when `/Volumes/prasta` is unmounted (2026-10-28). Run `--check --strict` to make the second case fail loudly instead of quietly shipping a thinner catalog. The four backslash-escaped symlinks that once made `--check` exit 1 have been repaired and load-tested.

---

Load field derivations, known nulls, and the current broken-entry list on demand:
`skill_view(name='fleet-catalog', file_path='references/derivations.md')`
