---
name: comfyui
description: Generate images, video, and audio via diffusion workflows.
version: 5.3.0
author: [kshitijk4poor, alt-glitch, purzbeats]
license: MIT
platforms: [macos, linux, windows]
compatibility: "Requires ComfyUI (local, Comfy Desktop, or Comfy Cloud) and comfy-cli (auto-installed via pipx/uvx by the setup script)."
prerequisites:
  commands: ["python"]
setup:
  help: "Run scripts/hardware_check.py FIRST to decide local vs Comfy Cloud; then scripts/comfyui_setup.sh auto-installs locally (or use Cloud API key for platform.comfy.org)."
metadata:
  hermes:
    tags:
      - comfyui
      - image-generation
      - stable-diffusion
      - flux
      - sd3
      - wan-video
      - hunyuan-video
      - creative
      - generative-ai
      - video-generation
    related_skills: []
    category: creative
---

# ComfyUI

Generate images, video, audio, and 3D content through ComfyUI using the
official `comfy-cli` for setup/lifecycle and direct REST/WebSocket API
for workflow execution.

## What's in this skill

**Reference docs (`references/`):**

- `official-cli.md` — every `comfy ...` command, with flags
- `rest-api.md` — REST + WebSocket endpoints (local + cloud), payload schemas
- `workflow-format.md` — API-format JSON, common node types, param mapping
- `template-integrity.md` — converting `comfyui-workflow-templates` from
  editor format to API format: Reroute bypass, dotted dynamic-input keys
  (`values.a`, `resize_type.width`), Cloud quirks (302 redirect, 1 concurrent
  free-tier job, 1080p VRAM ceiling), Discord-compatible ffmpeg stitch.
  Authored by [@purzbeats](https://github.com/purzbeats). Load this whenever
  you're starting from an official template.
- `style-library.md` — named style presets (flat-sticker, woodcut, risograph,
  neon, ...) with drop-in prompt fragments, per-style workflow deltas, text-risk
  and cutout-compatibility verdicts (machine-readable copy: `style-presets.json`,
  read by `run_style_sweep.py`). Load when the user wants to change the artistic
  style of a generation.
- `facecrop.md` — **reference-image prep: crop a folder of photos to a single
  person's face** (identity-filtered via insightface embeddings, not largest/
  best-quality face). Covers venv setup, the 0.35 vs 0.40 threshold lever, QC
  sheets, and the verified pitfalls (HEIC, format twins, vision-model QC
  unreliability). Load whenever the user asks to crop photos as reference
  images or training data.

**Scripts (`scripts/`):**

