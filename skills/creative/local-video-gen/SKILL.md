---
name: local-video-gen
description: Generate videos locally on the Studio ComfyUI engine.
version: 0.1.0
author: Patrick Ruster, Hermes Agent
license: MIT
platforms: [macos]
metadata:
  hermes:
    tags:
      - Video-Generation
      - ComfyUI
      - Wan
      - Local-Models
      - MLOps
    category: creative
    related_skills: [local-image-gen, comfyui]
---

# Local Video Generation — Mac Studio

Interactive skill for generating videos with **local models only** on the Mac
Studio ComfyUI engine. It does NOT use any cloud video API, and it never lists
a model/backend that isn't installed and runnable. Engines are probed live
before options are shown.

## When to Use

- "generate a video", "make a video of …", "text-to-video"
- "use the Mac Studio for video gen", "on ComfyUI / Wan"
- running a Wan 2.2 t2v workflow against the local server
- Patrick asks which local engine/model is best for a given video prompt

## Prerequisites

- Mac Studio: ComfyUI serving `http://127.0.0.1:8188` (no auth). Wan 2.2
  weights in `/Users/macstudio/models/diffusion` via `extra_model_paths.yaml`:
  - `diffusion_models/wan2.2_t2v_high_noise_14B_Q5_K_M.gguf`
  - `diffusion_models/wan2.2_t2v_low_noise_14B_Q5_K_M.gguf`
  - `text_encoders/umt5-xxl-encoder-Q8_0.gguf` (type `wan`)
  - `vae/wan_2.1_vae.safetensors` — the 16-channel VAE that actually decodes
    Wan 2.2 t2v latents. `vae/wan2.2_vae.safetensors` is also on disk but is
    the 48-channel VAE and fails at VAEDecode (see Pitfalls).
  - `loras/wan2.2_t2v_lightx2v_4steps_lora_v1.1_high_noise.safetensors` and
    `loras/wan2.2_t2v_lightx2v_4steps_lora_v1.1_low_noise.safetensors` —
    installed 2026-10-26; `wan22_t2v_gguf.json` is a 4-step graph by default.
  - Wan 2.2 **image-to-video** pair (installed 2026-10-28):
    `diffusion_models/wan2.2_i2v_{high,low}_noise_14B_Q5_K_M.gguf` (10.79 GB each)
    plus `loras/wan2.2_i2v_lightx2v_4steps_lora_v1_{high,low}_noise.safetensors`.
    Reuses the umt5 encoder and `wan_2.1_vae.safetensors`. Graph:
    `wan22_i2v_gguf.json` (WanImageToVideo drives the latent from a start frame;
    the start image must be in `ComfyUI/input/`).
  - LTX-2.5 (installed 2026-10-28, and **wired and run 2026-10-28/29**: outputs
    in `~/.hermes/outputs/video-gen/runs/2026-10-29-ltx-20s/` include a 20 s clip
    plus 2 s validation renders, with graphs `ltx25_i2v.json` and
    `ltx25_i2v_api.json`. Runnable is not the same as validated: those outputs
    have not been re-reviewed, so verify before relying on them):
    `diffusion_models/ltx-2.5-22b-distilled-transformer-comfy-int8-convrot.safetensors`
    (21.5 GB), `text_encoders/gemma4-12b-with-proj-ltx-2.5-comfy-int8-convrot.safetensors`
    (15.4 GB), `vae/ltx-2.5-{video,audio}-vae-bf16.safetensors`,
    `latent_upscale_models/ltx-2.5-latent-spatial-upscaler-x2-bf16-1.0.safetensors`.
    Native templates ship as `video_ltx2_5_{t2v,i2v,flf2v}.json`. This is the
    audio-and-length upgrade (one-pass synced audio, up to 20s, 4K) and the
    US-licensed alternative to MiniMax H3, whose license excludes the US.
- The `comfyui` skill's `scripts/run_workflow.py` exists (it executes the
  graph). No HF tokens, no API keys.
- **Video is Studio-only.** The MacBook Unsloth stack does not do video — do
  not offer it. ComfyUI is the only local video backend in this fleet.

## The Interactive Flow (mandatory)

