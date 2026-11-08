#!/usr/bin/env python3
"""Style sweep: one subject prompt, one seed, N styles -> honest batch comparison.

Reads style fragments from references/style-presets.json (the machine-readable
source; style-library.md is the human view). Submits via direct POST (reliable
path, pitfall 0h), polls /history, downloads outputs, emits JSON.

Convention: same seed across all styles so ONLY the style varies. After the
run, verify text spelling per style before presenting — text reliability
varies by style (style-library.md). Styles with cutout_ok=false (watercolor,
neon) are for on-paper/on-screen looks, not the transparent-PNG pipeline.

Usage:
  python run_style_sweep.py \
    --prompt "<subject core + text placement, WITHOUT any style words>" \
    --styles woodcut,risograph,vintage-road-sign \
    --seed 4242 --out ./outputs
  python run_style_sweep.py --prompt "..." --styles all --seed 7

Options: --steps (25), --cfg (1.0), --resolution (1024), --negative,
         --workflow (default qwen_img21_txt2img_int8.json)
"""
import argparse, json, os, sys, time, urllib.request, urllib.error, urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
PRESETS = os.path.join(HERE, "..", "references", "style-presets.json")
BASE_WF = os.path.join(HERE, "..", "workflows", "qwen_img21_txt2img_int8.json")
DEFAULT_NEG = ("blurry, low quality, distorted text, misspelled words, watermark, "
               "photograph, 3d render, gradients, drop shadow, extra text, crop marks")
BASE_URL = os.environ.get("COMFYUI_URL", "http://127.0.0.1:8188")


def load_presets():
    with open(PRESETS) as f:
        return json.load(f)


def resolve_styles(names, presets):
    avail = sorted(presets)
    if names == ["all"]:
        return avail
    bad = [n for n in names if n not in presets]
    if bad:
        sys.exit(f"unknown style(s): {', '.join(bad)}. Available: {', '.join(avail)}")
    return names


def post_prompt(wf):
    # pitfall 0j: drop top-level metadata keys ("_comment") or validate_prompt 500s
    wf = {k: v for k, v in wf.items() if isinstance(v, dict)}
    data = json.dumps({"prompt": wf, "client_id": "style-sweep"}).encode()
    req = urllib.request.Request(BASE_URL + "/prompt", data=data,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        return {"error": {"type": "HTTPError",
                          "message": f"{e.code}: {e.read().decode(errors='replace')[:800]}"}}


def wait_history(pid, timeout=600):
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            with urllib.request.urlopen(f"{BASE_URL}/history/{pid}", timeout=15) as r:
                h = json.loads(r.read())
        except Exception:
            time.sleep(5); continue
        if pid in h:
            entry = h[pid]
            st = entry.get("status", {})
            if st.get("completed") or st.get("status_str") == "success":
                return entry
            for m in st.get("messages", []):
                if m and m[0] == "execution_error":
                    return {"error": m[1]}
        time.sleep(5)
    return {"error": {"type": "timeout", "message": f"no completion in {timeout}s"}}


def download(fname, subfolder, dest):
    url = (f"{BASE_URL}/view?filename={urllib.parse.quote(fname)}"
           f"&subfolder={urllib.parse.quote(subfolder)}&type=output")
    urllib.request.urlretrieve(url, dest)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--prompt", required=True,
                    help="subject core + text placement, WITHOUT style words")
    ap.add_argument("--styles", required=True, help="comma-separated style names, or 'all'")
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--steps", type=int, default=25)
    ap.add_argument("--cfg", type=float, default=1.0)
    ap.add_argument("--resolution", type=int, default=1024)
    ap.add_argument("--negative", default=DEFAULT_NEG)
    ap.add_argument("--out", default=".")
    ap.add_argument("--workflow", default=BASE_WF)
    a = ap.parse_args()

    presets = load_presets()
    styles = resolve_styles([s.strip() for s in a.styles.split(",")], presets)
    os.makedirs(a.out, exist_ok=True)
    wf = json.load(open(a.workflow))
    wf.pop("_comment", None)

    results = []
    for style in styles:
        frag = presets[style]["fragment"]
        prompt = a.prompt.rstrip() + " " + frag
        w = json.loads(json.dumps(wf))
        w["452"]["inputs"]["prompt"] = prompt
        w["452"]["inputs"]["negative_prompt"] = a.negative
        w["452"]["inputs"]["resolution"] = a.resolution
        w["458"]["inputs"]["seed"] = a.seed
        w["458"]["inputs"]["steps"] = a.steps
        w["458"]["inputs"]["cfg"] = a.cfg
        print(f"[{style}] seed {a.seed} submitting...", flush=True)
        resp = post_prompt(w)
        if "error" in resp:
            results.append({"style": style, "status": "submit_failed", "detail": resp["error"]})
            print(f"[{style}] SUBMIT FAILED: {resp['error']}", flush=True)
            continue
        pid = resp["prompt_id"]
        print(f"[{style}] prompt_id {pid}", flush=True)
        entry = wait_history(pid)
        if "error" in entry:
            results.append({"style": style, "status": "failed", "detail": entry["error"]})
            print(f"[{style}] FAILED: {entry['error']}", flush=True)
            continue
        outs = []
        for nid, node_out in (entry.get("outputs") or {}).items():
            for img in node_out.get("images", []):
                fname = img.get("filename"); sub = img.get("subfolder", "")
                dest = os.path.join(a.out, f"{style}_{fname}")
                download(fname, sub, dest)
                outs.append({"node": nid, "file": dest, "size": os.path.getsize(dest)})
        results.append({"style": style, "status": "ok", "seed": a.seed, "outputs": outs})
        print(f"[{style}] done: {outs}", flush=True)
    print("FINAL_JSON=" + json.dumps(results), flush=True)


if __name__ == "__main__":
    main()