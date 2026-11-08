# Backends & Fleet Inventory (verified 2026-10-14)

## Mac Studio — ComfyUI

- Server: `http://127.0.0.1:8188`, no auth. `tailscale serve` also proxies
  tailnet-only `https://studio.taile85139.ts.net:8188`.
- Weights: `/Users/macstudio/models/diffusion` wired in via
  `/Users/macstudio/ComfyUI/extra_model_paths.yaml` (additive scan; local
  `models/` dirs are empty stubs). Old flux1-dev-fp8 / sd1.5 checkpoints
  were purged — do not offer them.
- Installed, selectable (from `scripts/probe_models.py` against live
  `/object_info` — re-probe; stock churns):
  - `UNETLoader.unet_name`: `z_image_turbo_bf16.safetensors`,
    `qwen_image_2.1_int8_convrot.safetensors`
  - `CLIPLoader.clip_name`: `qwen_3_4b.safetensors` (Z-Image pairing,
    type `lumina2`), `qwen3vl_8b_int8_convrot.safetensors` (Qwen-Image
    pairing)
  - `VAELoader.vae_name`: `ae.safetensors` (Z-Image),
      `qwen_image_2.1_vae_bf16.safetensors`, `pixel_space`
    - `LoraLoader.lora_name`: `pixel_art_style_z_image_turbo.safetensors`
      (tarn59, trigger `Pixel art style.`, added 2026-10-18) — the only LoRA
      installed; load it on the Z-Image-Turbo UNet for pixel-art output.
    - - No checkpoints installed.
- So exactly two runnable t2i families:
  - **Z-Image-Turbo**: blueprint `Text to Image (Z-Image-Turbo).json` —
    KSampler cfg=1, sampler `res_multistep`, scheduler `simple`, 4–8 steps.
    ~30s for 512²/6 steps incl. model swap (96GB RAM, bf16 ~20.5GB resident).
    Related blueprints (ControlNet/Canny/Depth/Pose/Upscale) exist but only
    run once their extra weights are installed.
  - **Qwen-Image-2.1-int8**: pre-converted API graph
    `~/.hermes/skills/creative/comfyui/workflows/qwen_img21_txt2img_int8.json`
    — runs directly under run_workflow.py; 20–25 steps, slower.

## Editor→API conversion (blueprints are editor format)

`scripts/comfy_editor_to_api.py` handles: array **and** dict link encodings,
`definitions.subgraphs` wrappers (blueprint format), Reroute chains,
Primitive nodes, Note drops, auto-append of `SaveImage` when the blueprint
exposes IMAGE with no save node (blueprints do — the socket is output-only).
Exposed slots (`-10` pseudo-links) are recorded and:
- baked once via `--set SLOT=VALUE`, or
- kept injectable via `--schema-out s.json` + comfyui run_workflow.py
  `--schema s.json --args '{...}'` (its auto-schema can't see empty combo
  slots — `text`, `unet_name` etc. are "unknown parameter" without this).
Feed run_workflow.py the `--raw` bare graph; the default wrapped output
`{"prompt": ...}` gets double-wrapped → 400 `prompt_no_outputs`.
Direct POST path instead: `curl :8188/prompt` with wrapped body, poll
`/history/<prompt_id>` until `status.completed`, fetch via `/view?filename=&type=output`.

## MacBook Pro M5 64GB — Unsloth Studio

- Server: `http://127.0.0.1:8888` **loopback only** (no tailnet route) →
  reach over `ssh macbook`. App is a menubar/GUI app; if :8888 refuses, ask
  Patrick to open it.
