#!/usr/bin/env python3
"""Interactive front-end for the fleet benchmark.

Asks what you want to measure BEFORE spending an hour of GPU time, so a
two-model question does not become an eighteen-model afternoon. Every step
defaults to the cheap/safe answer and can be overridden; --non-interactive
replays a saved profile for cron and scripted use.

Pipeline it drives (each step is independently runnable):
  1. discover_endpoints.py  — what is live, and which model ids it serves
  2. benchmark.py           — the timed runs, writes a CSV per family
  3. build_model_config.py  — CSV + on-disk GGUF sizes -> model-config.json
  4. generate_final_report.py — ranked tables, read from the CSVs
  5. push_to_notion.py      — one table row per (run x machine x family x model)

Plots are OPT-IN (--plots). The flat PNG/PDF pile was replaced by the Notion
table as the review surface; generate_scatter.py is unchanged and still there
for the runs where a chart is what you actually want.

Step 3 is not optional and is the one people skip: the plotting scripts read
model-config.json, never the CSVs, so a fresh benchmark that skips the merge
produces plots of the PREVIOUS run's numbers.

Usage:
    python3 scripts/run_interactive.py
    python3 scripts/run_interactive.py --preset vision
    python3 scripts/run_interactive.py --non-interactive --profile ~/.hermes/benchmark_results/last_profile.json
    python3 scripts/run_interactive.py --dry-run     # show the plan, run nothing
"""
import argparse
import datetime
import glob
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
REGISTRY = os.path.join(ROOT, "references", "endpoints.json")
PROMPTS_DIR = os.path.join(ROOT, "prompts")
DEFAULT_RESULTS = os.path.expanduser("~/.hermes/benchmark_results")
# The fleet view: latest known numbers per model across every run. Each run
# also writes its own model-config.json, which that run's plots and report read.
REF_CONFIG = os.path.join(ROOT, "references", "model-config.json")

# Substring -> human label. First match wins. Drives the pick menus, and is the
# same shape as build_model_config.TYPE_HINTS so a model's menu bucket and its
# plot colour agree.
TYPE_HINTS = [
    ("bge", "Embeddings (not benchmarkable — no chat)"),
    ("rerank", "Embeddings (not benchmarkable — no chat)"),
    ("vl", "Vision (mmproj)"),
    ("vision", "Vision (mmproj)"),
    ("moe", "MoE"),
    ("a3b", "MoE"),
    ("a4b", "MoE"),
    ("coder", "Coder"),
    ("mtp", "MTP / speculative"),
]

# Families, with the honest caveat about what deterministic scoring can measure.
FAMILIES = [
    ("builtin", "Built-in mixed coding (csv/go/rust/npm)"),
    ("sql_generation", "SQL generation — EXECUTES queries, strongest signal"),
    ("tool_calling", "Tool calling / JSON schema adherence"),
    ("structured_extraction", "Structured extraction to a schema"),
    ("instruction_following", "Instruction following"),
    ("data_analysis", "Data analysis over a small dataset"),
    ("web_frontend", "Web frontend generation"),
]


# ---------------------------------------------------------------------------
# terminal helpers
# ---------------------------------------------------------------------------
def _supports_unicode():
    enc = (sys.stdout.encoding or "").lower()
    return "utf" in enc


def c(text, code):
    """Colour if the terminal will take it, else plain. Never raises."""
    if not sys.stdout.isatty() or os.environ.get("NO_COLOR"):
        return text
    return f"\033[{code}m{text}\033[0m"


def bold(t):
    return c(t, "1")


def dim(t):
    return c(t, "2")


def hi(t):
    return c(t, "36")


def warn(t):
    return c(t, "33")


def bad(t):
    return c(t, "31")


def good(t):
    return c(t, "32")


def header(n, total, title):
    print()
    print(bold(f"[{n}/{total}] {title}"))
    print(dim("─" * 62))


