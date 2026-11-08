#!/usr/bin/env python3
"""image-gen executor — run a validated request against the fleet's local image engines.

Consumes the canonical request object (request-schema.json) and routes it to the
correct machine/backend per config.yaml (same directory). Handles auth (ComfyUI:
none; Unsloth: bearer key with rotation), endpoint selection, polling, timeouts,
retries, and non-2xx responses; downloads the output(s) to a timestamped file.
Every run is appended to a JSONL history log (prompt, model, settings, output
paths, timestamp, status); `--retry` replays the last failed run verbatim.

Usage:
  python3 executor.py --request request.json
  python3 executor.py --request request.json --out /tmp/img
  cat request.json | python3 executor.py --request -
  python3 executor.py --retry                # re-run last failed generation
  python3 executor.py --retry --history hist.jsonl

Exit 0 on success, 1 on failure, 130 on interrupt. Results go to stdout as JSON:
  {"status": "success", "outputs": [{"path": ..., "seed": ..., ...}], ...}
Errors go to stderr AND stdout as {"status": "error", "error": ..., "hint": ...}.
Progress/status lines go to stderr (suppressed with --quiet).

Requires PyYAML (python3 on this host has it). Stdlib otherwise.
"""
from __future__ import annotations

import argparse
import base64
import copy
import datetime
import json
import os
import random
import shlex
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent
GRAPH_DIR = SKILL_DIR / "graphs"

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None


class ExecutorError(Exception):
    """Actionable failure. `hint` is the fix; `status` is the short classifier."""

    def __init__(self, message: str, hint: str = "", status: str = "error"):
        super().__init__(message)
        self.message = message
        self.hint = hint
        self.status = status


# --------------------------------------------------------------------------- #
# Config / request loading
# --------------------------------------------------------------------------- #

def load_config(path: Path | None = None) -> dict:
    p = Path(path).expanduser() if path else SKILL_DIR / "config.yaml"
    if not p.exists():
        raise ExecutorError(f"config not found: {p}", "Expected config.yaml next to executor.py")
    if yaml is None:
        raise ExecutorError(
            "PyYAML is required to read config.yaml",
            "Run with python3 (has yaml), or `pip3 install --user pyyaml`.",
        )
    with p.open() as f:
        return yaml.safe_load(f)


def load_request(req: str) -> dict:
    try:
        if req == "-":
            raw = sys.stdin.read()
        else:
            raw = Path(req).expanduser().read_text()
    except OSError as e:
        raise ExecutorError(f"cannot read request: {e}", f"Check the path: {req}")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise ExecutorError(f"request is not valid JSON: {e}", "Fix the JSON and re-run.")
    if not isinstance(data, dict):
        raise ExecutorError("request must be a JSON object", "See request-schema.json.")
    return data


# --------------------------------------------------------------------------- #
# History log + status lines
# --------------------------------------------------------------------------- #

# Status/progress lines go to stderr (like all interactive text); --quiet
# suppresses them. History is a JSONL file (one entry per run) whose last
# non-success entry is what `--retry` replays.
QUIET = False
_LAST_STATUS_TS = 0.0


def resolve_history_path(cfg: dict, override: str | None = None) -> Path:
    if override:
        return Path(override).expanduser()
    d = (cfg.get("defaults") or {}).get("history_file", "~/Pictures/image-gen/history.jsonl")
    return Path(d).expanduser()


def status(msg: str, force: bool = False) -> None:
    """Print a stderr status line unless --quiet. Poll loops throttle to 8s."""
    global _LAST_STATUS_TS
    if QUIET:
        return
    now = time.time()
    if not force and now - _LAST_STATUS_TS < 8.0:
        return
    _LAST_STATUS_TS = now
    print(msg, file=sys.stderr, flush=True)


def make_history_entry(req: dict, result: dict, model: dict, machine: dict,
                       backend: dict) -> dict:
    """One JSONL history line: request + outcome + resolved seed (if any)."""
    settings = dict(req.get("settings") or {})
    outputs = result.get("outputs") or []
    if outputs and isinstance(outputs[0], dict) and settings.get("seed") is None:
        seed = outputs[0].get("seed")
        if seed is not None:
            settings["seed"] = seed
    entry = {
        "ts": int(time.time()),
        "iso": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
        "status": result.get("status"),
        "model_id": model["id"],
        "machine": machine.get("id"),
        "backend": backend.get("id"),
        "prompt": req.get("prompt"),
        "negative_prompt": req.get("negative_prompt"),
        "settings": settings,
        "request": req,
    }
    if result.get("status") == "success":
        entry["outputs"] = outputs
        entry["elapsed_s"] = result.get("elapsed_s")
    else:
        entry["error"] = result.get("error")
        if result.get("hint"):
            entry["hint"] = result["hint"]
    return entry