- Auth: bearer key from `/Users/prasta/.unsloth/studio/auth/agent_api_key.json`
  → `servers["http://127.0.0.1:8888"].minted[-1]` (keys rotate; `saved` may
  be empty). Over ssh, headers must go through `curl -K-` stdin config —
  `-H` args do not survive the ssh argv boundary (observed 401/"Not
  authenticated" even with a valid key).
- Endpoints (all verified live):
  - `POST /v1/images/generations` — `{model, prompt, size "WxH", n, steps,
    seed, negative_prompt}`; returns `data[i].url` (signed, loopback-bound,
    needs the bearer key) — not b64.
  - `GET /api/inference/models` → `{object, data[]}` (id/quant/loaded)
  - `GET /api/inference/images/info` → supported families + bf16 resident GB
  - `GET /api/inference/images/status` / `POST .../load` (`{"model_path":
    "<repo id>"}`) / `GET .../load-progress` (`phase/fraction/error`)
  - `/v1/images/generations` **503s** until a diffusion model is loaded;
    `unsloth_gen.py` auto-loads and polls.
- Installed image models (verified 2026-10-25): `abenzerps/Qwen-Image-2.1-Uncensored-Quantized` (Q4_K_M, uncensored — the spicy path; needs `--gguf-filename qwen-image-2.1-UC-Q4_K_M.gguf`, bare `--model` load is rejected), `unsloth/Qwen-Image-2.1-GGUF` (Q4_K_M), `unsloth/Z-Image-Turbo`, `unsloth/Z-Image-Turbo-GGUF`. The old `unsloth/Qwen-Image-Edit-2511-GGUF` edit model is GONE from the inventory — do not offer it. `--list` shows repo entries whose weights may be LFS pointers only; trust `images/status`, not the list.
- **Z-Image bf16 may fail the load guard on the MacBook** (`unsloth/Z-Image-Turbo` flat repo wants ~21GB, ~20GB usable) — use the GGUF variant `unsloth/Z-Image-Turbo-GGUF` with `--gguf-filename z-image-turbo-Q4_K_M.gguf` (4.7GB, fits). Z-Image accepts `--init-image` on the /v1 endpoint same as Qwen, needs only 8 steps (turbo) vs 25 for Qwen.
- **zsh array trap in background loops** (observed 2026-10-25): the Studio shell runs `/bin/zsh -lic`, and zsh arrays are 1-INDEXED — `promptA=(a b c)` makes `promptA[0]` empty and `promptA[1]` = a, silently shifting every loop iteration by one pose/seed and skipping the last item. In multi-render shell loops, either use explicit per-call invocations, `bash -c '...'` with bash 0-indexing, or verify output dir names against the intent after the loop (`ls` cross-check, not the echo labels).
  `images/info` supported families (bf16 resident GB): flux.1/kontext 33.8, flux.2-klein 16.0,
  qwen-image 57.8, qwen-image-2.1 33.1, z-image 20.5, lumina-2 10.6,
  krea-2 35.7, hunyuanimage-2.1 49.6, ideogram-4 53.7, hidream-i1 63.2,
  flux.2-dev 112.9 (**won't fit 64GB MacBook in bf16** — GGUF quants only).
- **Qwen-Image-2.1 composites under complex prompts** (observed 2026-10-25): with an init-image + a prompt carrying many conditions (outfit + crotchless + setting + pose + persona), Qwen-Image-2.1 sometimes returns a MULTI-PANEL COLLAGE (3-4 panels of the same woman in variations) instead of one frame, and frequently drops crotchless/outfit specifics. Z-Image-Turbo held the same prompts better on crotchless adherence (4/6 vs 1/6) but Z produced a 4-panel composite too (C3 stream) and the pointer cleared frames Patrick later killed (extra leg on C1, "nightmare" anatomy on C6) — the eye remains the only detector. For complex multi-condition lingerie/pose prompts, prefer Z-Image or simplify; keep single-condition concepts for the uncensored Qwen when its realism is wanted.
- **Unsloth app OOMs after a long render streak** (observed 2026-10-25): after ~5 Qwen renders at 1024x1024/25 steps the generation endpoint refuses with "device ran out of memory" even with 36% RAM free — restart the app (`ssh macbook 'killall unsloth-studio; sleep 2; open -a Unsloth'`, re-poll :8888) to clear the heap; the model reloads on the next call.

## Mac Studio — Unsloth Studio

- `/Applications/Unsloth.app` installed; **not running by default** →
  `open -a Unsloth` (ask Patrick — GUI app). When up: same :8888, same
  endpoint set, keyfile `/Users/macstudio/.unsloth/studio/auth/agent_api_key.json`.
  Tailnet proxy exists: `https://studio.taile85139.ts.net:8888`.
- Diffusion models on this machine: none confirmed while app was down —
  `--machine studio --list` is the only source of truth; if empty, downloads
  happen in the app's Models tab (96GB Studio fits bigger families).

## Choosing (default guidance)

- Fast draft / stylized speed: Z-Image-Turbo on Studio ComfyUI.
- Text rendering / fidelity: Qwen-Image family (int8 on Studio ComfyUI, or
  GGUF Q8 on MacBook Unsloth).
- Img2img/edit: Qwen image edit blueprints on Studio once weights present;
  `--init-image` on Unsloth.
- Anything needing cloud APIs (gemini-image, fal, together) is OUT OF
  SCOPE for this skill — say so rather than substituting `image_generate`.
