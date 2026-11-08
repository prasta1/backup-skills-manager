#!/usr/bin/env python3
"""Probe every registered inference endpoint and report which are live.

Endpoints that are down are expected, not errors — the fleet is spread across a
tailnet and several runtimes are retired. Exit code is 0 as long as at least one
endpoint answers.

Usage:
    python3 discover_endpoints.py                    # human-readable table
    python3 discover_endpoints.py --json             # machine-readable
    python3 discover_endpoints.py --models           # also list every model id
    python3 discover_endpoints.py --only llama-swap-studio lm-studio
    python3 discover_endpoints.py --add http://127.0.0.1:9999   # probe an ad-hoc url
"""
import argparse
import json
import os
import ssl
import sys
import time
import urllib.error
import urllib.request

DEFAULT_REGISTRY = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "references", "endpoints.json")

# Non-LLM entries LM Studio and friends report alongside real models.
NON_LLM_HINTS = ("embed", "embedding", "rerank", "bge", "vae", "text_encoder",
                 "transformer", "whisper", "clip", "mmproj")


def resolve_api_key(entry):
    """Resolve an endpoint api_key: file:/.../x.json#/pointer, env:VAR, or literal."""
    raw = (entry or {}).get("api_key")
    if not raw:
        return None
    if raw.startswith("file:"):
        path, _, ptr = raw[5:].partition("#")
        with open(path) as f:
            node = json.load(f)
        for part in ptr.strip("/").split("/"):
            node = node[part]
        return node
    if raw.startswith("env:"):
        return os.environ.get(raw[4:])
    return raw


def probe(url, timeout=4.0, insecure=False, api_key=None):
    """GET {url}/v1/models. Returns (ok, model_ids, latency_ms, error).

    A 200 that is not a well-formed OpenAI model list counts as NOT ok — port
    8000 and 8080 are commonly squatted by unrelated dev servers.
    """
    ctx = None
    if url.startswith("https") and insecure:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

    start = time.perf_counter()
    try:
        headers = {"Accept": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        req = urllib.request.Request(f"{url}/v1/models", headers=headers)
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            latency = (time.perf_counter() - start) * 1000
            payload = json.loads(resp.read())
        if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
            return False, [], latency, "not an OpenAI /v1/models payload"
        ids = [m.get("id", "?") for m in payload["data"] if isinstance(m, dict)]
        return True, ids, latency, None
    except urllib.error.HTTPError as e:
        return False, [], (time.perf_counter() - start) * 1000, f"HTTP {e.code}"
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        reason = getattr(e, "reason", e)
        msg = str(reason)
        if "refused" in msg.lower():
            msg = "connection refused"
        elif "timed out" in msg.lower() or isinstance(e, TimeoutError):
            msg = "timed out"
        return False, [], (time.perf_counter() - start) * 1000, msg
    except (json.JSONDecodeError, ValueError) as e:
        return False, [], (time.perf_counter() - start) * 1000, f"bad JSON: {e}"


def is_llm(model_id):
    """Filter out embeddings/rerankers/VAEs that share the /v1/models list."""
    low = model_id.lower()
    return not any(h in low for h in NON_LLM_HINTS)


def main():
    ap = argparse.ArgumentParser(description="Probe local/tailnet inference endpoints")
    ap.add_argument("--registry", default=DEFAULT_REGISTRY)
    ap.add_argument("--only", nargs="+", help="Probe only these registry names")
    ap.add_argument("--add", nargs="+", default=[], help="Extra ad-hoc URLs to probe")
    ap.add_argument("--models", action="store_true", help="List model ids per endpoint")
    ap.add_argument("--all-models", action="store_true",
                    help="With --models, include embeddings/rerankers/VAEs")
    ap.add_argument("--json", action="store_true", dest="as_json")
    ap.add_argument("--timeout", type=float, default=4.0)
    args = ap.parse_args()

    with open(args.registry) as f:
        entries = json.load(f)["endpoints"]
    if args.only:
        entries = [e for e in entries if e["name"] in args.only]
    entries += [{"name": u, "url": u, "runtime": "ad-hoc", "host": "-", "notes": ""}
                for u in args.add]

    results = []
    for e in entries:
        ok, ids, ms, err = probe(e["url"], args.timeout, e.get("insecure", False),
                                   resolve_api_key(e))
        llms = [i for i in ids if is_llm(i)]
        results.append({**e, "up": ok, "latency_ms": round(ms, 1), "error": err,
                        "model_count": len(ids), "llm_count": len(llms),
                        "models": ids if args.all_models else llms})

    if args.as_json:
        print(json.dumps(results, indent=2))
        return 0 if any(r["up"] for r in results) else 1

    up = [r for r in results if r["up"]]
    print(f"\n{'ENDPOINT':<28} {'STATUS':<8} {'MODELS':>7} {'LAT':>8}  RUNTIME")
    print("-" * 92)
    for r in results:
        if r["up"]:
            status, detail = "UP", r["runtime"]
            count = f"{r['llm_count']}"
            if r["model_count"] != r["llm_count"]:
                count += f"/{r['model_count']}"
        else:
            status, detail = "down", r["error"] or ""
            count = "-"
        print(f"{r['name']:<28} {status:<8} {count:>7} {r['latency_ms']:>7.0f}ms  {detail}")

    print(f"\n{len(up)}/{len(results)} endpoints live.")
    for r in results:
        if r["up"] and r.get("notes"):
            print(f"  note [{r['name']}]: {r['notes']}")

    if args.models:
        for r in up:
            print(f"\n--- {r['name']} ({r['url']}) — {len(r['models'])} models ---")
            for m in sorted(r["models"]):
                print(f"  {m}")

    if not up:
        print("\nNothing is serving. Start llama-swap, or open LM Studio's server tab.",
              file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
