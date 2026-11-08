#!/usr/bin/env python3
"""run_text_battery.py — run a list of text-rendering prompts through ComfyUI.

This is the text-rendering battery used to grade an image model's typography:
short words, alphanumeric strings, long headlines, a full pangram, and a
multi-element trap (arrow + text + phone number). See
workflows/README.md for the grading rubric.

Why not `run_workflow.py --args '{"prompt": ...}'`? The Qwen-Image-2.1
`TextEncodeQwenImage21` node's `prompt` field is NOT in the extracted schema
(that extractor only follows sampler→CLIPTextEncode links), so param injection
cannot reach it. This script JSON-injects `prompt` + `seed` straight into the
workflow dict per run, then submits /prompt, polls /history, downloads outputs.

Usage:
    python scripts/run_text_battery.py \
        --workflow workflows/qwen_img21_txt2img_int8.json \
        --prompts '@path/to/prompts.json' \
        --output-dir ./outputs/text-battery

    python scripts/run_text_battery.py \
        --prompts '["a HELP pin", "a HELLO WORLD postcard"]' \
        --seed-base 1003 --seed-step 11

Stdlib-only (Python 3.10+). Prints a JSON summary to stdout.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

DEFAULT_WORKFLOW = Path(__file__).resolve().parent.parent / "workflows" / "qwen_img21_txt2img_int8.json"
from _common import pick_local_host, strip_meta_keys

DEFAULT_HOST = pick_local_host()
DEFAULT_NEGATIVE = "blurry, low quality"


def http_json(host: str, path: str, payload=None, timeout: int = 300):
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(
        host + path, data=data,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        body = r.read().decode("utf-8")
        return json.loads(body) if body.strip() else None


def wait_done(host: str, prompt_id: str, timeout: float = 1200.0) -> dict:
    t0 = time.time()
    interval = 1.5
    while time.time() - t0 < timeout:
        try:
            hist = http_json(host, f"/history/{prompt_id}", timeout=30)
        except (urllib.error.URLError, urllib.error.HTTPError):
            time.sleep(interval)
            continue
        entry = (hist or {}).get(prompt_id) or {}
        st = entry.get("status") or entry
        if st.get("status_str") == "error":
            return {"status": "error", "data": entry}
        if st.get("completed"):
            return {"status": "success", "outputs": entry.get("outputs", {}), "entry": entry}
        time.sleep(interval)
        interval = min(8.0, interval * 1.4)
    return {"status": "timeout", "elapsed": time.time() - t0}


def download_output(host: str, filename: str, subfolder: str, out_path: Path) -> Path:
    url = host + "/view?" + urllib.parse.urlencode(
        {"filename": filename, "subfolder": subfolder, "type": "output"}
    )
    with urllib.request.urlopen(url, timeout=600) as r, open(out_path, "wb") as f:
        f.write(r.read())
    return out_path


def run_once(host: str, workflow: dict, prompt: str, seed: int,
             negative: str, out_dir: Path) -> dict:
    wf = json.loads(json.dumps(workflow))  # deepcopy
    wf["452"]["inputs"]["prompt"] = prompt
    wf["452"]["inputs"]["negative_prompt"] = negative
    wf["458"]["inputs"]["seed"] = seed

    try:
        sub = http_json(host, "/prompt", {"prompt": strip_meta_keys(wf), "client_id": f"text-battery-{seed}"}, timeout=120) or {}
    except urllib.error.HTTPError as e:
        try:
            body = e.read().decode("utf-8")[:300]
        except Exception:
            body = ""
        return {"prompt": prompt[:60], "seed": seed, "status": "submit_http_error",
                "http_status": e.code, "body": body}
    except Exception as e:
        return {"prompt": prompt[:60], "seed": seed, "status": "submit_error", "error": str(e)}

    if isinstance(sub.get("error"), dict):
        return {"prompt": prompt[:60], "seed": seed, "status": "validation_failed",
                "details": sub["error"]}
    pid = sub.get("prompt_id")
    if not pid:
        return {"prompt": prompt[:60], "seed": seed, "status": "no_prompt_id", "response": sub}

    res = wait_done(host, pid)
    if res["status"] != "success":
        return {"prompt": prompt[:60], "seed": seed, "status": res["status"],
                "prompt_id": pid, "detail": str(res.get("data", ""))[:200]}

    downloaded = []
    for node_id, node_out in (res.get("outputs") or {}).items():
        for key in ("images", "videos", "audio", "files"):
            entries = node_out.get(key) or []
            if not isinstance(entries, list):
                entries = [entries]
            for fi in entries:
                filename = fi.get("filename") or ""
                if not filename:
                    continue
                p = out_dir / f"run_{seed:03d}" / filename
                p.parent.mkdir(parents=True, exist_ok=True)
                try:
                    download_output(host, filename, fi.get("subfolder") or "", p)
                    downloaded.append({"file": str(p), "filename": filename})
                except Exception as e:
                    downloaded.append({"file": None, "filename": filename, "error": str(e)})

    return {"prompt": prompt[:60], "seed": seed, "status": "success",
            "prompt_id": pid, "outputs": downloaded}


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Run text-rendering prompts through ComfyUI")
    p.add_argument("--workflow", default=str(DEFAULT_WORKFLOW),
                   help="API-format workflow JSON (default: qwen_img21_txt2img_int8.json)")
    p.add_argument("--prompts", required=True,
                   help="JSON array of prompts, or @path/to/prompts.json, or - for stdin")
    p.add_argument("--host", default=DEFAULT_HOST, help="ComfyUI server URL")
    p.add_argument("--output-dir", default="./outputs/text-battery")
    p.add_argument("--negative-prompt", default=DEFAULT_NEGATIVE)
    p.add_argument("--seed-base", type=int, default=1003)
    p.add_argument("--seed-step", type=int, default=11)
    p.add_argument("--timeout", type=float, default=0, help="poll timeout per run (0 = 1200s)")
    args = p.parse_args(argv)

    wf_path = Path(args.workflow).expanduser()
    if not wf_path.exists():
        print(json.dumps({"error": f"workflow not found: {args.workflow}"}))
        return 1
    try:
        workflow = json.loads(wf_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(json.dumps({"error": f"invalid workflow JSON: {e}"}))
        return 1

    raw = args.prompts
    if raw == "-":
        raw = sys.stdin.read()
    elif raw.startswith("@"):
        try:
            raw = Path(raw[1:]).expanduser().read_text(encoding="utf-8")
        except OSError as e:
            print(json.dumps({"error": f"cannot read prompts file: {e}"}))
            return 1
    try:
        prompts = json.loads(raw)
    except json.JSONDecodeError as e:
        print(json.dumps({"error": f"invalid --prompts JSON: {e}"}))
        return 1
    if not isinstance(prompts, list) or not prompts:
        print(json.dumps({"error": "--prompts must be a non-empty JSON array"}))
        return 1

    out_dir = Path(args.output_dir).expanduser()
    out_dir.mkdir(parents=True, exist_ok=True)
    timeout = args.timeout or 1200.0

    # Quick health check (also surfaces the server before a long batch)
    try:
        stats = http_json(args.host, "/system_stats", timeout=10) or {}
    except Exception as e:
        print(json.dumps({"error": f"cannot reach server at {args.host}: {e}"}))
        return 1

    results = []
    for i, prompt in enumerate(prompts):
        seed = args.seed_base + i * args.seed_step
        results.append(run_once(args.host, workflow, prompt, seed,
                                args.negative_prompt, out_dir))
        print(f"[{i + 1:2d}/{len(prompts)}] seed {seed:04d} done", file=sys.stderr)

    ok = sum(1 for r in results if r["status"] == "success")
    print(json.dumps({
        "status": "success" if ok == len(results) else "partial",
        "total": len(results),
        "completed": ok,
        "failed": len(results) - ok,
        "server": stats.get("system", {}).get("comfyui_version"),
        "output_dir": str(out_dir),
        "results": results,
    }, indent=2))
    return 0 if ok == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
