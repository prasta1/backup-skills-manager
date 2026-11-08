#!/usr/bin/env python3
"""explore_engines.py — discover what inference engines are live, report back,
then stop so the user can pick what to benchmark.

Probes a known set of endpoints (llama-swap on Studio + MacBook), lists the
models each serves, flags Qwen3.8-family models that
are benchmarking targets, and prints a short report. It never benchmarks
anything itself — it answers "what is available right now".

Usage:
    python3 scripts/explore_engines.py                 # probe defaults
    python3 scripts/explore_engines.py --endpoint http://HOST:PORT/v1   # any extra engine
    python3 scripts/explore_engines.py --json          # machine-readable report

Defaults probe every endpoint in the table below with a 2s timeout each,
so a dead host costs ~2s, not a hang. Engines that do not answer are listed
as DOWN, which is expected — most endpoints are down at any given time.
"""

import argparse
import json
import sys
import urllib.error
import urllib.request
# name -> candidate base URLs; the first that answers wins.
DEFAULT_ENDPOINTS = {
    "studio llama-swap": ("http://127.0.0.1:9292/v1", "http://100.89.133.43:9292/v1"),
    "macbook llama-swap": ("http://100.68.81.83:8999/v1",),
}



# Tokenizer map for llama-benchy: model id -> HF tokenizer repo, for models whose id
# does not itself name a tokenizer. The --tokenizer flag must still be passed explicitly;
# this only annotates the report. The two Splash-era Qwen3.8 entries that used to live
# here are gone with their weights (Nov 1 deletion) — add a mapping when a Qwen3.8-family
# model actually returns to the fleet. An empty map is correct, not a bug: without it the
# report simply omits the tokenizer hint. (This dict being absent at all crashed the script
# with NameError from commit 380055e — a Nov 2 sweep commit unrelated to this file — until
# 2026-11-05. Keep it defined even when empty.)
TOKENIZERS = {}


def probe(url: str, timeout: float = 2.0) -> dict:
    """GET /models. Returns {"ok": bool, "models": [...], "error": str}."""
    try:
        req = urllib.request.Request(url + "/models", headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode())
    except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as exc:
        return {"ok": False, "models": [], "error": str(exc)}
    except ValueError as exc:
        return {"ok": False, "models": [], "error": f"bad json: {exc}"}

    models = []
    for m in data.get("data", []):
        models.append(
            {
                "id": m.get("id", ""),
                "name": m.get("name") or m.get("description") or "",
            }
        )
    return {"ok": True, "models": models, "error": ""}


def classify_engine(endpoint_name: str, url: str) -> str:
    if "splash" in endpoint_name:
        return "splash"
    if "llama-swap" in endpoint_name:
        return "llama.cpp"
    return "unknown"


def is_qwen38_family(model_id: str) -> bool:
    return "qwen3.8" in model_id.lower()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--endpoint", action="append", help="extra endpoint URL to probe (repeatable)")
    ap.add_argument("--json", action="store_true", help="emit machine-readable JSON report")
    args = ap.parse_args()

    endpoints = dict(DEFAULT_ENDPOINTS)
    for i, ep in enumerate(args.endpoint or []):
        endpoints[f"extra-{i}"] = (ep,)

    report = {}
    for name, urls in endpoints.items():
        info = {
            "url": urls[0],
            "engine": classify_engine(name, urls[0]),
            "ok": False,
            "models": [],
            "error": "no candidate endpoint answered",
        }
        for url in urls:
            info = {"url": url, "engine": classify_engine(name, url), **probe(url)}
            if info["ok"]:
                break
        report[name] = info

    if args.json:
        print(json.dumps(report, indent=2))
        return 0

    print("Inference engine discovery report")
    print("=" * 72)
    for name, info in report.items():
        status = "UP" if info["ok"] else "DOWN"
        print(f"\n[{status}] {name}  ({info['engine']})  {info['url']}")
        if not info["ok"]:
            print(f"      error: {info['error']}")
            continue
        q38 = [m for m in info["models"] if is_qwen38_family(m["id"])]
        for m in info["models"]:
            marker = " <-- Qwen3.8 family" if is_qwen38_family(m["id"]) else ""
            tok = TOKENIZERS.get(m["id"], "")
            print(f"      {m['id']:<45}{marker}")
            if tok and marker:
                print(f"      {'':<45}  tokenizer: {tok}")
        if q38:
            print(f"      -> {len(q38)} Qwen3.8-family model(s) benchmarkable here")
        else:
            print("      -> no Qwen3.8-family models")

    print("\n" + "=" * 72)
    print("Next: tell the agent which model(s)/endpoint(s) to benchmark,")
    print("or accept the default (Qwen3.8-family models across UPs).")
    return 0


if __name__ == "__main__":
    sys.exit(main())