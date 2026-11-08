---
name: local-image-gen
description: Generate images locally on the Studio/MacBook engines.
version: 0.1.0
author: Hermes
license: MIT
platforms: [macos]
metadata:
  hermes:
    tags:
      - Image-Generation
      - ComfyUI
      - Unsloth-Studio
      - Local-Models
      - MLOps
    category: creative
---

# Local Image Generation — Studio & MacBook

Interactive skill for generating images with **local models only**: pick the
machine (Mac Studio / MacBook Pro), the backend (ComfyUI / Unsloth Studio),
and the model, then run the generation and deliver the file. It does NOT use
any cloud image API, and it never lists a model/backend that isn't installed
and runnable on this fleet. Engines are probed live before options are shown.

## When to Use

- "generate an image", "make a picture of …", "draft a product/mockup image"
- "use the Mac Studio / MacBook for image gen", "on ComfyUI / Unsloth"
- running a ComfyUI blueprint/editor JSON against the local server
- Patrick asks which local engine/model is best for a given prompt

## Prerequisites

- Mac Studio: ComfyUI serving `http://127.0.0.1:8188` (no auth). Weights in
  `/Users/macstudio/models/diffusion` via `extra_model_paths.yaml`.
- MacBook: `ssh macbook` works; Unsloth Studio serving `127.0.0.1:8888`
  (loopback only) with an agent key in
  `/Users/prasta/.unsloth/studio/auth/agent_api_key.json`.
- Mac Studio Unsloth: `open -a Unsloth` launches it on the same port/keyfile
  path (`/Users/macstudio/.unsloth/...`) — installed, not auto-started.
- The `comfyui` skill's `scripts/run_workflow.py` exists (it executes the
  converted graphs). No HF tokens, no API keys beyond the local app file.

## The Interactive Flow (mandatory)

