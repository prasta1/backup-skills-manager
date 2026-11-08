#!/usr/bin/env python3
"""run_subject.py — Generate with permanent subject references (Patrick + Cora).

Wires ref_patrick.png / ref_cora.png into the Qwen-Image-2.1 txt2img workflow
so you don't have to hand over images each time. Direct POST (reliable path).

Usage:
    python run_subject.py --prompt "me and Cora at the desk" [--count 3] [--seed N]
    python run_subject.py --prompt "..." --subjects patrick,cora --count 2

--subjects: comma list of ref_*.png names (default: patrick,cora). Any file
named ref_<name>.png in the server input dir works.
"""
from __future__ import annotations

import argparse, json, os, random, sys, time, urllib.request
from pathlib import Path

HOST = os.environ.get("COMFYUI_URL", "http://127.0.0.1:8188")
WORKFLOW = Path(__file__).resolve().parent.parent / "workflows" / "qwen_subject_refs.json"

DEFAULT_NEG = ("blurry, low quality, distorted face, changed identity, extra limbs, "
               "deformed hands, text, watermark, wrong dog color")


def submit(wf: dict, client_id: str) -> str:
    body = json.dumps({"prompt": wf, "client_id": client_id}).encode()
    req = urllib.request.Request(f"{HOST}/prompt", data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)["prompt_id"]


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--prompt", required=True)
    p.add_argument("--subjects", default="patrick,cora",
                   help="comma list of ref_<name>.png to wire in")
    p.add_argument("--count", type=int, default=3)
    p.add_argument("--seed", type=int, default=None)
    p.add_argument("--negative", default=DEFAULT_NEG)
    p.add_argument("--resolution", type=int, default=1024)
    p.add_argument("--steps", type=int, default=25)
    args = p.parse_args()

    wf = json.loads(WORKFLOW.read_text())
    wf.pop("_comment", None)  # direct POST rejects top-level _comment (500)
    subjects = [s.strip() for s in args.subjects.split(",") if s.strip()]

    # rebuild LoadImage nodes for the requested subjects
    for i, name in enumerate(subjects, start=1):
        wf[str(469 + i)] = {"class_type": "LoadImage", "inputs": {"image": f"ref_{name}.png"}}
    wf["452"]["inputs"]["images"] = {f"image_{i}": [str(469 + i), 0]
                                     for i in range(1, len(subjects) + 1)}
    wf["452"]["inputs"]["prompt"] = args.prompt
    wf["452"]["inputs"]["negative_prompt"] = args.negative
    wf["452"]["inputs"]["resolution"] = args.resolution
    wf["458"]["inputs"]["steps"] = args.steps

    rng = random.SystemRandom()
    pids = []
    for _ in range(args.count):
        seed = args.seed if args.seed is not None else rng.randint(0, 2**31 - 1)
        wf["458"]["inputs"]["seed"] = seed
        wf["459"]["inputs"]["filename_prefix"] = f"qwen_subject_s{seed}"
        pid = submit(json.loads(json.dumps(wf)), f"hermes-subject-{seed}")
        pids.append((pid, seed))
        print(f"submitted {pid[:8]} seed {seed}", flush=True)

    # poll
    t0 = time.time()
    while time.time() - t0 < 900:
        with urllib.request.urlopen(f"{HOST}/history", timeout=5) as r:
            h = json.load(r)
        statuses = {pid: h.get(pid, {}).get("status", {}).get("status_str") for pid, _ in pids}
        if all(s == "success" for s in statuses.values()):
            for pid, seed in pids:
                for nid, v in h[pid]["outputs"].items():
                    for img in v.get("images", []):
                        print(f"OUT {seed} {img['filename']}")
            return 0
        if any(s == "error" for s in statuses.values()):
            print("ERRORS:", {p: s for p, s in statuses.items() if s == "error"}, file=sys.stderr)
            return 1
        time.sleep(20)
    print("TIMEOUT waiting for jobs", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
