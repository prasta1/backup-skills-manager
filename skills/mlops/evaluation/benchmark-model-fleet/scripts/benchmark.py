#!/usr/bin/env python3
"""Unified model fleet benchmark — coding speed, vision, quality scoring.

Invokes the llama-swap API at localhost:9292. For each model:
  - 1 warmup + 3 timed runs per prompt
  - median tok/s
  - quality score (0-1) via deterministic pattern matchers

Usage:
    python3 benchmark.py --prompts-file prompts.py \
      --results-dir ~/.hermes/benchmark_results \
      --endpoint http://127.0.0.1:9292 \
      --models ms-qwen3-coder-30b ms-devstral-24b

    python3 benchmark.py --vision \
      --image-path test_image.png \
      --models ms-qwen3-vl-8b ms-glm-4.6-vision \
      --endpoint http://127.0.0.1:9292

For thinking models: pass --enable-thinking=false and --max-tokens=512 to avoid
reasoning_content consuming output budget without improving quality.
For vision: uses base64 data URI from --image-path (llama-swap mmproj does not
fetch URLs).
"""
import json
import time
import urllib.request
import urllib.error
import csv
import os
import base64
import argparse
import datetime
import mimetypes
import ssl


REGISTRY = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "references", "endpoints.json")


def resolve_endpoint(value):
    """Accept a registry name ('llama-swap-studio') or a raw URL. Returns (url, entry)."""
    if value.startswith("http://") or value.startswith("https://"):
        return value.rstrip("/"), {}
    try:
        with open(REGISTRY) as f:
            entries = json.load(f)["endpoints"]
    except (OSError, ValueError) as e:
        raise SystemExit(f"--endpoint '{value}' is not a URL and the registry is unreadable: {e}")
    for e in entries:
        if e["name"] == value:
            return e["url"].rstrip("/"), e
    names = ", ".join(e["name"] for e in entries)
    raise SystemExit(f"Unknown endpoint '{value}'. Known names: {names}\n"
                     f"Or pass a full URL. Run discover_endpoints.py to see what is live.")


def resolve_api_key(entry):
    """Resolve an endpoint's optional api_key field to a string, or None.

    Accepted forms (keeps secrets out of the git-tracked registry):
      file:/path/to.json#/json/pointer   read from a JSON file at a pointer
      env:VARNAME                        read from an environment variable
      anything else                      used literally
    """
    raw = (entry or {}).get("api_key")
    if not raw:
        return None
    if raw.startswith("file:"):
        path, _, pointer = raw[5:].partition("#")
        with open(path) as f:
            node = json.load(f)
        for part in pointer.strip("/").split("/"):
            node = node[part]
        return node
    if raw.startswith("env:"):
        return os.environ.get(raw[4:])
    return raw


def _auth_headers(api_key):
    if api_key:
        return {"Authorization": f"Bearer {api_key}"}
    return {}


def list_models(endpoint, insecure=False, api_key=None):
    """Return the model ids an endpoint reports, or [] if it is unreachable."""
    ctx = None
    if endpoint.startswith("https") and insecure:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
    try:
        req = urllib.request.Request(f"{endpoint}/v1/models",
                                     headers=_auth_headers(api_key))
        with urllib.request.urlopen(req, timeout=5, context=ctx) as r:
            return [m["id"] for m in json.loads(r.read()).get("data", [])]
    except Exception:
        return []


def chat_completion(endpoint, model, prompt, max_tokens=512,
                    enable_thinking=None, image_data_uri=None, insecure=False,
                    api_key=None):
    """Hit an OpenAI-compatible /v1/chat/completions. Returns (tok_s, elapsed, pt, ct, text, error)."""
    if image_data_uri:
        messages = [{"role": "user", "content": [
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": image_data_uri}},
        ]}]
    else:
        messages = [{"role": "user", "content": prompt}]

    body = {"model": model, "messages": messages,
            "max_tokens": max_tokens, "temperature": 0.0}
    if enable_thinking is not None:
        body["enable_thinking"] = enable_thinking

    headers = {"Content-Type": "application/json"}
    headers.update(_auth_headers(api_key))
    request = urllib.request.Request(
        f"{endpoint}/v1/chat/completions",
        data=json.dumps(body).encode(),
        headers=headers,
    )

    ctx = None
    if endpoint.startswith("https") and insecure:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

    for attempt in range(1, 31):
        start = time.perf_counter()
        try:
            with urllib.request.urlopen(request, timeout=300, context=ctx) as resp:
                data = json.loads(resp.read())
            elapsed = time.perf_counter() - start
            msg = data["choices"][0]["message"]
            text = msg.get("content") or msg.get("reasoning_content", "")
            usage = data.get("usage", {})
            ct = usage.get("completion_tokens", 0)
            pt = usage.get("prompt_tokens", 0)
            tok_s = ct / elapsed if elapsed > 0 and ct > 0 else 0.0
            return tok_s, elapsed, pt, ct, text, None
        except urllib.error.HTTPError as e:
            if e.code in (503, 502, 504) and attempt < 30:
                time.sleep(5)
                continue
            return 0, time.perf_counter() - start, 0, 0, "", f"HTTP {e.code}: {e.reason}"
        except (urllib.error.URLError, Exception) as e:
            if "timed out" in str(e).lower() and attempt < 30:
                time.sleep(5)
                continue
            return 0, 0, 0, 0, "", str(e)
    return 0, 0, 0, 0, "", "max retries exceeded"


