#!/usr/bin/env python3
"""
comfy-assets — turn ComfyUI image generation into web-ready site assets.

ComfyUI produces beautiful 1024x1024 / 2K PNGs. A website needs the right
aspect ratio, the right format, a sane file size, and consistent art direction
across a set. This bridges that gap.

Usage:
    # one-shot, with a named preset
    comfy-assets.py --prompt "..." --preset hero --out ./public/img

    # a whole set sharing one style (same seed => same visual world)
    comfy-assets.py --set-set ./assets.json --out ./public/img

    # list presets
    comfy-assets.py --presets

Presets cover the ratios that actually show up in front-end work. Each one
specifies a generation resolution and an output width, because a 4K render
downscaled to 1600px looks better than a 1600px render upscaled.

Generation is slow on Apple Silicon (130-250s at 25 steps on an M3 Ultra).
Use --steps to trade quality for turnaround; 25 is the tested default.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

# ---------------------------------------------------------------------------
# Presets: aspect ratio -> (gen_w, gen_h, out_w, out_h)
#
# Gen dims are multiples of 32 (ComfyUI/latent requirement) chosen to be the
# smallest sensible canvas at or above the output size, so we never upscale.
# ---------------------------------------------------------------------------
PRESETS: dict[str, dict] = {
    # Wide hero / og:image / page header
    "hero":        {"ratio": "16:9",  "gen": [1344, 768],  "out": [1600, 900],
                    "use": "page hero, og:image, wide banner"},
    "og":          {"ratio": "1.91:1", "gen": [1408, 736],  "out": [1200, 630],
                    "use": "Open Graph / Twitter card (the 1.91:1 safe area)"},
    # Card in a grid
    "card":        {"ratio": "4:3",   "gen": [1152, 864],  "out": [800, 600],
                    "use": "grid card, blog thumbnail, feature tile"},
    "card-wide":   {"ratio": "3:2",   "gen": [1152, 768],  "out": [900, 600],
                    "use": "wider card, split-layout media"},
    # Portrait / people
    "portrait":    {"ratio": "4:5",   "gen": [896, 1120],  "out": [800, 1000],
                    "use": "portrait, person shot, tall tile"},
    "portrait-lg": {"ratio": "2:3",   "gen": [832, 1248],  "out": [1000, 1500],
                    "use": "full-bleed portrait, editorial"},
    # Square
    "square":      {"ratio": "1:1",   "gen": [1024, 1024], "out": [1024, 1024],
                    "use": "avatar, logo-ish mark, square card"},
    # Mobile-first vertical
    "mobile":      {"ratio": "9:16",  "gen": [768, 1344],  "out": [750, 1334],
                    "use": "phone hero, Story/Reel, vertical ad"},
    # Ultra-wide
    "panorama":    {"ratio": "21:9",  "gen": [1568, 672],  "out": [1920, 823],
                    "use": "ultra-wide band, cinematic header"},
}

DEFAULT_PRESET = "hero"

# ComfyUI always speaks in multiples of 32.
assert all(w % 32 == 0 and h % 32 == 0 for p in PRESETS.values()
           for w, h in [p["gen"]]), "generation dims must be multiples of 32"

# Node graph, API format. Mirrors the verified int8_convrot Qwen-Image-2.1 path.
WORKFLOW = {
    "451": {"class_type": "UNETLoader",
            "inputs": {"unet_name": "qwen_image_2.1_int8_convrot.safetensors",
                       "weight_dtype": "default"}},
    "480": {"class_type": "QwenImage21Cache",
            "inputs": {"model": ["451", 0], "device": "auto", "dtype": "default"}},
    "453": {"class_type": "CLIPLoader",
            "inputs": {"clip_name": "qwen3vl_8b_int8_convrot.safetensors",
                       "type": "qwen_image", "device": "default"}},
    "454": {"class_type": "VAELoader",
            "inputs": {"vae_name": "qwen_image_2.1_vae_bf16.safetensors"}},
    "474": {"class_type": "TextEncodeQwenImage21",
            "inputs": {"clip": ["453", 0],
                       "prompt": "",
                       "negative_prompt": "text, watermark, signature, jpeg artifacts, "
                                          "blurry, low quality, distorted",
                       "resolution": 1024,
                       "images": {}}},
    "456": {"class_type": "EmptyLatentImage",
            "inputs": {"width": 1024, "height": 1024, "batch_size": 1}},
    "458": {"class_type": "KSampler",
            "inputs": {"model": ["480", 0],
                       "positive": ["474", 0],
                       "negative": ["474", 1],
                       "latent_image": ["456", 0],
                       "seed": 0, "steps": 25, "cfg": 1.0,
                       "sampler_name": "euler", "scheduler": "simple", "denoise": 1.0}},
    "457": {"class_type": "VAEDecode",
            "inputs": {"samples": ["458", 0], "vae": ["454", 0]}},
    "459": {"class_type": "SaveImage",
            "inputs": {"filename_prefix": "comfy_asset", "images": ["457", 0]}},
}

DEFAULT_NEGATIVE = ("text, watermark, signature, logo, jpeg artifacts, blurry, "
                    "low quality, distorted, extra limbs, bad anatomy, oversaturated")


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------
def _post_json(url: str, payload: dict, timeout: int = 90) -> dict:
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode(), method="POST",
        headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        # A 500 here usually means validation errors we need to see. Re-read body.
        body = e.read().decode("utf-8", "replace")
        raise SystemExit(f"HTTP {e.code} from {url}\n{body[:2000]}")
    except urllib.error.URLError as e:
        raise SystemExit(f"Cannot reach ComfyUI at {url}: {e.reason}\n"
                         f"Is the server running?  /Users/macstudio/ComfyUI/venv/bin/comfy launch -- --port 8188")


def _get_json(url: str, timeout: int = 30) -> dict:
    with urllib.request.urlopen(url, timeout=timeout) as r:
        return json.loads(r.read())


# ---------------------------------------------------------------------------
# Generation
# ---------------------------------------------------------------------------
def generate(host: str, prompt: str, width: int, height: int, steps: int,
             seed: int, negative: str, timeout: int) -> tuple[str, int]:
    """Submit one image. Returns (server filename, elapsed seconds)."""
    wf = json.loads(json.dumps(WORKFLOW))  # deep copy
    wf["474"]["inputs"]["prompt"] = prompt
    wf["474"]["inputs"]["negative_prompt"] = negative
    # resolution is a PIXEL BUDGET, not a dimension. Give it enough for the
    # requested canvas; the latent still comes out at EmptyLatentImage's size.
    wf["474"]["inputs"]["resolution"] = 1024
    wf["456"]["inputs"]["width"] = width
    wf["456"]["inputs"]["height"] = height
    wf["458"]["inputs"]["steps"] = steps
    wf["458"]["inputs"]["seed"] = seed
    wf["459"]["inputs"]["filename_prefix"] = "comfy_asset"

    res = _post_json(f"{host}/prompt", {"prompt": wf, "client_id": "comfy-assets"})
    pid = res.get("prompt_id")
    if not pid:
        raise SystemExit(f"No prompt_id returned: {json.dumps(res)[:800]}")
    if res.get("node_errors"):
        raise SystemExit(f"Validation errors:\n{json.dumps(res['node_errors'], indent=2)[:2000]}")

    print(f"  submitted {pid} — {width}x{height}, {steps} steps, seed {seed}", flush=True)

    t0 = time.time()
    while True:
        if time.time() - t0 > timeout:
            raise SystemExit(f"Timed out after {timeout}s waiting for {pid}")
        try:
            hist = _get_json(f"{host}/history/{pid}", timeout=15)
        except Exception:
            time.sleep(5)
            continue
        if pid in hist:
            status = hist[pid].get("status", {})
            st = status.get("status_str")
            if st == "error":
                errs = [m for m in (status.get("messages") or []) if m[0] == "execution_error"]
                detail = json.dumps(errs, indent=2)[:1500] if errs else "unknown error"
                raise SystemExit(f"Generation failed:\n{detail}")
            if st == "success":
                for out in (hist[pid].get("outputs") or {}).values():
                    for img in (out.get("images") or []):
                        return img["filename"], int(time.time() - t0)
            time.sleep(3)
            continue
        # progress heartbeat from the server log is noisy; just tick
        print(f"  ... {int(time.time() - t0)}s", end="\r", flush=True)
        time.sleep(5)


def fetch(host: str, filename: str, dest: Path) -> None:
    url = f"{host}/view?filename={filename}&type=output"
    dest.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(url, timeout=180) as r, open(dest, "wb") as f:
        f.write(r.read())


# ---------------------------------------------------------------------------
# Post-processing
# ---------------------------------------------------------------------------
def export(src: Path, out_base: Path, out_w: int, out_h: int,
           quality: int, formats: list[str], manifest: list[dict],
           alt: str, prompt: str, preset: str, seed: int, elapsed: int) -> None:
    from PIL import Image

    try:
        # Pillow >= 9.1 exposes the resampling filters on the Image module itself.
        RESAMPLE_LANCZOS = Image.Resampling.LANCZOS
    except AttributeError:  # pragma: no cover - very old Pillow
        RESAMPLE_LANCZOS = Image.LANCZOS

    im = Image.open(src)
    had_alpha = im.mode in ("RGBA", "LA") or "transparency" in im.info

    # Flatten onto white — JPEG and most web pipelines have no alpha.
    if had_alpha:
        bg = Image.new("RGB", im.size, (255, 255, 255))
        im_rgba = im.convert("RGBA")
        bg.paste(im_rgba, mask=im_rgba.split()[-1])
        im = bg
    else:
        im = im.convert("RGB")

    # Only ever downscale.
    if im.width > out_w:
        scale = out_w / im.width
        im = im.resize((out_w, max(1, round(im.height * scale))), RESAMPLE_LANCZOS)
    elif im.width < out_w:
        print(f"  ! generated {im.width}px < target {out_w}px; not upscaling", flush=True)

    entry = {
        "alt": alt, "prompt": prompt, "preset": preset, "seed": seed,
        "width": im.width, "height": im.height, "gen_seconds": elapsed,
        "files": {},
    }

    for fmt in formats:
        if fmt == "jpeg":
            p = out_base.with_suffix(".jpg")
            im.save(p, "JPEG", quality=quality, optimize=True, progressive=True)
        elif fmt == "webp":
            p = out_base.with_suffix(".webp")
            im.save(p, "WEBP", quality=quality, method=5)
        elif fmt == "avif":
            p = out_base.with_suffix(".avif")
            im.save(p, "AVIF", quality=max(40, quality - 10))
        elif fmt == "png":
            p = out_base.with_suffix(".png")
            im.save(p, "PNG", optimize=True)
        else:
            continue
        kb = p.stat().st_size / 1024
        entry["files"][fmt] = {"path": str(p), "kb": round(kb, 1)}
        print(f"  {fmt.upper():<5} {p.name:<34} {im.width}x{im.height}  {kb:>7.1f} KB", flush=True)

    manifest.append(entry)


def write_manifest(out_dir: Path, entries: list[dict]) -> None:
    p = out_dir / "assets.manifest.json"
    p.write_text(json.dumps(entries, indent=2), encoding="utf-8")
    print(f"\nmanifest -> {p}  ({len(entries)} asset(s), prompts + alt text included)")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--prompt", help="image prompt")
    ap.add_argument("--alt", help="alt text (defaults to the prompt)")
    ap.add_argument("--preset", default=DEFAULT_PRESET, choices=sorted(PRESETS))
    ap.add_argument("--out", default="./assets", help="output directory")
    ap.add_argument("--name", help="output basename (default: derived from alt/prompt)")
    ap.add_argument("--host", default=os.environ.get("COMFYUI_URL", "http://127.0.0.1:8188"))
    ap.add_argument("--steps", type=int, default=25, help="sampling steps (default 25)")
    ap.add_argument("--seed", type=int, default=0, help="0 = random")
    ap.add_argument("--negative", default=DEFAULT_NEGATIVE)
    ap.add_argument("--format", default="jpeg", help="comma list: jpeg,webp,avif,png")
    ap.add_argument("--quality", type=int, default=82, help="JPEG/WebP quality")
    ap.add_argument("--batch", type=int, default=1, help="variations at the same seed")
    ap.add_argument("--presets", action="store_true", help="list presets and exit")
    ap.add_argument("--timeout", type=int, default=900)
    ap.add_argument("--keep-png", action="store_true",
                    help="also keep the raw generation PNG")
    args = ap.parse_args()

    if args.presets:
        print(f"{'preset':<12} {'ratio':<8} {'generates':<12} {'outputs':<12} use")
        print("-" * 78)
        for k, v in PRESETS.items():
            print(f"{k:<12} {v['ratio']:<8} "
                  f"{str(v['gen'][0])+'x'+str(v['gen'][1]):<12} "
                  f"{str(v['out'][0])+'x'+str(v['out'][1]):<12} {v['use']}")
        print("\nGeneration is 130-250s per image on this machine. Batch overnight, not inline.")
        return 0

    if not args.prompt:
        ap.error("--prompt is required (or use --presets)")

    preset = PRESETS[args.preset]
    gen_w, gen_h = preset["gen"]
    out_w, out_h = preset["out"]
    formats = [f.strip().lower() for f in args.format.split(",") if f.strip()]
    seed = args.seed if args.seed else int.from_bytes(os.urandom(4), "big")

    alt = args.alt or args.prompt[:120]
    slug = args.name or "".join(
        c.lower() if c.isalnum() else "-" for c in alt)[:48].strip("-").replace("--", "-")

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest: list[dict] = []

    try:
        _get_json(f"{args.host}/system_stats", timeout=10)
    except Exception:
        raise SystemExit(
            f"No ComfyUI server at {args.host}.\n"
            f"Start it:  /Users/macstudio/ComfyUI/venv/bin/comfy launch -- --port 8188")

    print(f"preset={args.preset} ({preset['ratio']})  gen={gen_w}x{gen_h}  "
          f"out={out_w}px  fmt={','.join(formats)}  q={args.quality}")

    tmp_dir = out_dir / ".raw"
    for i in range(args.batch):
        label = slug if args.batch == 1 else f"{slug}-{i + 1}"
        print(f"\n[{i + 1}/{args.batch}] {label}")
        fn, secs = generate(args.host, args.prompt, gen_w, gen_h,
                            args.steps, seed + i, args.negative, args.timeout)
        raw = tmp_dir / fn
        fetch(args.host, fn, raw)
        print(f"  generated in {secs}s")

        export(raw, out_dir / label, out_w, out_h, args.quality, formats,
               manifest, alt, args.prompt, args.preset, seed + i, secs)
        if args.keep_png:
            print(f"  raw PNG kept at {raw}")

    write_manifest(out_dir, manifest)

    if not args.keep_png:
        for f in tmp_dir.glob("*"):
            f.unlink()
        try:
            tmp_dir.rmdir()
        except OSError:
            pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