Ask these questions with `clarify` **before generating** — Patrick's choices,
not guesses. Skip any question only if this session already answered it or the
probe below leaves exactly one live option (then state the pick, don't ask).

1. **Backend** — probe first: `terminal`: `curl -m 2 :8188/system_stats`.
   If ComfyUI is down, say so and stop (no alternative backend exists).
2. **Model** — Wan 2.2 t2v is the only installed video family. Confirm the
   GGUF files are selectable via `scripts/probe_models.py` or `/object_info`
   (stock churns — re-probe, never trust memory).
3. **Prompt + knobs** — if the prompt isn't already in the request, ask it
   open-ended alongside defaults: resolution (832x480 default, 640x640
   square, 1280x720 max on 96GB),   length (33 frames ≈ 2s @ 16fps; 81 ≈ 5s),
   steps (the 4-step lightx2v LoRA config is the workflow default and much
   faster; 30-step is only the no-LoRA fallback), seed (fixed unless he
   wants variation).

Then run the procedure below and deliver the file with `MEDIA:/absolute/path.mp4`.

## How to Run

- **ComfyUI · Mac Studio** — run the pre-built Wan 2.2 GGUF graph:
  `terminal`: `python3 ~/.hermes/skills/creative/comfyui/scripts/run_workflow.py
  --workflow ~/.hermes/skills/creative/comfyui/workflows/wan22_t2v_gguf.json
  --host http://127.0.0.1:8188 --args '{"prompt":"…","seed":N,…}'
  --output-dir <dir>`.
  **Arg keys are the SCHEMA names, not the node field names:** `prompt`
    (not `text`), `seed` (not `noise_seed`), plus `width`/`height`/`length`/
    `steps`. Wrong keys are silently dropped with a warning — the run then
    uses the workflow's default prompt. Verify the submitted prompt in
    `/history` before trusting a long render.
    **`seed`/`steps` are NOT injectable as plain keys** — there are two
    `KSamplerAdvanced` nodes, so the schema names them `seed_10`/`seed_11`
    and `steps_10`/`steps_11` (duplicate-name suffixing). Passing `seed` or
    `steps` drops with a warning and the workflow defaults (seed 42, steps
    30) apply. That's fine for the standard config; only inject them if you
    need per-stage control.

## Quick Reference

| Need | Command |
|---|---|
| Studio live model slots | `python3 scripts/probe_models.py --host http://127.0.0.1:8188` |
| Run Wan 2.2 t2v | comfyui skill `run_workflow.py --workflow wan22_t2v_gguf.json --host :8188 --args '{"prompt":"...","seed":N,...}'` |
| Engines alive? | `curl -m 2 http://127.0.0.1:8188/system_stats` |
| Interrupt a run | `curl -X POST http://127.0.0.1:8188/interrupt` |
| Check uncommitted changes | `git status` |
| Revert uncommitted changes | `git checkout -- scripts/run_workflow.py` |
| Verify submitted prompt | `curl -s http://127.0.0.1:8188/history/<prompt_id>` |
| Check output path | `python3 -c "import os; print(os.path.expanduser('~/.hermes/outputs/'))"` |

## Procedure

1. Probe the engine (`terminal`), confirm ComfyUI is up and the Wan GGUF
   files are selectable.
2. Ask the flow questions via `clarify` (one call, up to 3 questions).
3. Run `run_workflow.py` against `wan22_t2v_gguf.json`. Inject via `--args`
   with exact values: model names **verbatim** from the choices arrays;
   integers for width/height/length/steps/seed; `prompt` for the text (the
   schema key is `prompt`, NOT `text` — a wrong key is silently dropped and
   the run uses the workflow default). **Verify the submitted prompt in
   `http://127.0.0.1:8188/history/<prompt_id>` before trusting a long render.**
4. **Timeout:** a 14B video render is slow — pass `--timeout 1500` (25 min)
   or the download may be cut off mid-render (the s9b timeout-casualty
   lesson from image work applies here too).
5. Verify the output with `video_analyze` against the prompt (catches
   slot-mapping and stale-name bugs), then deliver `MEDIA:<path>`.
6. **Always check `git status` before running a long job.** If uncommitted
   changes exist, revert them with `git checkout -- <file>` or run `git diff`
   to see what's changed. The `run_workflow.py` script is fragile and can
   break with uncommitted edits.
7. **Use the actual `~/.hermes/outputs/` dir for the output path.** The
   `gallery_month_dir` function uses the wrong path (`/Users/macstudio/.hermes/outputs/` vs `~/.hermes/outputs/`). Fix it to use the home-relative path.

## FILE CONVENTIONS

- Durable output -> `~/.hermes/outputs/video-gen/` (NEVER the scratch dir —
  pruned 24h). Batch renders go in `runs/<YYYY-MM-DD>-<concept>/`; single
  ad-hoc renders may drop a date-stamped file at the root. Report the
  absolute path back to Patrick via `MEDIA:`.

## Pitfalls

- **Submit new graphs through the `/prompt` API, not `run_workflow.py`.** For
  any graph you just built, `POST /prompt` with the graph dict is deterministic
  and returns `node_errors` on validation failure; `run_workflow.py`'s schema
  extraction silently drops unknown `--args` keys (see the injection pitfalls
  below). Always read back `/history/<prompt_id>` and print the submitted
  `CLIPTextEncode.text` to confirm the prompt that actually ran.
- **Measured Wan 2.2 i2v, 640x640 x 33 frames, 4-step LoRA path: 285 s wall**
  on the Studio (dominated by loading two 10.8 GB GGUF UNets, not by sampling).
  Budget ~5 min for the first render at this size; 81 frames costs roughly 2.5x.
- **Look at the source still before spending GPU on an i2v run.** The start
  frame IS the composition, so a random pick from `~/Pictures/ComfyUI/`
  produces a render about a subject nobody asked for. Choosing by filename is
  not choosing. Confirm the subject visually (and that it is not adult content
  from the spicy-image pipeline) first.
- **`video_analyze` descriptions of surreal or abstract footage are unreliable**
  and will confidently misname objects. It called a lime-green glass lens
  element a "droplet" and CNC-milled grooves a "leaf-shaped indentation". Use
  it to confirm the render is non-broken, not to establish what is on screen.

- **`check_deps.py` false-negatives on GGUF loaders.** It maps
  `UnetLoaderGGUF` to the `unet/` folder and `CLIPLoaderGGUF` to `clip/`,
  but the GGUF loaders actually read from `diffusion_models/` and
  `text_encoders/`. The models ARE installed — trust `/object_info` combo
  options, not `check_deps.py`.
- **Two-stage t2v is mandatory.** Wan 2.2 t2v needs BOTH the high_noise and
  low_noise UNets chained through two `KSamplerAdvanced` nodes (stage 1
  high-noise 0..15, stage 2 low-noise 15..30, `return_with_leftover_noise`
  enable then disable). A single-UNet graph will not produce correct video.
- **The 4-step LoRA IS installed (2026-10-26).** Both
  `wan2.2_t2v_lightx2v_4steps_lora_v1.1_{high,low}_noise.safetensors` are on
  disk and appear in `LoraLoaderModelOnly`'s combo list. `wan22_t2v_gguf.json`
  is now a 4-step graph: one `LoraLoaderModelOnly` per UNet (strength 1.0),
  stage 1 `steps: 4` 0..2, stage 2 `steps: 4` 2..4. Keep LoRA nodes and
  `steps: 4` together — don't strip the LoRAs and leave steps at 4, and don't
  run the 30-step 0..15/15..30 split on top of the LoRAs. Re-probe
  `/object_info/LoraLoaderModelOnly` rather than trusting this list.
- **`cfg` depends on the path, it is not a constant.** The 4-step lightx2v
  LoRA config runs `cfg` 1.0 (flow-matching, like Qwen-Image). The stock
  *non-turbo* path in the official template runs **`cfg` 3.5** with 20 steps
  split at 10 and no LoRA. Both are correct for their own config; do not carry
  1.0 into a 20-step run or 3.5 into a 4-step run.
- **How to read the official template's real parameters:** the Wan 2.2 i2v
  template is a subgraph driven by `ComfySwitchNode`s off one
  `PrimitiveBoolean` ("Enable 4steps LoRA?"). Resolve them from
  `definitions.subgraphs[0]` — links are dicts with `origin_id`/`target_id`,
  not lists — and follow each switch's `on_true`/`on_false`. For
  `video_wan2_2_14B_i2v.json`: turbo=false gives Steps 20, CFG 3.5, Split 10,
  and the raw UNET with no LoRA; turbo=true gives Steps 4, CFG 1.0, Split 2
  with the LoRAs. The widget values on the KSamplerAdvanced nodes are
  overridden by those links and are misleading on their own.
- **The 4-step LoRA path buys speed. Whether it buys restraint depends on the
  source, so steps are NOT a restraint knob.** Measured with the source, prompt
  and seed held constant: 640x640 x 33 ran 4-step 241 s against 20-step 1846 s
  (7.7x); 480x832 x 33 ran 255 s against 1696 s (6.6x). But the direction of
  the motion difference inverts with the subject:
  - Product still, seed 42: 4-step moved **2.25x MORE** (3.80 vs 1.69 mean abs
    diff), centre-local, and the 20-step arm decelerated smoothly (1.84 -> 1.53).
  - Barn figure still, seed 902117, prompt recovered byte-identical from the
    other arm's history entry: 20-step moved **58% MORE** (6.82 vs 4.32),
    drifted 10.1% of range against 6.8%, and ACCELERATED across the clip
    (5.63 -> 8.01).
  One variable, two sources, opposite directions. Two data points, so hold any
  rule provisionally and measure per shot. What survives every measurement:
  4-step is ~7x cheaper and has never been shown to cost anything, so it is the
  iterate default. Neither config is locked to the start frame (drift ran 2.9%
  to 10.1% of range by the last frame). Peak/mean stayed 1.6-1.8 in every arm, so
  "spiky vs smooth" did not separate the configs either.
- **Camera instructions are not being honoured at this config.** Prompts
  asking for a push-in produced essentially no edge change in either arm
  (0.64 and 0.45) against centre change of 10.3 and 3.6. Before blaming a
  prompt, measure centre-vs-edge change: a real camera move raises edge
  change, subject motion does not. A 2 s / 33-frame clip may simply be too
  short to express a camera move; test at 81 frames.
- **Do not trust a description of your own render.** `video_analyze`
  confidently misnamed objects in surreal footage, and there is no substitute
  for the user watching it. Measure composition and motion numerically and
  hand over the file.
- **The VAE must be `wan_2.1_vae.safetensors`, NOT `wan2.2_vae.safetensors`.** The
  `wan2.2_vae.safetensors` file is a 48-channel-latent VAE and fails at
  VAEDecode with `expected input[1, 16, ...] to have 48 channels, but got 16`
  — the Wan 2.2 t2v model produces 16-channel latents. The official blueprint
  pairs Wan 2.2 with the 16-channel `wan_2.1_vae.safetensors` (242 MB, from
  `Comfy-Org/Wan_2.2_ComfyUI_Repackaged/split_files/vae/`). Verify a VAE's
  latent channels by reading its safetensors header (`conv2.bias` = latent
  dim) before trusting it.
- **`EmptyHunyuanLatentVideo` is the right latent node** for Wan t2v (the
  old `wan_video_t2v.json` in this skill's workflows/ is Wan 2.1 and won't
  run against the 2.2 GGUF files — use `wan22_t2v_gguf.json`).
- **`SaveVideo` format is a nested dict**, not a plain string: `{"format":
  "mp4", "codec": {"codec": "h264", "encoding": {"mode": "auto"}}}`.
- **Model IDs/filenames must match server output exactly** — stale names
  400/404.
- **Video is Studio-only** — never offer the MacBook for video.
- **`--args` injection is fragile.** The `run_workflow.py` script's schema
  extractor only finds a parameter if it matches `CLIPTextEncode.text` exactly.
  The script injects `text` through the schema, but the schema must have
  `"text"` as a key — not `"prompt"` or `"clip_text"`. Use the actual
  schema key from the workflow (e.g. `prompt`, `seed`) — not the node field.
  The `prompt` field in the `CLIPTextEncode` node is the real key; `text` is
  a different field and is not used for `--args` injection. If `--args` fails,
  check the workflow's `CLIPTextEncode` node and use its field name as the
  key in `--args`.
- **A broken edit in `run_workflow.py` can break all video runs.** The script's
  `if args.no_download` block was buggy (unbound `slug`, `seed`, `run_dir`)
  and the uncommitted change was lost in the 03:30 backup. Always check `git
  status` before running a long job; if uncommitted changes exist, revert
  them with `git checkout -- <file>` or run `git diff` to see what's
  changed.
- **The `run_workflow.py` script's output directory logic is unreliable.** The
  script checks for a direct output in `/Users/macstudio/ComfyUI/output/` but
  the output dir is `~/ComfyUI/output/` (home-relative, not absolute).
  The script will never find a file in the actual output dir, so it always
  falls back to the API download. The direct output check is broken.
- **`--args` injection fails silently.** If the `--args` keys don't match the
  schema, the script silently drops them and uses the workflow's default
  prompt. The run then executes with a different prompt than requested —
  the `prompt` field in the `CLIPTextEncode` node is not `text`. Verify
  the submitted prompt in `http://127.0.0.1:8188/history/<prompt_id>` to
  catch this.
- **The `run_workflow.py` script's `find_seed_in_workflow` logic is flawed.** It
  uses `workflow.get("extra_data", {}).get("seed", -1)` but the seed is set
  in the `KSamplerAdvanced` node's `noise_seed` field. The script should
  extract the real seed from the node, not the workflow extra_data.
- **The `run_workflow.py` script's `gallery_month_dir` function is broken.** It
  uses `Path(GALLERY_ROOT)` but `GALLERY_ROOT` is defined as `"/Users/macstudio/.hermes/outputs/` in the script, not in the `~/.hermes` dir. The script uses the wrong path. Fix it to use the actual `~/.hermes/outputs/` dir.

## Verification

- ComfyUI: converted run + `video_analyze` on the output matches the prompt.
- **Proven end-to-end (2026-10-26):** two 832x480x33-frame renders completed
  to valid H.264 MP4s (16 fps, 2.06 s) in
  `~/.hermes/outputs/video-gen/runs/2026-10-25-cora-ball/`.
- **Render time is unmeasured — don't quote one.** No retained ComfyUI log
  covers the video runs (the gallery manifest carries no duration,
  `run_workflow.py` writes none, and the 8188 log lost the 2026-10-26
  window). Time an actual render before asserting a number; image-side
  evidence on this box is 4.7-7.8 s/step, plus the UNet pair + encoder load.

## References

- `~/.hermes/skills/creative/comfyui/workflows/wan22_t2v_gguf.json` — the
  pre-built Wan 2.2 t2v GGUF graph (two-stage 4-step with lightx2v LoRAs, MP4 out).
- `~/.hermes/skills/creative/comfyui/workflows/wan22_i2v_gguf.json` — the
  Wan 2.2 i2v GGUF graph (same two-stage 4-step config, `LoadImage` →
  `WanImageToVideo` → decode → MP4).
- `~/.hermes/skills/creative/comfyui/workflows/wan22_i2v_gguf_20step.json` —
  the non-turbo reference graph (20 steps, CFG 3.5, split 10, no LoRA). Its
  positive node ships as the literal string `PLACEHOLDER_POSITIVE`, so a run
  that fails to set node 7 renders a placeholder prompt for half an hour and
  still reports success. Set it.
  - **A clean A/B needs the SAME start image, prompt and seed, VERIFIED not
    assumed.** `runs/2026-10-28-i2v-ab/` does not hold a pair:
    `ab-A-4step-cora-portrait.mp4` is the dog and
    `ab-B-20step-product-still.mp4` is the product still (frame-0 mean abs diff
    92.1, against 0.95 between ab-B and the real 4-step partner). The true
    4-step product arm is `runs/2026-10-28-i2v-test/wan22-i2v-product-still.mp4`.
    The numbers quoted in this skill came from that real pair; only the folder
    attribution was wrong.
  - Confirm pairing before measuring anything: frame-0 mean abs diff under ~5
    is the same shot, 90+ is a different subject.
  - Hold the prompt constant by copying it out of the other arm's history entry
    (`/history/<prompt_id>` -> `entry["prompt"][2]["7"]["inputs"]["text"]`)
    rather than retyping it. Retyping silently changes a variable.
- `~/.hermes/skills/creative/comfyui/scripts/run_graph.py` — submit an
  API-format graph and fetch the media. Fails loudly on an unknown `--set`
  path instead of silently rendering a default prompt; echo the submitted
  `CLIPTextEncode.text` back. Prefer it over `run_workflow.py` for new graphs.
- `~/.hermes/outputs/video-gen/i2v_compare.py` — the measurement tool. Reports
  per-frame motion, peak/mean, centre-vs-edge split, and drift against the start
  frame; writes JSON with `--json`. The centre-over-edge ratio is the
  camera-vs-subject discriminator: ~8 is subject-local, ~1 means the whole frame
  is changing. **It lives here and not in `~/.hermes/cache/scratch/` because the
  first version was pruned inside 24 h**, which turned a measured method back
  into an opinion. Do not move it into scratch.
  - ffmpeg 9 **removed `-vsync`**; it fails with exit 8 ("Unrecognized option").
    Use `-fps_mode passthrough`.
- `~/.hermes/skills/creative/comfyui/SKILL.md` — the engine skill (gallery,
  scripts, pitfalls). Load it for any ComfyUI mechanics.