def ask(prompt, default=None, allow_blank=True):
    """Single free-text answer. Returns default on blank input.

    Set allow_blank=False for fields where a stray menu index would be accepted
    as a real value (a results dir of "2" is worse than a re-prompt).
    """
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
    """options: list of (value, label). Returns the chosen value."""
    for i, (val, label) in enumerate(options, 1):
        mark = bold(f"{i}.") if i - 1 == default_idx else f"{i}."
        print(f"    {mark} {label}")
    while True:
        raw = ask(prompt, str(default_idx + 1))
        if raw.isdigit() and 1 <= int(raw) <= len(options):
            return options[int(raw) - 1][0]
        # also accept the raw value, so this is scriptable by typing the name
        for val, _ in options:
            if raw == val:
                return val
        print(warn(f"    pick 1-{len(options)}"))


def ask_yesno(prompt, default=True):
    raw = ask(prompt, "y" if default else "n").lower()
    return raw.startswith("y")


def ask_multiselect(prompt, options, preselected=()):
    """Space/comma separated numbers or names. Blank = nothing selected."""
    print(dim("    (blank = none, 'all' = every one)"))
    for i, (val, label) in enumerate(options, 1):
        mark = "*" if val in preselected else " "
        print(f"    {i:>2}. [{mark}] {label}")
    while True:
        raw = ask(prompt, "")
        if not raw:
            return []
        if raw.lower() in ("all", "*"):
            return [v for v, _ in options]
        picked = []
        bad_tokens = []
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
        # de-dup, preserve registry order
        return [v for v, _ in options if v in picked]


# ---------------------------------------------------------------------------
# fleet introspection
# ---------------------------------------------------------------------------
def load_registry():
    with open(REGISTRY) as f:
        return json.load(f)["endpoints"]


def models_at(url, api_key=None, insecure=False):
    """GET /v1/models. Returns [] on any failure — a dead endpoint is normal."""
    import ssl
    import urllib.request

    ctx = None
    if url.startswith("https") and insecure:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
    headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
    try:
        req = urllib.request.Request(f"{url}/v1/models", headers=headers)
        with urllib.request.urlopen(req, timeout=5, context=ctx) as r:
            return [m["id"] for m in json.loads(r.read()).get("data", [])]
    except Exception:
        return []


def classify(name):
    n = name.lower()
    for frag, label in TYPE_HINTS:
        if frag in n:
            return label
    return "Standard"


def is_chatty(name):
    """Embeddings/rerankers have no /chat/completions. Benchmarking them is
    a guaranteed failure that costs a model load each."""
    n = name.lower()
    return not ("bge" in n or "rerank" in n or "e5-" in n or "gte-" in n)


def gguf_size_gb(model_id, swap_cfg):
    """On-disk size for a model id, or None. Unescapes the backslash-mangled
    symlink targets that a bad `ln` can leave behind, so a broken link reports
    the size the weights WOULD have rather than 0."""
    import re
    if not swap_cfg or not os.path.exists(swap_cfg):
        return None
    text = open(swap_cfg).read()
    for block in re.split(r"\n(?=  [a-zA-Z0-9_.-]+:\n)", text):
        if not re.match(rf"  {re.escape(model_id)}:", block):
            continue
        paths = re.findall(r"(?:-m|--model|--mmproj)\s+(\S+)", block)
        total = 0
        for p in paths:
            p = p.replace("\\", "")
            try:
                total += os.path.getsize(p)
            except OSError:
                continue
        return round(total / 1e9, 2) if total else None
    return None


def has_mmproj(model_id, swap_cfg):
    if not swap_cfg or not os.path.exists(swap_cfg):
        return False
    import re
    text = open(swap_cfg).read()
    for block in re.split(r"\n(?=  [a-zA-Z0-9_.-]+:\n)", text):
        if re.match(rf"  {re.escape(model_id)}:", block):
            return "--mmproj" in block
    return False


