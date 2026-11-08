# Example Workflows

These are starter API-format workflows for the most common tasks. They're
ready to run with `scripts/run_workflow.py` once you've installed (or have
cloud access to) the listed models. Run `check_deps.py <file>` first — it
reports `is_ready: false` with a `fix_hint` per missing model rather than
failing at submit time.

Use `python` (3.14.7) rather than `python3` (3.9.6) on this machine.

| File | Purpose | Required models | Min VRAM |
|------|---------|-----------------|----------|
| `sd15_txt2img.json` | SD 1.5 text-to-image (512×512) | SD1.5 checkpoint, e.g. `v1-5-pruned-emaonly.safetensors` | 4 GB |
| `sdxl_txt2img.json` | SDXL text-to-image (1024×1024) | `sd_xl_base_1.0.safetensors` | 8 GB |
| `flux_dev_txt2img.json` | Flux Dev text-to-image (1024×1024) | `flux1-dev.safetensors`, `t5xxl_fp16.safetensors`, `clip_l.safetensors`, `ae.safetensors` | 24 GB (or use `flux1-dev-fp8`) |
| `sdxl_img2img.json` | SDXL image-to-image | SDXL checkpoint | 8 GB |
| `sdxl_inpaint.json` | SDXL inpainting (image + mask) | SDXL checkpoint | 8 GB |
| `upscale_4x.json` | Standalone 4× ESRGAN upscale | `4x-UltraSharp.pth` (or any upscaler) | 4 GB |
| `animatediff_video.json` | AnimateDiff text-to-video (16 frames) | SD1.5 checkpoint, `mm_sd_v15_v2.ckpt` motion module | 8 GB |
| `wan_video_t2v.json` | Wan 2.x text-to-video (~33 frames) | `wan2.2_t2v_1.3B_fp16.safetensors`, `umt5_xxl_fp16.safetensors`, `wan_2.1_vae.safetensors` | 24 GB |
| `qwen_img21_txt2img.json` | Qwen-Image-2.1 text-to-image via **GGUF** | `qwen-image-2.1-Q4_K_M.gguf` (**not present on this machine**) | 8 GB |
| `qwen_img21_txt2img_int8.json` | Qwen-Image-2.1 text-to-image via **safetensors int8_convrot** (the working path on this machine) | `qwen_image_2.1_int8_convrot.safetensors`, `qwen3vl_8b_int8_convrot.safetensors`, `qwen_image_2.1_vae_bf16.safetensors` | 8 GB |
| `zimage_*.json` (8 files) | Z-Image Turbo variants — see **Z-Image Turbo starters** below | `z_image_turbo_bf16.safetensors`, `qwen_3_4b.safetensors`, `ae.safetensors` | n/a (MPS unified) |

### Qwen-Image-2.1 — read before using

Requires **ComfyUI >= 0.37.0** (this machine runs 0.37.0 — OK). The nodes are
`TextEncodeQwenImage21` and `QwenImage21Cache`.

`qwen_img21_txt2img.json` is the **GGUF** path and needs
`qwen-image-2.1-Q4_K_M.gguf`, which is **not downloaded**. `check_deps.py`
correctly reports `is_ready: false` for it. The GGUF route additionally needs
the **leejet** fork of ComfyUI-GGUF for 2.1 support — the installed city96
version (commit `6ea2651`) has no `ModelQwenImage` class and will fail with
`Unknown model architecture!`.

**The working path on this machine is safetensors, not GGUF.** On disk now
(bf16-era weights were purged — see the model table in `SKILL.md`):

| model | folder |
|---|---|
| `qwen_image_2.1_int8_convrot.safetensors` | `diffusion_models/` |
| `qwen3vl_8b_int8_convrot.safetensors` | `text_encoders/` |
| `qwen_image_2.1_vae_bf16.safetensors` | `vae/` |

A bf16 set (`qwen_image_2.1_bf16.safetensors` + `qwen3vl_8b_bf16.safetensors`)
was verified working here in early October 2026 and has since been removed;
graphs naming those filenames will not load.

int8_convrot is the config the three official templates expect, and it runs
**~15% faster than bf16** on MPS (131s vs 154s for 1024x1024 @ 25 steps,
including weight load).

Working API-format graph: `workflows/qwen_img21_txt2img_int8.json` in this
skill, or the inline block in `SKILL.md` under Pitfalls 0c.

## Z-Image Turbo starters

Eight API-format conversions of the editor-format starters in the shared
workflows dir (`/Users/macstudio/ComfyUI-Shared/user/workflows/starters/`,
converted 2026-10-20; the editor originals stay there for the UI). All run on
the on-disk trio — `z_image_turbo_bf16` UNet, `qwen_3_4b` text encoder
(`type: lumina2`), `ae` VAE — at 8 steps, cfg 1.0, `res_multistep`/`simple`
(Turbo is distilled; the negative prompt is zeroed out via
`ConditioningZeroOut`). ~60–90 s per image on MPS.