def append_history(path: Path, entry: dict) -> None:
    """Append one JSONL entry. Best-effort: a log failure must never mask a
    successful generation, so failures only warn to stderr."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(entry, ensure_ascii=False, default=str) + "\n"
        with open(path, "a", encoding="utf-8") as f:
            f.write(line)
    except OSError as e:
        print(f"WARNING: could not append history at {path}: {e}", file=sys.stderr)


def load_last_failed(path: Path) -> dict | None:
    """Return the most recent history entry whose status != 'success'."""
    if not path.exists():
        return None
    last = None
    skipped = 0
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    skipped += 1
                    continue
                if isinstance(entry, dict) and entry.get("status") != "success":
                    last = entry
    except OSError as e:
        print(f"WARNING: cannot read history {path}: {e}", file=sys.stderr)
        return None
    if skipped:
        print(f"WARNING: skipped {skipped} unparseable line(s) in {path}", file=sys.stderr)
    return last


# --------------------------------------------------------------------------- #
# Settings validation (per-model bounds from config.yaml)
# --------------------------------------------------------------------------- #

def _looks_int(v) -> bool:
    return isinstance(v, int) and not isinstance(v, bool)


def validate_settings(req: dict, model: dict) -> dict:
    """Apply defaults + enforce the model's settings map. Returns resolved settings.

    Rejects unknown keys, out-of-range values, multiple_of violations (Unsloth 32,
    ComfyUI 8), disallowed choice values, Unsloth area/side limits, and the
    ComfyUI qwen width==height rule.
    """
    spec = model.get("settings") or {}
    offered = set(req.get("settings") or {})
    unknown = offered - set(spec)
    if unknown:
        raise ExecutorError(
            f"settings not supported by {model['id']}: {', '.join(sorted(unknown))}",
            "Omit backend-unsupported keys (see config.yaml settings map).",
        )
    out = {}
    for key, s in spec.items():
        val = (req.get("settings") or {}).get(key, s.get("default"))
        if val is None and "default" in s and s.get("default") is None:
            out[key] = None
            continue
        if val is None:
            # key omitted entirely OR explicitly null with a real default -> default
            out[key] = s.get("default")
            continue
        if "choices" in s and val not in s["choices"]:
            raise ExecutorError(
                f"{model['id']} settings.{key}: '{val}' not allowed",
                f"choices: {', '.join(str(c) for c in s['choices'])}",
            )
        if "min" in s and val < s["min"]:
            raise ExecutorError(
                f"{model['id']} settings.{key}: {val} below min {s['min']}",
                f"Clamp to >= {s['min']}.",
            )
        if "max" in s and val > s["max"]:
            raise ExecutorError(
                f"{model['id']} settings.{key}: {val} above max {s['max']}",
                f"Clamp to <= {s['max']}.",
            )
        if "multiple_of" in s and _looks_int(val) and val % s["multiple_of"] != 0:
            raise ExecutorError(
                f"{model['id']} settings.{key}: {val} is not a multiple of {s['multiple_of']}",
                "Pick a value divisible by {mul} (e.g. {eg}).".format(
                    mul=s["multiple_of"], eg=((val // s["multiple_of"]) * s["multiple_of"])),
            )
        out[key] = val
    # cross-field rules
    w, h = out.get("width"), out.get("height")
    if w is not None and h is not None:
        rule = model.get("area_rule") or ""
        if "4300800" in rule and w * h > 4300800:
            raise ExecutorError(
                f"{model['id']}: width*height {w}x{h}={w*h} exceeds server limit 4300800 px",
                "Reduce width/height (Unsloth caps output area at 4300800 px).",
            )
        note_w = (spec.get("width") or {}).get("note", "")
        note_h = (spec.get("height") or {}).get("note", "")
        if ("must equal" in note_w or "must equal" in note_h) and w != h:
            raise ExecutorError(
                f"{model['id']}: width and height must be equal (single resolution param, got {w}x{h})",
                "Set width == height for this model.",
            )
    return out


def check_model(req: dict, cfg: dict) -> tuple[dict, dict, dict]:
    """Resolve model_id -> (model, machine, backend). Raises actionable errors."""
    mid = req.get("model_id")
    if not mid:
        raise ExecutorError("request missing model_id", "See request-schema.json.")
    model = next((m for m in cfg.get("models", []) if m.get("id") == mid), None)
    if model is None:
        known = ", ".join(m["id"] for m in cfg.get("models", []))
        raise ExecutorError(f"unknown model_id '{mid}'", f"Known ids: {known}")
    if model.get("availability") != "verified":
        raise ExecutorError(
            f"model '{mid}' is registered but NOT verified live "
            f"(availability={model.get('availability')})",
            "Re-check /api/inference/images/status (or ComfyUI object_info) to confirm "
            "weights are present before offering it. Executor does not auto-download.",
        )
    machine = cfg.get("machines", {}).get(model.get("machine"))
    backend = (machine or {}).get("backends", {}).get(model.get("backend"))
    if machine is None or backend is None:
        raise ExecutorError(
            f"model '{mid}' references unknown machine/backend "
            f"({model.get('machine')}/{model.get('backend')})",
            "Fix config.yaml machines section.",
        )
    return model, machine, backend


def resolve_output_dir(req: dict, cfg: dict) -> Path:
    d = (req.get("output") or {}).get("dir") or cfg.get("defaults", {}).get("output_dir", "~/Pictures/image-gen")
    p = Path(d).expanduser()
    try:
        p.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        raise ExecutorError(f"cannot create output dir {p}: {e}", "Pick a writable output.dir.")
    return p


def render_filename(template: str | None, ts: int, model: dict, n: int, seed: int | None) -> str:
    if not template:
        template = "{ts}_{model}_{n}.png"
    slug = model["id"].rsplit(":", 1)[-1]
    name = (template
            .replace("{ts}", str(ts))
            .replace("{model}", slug)
            .replace("{n}", str(n))
            .replace("{seed}", str(seed) if seed is not None else "rand"))
    suffix = Path(name).suffix or ".png"
    return name if name.endswith(suffix) else name + suffix


# --------------------------------------------------------------------------- #
# HTTP helpers
# --------------------------------------------------------------------------- #

def http_json(method: str, url: str, *, body: dict | None = None, headers: dict | None = None,
              timeout: float = 60, retries: int = 2, desc: str = "request") -> tuple[int, dict | str]:
    """urllib JSON call with retries on transient (5xx/conn) failures. Returns (status, json|text)."""
    last_err = None
    for attempt in range(retries + 1):
        data = json.dumps(body).encode() if body is not None else None
        hdr = {"Content-Type": "application/json"} if data else {}
        hdr.update(headers or {})
        req = urllib.request.Request(url, data=data, headers=hdr, method=method)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                raw = r.read()
                try:
                    return r.status, json.loads(raw)
                except Exception:
                    return r.status, raw.decode(errors="replace")
        except urllib.error.HTTPError as e:
            if 500 <= e.code < 600 and attempt < retries:
                time.sleep(1.5 * (attempt + 1))
                last_err = e
                continue
            raw = e.read().decode(errors="replace")
            try:
                return e.code, json.loads(raw)
            except Exception:
                return e.code, raw
        except (urllib.error.URLError, OSError, TimeoutError) as e:
            if attempt < retries:
                time.sleep(1.5 * (attempt + 1))
                last_err = e
                continue
            code = getattr(getattr(e, "reason", None), "errno", None)
            detail = getattr(e, "reason", e)
            if code == 61 or "Connection refused" in str(e):
                raise ExecutorError(
                    f"{desc} failed: nothing listening at {url}",
                    "Start the app (ComfyUI `comfy launch`, Unsloth Studio) or pick the other machine.",
                ) from e
            raise ExecutorError(
                f"{desc} failed after {retries + 1} tries: {detail}",
                "Check the engine is up and reachable, then retry.",
            ) from e
    raise ExecutorError(f"{desc} failed: {last_err}", "Retry the request.")


def non2xx(status: int, body, desc: str, machine_name: str = "") -> None:
    """Raise ExecutorError for non-2xx with an actionable message."""
    if 200 <= status < 300:
        return
    snippet = body if isinstance(body, str) else json.dumps(body)[:400]
    prefix = f" ({machine_name})" if machine_name else ""
    if status in (401, 403):
        raise ExecutorError(
            f"{desc}{prefix}: authentication failed (HTTP {status})",
            "Key rotation: re-read the agent key file; try each minted[] candidate "
            "newest-first then saved[] until one authenticates.",
        )
    if status == 404:
        raise ExecutorError(
            f"{desc}{prefix}: endpoint/route not found (HTTP 404): {snippet[:200]}",
            "Server version may not expose this path; check the config protocol notes.",
        )
    if status == 503:
        raise ExecutorError(
            f"{desc}{prefix}: engine not ready (HTTP 503): {snippet[:200]}",
            "Model not loaded yet — the executor loads it first; if this persists, "
            "check /api/inference/images/status.",
        )
    if status >= 500:
        raise ExecutorError(
            f"{desc}{prefix}: server error (HTTP {status}): {snippet[:300]}",
            "Engine-side failure — check the app logs and retry.",
        )
    raise ExecutorError(
        f"{desc}{prefix}: HTTP {status}: {snippet[:300]}",
        "The engine rejected the request payload; adjust settings.",
    )


# --------------------------------------------------------------------------- #
# Backends
# --------------------------------------------------------------------------- #

def _comfy_nodes(model: dict) -> tuple[dict, dict]:
    """Load the bare API graph for a ComfyUI model. Returns (graph, canonical params).

    param_map keys are the request-schema setting names (prompt, negative_prompt,
    width, height, steps, cfg_scale, seed, sampler, scheduler, denoise,
    unet_name, clip_name, vae_name) -> (node_id, field). Support both:
      - graph.api_graph: pre-converted JSON (node IDs discovered by class_type)
      - graph.blueprint: cached conversion in graphs/ (schema sidecar names
        translated: `text` -> prompt)
    """
    g = model.get("graph") or {}

    def scan(graph: dict) -> dict:
        params = {}
        for nid, node in graph.items():
            ct = node.get("class_type", "")
            if ct == "TextEncodeQwenImage21":
                params["prompt"] = (nid, "prompt")
                params["negative_prompt"] = (nid, "negative_prompt")
                params["resolution"] = (nid, "resolution")
            elif ct == "KSampler":
                params["seed"] = (nid, "seed")
                params["steps"] = (nid, "steps")
                params["cfg_scale"] = (nid, "cfg")
                params["sampler"] = (nid, "sampler_name")
                params["scheduler"] = (nid, "scheduler")
                params["denoise"] = (nid, "denoise")
            elif ct == "EmptySD3LatentImage":
                params["width"] = (nid, "width")
                params["height"] = (nid, "height")
            elif ct in ("UNETLoader", "DiffusionModelLoader"):
                params["unet_name"] = (nid, "unet_name")
            elif ct == "CLIPLoader":
                params["clip_name"] = (nid, "clip_name")
            elif ct == "VAELoader":
                params["vae_name"] = (nid, "vae_name")
        return params

    api_graph = g.get("api_graph")
    if api_graph:
        path = Path(api_graph).expanduser()
        if not path.exists():
            raise ExecutorError(
                f"ComfyUI api_graph missing for {model['id']}: {path}",
                "Re-export the workflow in API format or fix graph.api_graph.",
            )
        with path.open() as f:
            graph = json.load(f)
        return graph, scan(graph)

    blueprint = g.get("blueprint")
    if blueprint:
        # Pre-converted bare graph + schema sidecar (converted once at executor
        # build time; re-convert with comfy_editor_to_api.py after blueprint edits).
        bare = GRAPH_DIR / (model["id"].split(":")[-1] + ".bare.json")
        schema_path = GRAPH_DIR / (model["id"].split(":")[-1] + ".schema.json")
        if not bare.exists():
            raise ExecutorError(
                f"no cached API graph for blueprint '{blueprint}' (need {bare})",
                "Run comfy_editor_to_api.py on the blueprint with --raw --schema-out "
                "and save into graphs/, or convert a fresh copy.",
            )
        with bare.open() as f:
            graph = json.load(f)
        with schema_path.open() as f:
            schema = json.load(f)
        params = {}
        for name, pm in (schema.get("parameters") or {}).items():
            key = "prompt" if name == "text" else name
            params[key] = (pm["node_id"], pm["field"])
        # scanner fills slots the sidecar may miss (cfg/sampler/scheduler/denoise)
        params.update(scan(graph))
        return graph, params

    raise ExecutorError(
        f"model '{model['id']}' has no ComfyUI graph (need graph.api_graph or graph.blueprint)",
        "Fix config.yaml graph section.",
    )


def run_comfyui(req: dict, model: dict, backend: dict, machine: dict,
                out_dir: Path, cfg: dict) -> list[dict]:
    base = backend["base_url"].rstrip("/")
    graph, params = _comfy_nodes(model)
    graph = copy.deepcopy(graph)
    settings = validate_settings(req, model)

    def setv(graph_key: str, value) -> None:
        loc = params.get(graph_key)
        if loc and value is not None:
            nid, field = loc
            if nid in graph:
                graph[nid].setdefault("inputs", {})[field] = value

    # weights from config (blueprint loaders are empty until injected)
    w = model.get("weights") or {}
    setv("unet_name", w.get("unet"))
    setv("clip_name", w.get("clip"))
    setv("vae_name", w.get("vae"))

    setv("prompt", req.get("prompt", ""))
    setv("negative_prompt", req.get("negative_prompt"))
    w_, h_ = settings.get("width"), settings.get("height")
    if "resolution" in params and w_ is not None and h_ is not None and w_ == h_:
        setv("resolution", w_)
    else:
        setv("width", w_)
        setv("height", h_)
    setv("steps", settings.get("steps"))
    setv("cfg_scale", settings.get("cfg_scale", 1.0))
    setv("sampler", settings.get("sampler"))
    setv("scheduler", settings.get("scheduler"))
    setv("denoise", settings.get("denoise"))
    seed = settings.get("seed")
    if seed is None:
        seed = random.randint(0, 2**32 - 1)
        settings["seed"] = seed
    setv("seed", seed)

    # ComfyUI emits one image per run (schema: ComfyUI graphs here generate one)
    n_out = settings.get("n", 1)
    if n_out != 1:
        raise ExecutorError(
            f"{model['id']}: n={n_out} not supported by ComfyUI graphs here",
            "Set n=1 for ComfyUI, or use an Unsloth model for batches.",
        )

    payload = {"prompt": graph, "client_id": os.urandom(16).hex()}
    http_status, body = http_json("POST", f"{base}/prompt", body=payload,
                                  timeout=120, retries=cfg.get("defaults", {}).get("retries", 2),
                                  desc=f"ComfyUI submit ({model['id']})")
    if isinstance(body, dict) and body.get("error"):
        raise ExecutorError(
            f"ComfyUI rejected {model['id']}: {json.dumps(body['error'])[:300]}",
            "Workflow validation failed on the server; check graph deps and settings.",
        )
    non2xx(http_status, body, "ComfyUI submit", machine.get("name", ""))

    prompt_id = body.get("prompt_id") if isinstance(body, dict) else None
    if not prompt_id:
        raise ExecutorError("ComfyUI submit returned no prompt_id", "Check the server response.")
    status(f"ComfyUI {model['id']}: submitted (prompt_id={prompt_id})", force=True)

    timeout = cfg.get("defaults", {}).get("timeout_seconds", 900)
    start = time.time()
    interval = 2.0
    result = None
    while time.time() - start < timeout:
        st, hist = http_json("GET", f"{base}/history/{prompt_id}", timeout=30,
                             retries=1, desc="ComfyUI history poll")
        status(f"ComfyUI {model['id']}: waiting… {int(time.time() - start)}s elapsed")
        if st == 200 and isinstance(hist, dict):
            entry = (hist.get(prompt_id) or {})
            stt = entry.get("status") or {}
            if stt.get("status_str") == "error":
                msgs = [m.get("data", {}).get("message", "") for m in stt.get("messages", [])
                        if isinstance(m, dict) and m.get("type") == "execution_error"]
                raise ExecutorError(
                    f"ComfyUI execution failed for {model['id']}: "
                    f"{' | '.join(x for x in msgs if x) or 'unknown error'}",
                    "Check the ComfyUI browser UI for the node error trace.",
                )
            if stt.get("completed", False):
                result = entry.get("outputs", {})
                break
        time.sleep(interval)
        interval = min(interval * 1.3, 8.0)
    if result is None:
        raise ExecutorError(
            f"ComfyUI did not finish within {int(timeout)}s (prompt_id={prompt_id})",
            "Re-run with a larger defaults.timeout_seconds, or check the queue.",
        )

    # collect image refs
    files = []
    for node_id, node_out in (result or {}).items():
        for fi in (node_out.get("images") or []):
            files.append(fi)
    if not files:
        raise ExecutorError(
            f"ComfyUI completed but produced no image files for {model['id']}",
            "Check the graph's SaveImage node and output wiring.",
        )
    status(f"ComfyUI {model['id']}: done in {int(time.time() - start)}s, {len(files)} image(s)", force=True)

    ts = int(time.time())
    outputs = []
    for i, fi in enumerate(files):
        filename = fi.get("filename", "out.png")
        sub = fi.get("subfolder", "")
        typ = fi.get("type", "output")
        qs = urllib.parse.urlencode({"filename": filename, "subfolder": sub, "type": typ})
        url = f"{base}/view?{qs}"
        name = render_filename((req.get("output") or {}).get("filename_template"),
                               ts, model, i, seed)
        dest = out_dir / name
        try:
            with urllib.request.urlopen(url, timeout=600) as r:
                data = r.read()
        except Exception as e:
            raise ExecutorError(
                f"ComfyUI download of {filename} failed: {e}",
                "The file may have been pruned; regenerate.",
            ) from e
        dest.write_bytes(data)
        outputs.append({
            "path": str(dest), "seed": seed, "n": i, "width": settings.get("width"),
            "height": settings.get("height"), "steps": settings.get("steps"),
            "prompt_id": prompt_id, "bytes": len(data),
        })
    return outputs


def _unsloth_keyfile(machine: dict, backend: dict) -> list[str]:
    keyfile = (backend.get("auth") or {}).get("keyfile", "")
    ssh = machine.get("ssh_host")
    try:
        if ssh:
            r = subprocess.run(["ssh", "-o", "ConnectTimeout=8", ssh, "cat", keyfile],
                               capture_output=True, text=True, timeout=20)
            if r.returncode != 0:
                raise ExecutorError(
                    f"cannot read Unsloth keyfile on {ssh}: {r.stderr.strip()[:200]}",
                    "Check `ssh macbook` works and the agent key file exists.",
                )
            raw = r.stdout
        else:
            raw = Path(keyfile).expanduser().read_text()
    except ExecutorError:
        raise
    except OSError as e:
        raise ExecutorError(f"cannot read Unsloth keyfile {keyfile}: {e}",
                            "Check the auth.keyfile path in config.yaml.") from e
    try:
        j = json.loads(raw)
    except json.JSONDecodeError as e:
        raise ExecutorError(f"Unsloth keyfile {keyfile} is not JSON: {e}",
                            "The Unsloth Studio app rewrites this file; check it.") from e
    base = backend.get("base_url", "http://127.0.0.1:8888")
    srv = (j.get("servers") or {}).get(base, {})
    minted = srv.get("minted") or []
    saved = srv.get("saved") or []
    if not isinstance(minted, list):
        minted = []
    if not isinstance(saved, list):
        saved = []
    cands = [k for k in minted if isinstance(k, str)] + [k for k in saved if isinstance(k, str)]
    if not cands:
        raise ExecutorError(
            f"no agent API keys under servers['{base}'] in {keyfile}",
            "Unsloth Studio should have minted one on first launch.",
        )
    return cands


def _unsloth_auth_key(machine: dict, backend: dict, base: str,
                      retries: int = 2) -> str:
    """Try each key candidate until one authenticates (key rotation bug workaround).

    For ssh machines the probe must ride the curl -K- path to the REMOTE server;
    a local urllib call would hit the wrong host.
    """
    ssh = machine.get("ssh_host")
    cands = _unsloth_keyfile(machine, backend)
    last = None
    for k in cands:
        if ssh:
            cfg_txt = f'header = "Authorization: Bearer {k}"\n'
            try:
                out = _ssh_curl(ssh, [base.rstrip("/") + "/api/inference/models"],
                                cfg_txt, 15, "Unsloth auth probe")
                try:
                    json.loads(out)
                    return k
                except json.JSONDecodeError:
                    last = (k[:8], "non-JSON")
            except ExecutorError as e:
                last = (k[:8], str(e.message)[:60])
            continue
        st, body = http_json("GET", base.rstrip("/") + "/api/inference/models",
                             headers={"Authorization": f"Bearer {k}"},
                             timeout=15, retries=0, desc="Unsloth auth probe")
        if st == 200:
            return k
        last = (k[:8], st)
    raise ExecutorError(
        f"no Unsloth key authenticated (tried {len(cands)} candidates; last {last})",
        "Key rotation: read the keyfile again and retry, or restart the Unsloth app to mint a fresh key.",
    )


def _ssh_curl(ssh_host: str, args: list[str], cfg_stdin: str, timeout: int,
              desc: str) -> bytes:
    """Run curl on a remote host, auth/body riding a curl -K- config on stdin.

    ssh joins argv with spaces and the REMOTE shell re-parses it — unquoted URLs
    with `?` or `[]` trip zsh globbing ("no matches found"). Quote every token.
    """
    remote = " ".join(shlex.quote(a) for a in
                      ["curl", "-s", "-m", str(timeout), "-K-", "--"] + args)
    full = ["ssh", "-o", "ConnectTimeout=8", ssh_host, remote]
    try:
        r = subprocess.run(full, capture_output=True, input=cfg_stdin.encode(),
                           text=False, timeout=timeout + 30)
    except subprocess.TimeoutExpired:
        raise ExecutorError(f"{desc} via ssh timed out", "Increase timeout or check the remote engine.") from None
    if r.returncode != 0 or not r.stdout:
        err = r.stderr.decode(errors="replace").strip()[:300]
        raise ExecutorError(f"{desc} via ssh failed (rc={r.returncode}): {err}",
                            "Check `ssh macbook` and that Unsloth Studio is running there.")
    return r.stdout


def run_unsloth(req: dict, model: dict, backend: dict, machine: dict,
                out_dir: Path, cfg: dict) -> list[dict]:
    base = backend["base_url"].rstrip("/")
    ssh = machine.get("ssh_host")
    settings = validate_settings(req, model)
    retries = cfg.get("defaults", {}).get("retries", 2)
    timeout = cfg.get("defaults", {}).get("timeout_seconds", 900)

    key = None
    if (backend.get("auth") or {}).get("type") == "bearer":
        key = _unsloth_auth_key(machine, backend, base, retries=retries)

    def api(method: str, path: str, body: dict | None = None,
            *, t: int = 60, desc: str = "Unsloth API", pass_key: str | None = None) -> dict:
        k = pass_key if pass_key is not None else key
        if ssh:
            cfg_txt = ""
            if k:
                cfg_txt += f'header = "Authorization: Bearer {k}"\n'
            if body is not None:
                cfg_txt += 'header = "Content-Type: application/json"\n'
                cfg_txt += "data = " + json.dumps(json.dumps(body)) + "\n"
            out = _ssh_curl(ssh, [base + path], cfg_txt, t, desc)
            try:
                return json.loads(out)
            except json.JSONDecodeError:
                return {"_raw": out.decode(errors="replace")}
        st, resp = http_json(method, base + path, body=body,
                             headers={"Authorization": f"Bearer {k}"} if k else None,
                             timeout=t, retries=retries, desc=f"{desc} ({path})")
        if isinstance(resp, dict) and "_raw" in resp:
            resp = resp["_raw"]
        non2xx(st, resp, desc, machine.get("name", ""))
        return resp if isinstance(resp, dict) else {"_raw": resp}

    # ---- ensure model loaded (503 guard) ----
    st = api("GET", "/api/inference/images/status", desc="Unsloth status")
    repo = model["repo"]
    loaded = st.get("loaded") and (
        st.get("repo_id") == repo or st.get("display_repo_id") == repo.rsplit("/", 1)[-1])
    if not loaded:
        body = {"model_path": repo}
        if model.get("model_kind"):
            body["model_kind"] = model["model_kind"]
        if model.get("gguf_filename"):
            body["gguf_filename"] = model["gguf_filename"]
        status(f"Unsloth {model['id']}: loading {repo}…", force=True)
        lr = api("POST", "/api/inference/images/load", body=body, desc="Unsloth load", t=120)
        if lr.get("error") or lr.get("detail"):
            raise ExecutorError(
                f"Unsloth load rejected {repo}: {lr.get('error') or lr.get('detail')}",
                "Model may be a LFS pointer or missing weights; verify with images/status.",
            )
        # poll progress
        start = time.time()
        while time.time() - start < 1200:
            prog = api("GET", "/api/inference/images/load-progress",
                       desc="Unsloth load-progress", t=30)
            pct = prog.get("progress") if isinstance(prog, dict) else None
            if isinstance(pct, (int, float)):
                status(f"Unsloth {model['id']}: load {pct:.0%} ({int(time.time() - start)}s)")
            else:
                status(f"Unsloth {model['id']}: loading… {int(time.time() - start)}s")
            if prog.get("error"):
                raise ExecutorError(f"Unsloth load failed: {prog['error']}",
                                    "Verify the model repo id in config.yaml.")
            st2 = api("GET", "/api/inference/images/status", desc="Unsloth status", t=30)
            if st2.get("loaded") and (st2.get("repo_id") == repo or
                                      st2.get("display_repo_id") == repo.rsplit("/", 1)[-1]):
                status(f"Unsloth {model['id']}: loaded ({int(time.time() - start)}s)", force=True)
                break
            time.sleep(5)
        else:
            raise ExecutorError(f"Unsloth model {repo} did not load within 20 min",
                                "Check the Unsloth app logs / disk space.")

    # ---- generate ----
    gen_start = time.time()
    gen_body = {
        "model": repo,
        "prompt": req.get("prompt", ""),
        "n": settings.get("n", 1),
        "size": f"{settings.get('width', 1024)}x{settings.get('height', 1024)}",
    }
    if req.get("negative_prompt") is not None:
        gen_body["negative_prompt"] = req["negative_prompt"]
    if settings.get("steps") is not None:
        gen_body["steps"] = settings["steps"]
    seed = settings.get("seed")
    if seed is None:
        seed = random.randint(0, 2**32 - 1)
        settings["seed"] = seed
    gen_body["seed"] = seed
    init = req.get("settings", {}).get("init_image") if isinstance(req.get("settings"), dict) else None
    if init:
        ipath = Path(init).expanduser()
        if not ipath.exists():
            raise ExecutorError(f"init_image not found: {ipath}", "Check the path.")
        data = base64.b64encode(ipath.read_bytes()).decode()
        gen_body["image"] = f"data:image/png;base64,{data}"
        if settings.get("strength") is not None:
            gen_body["strength"] = settings["strength"]

    resp = api("POST", "/v1/images/generations", body=gen_body, t=timeout,
               desc=f"Unsloth generate ({model['id']})")
    status(f"Unsloth {model['id']}: generated in {int(time.time() - gen_start)}s", force=True)
    err = resp.get("error")
    if err:
        msg = err.get("message") if isinstance(err, dict) else err
        raise ExecutorError(
            f"Unsloth refused generation: {msg}",
            "Model may be edit-only for t2i, or still loading; check images/status.",
        )
    items = resp.get("data") or []
    if not items:
        raise ExecutorError(
            f"Unsloth returned no images for {repo}: {json.dumps(resp)[:300]}",
            "Check the model supports text2img and is actually loaded.",
        )

    ts = int(time.time())
    outputs = []
    for i, item in enumerate(items):
        name = render_filename((req.get("output") or {}).get("filename_template"),
                               ts, model, i, seed)
        dest = out_dir / name
        if item.get("b64_json"):
            img = base64.b64decode(item["b64_json"])
            dest.write_bytes(img)
        elif item.get("url"):
            if ssh:
                # signed URL is loopback-bound on the MacBook; fetch there with the
                # bearer key via curl -K- and ship the raw bytes back over ssh stdout
                cfg_txt = f'header = "Authorization: Bearer {key}"\n' if key else ""
                out = _ssh_curl(ssh, [item["url"]], cfg_txt, 120, "Unsloth image download")
                dest.write_bytes(out)
            else:
                with urllib.request.urlopen(item["url"], timeout=600) as r:
                    dest.write_bytes(r.read())
        else:
            raise ExecutorError(
                f"Unsloth item #{i} has neither b64_json nor url: {json.dumps(item)[:200]}",
                "Unexpected response shape; check the Unsloth version.",
            )
        outputs.append({
            "path": str(dest), "seed": seed, "n": i, "width": settings.get("width"),
            "height": settings.get("height"), "steps": settings.get("steps"),
            "bytes": dest.stat().st_size,
        })
    return outputs


# --------------------------------------------------------------------------- #
# Entrypoint
# --------------------------------------------------------------------------- #

def execute(req: dict, cfg: dict | None = None, out_dir_override: str | None = None,
            history_override: str | None = None) -> dict:
    """Run a request and append a history entry on success AND failure.

    Returns the result dict on success; raises ExecutorError on failure and
    KeyboardInterrupt on Ctrl-C — in both cases the run is logged first, so
    `--retry` can replay it. History writes are best-effort (never mask a
    real error).
    """
    cfg = cfg or load_config()
    hist = resolve_history_path(cfg, history_override)
    model = machine = backend = None
    start = time.time()
    try:
        if req.get("schema_version") != cfg.get("schema_version", 1):
            raise ExecutorError(
                f"schema_version mismatch: request={req.get('schema_version')} "
                f"config={cfg.get('schema_version', 1)}",
                "Regenerate the request with the current picker.",
            )
        if not isinstance(req.get("prompt"), str) or not req["prompt"].strip():
            raise ExecutorError("request prompt is empty", "Provide a positive prompt.")
        if req.get("settings") is not None and not isinstance(req["settings"], dict):
            raise ExecutorError("request settings must be an object", "See request-schema.json.")

        model, machine, backend = check_model(req, cfg)
        out_dir = Path(out_dir_override).expanduser() if out_dir_override else resolve_output_dir(req, cfg)
        bt = backend.get("type")
        if bt == "comfyui":
            outputs = run_comfyui(req, model, backend, machine, out_dir, cfg)
        elif bt == "unsloth":
            outputs = run_unsloth(req, model, backend, machine, out_dir, cfg)
        else:
            raise ExecutorError(f"unsupported backend type '{bt}'",
                                "config.yaml supports comfyui | unsloth.")
        result = {
            "status": "success",
            "model_id": model["id"],
            "machine": machine.get("id"),
            "backend": backend.get("id"),
            "outputs": outputs,
            "elapsed_s": round(time.time() - start, 1),
        }
        append_history(hist, make_history_entry(req, result, model, machine, backend))
        return result
    except ExecutorError as e:
        append_history(hist, make_history_entry(
            req,
            {"status": e.status, "error": e.message, "hint": e.hint},
            model or {"id": req.get("model_id", "unknown")}, machine or {}, backend or {},
        ))
        raise
    except KeyboardInterrupt:
        append_history(hist, make_history_entry(
            req,
            {"status": "interrupted", "error": "interrupted by user"},
            model or {"id": req.get("model_id", "unknown")}, machine or {}, backend or {},
        ))
        raise


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Run a validated image-gen request.")
    ap.add_argument("--request", help="request JSON file, or '-' for stdin "
                                      "(omit when using --retry)")
    ap.add_argument("--retry", action="store_true",
                    help="re-run the last failed generation from the history log")
    ap.add_argument("--history", help="history file (default: config defaults.history_file "
                                      "or ~/Pictures/image-gen/history.jsonl)")
    ap.add_argument("--out", help="override output dir")
    ap.add_argument("--config", help="override config.yaml path")
    ap.add_argument("--quiet", action="store_true", help="suppress stderr status lines")
    a = ap.parse_args(argv)
    global QUIET
    QUIET = a.quiet

    try:
        cfg = load_config(a.config)
        if a.retry:
            hist = resolve_history_path(cfg, a.history)
            entry = load_last_failed(hist)
            if entry is None:
                out = {"status": "error", "error": "no failed generation in history to retry",
                       "hint": f"history file: {hist}"}
                print(json.dumps(out, indent=2))
                print(f"ERROR: {out['error']}\nHINT: {out['hint']}", file=sys.stderr)
                return 1
            req = entry.get("request")
            if not isinstance(req, dict):
                out = {"status": "error", "error": "last failed history entry has no request",
                       "hint": "Inspect the history file; the entry may predate --retry support."}
                print(json.dumps(out, indent=2))
                print(f"ERROR: {out['error']}\nHINT: {out['hint']}", file=sys.stderr)
                return 1
            status(f"retrying run from {entry.get('iso', '?')}: "
                   f"{req.get('model_id')} — {entry.get('error', 'unknown error')[:120]}",
                   force=True)
        elif not a.request:
            ap.error("one of --request or --retry is required")
        else:
            req = load_request(a.request)
        result = execute(req, cfg, out_dir_override=a.out, history_override=a.history)
    except ExecutorError as e:
        out = {"status": e.status, "error": e.message, "hint": e.hint}
        print(json.dumps(out, indent=2))
        print(f"ERROR: {e.message}\nHINT: {e.hint}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        out = {"status": "interrupted", "error": "interrupted"}
        print(json.dumps(out, indent=2))
        return 130

    print(json.dumps(result, indent=2))
    if not a.quiet:
        for o in result["outputs"]:
            print(f"OK {o['path']} ({o.get('bytes', '?')} bytes)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