def run(cmd, dry=False):
    """Run a subprocess, streaming output. Returns exit code.

    A None in the argv (an omitted optional flag) is dropped rather than
    crashing on the join — passing --model-config None is a common shape here
    and the report script defaults it anyway.
    """
    cmd = [str(x) for x in cmd if x is not None]
    if not cmd:
        return 0
    print(dim("    $ " + " ".join(cmd)))
    if dry:
        return 0
    return subprocess.call(cmd)


# ---------------------------------------------------------------------------
# the interview
# ---------------------------------------------------------------------------
def interview(reg, swap_cfg):
    cfg = {}
    total = 6

    # --- 1. endpoint -------------------------------------------------------
    header(1, total, "Which machine should we benchmark?")
    live = []
    for e in reg:
        url = e["url"].rstrip("/")
        ids = models_at(url, insecure=e.get("insecure", False))
        if ids:
            live.append((e, ids, len(ids)))
    if not live:
        print(bad("    No endpoint is answering /v1/models."))
        print(dim("    Start llama-swap, or add an entry to references/endpoints.json."))
        raise SystemExit(1)
    for e, ids, n in live:
        print(f"    {good('UP')}  {e['name']:<26} {n} models   {dim(e.get('host',''))}")
    for e in reg:
        if not any(e is le[0] for le in live):
            print(f"    {dim('down')} {e['name']:<26} {dim('(skipped)')}")
    if len(live) == 1:
        cfg["endpoint"] = live[0][0]["name"]
        print(dim(f"    only one is up: {cfg['endpoint']}"))
    else:
        cfg["endpoint"] = ask_choice("endpoint", [(e["name"], f"{e['name']} — {len(i)} models")
                                                  for e, i, _ in live], 0)
    entry = next(e for e in reg if e["name"] == cfg["endpoint"])
    cfg["insecure"] = bool(entry.get("insecure"))
    cfg["served"] = models_at(entry["url"].rstrip("/"), insecure=cfg["insecure"])

    # --- 2. what kind of measurement --------------------------------------
    header(2, total, "What are you trying to find out?")
    mode = ask_choice("mode", [
        ("coding", "Coding speed + quality (the default fleet audit)"),
        ("vision", "Vision — speed + description detail, needs an image"),
        ("both", "Both coding and vision (longest run)"),
        ("family", "A specific task family (SQL, tool calling, extraction...)"),
    ], 0)
    cfg["mode"] = mode

    if mode == "family":
        avail = []
        for val, label in FAMILIES:
            p = os.path.join(PROMPTS_DIR, f"{val}.py")
            if val == "builtin" or os.path.exists(p):
                avail.append((val, label))
        cfg["family"] = ask_choice("family", avail, 0)
        mode = "coding"
        cfg["mode"] = "coding"
    else:
        cfg["family"] = "builtin"

    if mode == "vision":
        img_default = os.path.join(HERE, "test_image.png")
        if os.path.exists(img_default):
            print(dim(f"    test image present: {img_default}"))
        cfg["image"] = ask("image path", img_default)

    # --- 3. which models ---------------------------------------------------
    header(3, total, "Which models?")
    chatty = [m for m in cfg["served"] if is_chatty(m)]
    skipped = [m for m in cfg["served"] if not is_chatty(m)]
    print(f"    {len(chatty)} benchmarkable, {len(skipped)} skipped as non-chat "
          f"{dim('(' + ', '.join(skipped) + ')') if skipped else ''}")

    groups = {}
    for m in chatty:
        groups.setdefault(classify(m), []).append(m)
    if mode == "vision":
        vis = [m for m in chatty if has_mmproj(m, swap_cfg)]
        print(f"    {len(vis)} of these carry an mmproj: {dim(', '.join(vis))}")
        groups = {k: v for k, v in groups.items() if k == "Vision (mmproj)"}
        if not groups:
            print(bad("    No model on this endpoint has an mmproj — nothing to "
                      "benchmark for vision."))
            raise SystemExit(1)

    if len(chatty) == 1:
        cfg["models"] = chatty
        print(dim(f"    only one: {chatty[0]}"))
    else:
        buckets = sorted(groups.items())
        quick = []
        for _, ms in buckets:
            quick.append(("group:" + _, "all " + _ + f" ({len(ms)})"))
        quick.append(("top5", "top 5 by GGUF size (the heavyweight tier)"))
        quick.append(("all", f"everything ({len(chatty)}) — slow"))
        sel = ask_choice("shortcut", quick, 0)
        if sel.startswith("group:"):
            g = sel.split(":", 1)[1]
            cfg["models"] = sorted(groups[g])
        elif sel == "top5":
            sized = [(gguf_size_gb(m, swap_cfg) or 0, m) for m in chatty]
            cfg["models"] = [m for _, m in sorted(sized, reverse=True)[:5]]
        elif sel == "all":
            cfg["models"] = chatty
        else:
            opts = []
            for _, ms in buckets:
                for m in ms:
                    gb = gguf_size_gb(m, swap_cfg)
                    opts.append((m, f"{m:<28} {str(gb) + ' GB' if gb else 'size?'}"))
            cfg["models"] = ask_multiselect("models (numbers, names, or 'all')", opts)
            if not cfg["models"]:
                print(warn("    nothing selected — falling back to all"))
                cfg["models"] = chatty

    # --- 4. runtime budget -------------------------------------------------
    header(4, total, "How hard should we push?")
    n = len(cfg["models"])
    est = n * (7 if mode == "coding" else 5) if mode != "both" else n * 12
    print(f"    {n} model(s) selected "
          f"{dim(f'— roughly {est} min at ~1 prompt/min/model, more if models are cold')}")
    budget = ask_choice("budget", [
        ("quick", "quick — 1 prompt, 1 run (smoke test / is it alive)"),
        ("normal", "normal — 4 prompts, 3 runs (comparable numbers)"),
        ("deep", "deep — 4 prompts, 3 runs, thinking enabled (slow, Qwen-family only)"),
    ], 1)
    cfg["budget"] = budget
    if budget == "deep":
        cfg["thinking"] = True
        cfg["max_tokens"] = 2048
    else:
        cfg["thinking"] = False
        # Thinking models emit reasoning_content and leave content empty at low
        # max_tokens, which scores 0.0 for a reason that is not capability.
        cfg["max_tokens"] = 512

    # --- 5. output ---------------------------------------------------------
    header(5, total, "Where should results land?")
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    cfg["results_dir"] = os.path.join(DEFAULT_RESULTS, f"run-{stamp}")
    print(dim("    a fresh run dir keeps this sweep from polluting older CSVs"))
    print(dim(f"    default: {cfg['results_dir']}"))
    print(dim("    press enter for the default, or type a path ending in /"))
    while True:
        alt = ask("results dir", cfg["results_dir"])
        # A bare menu index here means an earlier answer was consumed by the
        # wrong prompt. Writing results to a dir named "2" is silently wrong,
        # so reject anything that is not a plausible path.
        if os.sep in alt or alt == cfg["results_dir"]:
            cfg["results_dir"] = alt
            break
        print(warn(f"    '{alt}' is not a path — expected something like "
                   f"{DEFAULT_RESULTS}/run-{stamp}"))
    cfg["plots"] = ask_yesno("also render the scatter plots + PDF?", False)
    cfg["report"] = ask_yesno("print the ranked report when done?", True)
    cfg["notion"] = ask_yesno("push the results into the Notion table?", True)
    if not cfg["plots"] and not cfg["report"] and not cfg["notion"]:
        print(dim("    all off — you will get CSVs and nothing else"))

    # --- 6. confirm --------------------------------------------------------
    header(6, total, "Plan")
    modes = ["coding", "vision"] if cfg["mode"] == "both" else [cfg["mode"]]
    plan = [
        ("endpoint", cfg["endpoint"]),
        ("measure", " + ".join(modes)),
        ("family", cfg["family"]),
        ("models", f"{len(cfg['models'])}: {', '.join(cfg['models'][:4])}"
                   + (f" +{len(cfg['models']) - 4} more" if len(cfg["models"]) > 4 else "")),
        ("max_tokens", cfg["max_tokens"]),
        ("thinking", str(cfg["thinking"]).lower()),
        ("results", cfg["results_dir"]),
        ("outputs", (("report " if cfg["report"] else "")
                     + ("plots " if cfg["plots"] else "")
                     + ("notion" if cfg["notion"] else "")).strip() or "csv only"),
    ]
    for k, v in plan:
        print(f"    {dim(k.rjust(11))}  {v}")
    if not ask_yesno("\n  Run it?", True):
        print("    cancelled — nothing was run")
        raise SystemExit(0)
    return cfg


