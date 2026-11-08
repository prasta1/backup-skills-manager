#!/usr/bin/env python3
"""List what a local ComfyUI server can actually generate right now.

Reads /object_info for the loader nodes (UNETLoader/CheckpointLoaderSimple/
CLIPLoader/VAELoader/loras) and prints the installed, selectable weights —
the verbatim values --args must use. Also flags which blueprint exposed
slots map to which loaders when given a converted graph.

Usage:
  python3 probe_models.py --host http://127.0.0.1:8188
Stdlib only.
"""
import argparse, json, os, urllib.request

LOADERS = {
    "UNETLoader": "unet_name", "CheckpointLoaderSimple": "ckpt_name",
    "CLIPLoader": "clip_name", "VAELoader": "vae_name",
    "LoraLoader": "lora_name", "CLIPVisionLoader": "clip_name",
}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default=os.environ.get("COMFYUI_URL", "http://127.0.0.1:8188"))
    a = ap.parse_args()
    with urllib.request.urlopen(a.host.rstrip("/") + "/object_info", timeout=30) as r:
        info = json.load(r)
    for cls, slot in LOADERS.items():
        d = info.get(cls)
        if not d:
            continue
        spec = (d.get("input") or {}).get("required", {}).get(slot)
        choices = spec[0] if isinstance(spec, (list, tuple)) and spec else None
        if choices is None:
            continue
        print(f"{cls}.{slot}:")
        for c in choices:
            print(f"  {c}")

if __name__ == "__main__":
    main()