def load_image_as_uri(path):
    """Read a PNG/JPEG and return a data URI for llama-swap mmproj."""
    with open(path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    mime = mimetypes.guess_type(path)[0] or "image/png"
    return f"data:{mime};base64,{b64}"


def median(values):
    vals = [v for v in values if v > 0]
    if not vals:
        return 0.0
    vals = sorted(vals)
    return vals[len(vals) // 2]


def parse_prompts_file(path):
    """Load PROMPTS and SCORERS from a prompts.py file via import."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("prompts_mod", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.PROMPTS, mod.SCORERS


def run_single_model(endpoint, model, prompts, scorers, max_tokens, enable_thinking,
                     image_uri, results_dir, prefix, insecure=False, api_key=None,
                     runs=3):
    """Benchmark one model across all prompts. Returns list of CSV row dicts.

    `runs` is the number of TIMED runs per prompt (default 3). Fewer runs is
    faster but noisier: a 3-run median over 4 prompts has already shown 7x
    spread between identical calls on the same model, so 1 run is a liveness
    check, not a speed measurement.
    """
    results = []
    # Microseconds, not seconds. Two sweeps launched together (a two-machine
    # fleet run, say) start their first model in the same second, so a
    # second-resolution name collides and the slower process silently
    # OVERWRITES the faster one's CSV. That cost a full 4-prompt coding result:
    # ms-devstral-24b's rows existed only in the log. Every other model was
    # unaffected because model start times drift apart within a few seconds.
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")

    for pname, pprompt in prompts:
        print(f"  [{model}] {pname}: warmup...", flush=True)
        wt, we, wp, wc, wtxt, werr = chat_completion(
            endpoint, model, pprompt, max_tokens, enable_thinking, image_uri, insecure, api_key)

        if werr:
            print(f"    WARMUP ERROR — {werr}", flush=True)
            results.append({
                "model": model, "endpoint": endpoint, "family": prefix, "prompt_name": pname,
                "warmup_tok_s": 0, "tok_s_1": 0, "tok_s_2": 0, "tok_s_3": 0,
                "median_tok_s": 0, "quality_score": 0.0, "quality_chars": 0,
                "prompt_tokens": wp, "completion_tokens": wc,
                "elapsed_sec": round(we, 3), "error": f"warmup: {werr}",
            })
            continue

        qscore = scorers[pname](wtxt)[0] if scorers and pname in scorers else 0.8
        print(f"    warmup ok ({wt:.1f} tok/s, {wc} toks, quality={qscore:.2f})", flush=True)

        speeds = []
        last_pt, last_ct, last_e = wp, wc, we
        for i in range(1, runs + 1):
            t, e, pt, ct, txt, err = chat_completion(
                endpoint, model, pprompt, max_tokens, enable_thinking, image_uri, insecure, api_key)
            if err:
                print(f"    run {i} ERROR — {err}", flush=True)
                speeds.append(0)
                results.append({
                    "model": model, "endpoint": endpoint, "family": prefix, "prompt_name": pname,
                    "warmup_tok_s": round(wt, 1),
                    "tok_s_1": 0, "tok_s_2": 0, "tok_s_3": 0,
                    "median_tok_s": 0, "quality_score": round(qscore, 2), "quality_chars": len(txt),
                    "prompt_tokens": pt, "completion_tokens": ct,
                    "elapsed_sec": round(e, 3), "error": f"run{i}: {err}",
                })
                break
            print(f"    run {i} — {t:.1f} tok/s ({ct} toks in {e:.1f}s)", flush=True)
            speeds.append(t)
            last_pt, last_ct, last_e = pt, ct, e
        else:
            med = median(speeds)
            # The CSV schema is fixed at tok_s_1..3 because downstream readers
            # (build_model_config, generate_final_report) index those columns by
            # name. Keep the header stable and pad unused slots rather than
            # emitting a ragged row that breaks DictReader consumers.
            slots = [round(s, 1) for s in speeds] + [0.0] * (3 - len(speeds))
            results.append({
                "model": model, "endpoint": endpoint, "family": prefix, "prompt_name": pname,
                "warmup_tok_s": round(wt, 1),
                "tok_s_1": slots[0], "tok_s_2": slots[1], "tok_s_3": slots[2],
                "median_tok_s": round(med, 1), "quality_score": round(qscore, 2), "quality_chars": len(wtxt),
                "prompt_tokens": last_pt, "completion_tokens": last_ct,
                "elapsed_sec": round(last_e, 3), "error": None,
            })

    # Write CSV
    os.makedirs(results_dir, exist_ok=True)
    csv_path = os.path.join(results_dir, f"{prefix}_{timestamp}.csv")
    if results:
        keys = list(results[0].keys())
        with open(csv_path, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=keys)
            w.writeheader()
            w.writerows(results)
    print(f"\n  Results → {csv_path}", flush=True)
    return results


def unload_model(endpoint, model, entry, api_key):
    """Unload a model from its runtime after benchmarking (frees VRAM/RAM).

    Uses the endpoint entry's optional 'unload' spec from endpoints.json:
      {"method": "POST", "path": "/api/models/unload/{model}", "body": null}
    '{model}' is substituted in both path and body. Non-fatal on failure.
    """
    spec = entry.get("unload")
    if not spec:
        return
    path = spec.get("path", "").replace("{model}", model)
    method = spec.get("method", "POST")
    body = spec.get("body")
    if body:
        body = body.replace("{model}", model)
    url = endpoint.rstrip("/") + path
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    data = json.dumps(body).encode() if body else None
    try:
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        with urllib.request.urlopen(req, timeout=30) as resp:
            resp.read()
        print(f"  unloaded {model}", flush=True)
    except Exception as e:
        print(f"  WARNING: could not unload {model}: {e}", flush=True)

def main():
    parser = argparse.ArgumentParser(description="Model fleet benchmark tool")
    parser.add_argument("--endpoint", default="llama-swap-studio",
                        help="Registry name (see references/endpoints.json) or a full URL")
    parser.add_argument("--models", nargs="+", help="Model ids to benchmark")
    parser.add_argument("--all-models", action="store_true",
                        help="Benchmark every LLM the endpoint reports (skips embeddings/rerankers/VAEs)")
    parser.add_argument("--insecure", action="store_true",
                        help="Skip TLS verification (tailnet endpoints use self-signed certs)")
    parser.add_argument("--prompts-file", default=None,
                        help="Python file with PROMPTS and SCORERS")
    parser.add_argument("--vision", action="store_true", help="Use vision prompts + image input")
    parser.add_argument("--image-path", default=None, help="Path to test image for vision")
    parser.add_argument("--results-dir", default=os.path.expanduser("~/.hermes/benchmark_results"))
    parser.add_argument("--max-tokens", type=int, default=512)
    parser.add_argument("--enable-thinking", type=lambda x: x.lower() != "false",
                        default=None, help="Set enable_thinking (true/false)")
    parser.add_argument("--no-unload", action="store_true",
                        help="Keep models loaded after benchmarking (default: unload each model when done)")
    parser.add_argument("--runs", type=int, default=3,
                        help="Timed runs per prompt (default 3). 1 is a liveness "
                             "check, not a speed measurement — per-run variance "
                             "on this hardware has been observed at 7x")
    parser.add_argument("--limit-prompts", type=int, default=0,
                        help="Use only the first N prompts (0 = all). A cheap "
                             "way to shorten a smoke test")
    args = parser.parse_args()

    # Resolve registry name -> URL, and inherit the entry's insecure/prefix hints
    endpoint, entry = resolve_endpoint(args.endpoint)
    insecure = args.insecure or entry.get("insecure", False)
    label = entry.get("name", endpoint)
    api_key = resolve_api_key(entry)

    # Preflight: fail in seconds on a dead endpoint rather than 30 retries per call
    available = list_models(endpoint, insecure, api_key)
    if not available:
        raise SystemExit(
            f"{label} ({endpoint}) is not answering /v1/models.\n"
            f"Run: python3 {os.path.join(os.path.dirname(os.path.abspath(__file__)), 'discover_endpoints.py')}")
    print(f"{label} -> {endpoint} ({len(available)} models reported)", flush=True)

    non_llm = ("embed", "rerank", "bge", "vae", "text_encoder", "transformer", "whisper", "clip", "mmproj")
    if args.all_models:
        models = [m for m in available if not any(h in m.lower() for h in non_llm)]
        print(f"--all-models: benchmarking {len(models)} of {len(available)}", flush=True)
    elif args.models:
        models = args.models
    else:
        raise SystemExit("Pass --models <id> ... or --all-models.")

    # Skip ids the endpoint does not serve — a stale id hard-404s and burns the retry budget
    missing = [m for m in models if m not in available]
    if missing:
        print(f"WARNING: not served by {label}, skipping: {', '.join(missing)}", flush=True)
        models = [m for m in models if m in available]
    if not models:
        raise SystemExit(f"None of the requested models are served by {label}.")

    # Load prompts
    if args.prompts_file:
        prompts, scorers = parse_prompts_file(args.prompts_file)
    else:
        import sys
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from prompts import CODING_PROMPTS, SCORERS, VISION_PROMPTS
        prompts = VISION_PROMPTS if args.vision else CODING_PROMPTS
        # Vision used to pass scorers=None here, so every model took the 0.8
        # unscored default and the only signal was quality_chars — a character
        # count, which rewards padding and inventing detail. The grounded family
        # scores against verified facts in references/vision_ground_truth.json
        # and subtracts for hallucinating absent objects. Use it by default, and
        # use it with the image it was written for: a scorer verified against one
        # picture is meaningless on another.
        if args.vision:
            # NOT `from prompts import vision_grounded`: scripts/prompts.py
            # shadows the prompts/ DIRECTORY of the same name, so that import
            # resolves to the module file and fails with ImportError. Load the
            # family by path instead, the same way parse_prompts_file does.
            grounded = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    "..", "prompts", "vision_grounded.py")
            prompts, scorers = parse_prompts_file(grounded)
            expected = json.load(open(os.path.join(
                os.path.dirname(os.path.abspath(__file__)), "..", "references",
                "vision_ground_truth.json")))["image"]
            if args.image_path and os.path.basename(args.image_path) != expected:
                print(f"WARNING: rubric expects {expected}, you passed "
                      f"{os.path.basename(args.image_path)}. Scores are only "
                      f"meaningful if the image matches the ground truth.",
                      flush=True)
        else:
            scorers = SCORERS

    # Load image if vision mode
    image_uri = load_image_as_uri(args.image_path) if (args.vision and args.image_path) else None
    if args.limit_prompts and args.limit_prompts < len(prompts):
        dropped = len(prompts) - args.limit_prompts
        prompts = prompts[:args.limit_prompts]
        print(f"NOTE: --limit-prompts {args.limit_prompts} — dropped {dropped} "
              f"prompt(s). This is a smoke test, not a comparable score.", flush=True)
    # Name the CSV after the family, so families do not collide in one results dir
    # (build_model_config.py globs coding_bench_*; mixing families would average
    # unrelated rubrics into one meaningless quality number).
    if args.vision:
        prefix = "vision_bench"
    elif args.prompts_file:
        prefix = os.path.splitext(os.path.basename(args.prompts_file))[0] + "_bench"
    else:
        prefix = "coding_bench"

    all_results = []
    for model in models:
        print(f"\n=== {model} ===", flush=True)
        r = run_single_model(
            endpoint, model, prompts, scorers,
            args.max_tokens, args.enable_thinking, image_uri,
            args.results_dir, prefix, insecure, api_key, runs=args.runs
        )
        all_results.extend(r)
        if not args.no_unload:
            unload_model(endpoint, model, entry, api_key)

    # Print summary
    print(f"\n{'='*80}")
    if args.vision:
        print(f"{'Model':<32} {'Avg tok/s':>10} {'Avg chars':>10}")
    else:
        print(f"{'Model':<32} {'Avg tok/s':>10} {'Avg qual':>10}")
    print("-" * 80)
    by_model = {}
    for r in all_results:
        by_model.setdefault(r["model"], []).append(r)
    for m, rows in by_model.items():
        speeds = [r["median_tok_s"] for r in rows if r["median_tok_s"] > 0]
        avg_s = sum(speeds) / len(speeds) if speeds else 0.0
        if args.vision:
            chars = [r["quality_chars"] for r in rows]
            avg_c = sum(chars) / len(chars) if chars else 0
            print(f"{m:<32} {avg_s:>10.1f} {avg_c:>10.0f}")
        else:
            quals = [r["quality_score"] for r in rows]
            avg_q = sum(quals) / len(quals) if quals else 0.0
            print(f"{m:<32} {avg_s:>10.1f} {avg_q:>10.2f}")


if __name__ == "__main__":
    main()