Ask these questions with `clarify` **before generating** — Patrick's choices,
not guesses. Skip any question only if this session already answered it or the
probe below leaves exactly one live option (then state the pick, don't ask).

1. **Machine + backend combined** (backend availability is machine-bound):
   probe first — `terminal`: ComfyUI Studio (`curl -m 2 :8188/system_stats`),
   Unsloth per machine (`curl -m 2 :8888/api/health` locally; over ssh use
   `--machine macbook --list`). Offer only what's live, e.g.:
   - ComfyUI · Mac Studio
   - Unsloth Studio · MacBook
   - Unsloth Studio · Mac Studio (if app is up)
2. **Model** — build choices from the live inventory (never from memory):
   ComfyUI: read loader `choices` (`scripts/probe_models.py` or
   `/object_info`); Unsloth: `unsloth_gen.py --machine <m> --list`.
3. **Prompt + knobs** — if the prompt isn't already in the request, ask it
   open-ended alongside defaults: size (Z-Image 1024² / quick 512²), steps
   (4–8 turbo, 20–25 base/Qwen), seed (fixed unless he wants variation).

Then run the matching procedure below and deliver the file with
`MEDIA:/absolute/path.png`.

## Style Defaults (model bias)

Qwen-Image and Z-Image are trained on Chinese-heavy data and default to
East Asian aesthetics even for prompts that don't specify ethnicity. Unless
the user explicitly asks for Asian/East Asian features, append a neutral
style hint to the prompt to counter that default, e.g.:

- `, Western/European features, neutral default` (people)
- `, Western-style setting` (scenes/architecture)

If the user names an ethnicity or aesthetic ("Asian woman", "Japanese
street", "Korean style"), omit the hint — their explicit ask wins. When in
doubt, ask in the prompt question rather than guessing.

## How to Run

- **ComfyUI · Mac Studio** — convert the blueprint once, then reuse:
  `terminal`: `python3 ~/.hermes/skills/creative/local-image-gen/scripts/comfy_editor_to_api.py
  "<blueprint.json>" --host http://127.0.0.1:8188 --raw -o <bare.json>
  --schema-out <schema.json>`, then run the `comfyui` skill's
  `run_workflow.py --workflow <bare.json> --schema <schema.json>
  --host http://127.0.0.1:8188 --args '{"text":"…","seed":N,…}'
  --output-dir <dir>`.
- **Unsloth Studio · either machine** — one call, loads the model itself:
  `terminal`: `python3 ~/.hermes/skills/creative/local-image-gen/scripts/unsloth_gen.py
  --machine macbook --model <id> --prompt "…" --size 1024x1024 --steps 25
  --seed N --out <dir>`.

## Quick Reference

| Need | Command |
|---|---|
| Studio live model slots | `python3 scripts/probe_models.py --host http://127.0.0.1:8188` |
| Blueprint → runnable | `scripts/comfy_editor_to_api.py BP.json --host :8188 --raw -o g.json --schema-out s.json` |
| Run converted graph | comfyui skill `run_workflow.py --workflow g.json --schema s.json --host :8188 --args '{...}'` |
| Unsloth inventory | `scripts/unsloth_gen.py --machine studio\|macbook --list` |
| Unsloth generate | `scripts/unsloth_gen.py --machine macbook --model ID --prompt P [--steps 25 --seed N --size WxH --init-image F]` |
| Engines alive? | `curl -m 2 http://127.0.0.1:8188/system_stats; curl -m 2 http://127.0.0.1:8888/api/health` |

## Procedure

1. Probe engines (`terminal`), assemble the real option set.
2. Ask the three flow questions via `clarify` (one call, up to 3 questions).
3. ComfyUI path: pick a blueprint that matches the task
   (`Text to Image (Z-Image-Turbo)`, `(Qwen-Image)`, `Image Edit (Qwen 2509)`…
   — only ones whose loader slots resolve; see references/backends.md).
   Convert with `--raw` + `--schema-out`; reuse a cached conversion.
4. Inject via `--args` with exact values: model names **verbatim** from the
   choices arrays; integers for width/height/seed/steps.
5. Unsloth path: `unsloth_gen.py` loads the model (first run of a family can
   take minutes), generates, downloads the signed URL back through ssh.
6. Verify the output with `vision_analyze` against the prompt (catches slot
   mapping and stale-name bugs), then deliver `MEDIA:<path>`.

## FILE CONVENTIONS

- Durable output -> `~/.hermes/outputs/image-gen/` (NEVER the scratch dir — pruned 24h). Batch renders go in `runs/<YYYY-MM-DD>-<concept>/`; single ad-hoc renders may drop a date-stamped file at the root. Report the absolute path back to Patrick via `MEDIA:`.
- **`~/ComfyUI/output/` is a SPOOL, not durable storage.** A launchd job
  (`ai.hermes.comfyui-gallery-sweep`, every 600s) sweeps it into
  `~/Pictures/ComfyUI/<YYYY-MM>/`, renaming files to a prompt-slug + seed and
  merging them into that month's `manifest.json`. Files vanish from the spool
  within minutes. Copy anything you need to keep BEFORE the next sweep, or
  look in `~/Pictures/ComfyUI/` after the fact.

## Pitfalls

- **Qwen-Image-2.1 portrait graphs: rebuild the latent.**
  `TextEncodeQwenImage21` emits positive/negative/**latent** and its latent is
  square-only (`resolution` only sizes *reference* images). For a portrait/
  landscape wallpaper, keep the shipped `qwen_img21_txt2img_int8.json` nodes
  but swap the KSampler's `latent_image` to a new `EmptySD3LatentImage` with the
  real width/height, and hand-write a schema for the changed nodes.
- **A Qwen-Image-2.1 render will outlive run_workflow.py's 300s wait.** At
  1088x2368 / 25 steps / cfg 2.5 it measured **~25.3 s/it ≈ 11 min** (the 8B
  text encoder runs on CPU here, the int8 DiT is only ~6.9GB resident), so the
  client exits with `{"status": "timeout"}` while the job keeps running
  server-side. Do NOT relaunch — poll
  `GET /history/<prompt_id>`, then copy the PNG out of `~/ComfyUI/output/`
  immediately (it is a 600s-swept spool). `GET /internal/logs/raw` shows the
  tqdm step counter for progress.
- **Z-Image-Turbo cannot hold `caduceus`.** Across 6 seeds it produced one
  snake, a bird, a heart, or a plain rod — never two entwined serpents with
  wings on top. For symbol-critical prompts use Qwen-Image-2.1, which also
  honours a negative prompt (Z-Image's negative is a `ConditioningZeroOut`).
  Z-Image likewise invents pseudo-Latin lettering on poster-style prompts; keep
  `no typography, no letters, no writing` in the prompt and QC for it.

- **Run these scripts with the ComfyUI venv Python, not the shell default.**
  Bare `python3` on the Studio resolves to Hermes's own install venv (Python
  3.14) whose `urllib3` and `PIL._imaging` are broken (`TypeError: unsupported
  operand type(s) for |` / `cannot import name '_imaging'`). Use
  `/Users/macstudio/ComfyUI/venv/bin/python <script>`; for Pillow work prefix
  `env -u PYTHONPATH` (the Hermes env leaks a PYTHONPATH that shadows it).
- The skill dir is `~/.hermes/skills/creative/local-image-gen/`, not
  `mlops/local-image-gen/` — older copies of this file had the wrong path.
- `run_workflow.py` wraps the graph itself — feed it the **bare** map
  (`--raw`), never the default wrapped output, or submission 400s.
- Blueprint-exposed slots (unet_name, clip_name, text…) are invisible to
  run_workflow's auto-schema: always pass `--schema-out` + `--schema`.
- Over ssh, curl `-H` auth headers do NOT reach the remote process
  ("Not authenticated"); `unsloth_gen.py` pipes them through `curl -K-`
  stdin config — keep that pattern.
- Downloading the signed render URL back over ssh: ssh flattens argv into
  one space-joined string, so a `sh -c 'S' x URL` structure is destroyed
  (x/URL leak into base64's args) AND the remote zsh globs the unquoted `?`
  in the signed URL ("no matches found"). Fix (in `download()`): pass a
  single self-contained command string with the URL `shlex.quote`d inline,
  no `sh -c`.
- `/v1/images/generations` returns **503 "No image model loaded"** until
  load finishes; `--model` handles this via `/api/inference/images/load`.
- Single-file GGUF repos (e.g. `unsloth/Qwen-Image-Edit-2511-GGUF`) must be
  loaded with `--gguf-filename` (script sends `model_kind: "gguf"` + the .gguf
  file from the HF snapshot dir); a bare `--model` load is rejected in-body
  or resolves to a different installed variant. `--list` shows repo entries
  whose weights may be LFS pointers only (28K cache = not really installed) —
  trust `images/status`, not the list.
- `abenzerps/Qwen-Image-2.1-Uncensored-Quantized` (uncensored Qwen-Image-2.1,
  Q4_K_M GGUF): the DiT GGUF may already be in the HF cache while the
  companions are missing — the repo needs `text_encoders/qwen3vl_8b_int8_convrot.safetensors`
  + `vae/qwen_image_2.1_vae_bf16.safetensors` in the same snapshot before it
  loads. `du -shL` the snapshot (not `du -sh`, which skips symlinked blobs).
- Unsloth's load-time memory guard refuses oversized loads and ONLY honors the
  env var `UNSLOTH_DIFFUSION_ALLOW_OVERSIZED_LOAD=1` (the per-request
  `allow_oversized` field is generate-time only). Set it in the user session
  (`launchctl setenv ... 1`) and restart the Unsloth app so the backend
  respawns with it; `--allow-oversized` on unsloth_gen.py covers the generate
  step. The guard's estimate is often wrong (refused ~16GB load with 27GB
  free) — check `memory_pressure -Q` before trusting it.
- Edit-only models (status `workflows: ["edit"]`) refuse plain t2i:
  "load a text-to-image model to use this endpoint" — pass `--init-image` for
  edits or switch to ComfyUI Studio for generation.
- Unsloth Studio on the Mac Studio is installed but not running by default;
  Connection refused on :8888 there means launch it, don't re-probe endlessly.
- ComfyUI has no auth on :8188; Unsloth does — 401 = key drift, re-read
  `minted[-1]` from the keyfile (keys rotate).
- Model IDs/filenames must match server output exactly — stale names 400/404.
- Don't offer blueprints whose required weights aren't installed (most of
  the ~120 in `blueprints/`); the runnable set is in references/backends.md.

## Prompt Enhancement (PE) — the 9B qwen3.5 PE encoder

`qwen3.5_9b_qwen_image_2.1_pe_t2i.int8_convrot.safetensors` (8.8G) is a
**prompt-enhancer**, not an image encoder. It rewrites a short prompt into a
detailed image prompt. Verified working 2026-10-29.

**The upstream template is broken.** `comfy_extras/nodes_textgen.py:56` does
`system_prompt=system_prompt if use_default_template else ""` — so the
official Qwen-Image-2.1 T2I template (which sets `use_default_template=False`)
**silently discards the system prompt**. The model then answers conversationally
("Here is a concept for…", markdown headings) instead of returning an image
prompt. Always set `use_default_template=True`.

Working wiring:

    CLIPLoader:   clip_name = qwen3.5_9b_qwen_image_2.1_pe_t2i.int8_convrot.safetensors
                  type = stable_diffusion
                  device = default
    TextGenerate: system_prompt = <image-gen system prompt, inner text — chat
                  wrapper <|im_start|>system\n…<|im_end|> stripped>
                  use_default_template = TRUE
                  max_length = 200..400
                  mtp = "off"          (checkpoint has no MTP head)
                  sampling_mode = on  (then dotted sub-keys: temperature, top_k,
                                       top_p, min_p, repetition_penalty, seed,
                                       presence_penalty — NOT a nested dict)
    SaveText:     format = txt  → read the rewrite, feed it to TextEncodeQwenImage21

**It runs on CPU, not the GPU.** On Apple Silicon this ComfyUI build forces
text encoders to CPU: `text_encoder_device()`
(`comfy/model_management.py:1219`) returns `cpu` because MPS sets
`vram_state=SHARED`, missing the `(HIGH_VRAM, NORMAL_VRAM)` branch.
Measured **~2.05 s/token** for this 9B model → a 200-token rewrite takes
~7 minutes. Use it as an offline enhancer with `max_length` 200–400; the
template's own 16k max_length would take hours. `--gpu-only` forces MPS but
risks OOM at 9B on a shared GPU.

## Verification

- ComfyUI: converted run + `vision_analyze` on the output matches the prompt
  (proven: Z-Image blueprint → "green tractor… autumn" rendered correctly).
- Unsloth: `unsloth_gen.py` prints the saved `.png` path; confirm the file
  is non-trivial (>100KB for a real render) via `search_files`/`read_file`
  metadata, and verify content with `vision_analyze`.

## References

- `references/backends.md` — endpoints, auth layout, model inventory per
  machine, blueprint slot notes. Load with `skill_view(name='local-image-gen',
  file_path='references/backends.md')` whenever picking models or debugging.
