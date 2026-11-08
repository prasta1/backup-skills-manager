#!/usr/bin/env python3
"""
Interactive front-end for llama-benchy.

Answers "what are you actually trying to measure?" BEFORE spending minutes of
inference time, because the answer determines the flags. A two-model question
should not become a twenty-model afternoon, and a decode-speed question should
not accidentally become a 32K depth sweep.

llama-benchy itself benchmarks exactly one model per invocation. This wrapper
loops it, one model at a time, sequentially — never concurrently — because
llama-swap serializes per model anyway and overlapping loads corrupt the
numbers.

Mirrors the interview structure of benchmark-model-fleet/scripts/run_interactive.py
on purpose: same terminal helpers, same confirm-before-run discipline, same
--dry-run / --non-interactive escape hatches. One house style for "ask first,
then spend time".

Usage:
    python3 scripts/benchy_interactive.py
    python3 scripts/benchy_interactive.py --dry-run
    python3 scripts/benchy_interactive.py --non-interactive --profile p.json
    python3 scripts/benchy_interactive.py --models ms-kat-coder-v2.5 --preset depth
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_BASE_URL = os.environ.get("BENCHY_BASE_URL", "http://127.0.0.1:9292/v1")
DEFAULT_OUT_DIR = os.environ.get("BENCHY_OUT_DIR", "/Users/macstudio/.hermes/benchy")
CATALOG = os.path.expanduser(
    "~/Library/Mobile Documents/com~apple~CloudDocs/Hermes/infra/fleet-catalog/"
    "catalog.json"
)

# --------------------------------------------------------------------------
# Tokenizer map — keep in sync with references/tokenizers.md and benchy.sh.
# (value, source) where source is verified | substitute | unresolved | n/a-*
# --------------------------------------------------------------------------
TOKENIZERS = {
    "ms-devstral-24b": ("mistralai/Devstral-Small-2-24B-Instruct-2512", "verified"),
    "ms-gemma-4-26b-moe": ("google/gemma-4-26B-A4B-it", "verified"),
    "ms-gemma-4-12b": ("google/gemma-4-12B-it", "verified"),
    "ms-gemma-4-e4b": ("google/gemma-4-E4B-it", "verified"),
    "ms-glm-4.6-vision": ("zai-org/GLM-4.6V-Flash", "verified"),
    "ms-kat-coder-v2.5": ("Kwaipilot/KAT-Coder-V2.5-Dev", "verified"),
    "ms-qwen3.6-35b-a3b": ("Qwen/Qwen3.6-35B-A3B", "verified"),
    "ms-qwen3-coder-30b": ("Qwen/Qwen3-Coder-30B-A3B-Instruct", "verified"),
    "ms-qwen3-vl-8b": ("Qwen/Qwen3-VL-8B-Instruct", "verified"),
    "ms-gpt-oss-20b": ("openai/gpt-oss-20b", "verified"),
    "ms-granite-4.2-3b": ("ibm-granite/granite-4.2-3b", "verified"),
    "ms-granite-4.2-8b": ("ibm-granite/granite-4.2-8b", "verified"),
    "ms-ministral-3-3b": ("mistralai/Ministral-3-3B-Instruct-2512", "verified"),
    "ms-qwen3.5-4b-mtp": ("Qwen/Qwen3.5-4B", "substitute"),
    "ms-qwopus3.8-27b-flash": ("Qwen/Qwen3.8-27B", "substitute"),
    "ms-nuextract3": ("Qwen/Qwen3.5-4B", "substitute"),
    "ms-muse-glimmer-30b": (None, "unresolved"),
}

# Measurement goals. Each is a complete flag set — picking a goal IS choosing
# the shape, which is the whole point of asking first.
PRESETS = {
    "quick": {
        "label": "Baseline speed — prefill + decode, no context",
        "detail": "pp 2048, tg 128, depth 0. The 'how fast is it' question.",
        "flags": ["--pp", "2048", "--tg", "128", "--depth", "0"],
    },
    "depth": {
        "label": "Context degradation — does it fall off at depth?",
        "detail": "pp 2048, tg 64 at depth 0/8K/16K/32K. The most useful axis.",
        "flags": ["--pp", "2048", "--tg", "64",
                  "--depth", "0", "8192", "16384", "32768"],
    },
    "cache": {
        "label": "Prefix caching — is llama-swap reusing the prefix?",
        "detail": "Two-step: load context cold, then re-run against it.",
        "flags": ["--pp", "2048", "--tg", "64",
                  "--depth", "0", "8192", "16384",
                  "--enable-prefix-caching"],
    },
    "load": {
        "label": "Concurrency — how does it behave under parallel load?",
        "detail": "Note: llama-swap serializes, so this measures the proxy.",
        "flags": ["--pp", "2048", "--tg", "64", "--concurrency", "1", "2", "4"],
    },
    "smoke": {
        "label": "Smoke test — is it alive at all?",
        "detail": "pp 256, tg 32, 1 run, no warmup. Seconds per model.",
        "flags": ["--pp", "256", "--tg", "32", "--runs", "1", "--warmup-runs", "0"],
    },
    "custom": {
        "label": "Custom — I'll type the shape myself",
        "detail": "Set --pp / --tg / --depth by hand below.",
        "flags": [],
    },
}

CUSTOM_FIELDS = [
    ("pp", "2048", "prompt-processing token counts (space separated)"),
    ("tg", "128", "generation token counts (space separated)"),
    ("depth", "0", "context depths (space separated)"),
]


# --------------------------------------------------------------------------
# terminal helpers (same shape as run_interactive.py)
# --------------------------------------------------------------------------
def c(text, code):
    if not sys.stdout.isatty() or os.environ.get("NO_COLOR"):
        return text
    return f"\033[{code}m{text}\033[0m"


def bold(t): return c(t, "1")
def dim(t): return c(t, "2")
def hi(t): return c(t, "36")
def warn(t): return c(t, "33")
def bad(t): return c(t, "31")
def good(t): return c(t, "32")


def header(n, total, title):
    print()
    print(bold(f"[{n}/{total}] {title}"))
    print(dim("─" * 62))


def ask(prompt, default=None, allow_blank=True):
    suffix = f" {dim(f'[{default}]')}" if default is not None else ""
    while True:
        try:
            raw = input(f"  {prompt}{suffix}: ").strip()
        except EOFError:
            print()
            raise SystemExit(1)
        if raw:
            return raw
        if default is not None and not allow_blank:
            print(warn("    this one is required"))
            continue
        return default if default is not None else ""


def ask_choice(prompt, options, default_idx=0):
    for i, (val, label) in enumerate(options, 1):
        mark = bold(f"{i}.") if i - 1 == default_idx else f"{i}."
        print(f"    {mark} {label}")
    while True:
        raw = ask(prompt, str(default_idx + 1))
        if raw.isdigit() and 1 <= int(raw) <= len(options):
            return options[int(raw) - 1][0]
        for val, _ in options:
            if raw == val:
                return val
        print(warn(f"    pick 1-{len(options)}"))


def ask_yesno(prompt, default=True):
    return ask(prompt, "y" if default else "n").lower().startswith("y")


def ask_multiselect(prompt, options, preselected=()):
    print(dim("    (blank = none, 'all' = every one)"))
    for i, (val, label) in enumerate(options, 1):
        mark = "*" if val in preselected else " "
        print(f"    {i:>2}. [{mark}] {label}")
    while True:
        try:
            raw = ask(prompt, "")
        except SystemExit:
            raise
        if not raw:
            return []
        if raw.lower() in ("all", "*"):
            return [v for v, _ in options]
        picked, bad_tokens = [], []
        for tok in raw.replace(",", " ").split():
            if tok.isdigit() and 1 <= int(tok) <= len(options):
                picked.append(options[int(tok) - 1][0])
            elif any(tok == v for v, _ in options):
                picked.append(tok)
            else:
                bad_tokens.append(tok)
        if bad_tokens:
            print(warn(f"    ignored: {', '.join(bad_tokens)}"))
            continue
        return [v for v, _ in options if v in picked]


# --------------------------------------------------------------------------
# fleet introspection
# --------------------------------------------------------------------------
def models_at(url):
    """GET {base_url}/models. Returns [] on failure — a dead endpoint is normal."""
    import urllib.request
    try:
        with urllib.request.urlopen(f"{url.rstrip('/')}/models", timeout=5) as r:
            return [m["id"] for m in json.loads(r.read()).get("data", [])]
    except Exception:
        return []


def load_catalog():
    """Optional enrichment: size, capability, ctx, and broken-symlink status."""
    if not os.path.exists(CATALOG):
        return {}
    try:
        data = json.load(open(CATALOG))
    except (OSError, json.JSONDecodeError):
        return {}
    return {m["id"]: m for m in data.get("models", [])}


def is_chatty(name):
    """Embeddings/rerankers have no /chat/completions. Benchmarking one is a
    guaranteed failure that still costs a model load."""
    n = name.lower()
    return not any(k in n for k in ("bge", "rerank", "e5-", "gte-"))


def describe(mid, cat):
    m = cat.get(mid)
    if not m:
        return mid
    bits = []
    caps = m.get("capabilities") or []
    if caps:
        bits.append("+".join(caps))
    size = m.get("gguf_size_gb")
    bits.append(f"{size} GB" if size else "MISSING")
    if m.get("params_total_b"):
        bits.append(f"{m['params_total_b']:g}B")
    if m.get("vision"):
        bits.append("vision")
    if m.get("spec_type") and "mtp" in m["spec_type"]:
        bits.append("mtp")
    return f"{mid:<28} {'  '.join(bits)}"


def estimate_minutes(preset, n_models, runs, isolated):
    """Rough wall-clock in minutes. Dominated by model loads, not by shapes.

    Measured on this Studio: granite-4.2-3b warm, pp256/tg32, 1 run = 2.3s.
    A cold load of a small model is ~30-60s; 20GB+ models run 60-180s.

    Every model in the list needs its OWN load unless it is already resident,
    and the interview never checks residency — llama-swap's ttl is 900s, so a
    model touched within the last 15 min may well be warm. Budget a full load
    for every model regardless. Overestimating costs a few minutes of
    waiting; underestimating costs an hour of "is it stuck?".
    """
    shapes = {"smoke": 1, "quick": 1, "depth": 4, "cache": 7,
              "load": 3, "custom": 4}.get(preset, 1)

    # per-shape cost: prefill+decode is ~0.05-0.15 min per run at pp2048/tg128,
    # more at depth because each depth level is a fresh 8-32K prefill.
    per_shape = 0.2 * runs * shapes
    if preset in ("depth", "cache"):
        per_shape = 0.6 * runs * shapes
    if preset == "custom":
        per_shape = 0.5 * runs * shapes

    load = 1.5 * n_models          # conservative cold-load allowance
    total = load + per_shape * n_models
    if not isolated:
        total *= 1.3               # contention makes everything slower
    return max(1, round(total))


# --------------------------------------------------------------------------
# the interview
# --------------------------------------------------------------------------
def interview(base_url):
    cfg = {"base_url": base_url, "runs": 3, "warmup_runs": 1}
    total = 5

    # --- 1. what are we measuring -----------------------------------------
    header(1, total, "What are you trying to find out?")
    print(dim("    this picks the flags — the fastest and slowest options differ by 100x"))
    opts = [(k, v["label"]) for k, v in PRESETS.items()]
    cfg["preset"] = ask_choice("goal", opts, 0)
    p = PRESETS[cfg["preset"]]
    print(dim(f"    {p['detail']}"))

    if cfg["preset"] == "custom":
        for key, dflt, helptext in CUSTOM_FIELDS:
            val = ask(f"{key} — {helptext}", dflt)
            cfg[key] = val.split()
    else:
        cfg["flags"] = list(p["flags"])

    # --- 2. which models ---------------------------------------------------
    header(2, total, "Which models?")
    served = models_at(base_url)
    if not served:
        print(bad(f"    {base_url} is not answering /v1/models"))
        print(dim("    start llama-swap, or pass --base-url"))
        raise SystemExit(1)

    cat = load_catalog()
    chatty = [m for m in served if is_chatty(m)]
    skipped = [m for m in served if not is_chatty(m)]
    print(f"    {len(chatty)} benchmarkable at this endpoint")
    if skipped:
        print(dim(f"    skipped (no chat endpoint): {', '.join(skipped)}"))

    # Surface config/disk problems BEFORE they waste a model load each.
    broken = [m for m in chatty if m in cat and not cat[m].get("gguf_exists")]
    if broken:
        print()
        print(bad(f"    {len(broken)} of these have a missing or broken GGUF on disk:"))
        for m in broken:
            print(bad(f"      {m}  ({cat[m].get('gguf_path')})"))
        print(dim("    llama-swap will fail to load them. Re-download or drop them first."))
        chatty = [m for m in chatty if m not in broken]
        if not chatty:
            raise SystemExit(1)

    notok = [m for m in chatty if TOKENIZERS.get(m, (None,))[1] == "unresolved"]
    if notok:
        print(warn(f"    no verified tokenizer for: {', '.join(notok)}"))
        print(dim("    these will silently fall back to gpt2 unless you pass --tokenizer"))

    if not cat:
        print(dim("    (no catalog.json — sizes and capabilities unavailable)"))

    if len(chatty) == 1:
        cfg["models"] = chatty
        print(dim(f"    only one: {chatty[0]}"))
    else:
        print()
        for m in chatty:
            print(f"      {describe(m, cat)}")
        print()
        quick = [
            ("all", f"every one ({len(chatty)}) — slowest, minutes per model"),
            ("chat", f"chat-capable only — same as above, {len(chatty)}"),
        ]
        vision = [m for m in chatty if cat.get(m, {}).get("vision")]
        if vision and len(vision) < len(chatty):
            quick.insert(0, ("vision", f"the {len(vision)} with an mmproj (vision-capable)"))
        code = [m for m in chatty if "code" in (cat.get(m, {}).get("capabilities") or [])]
        if code and len(code) < len(chatty):
            quick.insert(0, ("code", f"the {len(code)} code models"))
        quick.append(("pick", "I'll choose individually"))
        sel = ask_choice("shortcut", quick, 0)
        if sel == "all" or sel == "chat":
            cfg["models"] = chatty
        elif sel == "vision":
            cfg["models"] = vision
        elif sel == "code":
            cfg["models"] = code
        else:
            cfg["models"] = ask_multiselect(
                "models (numbers, names, or 'all')",
                [(m, describe(m, cat)) for m in chatty],
            )
            if not cfg["models"]:
                print(warn("    nothing selected"))
                raise SystemExit(1)

    # --- 3. rigor ----------------------------------------------------------
    header(3, total, "How many runs per shape?")
    print(dim("    more runs = tighter error bars, linearly more time"))
    cfg["runs"] = int(ask_choice("runs", [
        ("1", "1 run — smoke test, no error bars"),
        ("3", "3 runs — the default, usable stddev"),
        ("5", "5 runs — for a decision you will act on"),
    ], 1))
    cfg["warmup_runs"] = 0 if cfg["runs"] == 1 else 1

    # --- 4. isolation ------------------------------------------------------
    header(4, total, "Is the box otherwise quiet?")
    print(dim("    a second loaded model (LM Studio, another llama-swap id) skews decode t/s"))
    print(dim("    this only affects accuracy of the numbers, not how long the run takes"))
    cfg["isolated"] = ask_yesno("nothing else is holding weights right now?", True)
    if not cfg["isolated"]:
        print(warn("    numbers will read as 'under contention', not 'this model's speed'"))

    # --- 5. confirm --------------------------------------------------------
    header(5, total, "Plan")
    est = estimate_minutes(cfg["preset"], len(cfg["models"]), cfg["runs"],
                           cfg["isolated"])
    flags = cfg.get("flags") or (
        sum(([f"--{k}"] + cfg[k] for k, _, _ in CUSTOM_FIELDS), []))
    out_dir = os.path.join(
        DEFAULT_OUT_DIR, datetime.datetime.now().strftime("run-%Y%m%d-%H%M%S"))
    cfg["out_dir"] = out_dir

    for k, v in [
        ("goal", cfg["preset"]),
        ("models", f"{len(cfg['models'])}: " + ", ".join(cfg["models"][:4])
                   + (f" +{len(cfg['models']) - 4} more" if len(cfg["models"]) > 4 else "")),
        ("shape", " ".join(flags)),
        ("runs", f"{cfg['runs']} (+{cfg['warmup_runs']} warmup)"),
        ("out", out_dir),
        ("estimate", f"~{est} min" if est < 60
                     else f"~{est // 60}h {est % 60}m"),
    ]:
        print(f"    {dim(k.rjust(9))}  {v}")

    n_over = 0
    for m in cfg["models"]:
        c_ = cat.get(m)
        if not c_:
            continue
        need = max((int(x) for x in (cfg.get("depth") or flags_depth(flags))), default=0)
        ctx = c_.get("ctx_size") or 0
        if ctx and need + 2048 > ctx:
            print(bad(f"    WARNING {m}: depth {need} + pp 2048 exceeds ctx {ctx}"))
            n_over += 1
    if n_over:
        print(dim("    those runs will fail or truncate — lower --depth or drop the model"))

    if not ask_yesno("\n  Run it?", True):
        print("    cancelled — nothing was run")
        raise SystemExit(0)
    return cfg


def flags_depth(flags):
    """Pull the max --depth out of a concrete flag list, for the ctx check."""
    vals = []
    for i, f in enumerate(flags):
        if f == "--depth":
            for v in flags[i + 1:]:
                if v.startswith("-"):
                    break
                if v.isdigit():
                    vals.append(int(v))
    return vals or [0]


# --------------------------------------------------------------------------
# execution
# --------------------------------------------------------------------------
def build_cmd(cfg, mid, out_path):
    tok, _src = TOKENIZERS.get(mid, (None, None))
    cmd = [
        "llama-benchy",
        "--base-url", cfg["base_url"],
        "--model", mid,
        # api, NOT generation: the generation probe times to the first stream
        # chunk, which on llama-swap includes the on-demand model load, and
        # est_ppt = max(0, ttfr - latency) then zeroes out the whole pp row.
        "--latency-mode", "api",
        "--runs", str(cfg["runs"]),
        "--warmup-runs", str(cfg["warmup_runs"]),
        "--format", "json",
        "--save-result", out_path,
    ]
    if tok:
        cmd += ["--tokenizer", tok]
    if cfg["preset"] == "custom":
        for key, _d, _h in CUSTOM_FIELDS:
            cmd += [f"--{key}"] + cfg[key]
    else:
        cmd += cfg["flags"]
    return cmd


def execute(cfg, dry=False):
    os.makedirs(cfg["out_dir"], exist_ok=True)
    ok, failed = [], []

    for i, mid in enumerate(cfg["models"], 1):
        safe = mid.replace("/", "_")
        out = os.path.join(cfg["out_dir"], f"{safe}.json")
        cmd = build_cmd(cfg, mid, out)
        print()
        print(bold(f"── [{i}/{len(cfg['models'])}] {mid} " + "─" * 30))
        print(dim("    $ " + " ".join(cmd)))
        if dry:
            ok.append(mid)
            continue
        t0 = time.time()
        rc = subprocess.call(cmd)
        dt = time.time() - t0
        if rc == 0:
            print(good(f"    ok in {dt:.0f}s -> {out}"))
            ok.append(mid)
        else:
            print(warn(f"    exited {rc} after {dt:.0f}s — continuing"))
            failed.append(mid)

    with open(os.path.join(cfg["out_dir"], "plan.json"), "w") as f:
        json.dump(cfg, f, indent=2)

    print()
    print(bold("── SUMMARY " + "─" * 52))
    print(f"    {len(ok)} ok, {len(failed)} failed")
    if failed:
        print(warn(f"    failed: {', '.join(failed)}"))
    print(f"    results: {cfg['out_dir']}")
    if not dry and ok:
        # Print the table here rather than handing back a one-liner. A summary
        # you have to assemble yourself is a summary nobody reads.
        print()
        print(f"    {'model':<30} {'pp t/s':>9} {'tg t/s':>9} {'peak':>8} {'est_ppt':>9}")
        for mid in ok:
            path = os.path.join(cfg["out_dir"], f"{mid.replace('/', '_')}.json")
            try:
                with open(path) as f:
                    d = json.load(f)
            except (OSError, json.JSONDecodeError):
                print(warn(f"    {mid:<30} (unreadable)"))
                continue
            for b in d.get("benchmarks", []):
                pp = b.get("pp_throughput")
                tg = b.get("tg_throughput")
                pk = b.get("peak_throughput")
                ep = b.get("est_ppt")
                label = mid if not b.get("context_size") else \
                    f"{mid} @d{b['context_size']}"
                if b.get("is_context_prefill_phase"):
                    label += " ctx"
                print(f"    {label:<30} "
                      f"{(pp['mean'] if pp else 0):>9.1f} "
                      f"{(tg['mean'] if tg else 0):>9.1f} "
                      f"{(pk['mean'] if pk else 0):>8.1f} "
                      f"{(ep['mean'] if ep else 0):>9.1f}")
        print(dim(f"    full JSON incl. stddev: {cfg['out_dir']}"))
    return cfg


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base-url", default=DEFAULT_BASE_URL)
    ap.add_argument("--preset", choices=list(PRESETS), help="skip the goal question")
    ap.add_argument("--models", nargs="+", help="skip model selection")
    ap.add_argument("--runs", type=int, help="skip the rigor question")
    ap.add_argument("--dry-run", action="store_true", help="print the plan, run nothing")
    ap.add_argument("--non-interactive", action="store_true",
                    help="require --profile; never prompt")
    ap.add_argument("--profile", help="replay a saved plan.json")
    args = ap.parse_args()

    if args.non_interactive:
        if not args.profile:
            print("--non-interactive needs --profile <plan.json>")
            return 2
        execute(json.load(open(args.profile)), args.dry_run)
        return 0

    if args.profile and not sys.stdin.isatty():
        execute(json.load(open(args.profile)), args.dry_run)
        return 0

    if not sys.stdin.isatty():
        print("stdin is not a tty — refusing to prompt.")
        print("use --dry-run, or --non-interactive --profile <plan.json>")
        return 2

    cfg = interview(args.base_url)
    if args.preset:
        cfg["preset"] = args.preset
        if args.preset != "custom":
            cfg["flags"] = list(PRESETS[args.preset]["flags"])
    if args.models:
        cfg["models"] = args.models
    if args.runs:
        cfg["runs"] = args.runs
        cfg["warmup_runs"] = 0 if args.runs == 1 else 1

    execute(cfg, args.dry_run)
    return 0


if __name__ == "__main__":
    sys.exit(main())