| File | Variant |
|------|---------|
| `zimage_square_1024.json` | 1024×1024 |
| `zimage_portrait_768x1344.json` | 768×1344 portrait |
| `zimage_ultrawide_1792x768.json` | 1792×768 ultrawide |
| `zimage_batch_4up.json` | `batch_size=4` at 896×896 — four variants, one run |
| `zimage_hires_two_pass.json` | 1024² pass 1 → 1.5× latent upscale → pass 2 at denoise 0.5 |
| `zimage_img2img.json` | img2img, denoise 0.6 |
| `zimage_inpaint.json` | masked inpaint (`GrowMask` → `SetLatentNoiseMask`), denoise 0.9 |
| `zimage_outpaint.json` | outpaint (`ImagePadForOutpaint` → `VAEEncodeForInpaint`), denoise 1.0 |

img2img/inpaint/outpaint default their `LoadImage` to `example.png` (bundled
ComfyUI sample, present on both installs' input dirs — the editor starters
reference `starters_samples/` files that were never on this machine). Override
with `run_workflow.py --input-image image=<your file>`. Inpaint masks: paint in
the UI's MaskEditor and export API format, or supply a mask via
`--input-image mask_image=<file>`. Seed 0 in the templates is a placeholder —
pass `seed: -1` in `--args` (the script expands it) or a real seed.

## Text-rendering battery

`../scripts/run_text_battery.py` grades a model's typography: short words,
alphanumeric strings, long headlines, a full pangram, and a multi-element trap.
It JSON-injects `prompt` + `seed` straight into the workflow dict — NOT via
`--args`, because the `TextEncodeQwenImage21` `prompt` field is not in the
extracted schema (the extractor only follows sampler→CLIPTextEncode links).

```bash
python3 ../scripts/run_text_battery.py \
  --workflow qwen_img21_txt2img_int8.json \
  --prompts '@prompts.json' \
  --output-dir ./outputs/text-battery
```

The stock 12-prompt battery (short → alphanumeric → headline → pangram →
multi-element trap) produced Qwen-Image-2.1 scores of 11/12 clean with one
partial (dense phone-screen UI text garbles secondary text) on 2026-10-06/07.
Set per-run seeds with `--seed-base`/`--seed-step` (defaults 1003 / 11).

Grading rubric (failure modes, in order of severity): total gibberish, missing
letters, case collapse, extra characters, fabricated words, then contextual
adaptation — "renders 'not text' instead of text" counts as the pass condition.
Grade with the local vision model (`auxiliary.vision` → llama-swap
`ms-qwen3-vl-8b`), not the flaky cloud gemini route.

## Quick start

```bash
# Run a workflow with prompt injection
python3 ../scripts/run_workflow.py \
  --workflow sdxl_txt2img.json \
  --args '{"prompt": "majestic eagle in flight", "seed": 12345, "steps": 35}' \
  --output-dir ./out

# Img2img: upload an input image first via the script's helper
python3 ../scripts/run_workflow.py \
  --workflow sdxl_img2img.json \
  --input-image image=./photo.png \
  --args '{"prompt": "make it watercolor", "denoise": 0.6}' \
  --output-dir ./out

# Cloud (set API key once)
export COMFY_CLOUD_API_KEY="comfyui-..."
python3 ../scripts/run_workflow.py \
  --workflow flux_dev_txt2img.json \
  --args '{"prompt": "a fox in a misty forest"}' \
  --host https://cloud.comfy.org \
  --output-dir ./out

# What can I tweak in this workflow?
python3 ../scripts/extract_schema.py sdxl_txt2img.json --summary-only

# Are all required models / nodes installed?
python3 ../scripts/check_deps.py wan_video_t2v.json
```

## Notes

- **Inpaint masks**: white pixels = "regenerate this region", black = preserve.
  ComfyUI's `LoadImageMask` reads the **red channel** by default; export your
  mask as a single-channel image or as a normal RGB where red==intensity.

- **Denoise strength** in img2img: `0.0` = output identical to input,
  `1.0` = ignore input entirely. Sweet spot is usually 0.4–0.7.

- **Flux Dev** needs ~24 GB VRAM in its base form. The `flux1-dev-fp8.safetensors`
  variant (already on Comfy Cloud) cuts that roughly in half.

- **Video workflows** can take many minutes. The skill auto-detects video
  output nodes and bumps the default timeout to 900s. Override with `--timeout 1800`.

- These JSON files are deliberately **API format** (top-level keys are node IDs
  with `class_type`), not editor format. To open them in ComfyUI's web UI for
  visual editing, use `Workflow → Load (API Format)` or `Workflow → Open` and
  follow the prompt.

## Cloud vs local model names

Comfy Cloud's preinstalled checkpoints sometimes have a `-fp16` suffix
(`v1-5-pruned-emaonly-fp16.safetensors`) while the canonical local download
keeps the original name (`v1-5-pruned-emaonly.safetensors`). The example
workflows use the local-canonical names. When running on cloud, override with:

```bash
python3 ../scripts/run_workflow.py \
  --workflow sd15_txt2img.json \
  --args '{"ckpt_name": "v1-5-pruned-emaonly-fp16.safetensors", "prompt": "..."}' \
  --host https://cloud.comfy.org
```

The `ckpt_name`, `vae_name`, `lora_name`, `unet_name`, etc. are all exposed
as controllable parameters by `extract_schema.py` — discover what's installed
with `comfy model list` (local) or `curl /api/experiment/models/checkpoints`
(cloud).