# ---------------------------------------------------------------------------
# execution
# ---------------------------------------------------------------------------
def execute(cfg, swap_cfg, dry=False):
    os.makedirs(cfg["results_dir"], exist_ok=True)
    py = sys.executable
    bench = os.path.join(HERE, "benchmark.py")
    common = ["--endpoint", cfg["endpoint"], "--results-dir", cfg["results_dir"]]
    if cfg["insecure"]:
        common.append("--insecure")
    common += ["--models"] + cfg["models"]

    family_file = None if cfg["family"] == "builtin" else os.path.join(
        PROMPTS_DIR, f"{cfg['family']}.py")

    phases = []
    modes = ["coding", "vision"] if cfg["mode"] == "both" else [cfg["mode"]]
    for m in modes:
        cmd = [py, bench] + common
        if m == "vision":
            cmd.append("--vision")
            cmd += ["--image-path", cfg["image"]]
        if family_file:
            cmd += ["--prompts-file", family_file]
        cmd += ["--max-tokens", str(cfg["max_tokens"]),
                "--enable-thinking", str(cfg["thinking"]).lower()]
        if cfg["budget"] == "quick":
            cmd += ["--runs", "1", "--limit-prompts", "1"]
        phases.append((m, cmd))

    for m, cmd in phases:
        print()
        print(bold(f"── {m.upper()} BENCHMARK " + "─" * 40))
        rc = run(cmd, dry)
        if rc != 0 and not dry:
            print(warn(f"    {m} phase exited {rc} — continuing so partial "
                       f"results still make it to the report"))

    # The merge is what makes the plots real. Skipping it silently re-plots
    # the previous run's numbers, which is the single most confusing failure
    # this pipeline has.
    print()
    print(bold("── MERGING RESULTS " + "─" * 44))
    # Two configs, two jobs. The run's own file is what this run's plots and
    # report read -- only this run's numbers. Then the run is folded into the
    # references config, the fleet view: latest known numbers per model.
    merged = os.path.join(cfg["results_dir"], "model-config.json")
    # build_model_config reads ONE csv prefix. A non-default rubric names its
    # CSVs <family>_bench, and the default 'coding_bench' would silently find
    # nothing and merge an all-null config.
    csv_prefix = ("coding_bench" if cfg["family"] == "builtin"
                  else f"{cfg['family']}_bench")
    rc = run([py, os.path.join(HERE, "build_model_config.py"),
              "--results-dir", cfg["results_dir"],
              "--llama-swap-config", swap_cfg,
              "--family", csv_prefix,
              "--out", merged], dry)
    if rc != 0 and not dry:
        print(bad("    merge failed — plots would show stale numbers, skipping them"))
        cfg["plots"] = False
    elif csv_prefix == "coding_bench":
        # Only the built-in coding family folds in: --family writes its scores
        # into the coding_spd/quality fields, so folding a tool-calling run
        # would overwrite every model's coding score in the fleet view.
        # --carry-forward keeps the models (and fields) this run did not touch;
        # pass it only when there is a file to carry from.
        carry = (["--carry-forward", REF_CONFIG]
                 if os.path.exists(REF_CONFIG) else [])
        print(dim("    folding this run into the fleet view (references/model-config.json)"))
        if run([py, os.path.join(HERE, "build_model_config.py"),
                "--results-dir", cfg["results_dir"],
                "--llama-swap-config", swap_cfg,
                "--out", REF_CONFIG] + carry, dry) != 0 and not dry:
            print(warn("    fleet-view fold failed — this run's own report is unaffected"))

    if cfg.get("plots"):
        print()
        print(bold("── PLOTS " + "─" * 55))
        run([py, os.path.join(HERE, "generate_scatter.py"),
             "--results-dir", cfg["results_dir"],
             "--model-config", merged,
             "--label", cfg["family"].replace("_", " ").title()], dry)

    if cfg["report"]:
        print()
        print(bold("── RANKED REPORT " + "─" * 46))
        run([py, os.path.join(HERE, "generate_final_report.py"),
             "--results-dir", cfg["results_dir"],
             "--model-config", merged if os.path.exists(merged) else None], dry)

    # The table is the review surface: one row per (run x machine x family x
    # model), upserted, so re-pushing after a scorer fix corrects rows in place
    # instead of duplicating the run.
    if cfg.get("notion", True):
        print()
        print(bold("── NOTION " + "─" * 54))
        rc = run([py, os.path.join(HERE, "push_to_notion.py"),
                  "--results-dir", cfg["results_dir"],
                  "--root", DEFAULT_RESULTS], dry)
        if rc != 0 and not dry:
            print(warn("    Notion push failed — the CSVs are unaffected, "
                       "re-run push_to_notion.py when you want the rows"))

    with open(os.path.join(cfg["results_dir"], "profile.json"), "w") as f:
        json.dump(cfg, f, indent=2)
    print()
    print(good(f"  Done. Artifacts in {cfg['results_dir']}"))
    csvs = sorted(glob.glob(os.path.join(cfg["results_dir"], "*_bench_*.csv")))
    print(f"    {len(csvs)} benchmark CSV{'s' if len(csvs) != 1 else ''}")
    return cfg


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--preset", help="skip straight to a mode: coding|vision|both|family")
    ap.add_argument("--models", nargs="+", help="skip selection: explicit model ids")
    ap.add_argument("--endpoint", help="skip endpoint choice")
    ap.add_argument("--non-interactive", action="store_true",
                    help="require --profile; never prompt")
    ap.add_argument("--profile", help="replay a saved profile.json")
    ap.add_argument("--dry-run", action="store_true", help="print the plan, run nothing")
    ap.add_argument("--plots", action="store_true",
                    help="also render the scatter plots + PDF. Off by default: the "
                         "Notion table is the review surface now.")
    ap.add_argument("--swap-config",
                    default=os.path.expanduser("~/.hermes/llama-swap/config.yaml"))
    args = ap.parse_args()

    if args.non_interactive:
        if not args.profile:
            print("--non-interactive needs --profile <profile.json>")
            return 2
        cfg = json.load(open(args.profile))
        cfg["plots"] = bool(args.plots or cfg.get("plots"))
        return 0 if execute(cfg, args.swap_config, args.dry_run) else 0

    if args.profile and not sys.stdin.isatty():
        cfg = json.load(open(args.profile))
        cfg["plots"] = bool(args.plots or cfg.get("plots"))
        execute(cfg, args.swap_config, args.dry_run)
        return 0

    reg = load_registry()
    cfg = interview(reg, args.swap_config)

    # non-interactive overrides applied after the interview, so a caller can
    # answer the questions but still override the answers
    if args.preset:
        cfg["mode"] = args.preset
    if args.models:
        cfg["models"] = args.models
    if args.endpoint:
        cfg["endpoint"] = args.endpoint
    if args.plots:
        cfg["plots"] = True

    execute(cfg, args.swap_config, args.dry_run)
    return 0


if __name__ == "__main__":
    sys.exit(main())
