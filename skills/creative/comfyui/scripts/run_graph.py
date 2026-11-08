#!/usr/bin/env python3
"""Submit a ComfyUI API-format workflow and fetch the resulting media.

For graphs you built yourself this is more reliable than run_workflow.py, whose
schema extraction silently drops --args keys it cannot match. Here an override
either lands or the run fails loudly.

Usage:
  run_graph.py --workflow W.json --outdir DIR --name NAME \
      [--set 'NODE.inputs_key=value'] [--set 'NODE.inputs_key=42'] \
      [--wait-timeout SECONDS]

--set value coercion: true/false -> bool, ints/floats -> number, everything
else stays a string. Repeat --set per override. Prints a JSON summary, echoes
the prompt text actually submitted, and exits non-zero on any failure.
"""
import argparse
import json
import os
import shutil
import sys
import time
import urllib.error
import urllib.request
import uuid

HOST = "http://127.0.0.1:8188"


def coerce(v):
    if v.lower() in ("true", "false"):
        return v.lower() == "true"
    try:
        return int(v)
    except ValueError:
        pass
    try:
        return float(v)
    except ValueError:
        pass
    return v


def find_in_gallery(filename, max_age_s=7200):
    """Locate a render that comfyui-gallery-sweep has moved out of ComfyUI/output.

    The sweep archives to ~/Pictures/ComfyUI/<YYYY-MM>/ and REWRITES the name
    (underscores -> hyphens, plus a _NN suffix), e.g.
    wan_i2v_len121_00001_.mp4 -> wan-i2v-len121-00001_01.mp4
    so match on a normalised prefix of the stem rather than the literal name.
    """
    import glob
    import re
    import time

    stem = os.path.splitext(os.path.basename(filename))[0]
    norm = lambda s: re.sub(r"[^a-z0-9]", "", s.lower())  # noqa: E731
    want = norm(stem)
    if not want:
        return None
    now = time.time()
    for p in glob.glob(os.path.expanduser("~/Pictures/ComfyUI/*/*")):
        if not os.path.isfile(p):
            continue
        try:
            if now - os.path.getmtime(p) > max_age_s:
                continue
        except OSError:
            continue
        if norm(os.path.splitext(os.path.basename(p))[0]).startswith(want):
            return p
    return None


def apply_sets(graph, pairs):
    for p in pairs:
        if "=" not in p:
            sys.exit(f"bad --set (no '='): {p}")
        path, raw = p.split("=", 1)
        if "." not in path:
            sys.exit(f"bad --set (need NODE.key): {p}")
        node_id, key = path.split(".", 1)
        if node_id not in graph:
            sys.exit(f"--set targets unknown node {node_id!r} in {p}")
        if key not in graph[node_id].get("inputs", {}):
            sys.exit(f"--set targets unknown input {key!r} on node {node_id} "
                     f"(available: {sorted(graph[node_id].get('inputs', {}))})")
        graph[node_id]["inputs"][key] = coerce(raw)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workflow", required=True)
    ap.add_argument("--outdir", required=True)
    ap.add_argument("--name", required=True)
    ap.add_argument("--set", action="append", default=[])
    ap.add_argument("--wait-timeout", type=int, default=2400)
    args = ap.parse_args()

    graph = json.load(open(args.workflow))
    graph = {k: v for k, v in graph.items() if not k.startswith("_")}
    apply_sets(graph, args.set)

    os.makedirs(args.outdir, exist_ok=True)
    payload = {"prompt": graph, "client_id": str(uuid.uuid4())}
    req = urllib.request.Request(HOST + "/prompt",
                                 data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=90) as r:
            body = json.load(r)
    except urllib.error.HTTPError as e:
        detail = json.loads(e.read().decode())
        print(json.dumps({"status": "rejected", "http": e.code, "detail": detail}, indent=2))
        return 2

    pid = body["prompt_id"]
    print(f"submitted prompt_id={pid} node_errors={body.get('node_errors')}", flush=True)

    t0 = time.time()
    while time.time() - t0 < args.wait_timeout:
        try:
            with urllib.request.urlopen(f"{HOST}/history/{pid}", timeout=30) as r:
                hist = json.load(r)
        except Exception:
            hist = {}
        if hist:
            rec = list(hist.values())[0]
            status = rec.get("status", {})
            outs = rec.get("outputs", {})

            submitted = rec.get("prompt", [None, None, {}])[2]
            for nid, n in (submitted.items() if isinstance(submitted, dict) else []):
                if n.get("class_type") == "CLIPTextEncode":
                    print(f"  submitted text[{nid}]: {n['inputs'].get('text', '')[:110]}", flush=True)

            media = []
            for nid, out in outs.items():
                for key in ("videos", "gifs", "images", "animated"):
                    for item in (out.get(key) or []):
                        if isinstance(item, dict):
                            media.append((nid, item))

            if not media:
                print(json.dumps({"status": status.get("status_str"),
                                  "completed": status.get("completed"),
                                  "error": "no media in outputs", "outputs": {k: list(v) for k, v in outs.items()}},
                                 indent=2))
                return 3

            saved = []
            ext_default = ".mp4"
            for nid, item in media:
                rel = os.path.join(item.get("subfolder") or "", item.get("filename") or "")
                src = os.path.join(os.path.expanduser("~/ComfyUI/output"), rel)
                if not os.path.exists(src):
                    # The comfyui-gallery-sweep LaunchAgent can MOVE the render out of
                    # ComfyUI/output within a minute of it finishing, so a plain copy
                    # races it and silently loses the file. Fall back to the archive.
                    src = find_in_gallery(item.get("filename") or "")
                if not src or not os.path.exists(src):
                    print(f"  WARN: could not locate output for node {nid} "
                          f"({item.get('filename')}) in output/ or the gallery archive",
                          flush=True)
                    continue
                ext = os.path.splitext(item["filename"])[1] or ext_default
                dst = os.path.join(args.outdir, f"{args.name}{ext}")
                shutil.copy2(src, dst)
                saved.append({"src": src, "dst": dst, "bytes": os.path.getsize(dst)})

            print(json.dumps({"status": status.get("status_str"),
                              "completed": status.get("completed"),
                              "elapsed_s": round(time.time() - t0, 1),
                              "saved": saved}, indent=2))
            return 0 if (saved and status.get("completed")) else 4
        time.sleep(15)

    print(json.dumps({"status": "timeout", "waited_s": args.wait_timeout}))
    return 5


if __name__ == "__main__":
    sys.exit(main())
