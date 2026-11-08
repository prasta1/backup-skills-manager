#!/usr/bin/env python3
"""Generate images with Unsloth Studio's local diffusion models.

Unsloth Studio serves OpenAI-compatible image generation at
POST /v1/images/generations (model, prompt, size "WxH", n, steps, seed —
verified live). Auth is a bearer key from the app's own agent key file
(`~/.unsloth/studio/auth/agent_api_key.json`, `servers.<base_url>.minted[-1]`
or `.saved[0]`). On the Mac Studio the app is at 127.0.0.1:8888 (tailnet:
https://studio.taile85139.ts.net:8888 via `tailscale serve`). On the MacBook
it binds loopback only and is reached by SSH (`ssh macbook`).

Usage (run on the Mac Studio; stdlib + ssh only):
  python3 unsloth_gen.py --machine studio --list
  python3 unsloth_gen.py --machine macbook --model unsloth/Qwen-Image-2.1-GGUF \
      --prompt "a glossy red cube" --size 1024x1024 --steps 25 --seed 42 \
      --out ./outputs
Flags: --negative, --n (batch), --size WxH, --steps, --seed, --init-image
(img2img: sends b64), --strength, --base-url override, --ssh-host override.

--list prints live image-capable models (id, quant, loaded) plus supported
families from /api/inference/images/info. Outputs land in --out as .png.
"""
import argparse, base64, json, os, shlex, subprocess, sys, time, urllib.request

MACHINES = {
    "studio": {"base": "http://127.0.0.1:8888", "keyfile":
        "/Users/macstudio/.unsloth/studio/auth/agent_api_key.json", "ssh": None},
    "macbook": {"base": "http://127.0.0.1:8888", "keyfile":
        "/Users/prasta/.unsloth/studio/auth/agent_api_key.json", "ssh": "macbook"},
}

def ssh_run(host, cmd, stdin=None):
    return subprocess.run(["ssh", "-o", "ConnectTimeout=8", host] + cmd,
                          capture_output=True, text=True, input=stdin)