| Script | Purpose |
|--------|---------|
| `_common.py` | Shared HTTP, cloud routing, node catalogs (don't run directly) |
| `convert_workflow.py` | **Editor format → API format.** Parses ComfyUI's saved `nodes`/`links` JSON, resolves links, maps `widgets_values` positionally against bundled node schemas (core 0.37 set), preserves dotted keys (`format.bit_depth`), collapses container inputs (`images.image_1` → `images: {...}`), bypasses Reroute, drops Note + detached LoadImage nodes. Refuses UUID subgraph-template nodes. Use when someone drops an editor-format file into the shared workflows dir — no UI export needed |
| `hardware_check.py` | Probe GPU/VRAM/disk → recommend local vs Comfy Cloud |
| `comfyui_setup.sh` | Hardware check + comfy-cli + ComfyUI install + launch + verify |
| `extract_schema.py` | Read a workflow → list controllable params + model deps |
| `check_deps.py` | Check workflow against running server → list missing nodes/models |
| `auto_fix_deps.py` | Run check_deps then `comfy node install` / `comfy model download` |
| `run_workflow.py` | Inject params, submit, monitor, download outputs (HTTP or WS). Downloads land in the **gallery** (`~/Pictures/ComfyUI/<YYYY-MM>/`) with renamed files plus a merged `manifest.json` per month |
| `comfy-assets.py` | **Web-asset pipeline: prompt → correctly-sized, correctly-formatted site imagery.** Pairs with the `impeccable` skill for front-end work. |
| `run_batch.py` | Submit a workflow N times with sweeps, parallel up to your tier. Writes per-run + batch manifests into the gallery |
| `run_style_sweep.py` | One prompt, one seed, N styles → batch comparison; reads fragments from `references/style-presets.json` |
| `run_text_battery.py` | Typographic stress battery: run N prompts through a workflow, JSON-injecting `prompt`+`seed` (works where schema inject can't reach the prompt field), collect outputs, emit JSON |
| `ws_monitor.py` | Real-time WebSocket viewer for executing jobs (live progress) |
| `health_check.py` | Verification checklist runner — comfy-cli + server + models + smoke test |
| `fetch_logs.py` | Pull traceback / status messages for a given prompt_id |
| `cutout_flat.py` | **Flat-design cutout: near-white flood-fill to transparent** (t-shirt/sticker/logos) — see pitfall 0m |
| `facecrop.py` | **Reference-set prep: identity-filtered face crops.** Detect + embed every face (insightface buffalo_l), cluster the folder's single-face images, crop to the dominant identity only. Needs the `faceenv` venv (see `references/facecrop.md`); not stdlib-only. Feeds `--input-image` / multi-ref reference slots |
| `facecrop_qc.py` | **Build labeled QC contact sheets** from a `facecrop.py` report — borderline red, confident green, source filename + score under every crop. Human QC is the last mile; always run it |

**Example workflows (`workflows/`):** SD 1.5, SDXL, Flux Dev, SDXL img2img,
SDXL inpaint, ESRGAN upscale, AnimateDiff video, Wan T2V, Qwen-Image-2.1
(int8 working path + GGUF dead end), Z-Image Turbo starters (8 API-format
conversions of the shared editor-format starters). See
`workflows/README.md`.

## When to Use

- User asks to generate images with Stable Diffusion, SDXL, Flux, SD3, etc.
- User wants to run a specific ComfyUI workflow file
- User wants to chain generative steps (txt2img → upscale → face restore)
- User needs ControlNet, inpainting, img2img, or other advanced pipelines
- User asks to manage ComfyUI queue, check models, or install custom nodes
- User wants video/audio/3D generation via AnimateDiff, Hunyuan, Wan, AudioCraft, etc.

## This machine (Mac Studio) — read this first

The generic instructions below describe ComfyUI everywhere. This machine differs
in ways that will waste your time if you assume otherwise.

| | |
|---|---|
| **Server** | Single comfy-cli install `http://127.0.0.1:8188` (Comfy Desktop was retired 2026-10-23 — one endpoint, no :8189). Pin with `COMFYUI_URL`. |
| **Install** | `/Users/macstudio/ComfyUI` (comfy-cli managed), ComfyUI **0.42.0**, Python 3.11, torch 2.13.0 |
| **Model library** | `/Users/macstudio/models/diffusion` — wired via `extra_model_paths.yaml` in the install root. Contents: Qwen-Image-2.1 int8_convrot UNet (`qwen_image_2.1_int8_convrot.safetensors`) + `qwen3vl_8b_int8_convrot` text encoder + `qwen_image_2.1_vae_bf16` VAE, the **Z-Image-Turbo trio** (z_image_turbo_bf16 UNet, qwen_3_4b text encoder, ae VAE) plus the pixel-art style LoRA (`loras/pixel_art_style_z_image_turbo.safetensors`, tarn59, trigger `Pixel art style.`, added 2026-10-18). A third Qwen text encoder is present: `qwen3.5_9b_qwen_image_2.1_pe_t2i.int8_convrot.safetensors` (~9 GB) — the *prompt-enhancer* encoder used by the official T2I subgraph template (loaded with `type=stable_diffusion`), not needed by the flat `qwen-image-2.1-simple` workflow. The library also now carries two video stacks: **Wan 2.2** (t2v + i2v, `wan2.2_{t2v,i2v}_{high,low}_noise_14B_Q5_K_M.gguf` UNETs, `umt5-xxl-encoder-Q8_0.gguf` text encoder, `wan2.2_vae` / `wan_2.1_vae` VAEs, and the four lightx2v 4-step LoRAs) and **LTX-2.5** (`ltx-2.5-22b-distilled-transformer-comfy-int8-convrot.safetensors` plus `ltx-2.5-22b-distilled-UD-Q4_K_XL.gguf` UNETs, `gemma4-12b-with-proj-ltx-2.5-comfy-int8-convrot` text encoder, separate video and audio VAEs, and `ltx-2.5-latent-spatial-upscaler-x2-bf16-1.0` via `LatentUpscaleModelLoader`). The two `Z-Image-AbliteratedV1.{Q8_0,Q4_K_M}.gguf` encoders are visible *only* through the bootleg GGUF CLIP loaders. Upscale model is `RealESRGAN_x4plus.safetensors` from the install's own `models/upscale_models/`, not the shared library. `checkpoints` is **empty** — no SDXL/Flux/1.5 checkpoint on disk and no bf16 Qwen UNet or text encoder; graphs naming those filenames fail to load. `.gguf` weights show in the plain loaders' dropdowns too, but only the bootleg GGUF loaders can actually load them |
| **comfy-cli** | `/Users/macstudio/ComfyUI/venv/bin/comfy` — **NOT on PATH.** Use the absolute path or activate the venv |
| **MCP bridge** | `comfy-mcp` 0.10.0 wired into Hermes as stdio MCP server (39 tools) — registered in `~/.hermes/config.yaml` `mcp_servers.comfy-mcp` (command `/Users/macstudio/ComfyUI/venv/bin/comfy-mcp`, env `COMFY_BIN=/Users/macstudio/ComfyUI/venv/bin/comfy`). Hermes sessions see `mcp__comfy-mcp__*` tools after /reload-mcp or a new session. Prefer MCP tools for local workflow runs; the skill scripts remain the fallback |
| **Device** | MPS, 96 GB unified, shared VRAM |
| **Comfy Desktop** | **RETIRED 2026-10-23** — app, `~/ComfyUI-Installs`, and `~/Library/Application Support/Comfy Desktop/` all removed; consolidated to the single CLI install on :8188. Its old spool `~/ComfyUI-Shared/output` is gone too. |
| **Shared workflows** | Canonical home `/Users/macstudio/ComfyUI-Shared/user/workflows/` (8 Z-Image starters + 2 Qwen at top level = as of 2026-10-22: 11 editor + 11 `.api.json` converted files in `starters/` + `qwen-image-2.1-simple.json`). The single CLI install's `user/default/workflows` is a symlink to it (the Desktop install's symlink died with Desktop 2026-10-23). **Run scripts against the `.api.json` versions** (API format, already converted), not the editor-format `.json` originals. Convert new editor drops with `scripts/convert_workflow.py`. The 2 official subgraph-template files (`image_qwen_image_2_1_t2i`, `qwen-image-2.1-t2i-no-enhancer`) were archived 2026-10-22 to `~/ComfyUI-Shared/backups/workflows-editor-format-2026-10-22/archived-subgraph-templates/` — they use UUID packed-subgraph nodes that don't convert; `qwen-image-2.1-simple` covers the use case. Models are shared via `extra_model_paths.yaml` → `/Users/macstudio/models/diffusion`. |
| **Gallery (generated images)** | `~/Pictures/ComfyUI/` — grouped by MONTH: `<YYYY-MM>/` holds every file that month's generations produced, flat, plus ONE merged `manifest.json` (prompt, seed, params, workflow, prompt_id, per-file sha256). `run_workflow.py`/`run_batch.py` download here by default; `gallery.py sweep` organizes whatever the server wrote into the same layout. The server's output dir is a **staging spool**: `~/ComfyUI/output` (the single CLI install). Root override: `$COMFY_GALLERY`; spool override: `$COMFY_SPOOL_DIRS`. |

Start the server (there is deliberately **no launchd job for the server** — it does not autostart;
the gallery *sweeper* does have one, see The gallery section):

```bash
/Users/macstudio/ComfyUI/venv/bin/comfy launch -- --port 8188
# or directly:
cd /Users/macstudio/ComfyUI && ./venv/bin/python main.py --port 8188
```

**Which interpreter runs the scripts:** both work. `python` is 3.14.7, `python3` is
3.9.6. The scripts declare 3.10+ but `from __future__ import annotations` makes
them run under 3.9 too — verified by actually executing `health_check.py`,
`check_deps.py` and `run_workflow.py` under both. Prefer `python`.

**Why there's no launchd job for the server:** Patrick works in a browser against
`127.0.0.1:8188` and does not want the server autostarting. Don't propose a
`KeepAlive` LaunchAgent — it was considered and rejected. (Comfy Desktop, the
former :8189 server, was retired 2026-10-23; the single CLI install serves the
same browser UI.)

**Disk:** 97 GB free of 926 GB (90% used, checked 2026-10-20). Free space drifts:
run `df -h /System/Volumes/Data` before downloading anything new — at ~97 GB free,
a ~30 GB bf16 UNet + encoder pair no longer fits comfortably.

## Architecture: Two Layers

```
┌─────────────────────────────────────────────────────┐
│ Layer 1: comfy-cli (official lifecycle tool)        │
│   Setup, server lifecycle, custom nodes, models     │
│   → comfy install / launch / stop / node / model    │
└─────────────────────────┬───────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────┐
│ Layer 2: REST/WebSocket API + skill scripts         │
│   Workflow execution, param injection, monitoring   │
│   POST /api/prompt, GET /api/view, WS /ws           │
│   → run_workflow.py, run_batch.py, ws_monitor.py    │
└─────────────────────────────────────────────────────┘
```

**Why two layers?** The official CLI is excellent for installation and server
management but has minimal workflow execution support. The REST/WS API fills
that gap — the scripts handle param injection, execution monitoring, and
output download that the CLI doesn't do.

## Quick Start

### Detect environment

```bash
# What's available?
command -v comfy >/dev/null 2>&1 && echo "comfy-cli: installed"
curl -s http://127.0.0.1:8188/system_stats 2>/dev/null && echo "server: running"

# Can this machine run ComfyUI locally? (GPU/VRAM/disk check)
python scripts/hardware_check.py
```

If nothing is installed, see **Setup & Onboarding** below — but always run the
hardware check first.

### One-line health check

```bash
python scripts/health_check.py
# → JSON: comfy_cli on PATH? server reachable? at least one checkpoint? smoke-test passes?
```

## Core Workflow

### Step 1: Get a workflow JSON in API format

Workflows must be in API format (each node has `class_type`). They come from:

- ComfyUI web UI → **Workflow → Export (API)** (newer UI) or
  the legacy "Save (API Format)" button (older UI)
- This skill's `workflows/` directory (ready-to-run examples)
- Community downloads (civitai, Reddit, Discord) — usually editor format.
  Run `python scripts/convert_workflow.py W.json` to convert without
  touching the UI (refuses UUID subgraph-template nodes); or load into
  ComfyUI then re-export

Editor format (top-level `nodes` and `links` arrays) is **not directly
executable**. The scripts detect it and direct you to `convert_workflow.py`
or a UI re-export.

### Step 2: See what's controllable

```bash
python scripts/extract_schema.py workflow_api.json --summary-only
# → {"parameter_count": 12, "has_negative_prompt": true, "has_seed": true, ...}

python scripts/extract_schema.py workflow_api.json
# → full schema with parameters, model deps, embedding refs
```

### Step 3: Run with parameters

```bash
# Local (defaults to http://127.0.0.1:8188)
python scripts/run_workflow.py \
  --workflow workflow_api.json \
  --args '{"prompt": "a beautiful sunset over mountains", "seed": -1, "steps": 30}' \
  --output-dir ./outputs

# Cloud (export API key once; uses correct /api routing automatically)
export COMFY_CLOUD_API_KEY="comfyui-..."
python scripts/run_workflow.py \
  --workflow workflow_api.json \
  --args '{"prompt": "..."}' \
  --host https://cloud.comfy.org \
  --output-dir ./outputs

# Real-time progress via WebSocket (requires `pip install websocket-client`)
python scripts/run_workflow.py \
  --workflow flux_dev.json \
  --args '{"prompt": "..."}' \
  --ws

# img2img / inpaint: pass --input-image to upload + reference automatically
python scripts/run_workflow.py \
  --workflow sdxl_img2img.json \
  --input-image image=./photo.png \
  --args '{"prompt": "make it watercolor", "denoise": 0.6}'

# Batch / sweep: 8 random seeds, parallel up to cloud tier limit
# (no --output-dir → gallery: ~/Pictures/ComfyUI/<YYYY-MM>/, files flat)
python scripts/run_batch.py \
  --workflow sdxl.json \
  --args '{"prompt": "abstract"}' \
  --count 8 --randomize-seed --parallel 3 \
  --slug abstract-forms
```

`-1` for `seed` (or omitting it with `--randomize-seed`) generates a fresh
random seed per run.

### Step 4: Present results

**Display outputs in-session automatically.** Never end a ComfyUI run with just a file path or a
JSON blob. After downloading each output, include a `MEDIA:<absolute-path>` line in the response so
the image renders inline in the chat (the platform's MEDIA directive; one line per image).

- Outputs land in the **gallery**, never scratch: `~/Pictures/ComfyUI/<YYYY-MM>/`
  (override the root with `$COMFY_GALLERY`), files renamed `<slug>_<seed>_<NN>.<ext>`, plus a
  merged `manifest.json` per month recording prompt, seed, params, workflow, prompt_id, and
  per-file sha256. Point MEDIA at the gallery paths — they survive; `~/.hermes/cache/scratch/`
  gets pruned after 24h.
- The run scripts already do the organizing (default `--output-dir` is the gallery, `--slug`
  overrides the prompt-derived name, `--no-rename` keeps server filenames). Explicit `--output-dir`
  still wins and also gets rename + manifest.
- When a run produces a batch (multiple seeds/variants), send the whole set, not just the "best" —
  the user picks; don't pre-filter on a vision model's ranking. Label each with its variant name
  (e.g. `**v2** —`) or seed, and note file size/format only when it matters.
- After sending, say what changed and what the known flaws are — the machine verdict ("it's
great") is not your verdict. Flag seams, lighting mismatches, or dropped elements explicitly;
verify with pixel stats (diff against source in/out of mask) rather than a vision model's opinion.

The scripts emit JSON to stdout describing every output file:

```json
{
  "status": "success",
  "prompt_id": "abc-123",
  "slug": "sunset-over-mountains",
  "seed": 42,
  "output_dir": "…/ComfyUI/2026-10",
  "manifest": "…/manifest.json",
  "outputs": [
    {"file": "…/sunset-over-mountains_42_01.png", "source": "sd15_00001_.png",
     "node_id": "9", "type": "image", "subfolder": ""}
  ]
}
```

## The gallery (where generated images live)

One scheme for everything, whether it came from a script run or the ComfyUI UI.
Grouped by **month** so a month's whole output is reviewable at scale in one
folder — no per-run subfolders to drill into:

```
~/Pictures/ComfyUI/
└── 2026-10/                              # one folder per month
    ├── sunset-over-mountains_42_01.png    # <slug>_<seed>_<NN>.<ext>, all flat
    ├── sunset-over-mountains_42_02.png
    ├── another-prompt_7_01.png
    └── manifest.json                     # ONE merged manifest for the month
```

- **Script runs** (`run_workflow.py`, `run_batch.py`) download straight into
  this layout. `run_batch.py` drops every run's files flat into the month
  folder too (no `run_NNNN` subdirs) — filenames carry the seed, and a
  collision (same slug+seed twice in a month) bumps NN. The month
  `manifest.json` records every run; the batch also writes a
  `manifest.batch.json` summary linking args/seed → files.
- **UI/Desktop/MCP runs** write into the server's staging dir —
  `~/ComfyUI/output` (the single CLI install). Same flat-accumulation problem, so sweep them into the gallery:
  `gallery.py sweep` reads the embedded PNG metadata (prompt + workflow JSON),
  names files `<slug>_<seed>_<NN>`, merges them into the month manifest, and
  deletes spool copies that are byte-identical to something already archived
  (that's a script run that also downloaded them). Files with no readable
  metadata get slugged from their server filename.
  ```bash
  python scripts/gallery.py sweep            # both spools, default gallery
  python scripts/gallery.py sweep --dry-run   # preview first — always
  python scripts/gallery.py list              # table of everything
  python scripts/gallery.py list --match fox --seed 4242 --json
  ```
- **Legacy layout migration.** Outputs created before the month scheme
  (per-day/per-run folders like `2026-10-18/<slug>_<time>/`) can be flattened
  into month folders with `gallery.py reorganize` — it moves each run's files
  into `<YYYY-MM>/`, merges the run records into the month manifest, and prunes
  the now-empty legacy dirs. Run `--dry-run` first.
  ```bash
  python scripts/gallery.py reorganize --dry-run
  python scripts/gallery.py reorganize
  ```
- **Automated on this machine:** launchd job `ai.hermes.comfyui-gallery-sweep` runs
  `gallery.py sweep` every 10 minutes (plist `~/Library/LaunchAgents/ai.hermes.comfyui-gallery-sweep.plist`,
  no `KeepAlive` — it never starts the server, just files papers; log at
  `~/Library/Logs/comfyui-gallery-sweep.log`). Exit 0 on a clean poll including nothing-to-do.
  Remove with `launchctl bootout gui/$(id -u)/ai.hermes.comfyui-gallery-sweep`.
- **Dedup is exact** (sha256), so re-sweeping is safe. Spools are staging; the gallery is the
  archive. One tradeoff to know: sweeping moves files out of the server output dirs, so the
  ComfyUI UI's "past outputs" list fades as sweeps run — old `/history` entries 404 on thumbnails.
  That is the point: the gallery becomes the archive.
- Manifests are the machine-readable record of a run — replay a generation by re-submitting
  `workflow` + `params` + `seed`. `comfy-assets.py` keeps its own `assets.manifest.json`; point its
  `--out` into the gallery if you want web assets archived alongside raw runs.
- **Human-readable recipe in the PNG itself.** Every PNG that passes through `finalize_downloads()`
  (run_workflow.py / run_batch.py) or `gallery.py sweep` (UI/MCP runs) gets a flat `key: value`
  `parameters` tEXt chunk written alongside ComfyUI's `prompt` chunk — prompt, negative, seed,
  steps, cfg, denoise, resolution, sampler, scheduler, model, text_encoder, vae, references.
  The file alone tells you what made it, no JSON parsing. Idempotent (re-running replaces, never
  duplicates) and lossless (pixel stream untouched). Implemented in `_common.py`:
  `render_human_params()` / `write_png_parameters()` / `embed_human_params()`.

## Decision Tree

| User says | Tool | Command |
|-----------|------|---------|
| **Lifecycle (use comfy-cli)** | | |
| "install ComfyUI" | comfy-cli | `bash scripts/comfyui_setup.sh` |
| "start ComfyUI" | comfy-cli | `comfy launch --background` |
| "stop ComfyUI" | comfy-cli | `comfy stop` |
| "install X node" | comfy-cli | `comfy node install <name>` |
| "download X model" | comfy-cli | `comfy model download --url <url> --relative-path models/checkpoints` |
| "list installed models" | comfy-cli | `comfy model list` |
| "list installed nodes" | comfy-cli | `comfy node show installed` |
| **Execution (use scripts)** | | |
| "is everything ready?" | script | `health_check.py` (optionally with `--workflow X --smoke-test`) |
| "what can I change in this workflow?" | script | `extract_schema.py W.json` |
| "convert an editor workflow to API" | script | `convert_workflow.py W.json` (outputs `W.api.json`; refuses UUID subgraph templates) |
| "check if W's deps are met" | script | `check_deps.py W.json` |
| "fix missing deps" | script | `auto_fix_deps.py W.json` |
| "generate an image" | script | `run_workflow.py --workflow W --args '{...}'` |
| "change the artistic style" | reference + script | load `references/style-library.md`, or `run_style_sweep.py --prompt '...' --styles woodcut,risograph --seed N` for a one-batch comparison |
| "crop these photos to my face / as references" | script + QC | `scripts/facecrop.py in out --score 0.40` (needs faceenv venv), then `scripts/facecrop_qc.py`; show the QC sheets and get human sign-off before deleting sources |
| "use this image" (img2img) | script | `run_workflow.py --input-image image=./x.png ...` |
| "8 variations with random seeds" | script | `run_batch.py --count 8 --randomize-seed ...` |
| "show me live progress" | script | `ws_monitor.py --prompt-id <id>` |
| "fetch the error from job X" | script | `fetch_logs.py <prompt_id>` |
| "organize the output folders / sweep UI & Desktop runs" | script | `gallery.py sweep` (add `--dry-run` to preview) |
| "flatten old per-day/per-run folders into months" | script | `gallery.py reorganize` (add `--dry-run` to preview) |
| "what's in the gallery / find that image" | script | `gallery.py list --match <text> [--seed N] [--since YYYY-MM-DD]` |
| **Direct REST** | | |
| "what's in the queue?" | REST | `curl http://HOST:8188/queue` (local) or `--host https://cloud.comfy.org` |
| "cancel that" | REST | `curl -X POST http://HOST:8188/interrupt` |
| "free GPU memory" | REST | `curl -X POST http://HOST:8188/free` |

## Setup & Onboarding

When a user asks to set up ComfyUI, **the FIRST thing to do is ask whether
they want Comfy Cloud (hosted, zero install, API key) or Local (install
ComfyUI on their machine)**. Don't start running install commands or hardware
checks until they've answered.

**Official docs:** https://docs.comfy.org/installation
**CLI docs:** https://docs.comfy.org/comfy-cli/getting-started
**Cloud docs:** https://docs.comfy.org/get_started/cloud
**Cloud API:** https://docs.comfy.org/development/cloud/overview

### Step 0: Ask Local vs Cloud (ALWAYS FIRST)

Suggested script:

> "Do you want to run ComfyUI locally on your machine, or use Comfy Cloud?
>
> - **Comfy Cloud** — hosted on RTX 6000 Pro GPUs, all common models pre-installed,
>   zero setup. Requires an API key (paid subscription required to actually run
>   workflows; free tier is read-only). Best if you don't have a capable GPU.
> - **Local** — free, but your machine MUST meet the hardware requirements:
>   - NVIDIA GPU with **≥6 GB VRAM** (≥8 GB for SDXL, ≥12 GB for Flux/video), OR
>   - AMD GPU with ROCm support (Linux), OR
>   - Apple Silicon Mac (M1+) with **≥16 GB unified memory** (≥32 GB recommended).
>   - Intel Macs and machines with no GPU will NOT work — use Cloud instead.
>
> Which would you like?"

Routing:

- **Cloud** → skip to **Path A**.
- **Local** → run hardware check first, then pick a path from Paths B–E based on the verdict.
- **Unsure** → run the hardware check and let the verdict decide.

### Step 1: Verify Hardware (ONLY if user chose local)

```bash
python scripts/hardware_check.py --json
# Optional: also probe `torch` for actual CUDA/MPS:
python scripts/hardware_check.py --json --check-pytorch
```

| Verdict    | Meaning                                                       | Action |
|------------|---------------------------------------------------------------|--------|
| `ok`       | ≥8 GB VRAM (discrete) OR ≥32 GB unified (Apple Silicon)       | Local install — use `comfy_cli_flag` from report |
| `marginal` | SD1.5 works; SDXL tight; Flux/video unlikely                  | Local OK for light workflows, else **Path A (Cloud)** |
| `cloud`    | No usable GPU, <6 GB VRAM, <16 GB Apple unified, Intel Mac, Rosetta Python | **Switch to Cloud** unless user explicitly forces local |

The script also surfaces `wsl: true` (WSL2 with NVIDIA passthrough) and
`rosetta: true` (x86_64 Python on Apple Silicon — must reinstall as ARM64).

If verdict is `cloud` but the user wants local, do not proceed silently.
Show the `notes` array verbatim and ask whether they want to (a) switch to
Cloud or (b) force a local install (will OOM or be unusably slow on modern models).

### Choosing an Installation Path

Use the hardware check first. The table below is the fallback for when the
user has already told you their hardware:

| Situation | Recommended Path |
|-----------|------------------|
| `verdict: cloud` from hardware check | **Path A: Comfy Cloud** |
| No GPU / want to try without commitment | **Path A: Comfy Cloud** |
| Windows + NVIDIA + non-technical | **Path B: ComfyUI Desktop** |
| Windows + NVIDIA + technical | **Path C: Portable** or **Path D: comfy-cli** |
| Linux + any GPU | **Path D: comfy-cli** (easiest) |
| macOS + Apple Silicon | **Path B: Desktop** or **Path D: comfy-cli** |
| Headless / server / CI / agents | **Path D: comfy-cli** |

For the fully automated path (hardware check → install → launch → verify):

```bash
bash scripts/comfyui_setup.sh
# Or with overrides:
bash scripts/comfyui_setup.sh --m-series --port=8190 --workspace=/data/comfy
```

It runs `hardware_check.py` internally, refuses to install locally when the
verdict is `cloud` (unless `--force-cloud-override`), picks the right
`comfy-cli` flag, and prefers `pipx`/`uvx` over global `pip` to avoid polluting
system Python.

---

### Path A: Comfy Cloud (No Local Install)

For users without a capable GPU or who want zero setup. Hosted on RTX 6000 Pro.

**Docs:** https://docs.comfy.org/get_started/cloud

1. Sign up at https://comfy.org/cloud
2. Generate an API key at https://platform.comfy.org/login
3. Set the key:
   ```bash
   export COMFY_CLOUD_API_KEY="your-comfyui-key"
   ```
4. Run workflows:
   ```bash
   python scripts/run_workflow.py \
     --workflow workflows/flux_dev_txt2img.json \
     --args '{"prompt": "..."}' \
     --host https://cloud.comfy.org \
     --output-dir ./outputs
   ```

**Pricing:** https://www.comfy.org/cloud/pricing
**Concurrent jobs:** Free/Standard 1, Creator 3, Pro 5. Free tier
**cannot run workflows via API** — only browse models. Paid subscription
required for `/api/prompt`, `/api/upload/*`, `/api/view`, etc.

---

### Path B: ComfyUI Desktop (Windows / macOS)

One-click installer for non-technical users. Currently Beta.

**Docs:** https://docs.comfy.org/installation/desktop
- **Windows (NVIDIA):** https://download.comfy.org/windows/nsis/x64
- **macOS (Apple Silicon):** https://comfy.org

Linux is **not supported** for Desktop — use Path D.

---

### Path C: ComfyUI Portable (Windows Only)

**Docs:** https://docs.comfy.org/installation/comfyui_portable_windows

Download from https://github.com/comfyanonymous/ComfyUI/releases, extract,
run `run_nvidia_gpu.bat`. Update via `update/update_comfyui_stable.bat`.

---

### Path D: comfy-cli (All Platforms — Recommended for Agents)

The official CLI is the best path for headless/automated setups.

**Docs:** https://docs.comfy.org/comfy-cli/getting-started

#### Install comfy-cli

```bash
# Recommended:
pipx install comfy-cli
# Or use uvx without installing:
uvx --from comfy-cli comfy --help
# Or (if pipx/uvx unavailable):
pip install --user comfy-cli
```

Disable analytics non-interactively:
```bash
comfy --skip-prompt tracking disable
```

#### Install ComfyUI

```bash
comfy --skip-prompt install --nvidia              # NVIDIA (CUDA)
comfy --skip-prompt install --amd                 # AMD (ROCm, Linux)
comfy --skip-prompt install --m-series            # Apple Silicon (MPS)
comfy --skip-prompt install --cpu                 # CPU only (slow)
comfy --skip-prompt install --nvidia --fast-deps  # uv-based dep resolution
```

Default location: `~/comfy/ComfyUI` (Linux), `~/Documents/comfy/ComfyUI`
(macOS/Win). Override with `comfy --workspace /custom/path install`.

#### Launch / verify

```bash
comfy launch --background                       # background daemon on :8188
comfy launch -- --listen 0.0.0.0 --port 8190    # LAN-accessible custom port
curl -s http://127.0.0.1:8188/system_stats      # health check
```

---

### Path E: Manual Install (Advanced / Unsupported Hardware)

For Ascend NPU, Cambricon MLU, Intel Arc, or other unsupported hardware.

**Docs:** https://docs.comfy.org/installation/manual_install

```bash
git clone https://github.com/comfyanonymous/ComfyUI.git
cd ComfyUI
pip install torch torchvision torchaudio --extra-index-url https://download.pytorch.org/whl/cu130
pip install -r requirements.txt
python main.py
```

---

### Post-Install: Download Models

```bash
# SDXL (general purpose, ~6.5 GB)
comfy model download \
  --url "https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0/resolve/main/sd_xl_base_1.0.safetensors" \
  --relative-path models/checkpoints

# SD 1.5 (lighter, ~4 GB, good for 6 GB cards)
comfy model download \
  --url "https://huggingface.co/stable-diffusion-v1-5/stable-diffusion-v1-5/resolve/main/v1-5-pruned-emaonly.safetensors" \
  --relative-path models/checkpoints

# Flux Dev fp8 (smaller variant, ~12 GB)
comfy model download \
  --url "https://huggingface.co/Comfy-Org/flux1-dev/resolve/main/flux1-dev-fp8.safetensors" \
  --relative-path models/checkpoints

# CivitAI (set token first):
comfy model download \
  --url "https://civitai.com/api/download/models/128713" \
  --relative-path models/checkpoints \
  --set-civitai-api-token "YOUR_TOKEN"
```

List installed: `comfy model list`.

### Post-Install: Install Custom Nodes

```bash
comfy node install comfyui-impact-pack             # popular utility pack
comfy node install comfyui-animatediff-evolved     # video generation
comfy node install comfyui-controlnet-aux          # ControlNet preprocessors
comfy node install comfyui-essentials              # common helpers
comfy node update all
comfy node install-deps --workflow=workflow.json   # install everything a workflow needs
```

### Post-Install: Verify

```bash
python scripts/health_check.py
# → comfy_cli on PATH? server reachable? checkpoints? smoke test?

python scripts/check_deps.py my_workflow.json
# → are this workflow's nodes/models/embeddings installed?

python scripts/run_workflow.py \
  --workflow workflows/sd15_txt2img.json \
  --args '{"prompt": "test", "steps": 4}' \
  --output-dir ./test-outputs
```

## Image Upload (img2img / Inpainting)

**For a folder of reference photos, crop them to the subject's face first**
with `scripts/facecrop.py` (identity-filtered, see `references/facecrop.md`),
then feed the crops via `--input-image`. Tight single-subject crops beat
full-scene photos for identity work (pitfall 0n).

The simplest way is to use `--input-image` with `run_workflow.py`:

```bash
python scripts/run_workflow.py \
  --workflow workflows/sdxl_img2img.json \
  --input-image image=./photo.png \
  --args '{"prompt": "make it cyberpunk", "denoise": 0.6}'
```

The flag uploads `photo.png`, then injects its server-side filename into
whatever schema parameter is named `image`. For inpainting, pass both:

```bash
python scripts/run_workflow.py \
  --workflow workflows/sdxl_inpaint.json \
  --input-image image=./photo.png \
  --input-image mask_image=./mask.png \
  --args '{"prompt": "fill with flowers"}'
```

Manual upload via REST:
```bash
curl -X POST "http://127.0.0.1:8188/upload/image" \
  -F "image=@photo.png" -F "type=input" -F "overwrite=true"
# Returns: {"name": "photo.png", "subfolder": "", "type": "input"}

# Cloud equivalent:
curl -X POST "https://cloud.comfy.org/api/upload/image" \
  -H "X-API-Key: $COMFY_CLOUD_API_KEY" \
  -F "image=@photo.png" -F "type=input" -F "overwrite=true"
```

## Cloud Specifics

- **Base URL:** `https://cloud.comfy.org`
- **Auth:** `X-API-Key` header (or `?token=KEY` for WebSocket)
- **API key:** set `$COMFY_CLOUD_API_KEY` once and the scripts pick it up automatically
- **Output download:** `/api/view` returns a 302 to a signed URL; the scripts
  follow it and strip `X-API-Key` before fetching from the storage backend
  (don't leak the API key to S3/CloudFront).
- **Endpoint differences from local ComfyUI:**
  - `/api/object_info`, `/api/queue`, `/api/userdata` — **403 on free tier**;
    paid only.
  - `/history` is renamed to `/history_v2` on cloud (the scripts route
    automatically).
  - `/models/<folder>` is renamed to `/experiment/models/<folder>` on cloud
    (the scripts route automatically).
  - `clientId` in WebSocket is currently ignored — all connections for a
    user receive the same broadcast. Filter by `prompt_id` client-side.
  - `subfolder` is accepted on uploads but ignored — cloud has a flat namespace.
- **Concurrent jobs:** Free/Standard: 1, Creator: 3, Pro: 5. Extras queue
  automatically. Use `run_batch.py --parallel N` to saturate your tier.

## Queue & System Management

```bash
# Local
curl -s http://127.0.0.1:8188/queue | python -m json.tool
curl -X POST http://127.0.0.1:8188/queue -d '{"clear": true}'    # cancel pending
curl -X POST http://127.0.0.1:8188/interrupt                      # cancel running
curl -X POST http://127.0.0.1:8188/free \
  -H "Content-Type: application/json" \
  -d '{"unload_models": true, "free_memory": true}'

# Cloud — same paths under /api/, plus:
python scripts/fetch_logs.py --tail-queue --host https://cloud.comfy.org
```

## Web assets (`comfy-assets.py`)

For front-end work, generation is only half the job — a website also needs the
right aspect ratio, format, dimensions, file size, and consistent art direction.
`scripts/comfy-assets.py` handles the second half.

```bash
# what's available
python scripts/comfy-assets.py --presets

# one asset, correct ratio + JPEG/WebP at a sane weight
python scripts/comfy-assets.py \
  --prompt "editorial photograph of ..." --alt "Descriptive alt text" \
  --preset hero --format jpeg,webp --out ./public/img

# variations from one seed (same visual world)
python scripts/comfy-assets.py --prompt "..." --preset card --batch 4 --seed 7
```

Presets: `hero` 16:9, `og` 1.91:1 (Open Graph safe area), `card` 4:3,
`card-wide` 3:2, `portrait` 4:5, `portrait-lg` 2:3, `square` 1:1,
`mobile` 9:16, `panorama` 21:9.

- Generates at the smallest sensible canvas at-or-above the output size, then
  **only ever downscales** — it refuses to upscale and says so.
- Flattens alpha onto white for JPEG (no alpha channel in JPEG).
- Writes `assets.manifest.json` capturing prompt, alt text, seed, preset,
  dimensions, and per-format file size. Alt text starts as the prompt; override
  it with `--alt`.
- `--seed N` is what makes a set look like one site. Generate a batch, keep the
  seed, and every image shares a visual world.
- Negative prompt defaults to the usual suspects (text, watermark, anatomy).
  Qwen-Image-2.1 renders text well, so **omit** "text" from `--negative` when you
  actually want typography.
- **130–250s per image on this machine.** Batch it; don't generate inline while
  iterating on layout.

## Pitfalls

0. **Model visibility is per-server, not per-machine.** A ComfyUI server only sees
   the model dirs it was told about at boot. Two servers on one Mac routinely see
   different libraries. Before debugging a "missing model," confirm what the
   *running* server actually lists — never infer it from the filesystem:

   ```bash
   curl -s http://127.0.0.1:8188/object_info | python3 -c "
   import json,sys; d=json.load(sys.stdin)
   for n in ('UNETLoader','DiffusionModelLoader','CLIPLoader','VAELoader'):
       for k,v in (d.get(n,{}).get('input',{}).get('required') or {}).items():
           if isinstance(v,list) and v and isinstance(v[0],list) and v[0] and isinstance(v[0][0],str):
               print(f'{n}.{k}:', v[0])"
   ```

   If the dropdown lists only `default`/`fp8_*` weight-type enums and no real
   filenames, the server has no model paths configured. That is the bug.

   Ways model paths get set, and the trap in each:
   - **comfy-cli install:** needs `extra_model_paths.yaml` in the ComfyUI root
     (ComfyUI reads it automatically). Omit `is_default: true` to make the block
     *additive* to the local `models/` dir instead of replacing it.
   - **Comfy Desktop (retired 2026-10-23):** generated its own files and passed
        `--extra-model-paths-config <App Support>/Comfy Desktop/instance-model-paths/<id>.yaml`.
        Launching `main.py` by hand WITHOUT that flag reproduced the "invisible
        models" bug exactly. When testing a Desktop install from the shell, copy the
        flag out of `installations.json` / the instance-model-paths dir. (No longer
        applicable here — Desktop is gone; kept as a general lesson.)
   - Stale Desktop **v1** config (`~/Library/Application Support/ComfyUI/config.json`
     plus `extra_models_config.yaml`) can point at a basePath that no longer
     exists. Check it before assuming a path bug is a permissions bug.

0b. **Two servers on one port, different interfaces, is a silent failure.** A
   loopback-bound server and a tailnet-bound one both "work" on 8188 while
   fighting over the SQLite DB. Symptom is an empty `/history` and error messages
   that are generated then dropped:

   ```
   Failed to initialize database ... Could not acquire lock on
   '/path/user/comfyui.db'. Another ComfyUI process may already be using it.
   ```

   Diagnose with `lsof -nP -iTCP:8188` (LISTEN *and* ESTABLISHED lines) plus
   `lsof /path/user/comfyui.db`. Do not kill a server on the tailnet interface
   reflexively — check for ESTABLISHED connections first; it may be serving
   another machine (e.g. a laptop on the tailnet) and be very much in use.
   (This machine now runs a single install on :8188, so the two-server case is
   historical — kept as a general lesson.)

0c. **Qwen-Image-2.1 (Sept 2026) needs ComfyUI >= 0.37.0.** Merged via Comfy-Org/ComfyUI
   PR #16400. Older ComfyUI has no `TextEncodeQwenImage21` / `QwenImage21Cache`
   nodes and cannot load the weights at all. Check `<install>/comfyui_version.py`
   before downloading 30GB of anything. Nodes land in
   `comfy_extras/nodes_qwen.py`.

   Its official templates are **hardcoded to int8_convrot**
   (`qwen_image_2.1_int8_convrot.safetensors`, `qwen3vl_8b_int8_convrot.safetensors`).
   If you downloaded bf16 instead, the dropdowns default to filenames you don't
   have. Either switch the dropdowns to your bf16 files or fetch the int8 pair.

   T2I and Edit templates want *different* text encoders
   (`qwen3.5_9b_qwen_image_2.1_pe_t2i` vs `..._pe_i2i`); the single
   `qwen3vl_8b_bf16` is the one that serves both.

   Working single-file set (Comfy-Org/Qwen-Image-2.1), bf16, ~32.4 GB total:
   `diffusion_models/qwen_image_2.1_bf16.safetensors` (14.23 GB),
   `text_encoders/qwen3vl_8b_bf16.safetensors` (17.53 GB),
   `vae/qwen_image_2.1_vae_bf16.safetensors` (0.68 GB).

   Minimal working API-format graph (verified on 0.37.4, MPS, 143 s for
   1024x1024 @ 25 steps including weight load):

   ```json
   {"451": {"class_type": "UNETLoader",
            "inputs": {"unet_name": "qwen_image_2.1_bf16.safetensors", "weight_dtype": "default"}},
    "452": {"class_type": "TextEncodeQwenImage21",
            "inputs": {"clip": ["453", 0], "prompt": "...", "negative_prompt": "...",
                       "resolution": 1024, "images": []}},
    "453": {"class_type": "CLIPLoader",
            "inputs": {"clip_name": "qwen3vl_8b_bf16.safetensors", "type": "qwen_image", "device": "default"}},
    "454": {"class_type": "VAELoader",
            "inputs": {"vae_name": "qwen_image_2.1_vae_bf16.safetensors"}},
    "458": {"class_type": "KSampler",
            "inputs": {"model": ["451", 0], "positive": ["452", 0], "negative": ["452", 1],
                       "latent_image": ["452", 2], "seed": 42, "steps": 25, "cfg": 1.0,
                       "sampler_name": "euler", "scheduler": "simple", "denoise": 1.0}},
    "457": {"class_type": "VAEDecode", "inputs": {"samples": ["458", 0], "vae": ["454", 0]}},
    "459": {"class_type": "SaveImage", "inputs": {"filename_prefix": "qwen21", "images": ["457", 0]}}}
   ```

   Two schema facts that are not guessable: `TextEncodeQwenImage21` requires
   `negative_prompt` and `resolution` (no `max_sequence_length`), and its
   **output 2 is a LATENT** — feed that to the KSampler instead of adding an
   `EmptyLatentImage`. Output names are `positive`, `negative`, `latent`.

   The graph above is the **bf16** set. This machine (Mac Studio) keeps the
   **int8_convrot** files instead, so use
   `workflows/qwen_img21_txt2img_int8.json` (same graph, int8 filenames) —
   and note the GGUF workflow `qwen_img21_txt2img.json` in the same folder is
   a dead end here (city96's ComfyUI-GGUF has no 2.1 support; the Q4_K_M gguf
   is not on disk). Text-rendering grading battery: `scripts/run_text_battery.py`.

   Reference images go in as a **dict**, not a dotted key:
   `"images": {"image_1": ["470", 0]}`. A bare `"image_1"` raises
   `TypeError: ... unexpected keyword argument 'image_1'`. See
   `references/template-integrity.md`.

   Background removal specifics: build the graph from the official Qwen-Image
   Edit template (flattened per `references/template-integrity.md`; any scratch
   copy is ephemeral and gone within a day). **`resolution` is a total
   pixel BUDGET, not width or height** — aspect ratio preserved, default 1024,
   schema max 4096, and `0` means "no resize beyond a multiple of 32". The
   template ships `0`; the 4096 max does not mean 4096x4096 is tested here.

   **Verified: alpha works, subject preservation does not (yet).** A run on a
   generated greyscale portrait produced valid RGBA with genuine transparency
   (39% fully transparent, correctly placed) but **destroyed the subject** — 86%
   of opaque pixels differed from the input. Most likely cause: the test image
   had soft studio gradients, and background removal needs a clean opaque
   subject against a flat field. Test on a real product-on-white or
   person-against-wall photo first. Transparent pixels also retain non-zero RGB
   (diffusion premultiplication garbage) which can fringe in compositors, and the
   official template uses `SaveImageAdvanced` rather than plain `SaveImage` —
   prefer it for alpha work.

0g. **Model swapping dominates wall-clock.** int8 vs bf16 is ~15% apart in
   isolation, but a queue alternating dtypes pays a 13.5 GB UNet reload plus a
   16.7 GB text-encoder reload per switch — observed 247s for a 25-step job
   (9.28s/it) against 131s with one dtype resident. Pick one dtype per session.

0g2. **ComfyUI 0.37 "template nodes" are packed subgraphs that do NOT convert
   to API format.** The official template files (e.g. `image_qwen_image_2_1_t2i`)
   contain a node whose `type` is a UUID (e.g. `c291ceec-b98f-4751-9d0b-7bc288f27b30`)
   defined in `definitions.subgraphs` inside the workflow JSON. That packed graph
   bundles multiple nodes (including a `TextGenerate` LLM prompt-enhancer with
   its own `qwen3.5_9b` text encoder) behind one node. `convert_workflow.py`
   refuses these with a clear error. Solution: use the flat hand-built workflows
   (`qwen-image-2.1-simple.api.json`) instead — same model, no subgraph, no
   hidden LLM dependency. The 2 archived template files live in
   `~/ComfyUI-Shared/backups/workflows-editor-format-2026-10-22/archived-subgraph-templates/`
   if you ever need to inspect the packed graph.

0q. **Isolating a test on a second ComfyUI instance: use `--disable-manager`, and never put the `--user-directory` under `~/.hermes/cache/scratch/`.** Two separate traps, both hit 2026-10-29:

   - **ComfyUI-Manager hijacks stderr.** Its `prestartup_script.py` wraps `sys.stderr` and, on the first tqdm progress write, calls `original_stderr.flush()`. If the parent's stderr pipe is gone (backgrounded launch with a closed pipe), that raises `BrokenPipeError` **mid-generation** — the model has already loaded and been generating for minutes, and the job dies with `status_str: error`. It reads exactly like a model/VRAM failure and is not one. Fix: launch with `--disable-manager`.
   - **The scratch dir is pruned.** `--user-directory ~/.hermes/cache/scratch/...` gets wiped by the 24h scratch pruner, and the instance dies at startup. Use `~/.hermes/cache/<name>/` (outside `scratch/`) for any long-lived instance dir.

   Working launch (isolated, leaves the production :8188 untouched):

   ```bash
   cd /Users/macstudio/ComfyUI && exec ./venv/bin/python main.py \
     --listen 127.0.0.1 --port 8189 \
     --user-directory /Users/macstudio/.hermes/cache/comfy-<name>/user \
     --disable-manager
   ```

   **Text encoders run on CPU on Apple Silicon.** `text_encoder_device()` (`comfy/model_management.py:1219`) returns `cpu` because MPS sets `vram_state=SHARED`, missing the `(HIGH_VRAM, NORMAL_VRAM)` branch. A 9B text encoder measured **~2.05 s/token** — a 200-token `TextGenerate` takes ~7 minutes. Budget minutes for any LLM-in-the-graph node, not seconds.

   **`TextGenerate` dynamic-combo inputs are dotted keys, not a nested dict.** `sampling_mode` must be flattened: `"sampling_mode": "on"`, `"sampling_mode.temperature": 1.0`, `"sampling_mode.top_k": 20`, `"sampling_mode.top_p": 0.95`, `"sampling_mode.min_p": 0.0`, `"sampling_mode.repetition_penalty": 1.05`, `"sampling_mode.seed": 1234`, `"sampling_mode.presence_penalty": 0.0`. Passing `{"sampling_mode": {"temperature": ...}}` fails validation.

   **`use_default_template=False` silently discards the system prompt.** `comfy_extras/nodes_textgen.py:56` does `system_prompt=system_prompt if use_default_template else ""`. The official Qwen-Image-2.1 T2I template sets it to False, so the PE prompt-enhancer answers conversationally ("Here is a concept for…", markdown headings) instead of returning an image prompt. Set `use_default_template=True` and the same model returns a clean image prompt. Verified by A/B render 2026-10-29.

   Also: `TextGenerate` has no MTP head support on the `qwen3.5_9b...pe_t2i` checkpoint — set `mtp: "off"`.

0g3. **Input dir symlinks fail the path-traversal guard — real dirs only.**
   Sharing input images across installs by symlinking into the input dir
   (`ln -s ~/ComfyUI-Shared/input/starters_samples ~/ComfyUI/input/starters_samples`)
   makes LoadImage fail with `Invalid image file:` even though the file list
   and `/view` find the target. `folder_paths.exists_annotated_filepath()` resolves `realpath`
   on both sides of `is_within_directory()`, so a symlink pointing outside the
   input dir is rejected as a traversal attempt. Workflows and model dirs are
   exempt (additive `extra_model_paths.yaml`), but the input dir is not. Fix:
   `cp -R` the samples into each install's `input/` (re-copy when samples
   change). This burns ~30 min of debugging on first encounter — verified 2026-10-22.

0h. **The 500 on `/prompt` is real and has a known workaround.** `run_workflow.py`
   can get `500 Internal Server Error / Server got itself in trouble` where a
   direct POST of the same payload succeeds. Build the payload, POST with curl,
   poll `/history/<prompt_id>`. Use direct POST when you need real validation
   errors — a 500 hides them. Distinguish from pitfall 0j: a top-level
   `_comment` key 500s *every* time (the scripts now strip it — fixed
   2026-10-20); the 0h failure is intermittent on an identical payload.

0i. **Verify generated images; don't infer them from metadata.** An RGBA
   container does not prove a cutout happened. Decode the alpha channel, count
   transparent vs opaque pixels, and diff subject pixels against the input. A
   vision model can hallucinate confidently on generated images (it described a
   norbornane chemical structure in a portrait, twice, on both raw and composited
   versions) — cross-check with pixel statistics before reporting. Compositing
   over a red/grey checkerboard makes both transparency and missing subjects
   immediately visible. Even a checkerboard composite did not stop a vision model
   calling a broken cutout (37% of the subject's dark pixels removed) "clean" and
   reading "WOOLY BEAR" as "COOL BEA" — vision is for eyeballing; pixel stats are
   the verdict.

## Watch a job run

Browser at `http://127.0.0.1:8188` is the best view. Terminal options, including
the `ws_monitor.py` client_id gotcha, are in
`references/template-integrity.md`.

0d. **Apple Silicon (MPS) cannot run fp8 weights.** Qwen-Image 1.0's default
   `qwen_image_fp8_e4m3fn.safetensors` dies at load with:

   ```
   TypeError: Trying to convert Float8_e4m3fn to the MPS backend but it does
   not have support for that dtype.
   ```

   Not a memory problem. Use bf16, or int8_convrot / GGUF, on Mac. Qwen-Image-2.1
   already dropped fp8, which is why it works where 1.0 doesn't.

0e. **Verify safetensors by byte size against Content-Length, not by eyeballing
   `du`.** `rc=0` from a resumed `curl --continue-at -` does NOT prove the file is
   complete. And `du -m` reports MiB while HF reports decimal GB, so a correct file
   looks ~7% "short" (13.25 vs 14.23). Compare exact byte counts:

   ```bash
   stat -f "%z" local.safetensors
   curl -sIL "$URL" | grep -i ^content-length | tail -1
   ```

   Header sanity check: first 8 bytes are a little-endian u64 length, then `{"__metadata"`.
   Use `od -c` to inspect — do not grep for specific magic bytes, the length varies
   per file.

0f. **Download scripts: never flatten model subdirectories.** `--output "$(basename
   "$f")"` writes every file into the models/ root where ComfyUI cannot see it.
   Preserve the full relative path (`diffusion_models/foo.safetensors`) and
   `mkdir -p "$(dirname ...)"` first.

0j. **Direct POST of a workflow with stock `_comment` keys 500s.** The skill's stock workflow files carry
    a top-level `_comment` string. `run_workflow.py` strips it; a hand-built direct POST does not —
    ComfyUI's `validate_prompt` iterates every top-level key as a node and dies with
    `AttributeError: 'str' object has no attribute 'get'` (server log traceback) → 500 "Server got itself
    in trouble". Pop `_comment` before submitting.

0k. **KSampler `seed: -1` is rejected by this build.** Direct POST validation fails with
    `value_smaller_than_min: Value -1 smaller than min of 0` on `seed`. Generate a real seed
    (`int.from_bytes(os.urandom(4), 'big')`) instead of using the -1 randomize convention.

0l. **Qwen-Image-2.1 masked inpaint on this stack:** `VAEEncodeForInpaint` + `LoadImageMask` exist
    (no SAM/segmentation nodes installed — build masks programmatically with PIL from a vision-model
    box read). Wire KSampler's `latent_image` to the VAEEncodeForInpaint latent, not the text encoder's
    latent. Mask only the region to regenerate; the unmasked latent hard-locks the foreground. The
    official "Image Inpainting (Qwen-image)" blueprint at `~/ComfyUI/blueprints/` is Qwen 1.0-era
    (AuraFlow/ControlNet/FluxKontext) — do not use it for the 2.1 int8 files.

0m. **Flat-design cutouts: near-white flood-fill, never luminance threshold.** For
   flat-vector art on a solid white field (t-shirt designs, stickers, logos), the
   reliable way to a transparent cut is a 4-connected flood-fill from the image
   corners over near-white pixels only (all channels > ~235), then feather the
   edge ~1px. Two traps:
   - **Never threshold on luminance.** Yellow fill is high-luminance (~226) and
     would be removed as "white"; the flood-fill's enclosure test is what keeps
     the yellow diamond intact.
   - **Never remove dark pixels.** A luminance flood-fill eats thin dark features
     (caterpillar bristles) via their anti-aliased edges — observed 37% of a
     subject's dark body removed. Protect the subject: only near-white pixels
     connected to the border become transparent.
   Verify with pixel stats: the subject's dark pixels must be ~100% opaque in the
   cutout and the white field gone. This is a *specialized* technique — it only
   applies to flat colors on a solid white background with the subject enclosed
   by a dark border. For photos, white-in-subject, or non-white backgrounds use
   the qwen bgremoval graph or rembg instead. For flat art, PIL lanczos 4x
   upscale is crisp enough — no need for the ESRGAN `4x-UltraSharp.pth` (not on
   disk) that `upscale_4x.json` wants. Script: `scripts/cutout_flat.py`.

0n. **Subject references on Qwen-Image-2.1: `TextEncodeQwenImage21`'s `vae` input is OPTIONAL and silently required for identity.** (node tooltip) — with no `vae` wired, the node silently drops every reference and you get a generic breed-typical image with no validation error. Fixed 2026-10-20 by adding `"vae": ["454", 0]` to the encode node in `workflows/qwen_subject_refs.json`; proven by control runs (Patrick's photo as reference produced a human portrait once wired, identical generic dog before). Same-session lessons baked into that workflow's usage:
    - cfg 1.0 = negative prompt is INERT on this stack (flow matching). Never fix identity/coat color via negatives; state attributes in the POSITIVE prompt ("solid jet-black shaggy coat, floppy ears, no tan or brown markings").
    - Crop reference photos tight to the subject (subject fills most of the frame) — `ref_cora_tight.png` (649×629) beats the full-scene original. Automate the cropping with `scripts/facecrop.py` for a whole folder.
    - Prompt pattern that works: "the dog in image_1" + explicit attribute description. Breed-name words ("German Shepherd") pull hard toward breed stereotypes and overpower the reference.

0p. **"Render" language invites CGI; "photograph" language invites photorealism.** For product/photo-real work, never write "8k product render", "commercial advertising quality", or "3D render" into the prompt — the model literally renders. Use photographic framing instead: "shot on a full-frame camera with an 85mm lens at f/2.8", "natural window light", "subtle film grain", "unretouched photograph". Verified 2026-10-24 on Qwen-Image-2.1: the same device + seed, reworded from render-language to photograph-language, flipped a macro shot from "reads as CGI" to "reads as a real photograph" (vision QC flagged zero CGI tells). Caveat: prompt language fixes ~half the gap. A pristine object on a black pedestal against a clean gradient still reads as a render no matter the wording — that's a *compositional* tell. For true photorealism put the subject in a real scene (dock, tackle box, workshop bench, natural light, slight imperfections), not a studio pedestal.

1. **API format required** — every script and the `/api/prompt` endpoint expect
   API-format workflow JSON. The scripts detect editor format (top-level
   `nodes` and `links` arrays) and tell you to re-export via
   "Workflow → Export (API)" (newer UI) or "Save (API Format)" (older UI).

2. **Server must be running** — all execution requires a live server.
   `comfy launch --background` starts one. Verify with
   `curl http://127.0.0.1:8188/system_stats`.

3. **Model names are exact** — case-sensitive, includes file extension.
   `check_deps.py` does fuzzy matching (with/without extension and folder
   prefix), but the workflow itself must use the canonical name. Use
   `comfy model list` to discover what's installed.

4. **Missing custom nodes** — "class_type not found" means a required node
   isn't installed. `check_deps.py` reports which package to install;
   `auto_fix_deps.py` runs the install for you.

5. **Working directory** — `comfy-cli` auto-detects the ComfyUI workspace.
   If commands fail with "no workspace found", use
   `comfy --workspace /path/to/ComfyUI <command>` or
   `comfy set-default /path/to/ComfyUI`.

6. **Cloud free-tier API limits** — `/api/prompt`, `/api/view`, `/api/upload/*`,
   `/api/object_info` all return 403 on free accounts. `health_check.py` and
   `check_deps.py` handle this gracefully and surface a clear message.

7. **Timeout for video/audio workflows** — auto-detected when an output node
   is `VHS_VideoCombine`, `SaveVideo`, etc.; the default jumps from 300 s to
   900 s. Override explicitly with `--timeout 1800`.

8. **Path traversal in output filenames** — server-supplied filenames are
   passed through `safe_path_join` to refuse anything escaping `--output-dir`.
   Keep this protection on — workflows with custom save nodes can produce
   arbitrary paths.

9. **Workflow JSON is arbitrary code** — custom nodes run Python, so
   submitting an unknown workflow has the same trust profile as `eval`.
   Inspect workflows from untrusted sources before running.

10. **Auto-randomized seed** — pass `seed: -1` in `--args` (or use
    `--randomize-seed` and omit the seed) to get a fresh seed per run.
    The actual seed is logged to stderr.

11. **`tracking` prompt** — first run of `comfy` may prompt for analytics.
    Use `comfy --skip-prompt tracking disable` to skip non-interactively.
    `comfyui_setup.sh` does this for you.

## Verification Checklist

Use `python scripts/health_check.py` to run the whole list at once. Manual:

- [ ] `hardware_check.py` verdict is `ok` OR the user explicitly chose Comfy Cloud
- [ ] `comfy --version` works (or `uvx --from comfy-cli comfy --help`)
- [ ] `curl http://HOST:PORT/system_stats` returns JSON
- [ ] `comfy model list` shows at least one checkpoint (local) OR
      `/api/experiment/models/checkpoints` returns models (cloud)
- [ ] Workflow JSON is in API format
- [ ] `check_deps.py` reports `is_ready: true` (or only `node_check_skipped`
      on cloud free tier)
- [ ] Test run with a small workflow completes; outputs land in `--output-dir`

## Known quirks: Qwen deployment and the run_workflow.py 500

**ComfyUI version floor.** Qwen models require ComfyUI **0.37.0 or newer**. Older versions ship
without the required nodes. The Studio install is already past this floor, so check
`comfy --version` before assuming a missing node is a model problem.

**Model placement is hierarchical.** Weights go in typed subdirectories under
`/Users/macstudio/models/diffusion/` (`diffusion_models/`, `text_encoders/`, `vae/`), never in
the root. The root is on the search path but the loaders resolve by subdirectory, so a root-level
drop is invisible to the UI.

**`int8_convrot` vs `bf16`.** The official templates target `int8_convrot`. On Apple Silicon the
`bf16` weights are often the better choice. If you stay on the templates you must either select the
`bf16` files manually in the UI or download the `int8` pair; otherwise the node dropdowns default to
filenames you do not have on disk and fail with a bare "file not found."

**Download scripts must preserve the full relative path.** A `curl` loop that flattens the Hugging
Face repo structure into one directory breaks model resolution, because ComfyUI resolves weights by
their subdirectory. Mirror the upstream path exactly.

**`run_workflow.py` returns 500 "Server got itself in trouble."** The submission path through
`run_workflow.py` intermittently fails with that error. It is a client-side submission problem, not a
generation problem. Workaround: POST the full workflow JSON directly to the ComfyUI REST endpoint
`/prompt`; that path is reliable.