def api(base, path, body=None, key=None, ssh=None, timeout=600):
    url = base.rstrip("/") + path
    if ssh:
        # remote curl won't honor -H across the ssh argv boundary (observed:
        # "Not authenticated"); route auth/body through a curl config on stdin.
        cfg = ""
        if key: cfg += f'header = "Authorization: Bearer {key}"\n'
        if body is not None:
            cfg += 'header = "Content-Type: application/json"\n'
            cfg += "data = " + json.dumps(json.dumps(body)) + "\n"
        r = ssh_run(ssh, ["curl", "-s", "-m", str(timeout), "--fail-with-body", "-K-", "--", url],
                    stdin=cfg)
        if r.returncode != 0 and not r.stdout:
            sys.exit(f"ssh to {ssh} failed (curl rc={r.returncode}): {r.stderr[:200]}")
        return r.stdout
    req = urllib.request.Request(url, data=json.dumps(body).encode() if body else None,
        headers={"Authorization": f"Bearer {key}"} if key else {},
        method="POST" if body else "GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read().decode()
    except Exception as e:
        if "Connection refused" in str(e) or "Errno 61" in str(e):
            sys.exit(f"nothing listening at {base} — start the Unsloth Studio app, "
                     f"or pick the other machine")
        code = getattr(e, "code", type(e).__name__)
        body = e.read().decode()[:300] if hasattr(e, "read") else str(e)[:300]
        sys.exit(f"HTTP {code} on {path}: {body}")

def get_key(m, base):
    # read the app's own agent key file: locally (studio) or via ssh cat (macbook)
    if m["ssh"]:
        txt = ssh_run(m["ssh"], ["cat", m["keyfile"]]).stdout
    else:
        txt = open(os.path.expanduser(m["keyfile"])).read()
    j = json.loads(txt)
    srv = j.get("servers", {}).get(base, {})
    keys = [k for k in srv.get("minted", []) if isinstance(k, str)] or \
           [k for k in srv.get("saved", []) if isinstance(k, str)]
    if not keys:
        sys.exit(f"no agent API key under servers['{base}'] in {m['keyfile']}")
    return keys[-1]

def live_models(m, base, key):
    models = json.loads(api(base, "/api/inference/models", key=key, ssh=m["ssh"]))["data"]
    fam_raw = api(base, "/api/inference/images/info", key=key, ssh=m["ssh"])
    fams = json.loads(fam_raw).get("families", [])
    print("SUPPORTED FAMILIES (bf16 resident GB):")
    for f in fams:
        print(f"  {f['family']:24s} {f.get('estimated_resident_gb',{}).get('bf16')}")
    print("INSTALLED IMAGE MODELS:")
    img_kw = ("flux", "qwen-image", "z-image", "sd3", "stable", "kontext",
              "seedream", "hidream", "ideogram", "krea", "hunyuanimage",
              "lumina", "image")
    seen = False
    for mo in models:
        mid = mo.get("id", "")
        if any(w in mid.lower() for w in img_kw):
            seen = True
            print(f"  {mid} | quant={mo.get('quant')} | loaded={mo.get('loaded')}")
    if not seen:
        print("  (none installed — download via the Studio app's Models tab)")

def ensure_loaded(m, base, key, model, quiet=False, gguf_filename=None, allow_oversized=False, force_reload=False):
    """The /v1 endpoint 503s with 'No image model loaded' until a diffusion
    model is loaded; /api/inference/images/load loads (and downloads) it."""
    st = json.loads(api(base, "/api/inference/images/status", key=key, ssh=m["ssh"]))
    def matches():
        # loaded flag can belong to a PREVIOUS model while a swap is in flight
        # (observed: finalizing 100% of the old edit model, new one never loaded)
        return st.get("loaded") and (st.get("repo_id") == model or
            st.get("display_repo_id") == model.rsplit("/", 1)[-1])
    if matches() and not force_reload:
        if not quiet: print(f"already loaded: {st.get('repo_id')}")
        return
    if not quiet: print(f"loading {model} ...")
    # single-file GGUF repos need model_kind + the .gguf filename explicitly;
    # a bare model_path either errors in-body or resolves to another variant
    body = {"model_path": model}
    if gguf_filename:
        body.update({"model_kind": "gguf", "gguf_filename": gguf_filename})
    if allow_oversized:
        body["allow_oversized"] = True
    resp = api(base, "/api/inference/images/load", body=body, key=key, ssh=m["ssh"])
    try:
        rl = json.loads(resp)
    except Exception:
        rl = {}
    if rl.get("error") or rl.get("detail"):
        sys.exit(f"load rejected: {rl.get('error') or rl.get('detail')}")
    for _ in range(240):
        prog = json.loads(api(base, "/api/inference/images/load-progress", key=key, ssh=m["ssh"]))
        if prog.get("error"):
            sys.exit(f"load failed: {prog['error']}")
        st = json.loads(api(base, "/api/inference/images/status", key=key, ssh=m["ssh"]))
        if st.get("loaded") and matches():
            if not quiet: print(f"loaded: {st.get('repo_id')} ({st.get('device')}/{st.get('dtype')})")
            return
        if not quiet and prog.get("phase"):
            print(f"  {prog['phase']} {int((prog.get('fraction') or 0)*100)}%", file=sys.stderr)
        time.sleep(5)
    sys.exit("load did not finish within 20 min")

def download(m, url, dest, key=None):
    if m["ssh"]:
        # signed URL is loopback-bound on the MBP and needs the bearer key:
        # fetch there via curl config, ship base64 back through ssh stdout.
        # ssh flattens argv into one space-joined string, so a `sh -c 'S' x URL`
        # structure is destroyed (x/URL leak into base64's args). Pass a single
        # self-contained command with the URL shell-quoted inline instead.
        cfg = f'header = "Authorization: Bearer {key}"\n' if key else ""
        cmd = f"curl -s -m 600 -K- -- {shlex.quote(url)} | base64"
        r = ssh_run(m["ssh"], [cmd], stdin=cfg)
        if not r.stdout.strip():
            sys.exit(f"download of {url[:60]} via ssh failed: {r.stderr[:200]}")
        open(dest, "wb").write(base64.b64decode(r.stdout))
    else:
        with urllib.request.urlopen(url, timeout=120) as r:
            open(dest, "wb").write(r.read())

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--machine", choices=MACHINES, required=True)
    ap.add_argument("--base-url"); ap.add_argument("--ssh-host")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--model"); ap.add_argument("--prompt")
    ap.add_argument("--negative"); ap.add_argument("--size", default="1024x1024")
    ap.add_argument("--steps", type=int); ap.add_argument("--seed", type=int)
    ap.add_argument("--n", type=int, default=1)
    ap.add_argument("--init-image"); ap.add_argument("--strength", type=float)
    ap.add_argument("--force-reload", action="store_true",
        help="always call the load endpoint, even if the repo is already loaded")
    ap.add_argument("--allow-oversized", action="store_true",
        help="send allow_oversized to bypass the memory-estimate load guard")
    ap.add_argument("--gguf-filename", help="single-file GGUF checkpoint inside a "
        "GGUF repo (required when the repo is single-file, e.g. "
        "qwen-image-edit-2511-Q4_K_M.gguf)")
    ap.add_argument("--out", default="./outputs")
    a = ap.parse_args()
    m = dict(MACHINES[a.machine])
    if a.ssh_host: m["ssh"] = a.ssh_host
    base = a.base_url or m["base"]
    key = get_key(m, base)
    if a.list:
        live_models(m, base, key); return
    if not a.model or not a.prompt:
        sys.exit("--model and --prompt required (or use --list)")
    ensure_loaded(m, base, key, a.model, gguf_filename=a.gguf_filename,
                    allow_oversized=a.allow_oversized, force_reload=a.force_reload)
    body = {"model": a.model, "prompt": a.prompt, "n": a.n, "size": a.size}
    if a.negative: body["negative_prompt"] = a.negative
    if a.steps: body["steps"] = a.steps
    if a.seed is not None: body["seed"] = a.seed
    if a.init_image:
        body["image"] = "data:image/png;base64," + base64.b64encode(open(a.init_image, "rb").read()).decode()
        if a.strength: body["strength"] = a.strength
    txt = api(base, "/v1/images/generations", body=body, key=key, ssh=m["ssh"], timeout=900)
    r = json.loads(txt)
    if r.get("error"):
        sys.exit(f"generation refused: {r['error'].get('message', r['error'])}")
    if not r.get("data"):
        sys.exit(f"no images returned ({a.model}): {txt[:300]} — model may be "
                 f"edit-only or still swapping; check --list / images/status")
    os.makedirs(a.out, exist_ok=True)
    for i, item in enumerate(r.get("data", [])):
        dest = os.path.join(a.out, f"unsloth_{a.model.rsplit('/',1)[-1]}_{i:02d}.png")
        if item.get("b64_json"):
            open(dest, "wb").write(base64.b64decode(item["b64_json"]))
        elif item.get("url"):
            download(m, item["url"], dest, key=key)
        else:
            sys.exit(f"unexpected item: {json.dumps(item)[:200]}")
        print(dest)

if __name__ == "__main__":
    main()
