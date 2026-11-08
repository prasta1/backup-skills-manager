#!/usr/bin/env python3
"""Merge benchmark CSVs + on-disk GGUF sizes into the model-config.json the
plots and the final report read.

Replaces hand-transcribing 15 models x 4 fields out of the CSVs.

Sizes and model->file mapping come from the llama-swap config, so a model whose
GGUF path is broken shows up as 0.0 GB — which is itself a useful signal.

Usage:
    python3 build_model_config.py --results-dir ~/.hermes/benchmark_results/run-X \
        --llama-swap-config ~/.hermes/llama-swap/config.yaml \
        --out ~/.hermes/benchmark_results/run-X/model-config.json
"""
import argparse
import csv
import glob
import json
import os
import re
import statistics
import sys

# Substring -> type, first match wins. Drives bubble colour in the scatter plots.
TYPE_HINTS = [
    ("vl", "Vision"), ("vision", "Vision"), ("glm-4-6", "Vision"),
    ("moe", "MoE"), ("a3b", "MoE"), ("a4b", "MoE"), ("coder-30b", "MoE"),
    ("kat-coder", "MoE"), ("gpt-oss", "MoE"), ("laguna", "MoE"),
    ("bge", "Embeddings"), ("rerank", "Embeddings"),
]


def expand_shards(paths):
    """A config names only shard 1 of a split GGUF ('-00001-of-00003.gguf'), but the
    model on disk is all of them — count every sibling or the size is a big undercount."""
    out = []
    for p in paths:
        m = re.search(r'-(\d{5})-of-(\d{5})\.gguf$', p)
        if m:
            out += sorted(glob.glob(re.sub(r'-\d{5}-of-\d{5}\.gguf$',
                                           f'-*-of-{m.group(2)}.gguf', p)))
        else:
            out.append(p)
    return out


def model_sizes(config_path):
    """model id -> (size_gb, [missing paths]) from the llama-swap config."""
    text = open(config_path).read()
    out = {}
    for block in re.split(r'\n(?=  [a-zA-Z0-9_.-]+:\n)', text):
        m = re.match(r'  ([a-zA-Z0-9_.-]+):', block)
        if not m:
            continue
        # The value must look like a path. Without this guard a prose comment
        # containing the word '--model' (e.g. "...is --model wired to...") is
        # scraped as a filename, reported as a broken GGUF path, and sets
        # broken_paths on a model whose weights are present and fine.
        paths = [p for p in re.findall(r'(?:-m|--model|--mmproj)\s+(\S+)', block)
                 if "/" in p]
        if not paths:
            continue
        total, missing = 0, []
        for p in expand_shards(paths):
            try:
                total += os.path.getsize(p)
            except OSError:
                missing.append(p)
        out[m.group(1)] = (round(total / 1e9, 1), missing)
    return out


def read_rows(results_dir, prefix):
    rows = []
    for path in glob.glob(os.path.join(results_dir, f"{prefix}_*.csv")):
        with open(path) as f:
            head = f.readline()
            if not head.startswith("model,"):
                print(f"  skipping headerless CSV (pre-fix format): {os.path.basename(path)}")
                continue
            f.seek(0)
            rows += list(csv.DictReader(f))
    return rows


def agg(rows, model, field, drop_zero=True, fn=statistics.mean):
    """drop_zero=True for speeds (0 tok/s means the call failed).
    drop_zero=False for scores — a genuine 0.0 quality must not be averaged away."""
    vals = []
    for r in rows:
        if r["model"] != model or r.get("error"):
            continue
        try:
            v = float(r.get(field) or 0)
        except ValueError:
            continue
        if v > 0 or not drop_zero:
            vals.append(v)
    return round(fn(vals), 2) if vals else None


def guess_type(name):
    low = name.lower()
    for hint, t in TYPE_HINTS:
        if hint in low:
            return t
    return "Standard"


def config_model_keys(config_path):
    """The model ids this host's llama-swap config actually declares.

    Keys are the 2-space-indented entries of the top-level `models:` mapping,
    which sits between `models:` and the next column-0 key (`groups:`). Nested
    block contents are at 4-space indent, so 2-space keys in that window are
    exactly the model ids.
    """
    if not os.path.exists(config_path):
        return set()
    lines = open(config_path).read().splitlines()
    keys, inside = set(), False
    for line in lines:
        if re.match(r'^models:\s*$', line):
            inside = True
            continue
        if inside:
            if line and not line.startswith((' ', '\t', '#')):
                break                      # left the models block
            m = re.match(r'^  ([a-zA-Z0-9_.\-]+):\s*$', line)
            if m:
                keys.add(m.group(1))
    return keys


def prefix_map(config_path, registry_path):
    """Split the registry's id_prefix values into (local, remote).

    Do NOT decide this from the URL: llama-swap-mbp-loopback is 127.0.0.1 with
    prefix 'mb-', so a loopback-means-local test classifies the MacBook's whole
    roster as local and marks every mb-* model deleted on the Studio.

    Instead derive it from the config itself -- a prefix is LOCAL if this host's
    config declares any key carrying it. That is self-consistent on both boxes:
    the Studio's keys are all ms-* so mb- is remote, and on the MacBook the same
    code reaches the opposite answer from its own config.
    """
    if not os.path.exists(registry_path):
        return set(), set()
    try:
        entries = json.load(open(registry_path)).get("endpoints", [])
    except (OSError, ValueError):
        return set(), set()
    declared = {e["id_prefix"] for e in entries if e.get("id_prefix")}
    keys = config_model_keys(config_path)
    local = {p for p in declared if any(k.startswith(p) for k in keys)}
    return local, declared - local


def reconcile(entries, config_path, registry_path):
    """Mark ids no machine can load as deleted instead of silently keeping them.

    THE bug this exists to fix: the name universe is the union of every CSV ever
    written, and nothing ever removes a name. A model that was benchmarked once,
    then pruned or renamed, stays in the config forever -- rendered as a LIVE
    bubble on every chart, because `deleted` was hardcoded False and nothing
    ever set it True. A pruned 8B model sat at rank #2 on the coding plot for
    weeks, looking like the second-fastest thing in the fleet.

    An id survives only if SOME host can load it: this box's config, or the
    peer's over ssh. That is the same rule the sinks publish on (loadability.py),
    so the report, the plots and both tables cannot disagree. The old rule kept
    anything carrying a remote prefix alive, on the reasoning that "absent from
    this config" is normal for another box's roster; true, but it also meant a
    model pruned on the laptop stayed live here forever, and that an id no host
    ever declared was never examined at all.

    Returns (n_local, n_remote, n_deleted).
    """
    # Deferred: loadability imports THIS module for config_model_keys/prefix_map,
    # so a module-level import here would be circular.
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import loadability as LOAD
    is_loadable = LOAD.resolver(verbose=False)

    keys = config_model_keys(config_path)
    _, remote = prefix_map(config_path, registry_path)
    n_local = n_remote = n_deleted = 0
    for e in entries:
        name = e["name"]
        if not is_loadable(name):
            e["deleted"] = True
            e["not_loadable"] = True
            n_deleted += 1
        elif name in keys:
            n_local += 1
        else:
            n_remote += 1
    return n_local, n_remote, n_deleted


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--results-dir", required=True)
    ap.add_argument("--llama-swap-config",
                    default=os.path.expanduser("~/.hermes/llama-swap/config.yaml"))
    ap.add_argument("--out", required=True)
    ap.add_argument("--family", default="coding_bench",
                    help="CSV prefix to read for the speed/quality columns, e.g. "
                         "'structured_extraction_bench'. Defaults to coding_bench.")
    ap.add_argument("--extra-sizes",
                    help="JSON file of {model_id: {size_gb, broken:[...]}} measured on "
                         "another host. A fleet spanning two machines has GGUF paths that "
                         "only resolve on the machine holding them, so the Studio's config "
                         "reports every remote model as 0.0 GB / broken. Merge these in and "
                         "they take precedence for ids absent from the local config.")
    ap.add_argument("--vision-results-dir",
                    help="A second results dir whose vision_bench_*.csv scores SUPERSEDE "
                         "the primary ones for the same model ids. Use after a scorer fix: "
                         "the corrected scores win and the originals stay on disk as the "
                         "audit trail. Writes a 'vision_quality' field the scatter plot "
                         "prefers over the character count.")
    ap.add_argument("--registry",
                    default=os.path.join(
                        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "references", "endpoints.json"),
                    help="endpoints.json, used to learn which id prefixes belong to "
                         "OTHER machines. A model carrying a remote prefix is absent "
                         "from this host's config by design and is not stale.")
    ap.add_argument("--no-reconcile", action="store_true",
                    help="Keep every id found in the CSVs, even ones no machine can "
                         "load. Default is to mark those deleted so pruned and renamed "
                         "models stop rendering as live bubbles.")
    ap.add_argument("--carry-forward", metavar="PATH",
                    help="An existing model-config.json to seed from. Names in it that "
                         "no CSV covers are kept with their prior scores, so the file "
                         "accumulates fleet coverage instead of shrinking to whatever "
                         "the last run happened to touch. Only meaningful when writing "
                         "to a long-lived config such as references/model-config.json.")
    args = ap.parse_args()

    coding = read_rows(args.results_dir, args.family)
    vision = read_rows(args.results_dir, "vision_bench")
    sizes = model_sizes(args.llama_swap_config) if os.path.exists(args.llama_swap_config) else {}

    # Remote-host sizes. Only fills gaps: a local config entry always wins, since
    # it is the machine that can actually stat the file.
    if args.extra_sizes:
        with open(args.extra_sizes) as f:
            remote = json.load(f)
        for k, v in remote.items():
            if k not in sizes:
                sizes[k] = (v.get("size_gb"), v.get("broken") or [])

    names = sorted({r["model"] for r in coding} | {r["model"] for r in vision})
    entries = []
    for n in names:
        size, missing = sizes.get(n, (None, []))
        e = {
            "name": n,
            "coding_spd": agg(coding, n, "median_tok_s"),
            "quality": agg(coding, n, "quality_score", drop_zero=False),
            "vision_spd": agg(vision, n, "median_tok_s"),
            "vision_chars": agg(vision, n, "quality_chars", drop_zero=False),
            "size_gb": size,
            "type": guess_type(n),
            "deleted": False,
        }
        if missing:
            e["broken_paths"] = missing
        entries.append(e)

    # Seed from a long-lived config so the file accumulates fleet coverage. A
    # partial sweep must not shrink a 41-row metadata file to the 2 models it
    # just ran -- the plots read this file for the WHOLE fleet.
    if args.carry_forward and os.path.exists(args.carry_forward):
        have = {e["name"] for e in entries}
        try:
            prev = json.load(open(args.carry_forward))
        except (OSError, ValueError):
            prev = []
        # A model this run measured keeps its earlier values for the fields
        # this run did NOT measure. Without this, a vision-only run would wipe
        # every vision model's coding score from the fleet view.
        prev_by_name = {o.get("name"): o for o in prev}
        for e in entries:
            for k, v in prev_by_name.get(e["name"], {}).items():
                if k != "not_loadable" and e.get(k) is None and v is not None:
                    e[k] = v
        carried = 0
        for old in prev:
            if old.get("name") in have:
                continue
            old.pop("not_loadable", None)   # re-derived by reconcile below
            entries.append(old)
            carried += 1
        if carried:
            print(f"  carried forward {carried} entries not covered by this run")

    # A second rubric run can supersede an earlier one for the same ids (a
    # scorer fix, say). --vision-results-dir lets the corrected scores win
    # without deleting the originals, which stay as the audit trail.
    #
    # An ORDINARY vision run must set vision_quality too, from its own CSVs.
    # This block used to run only when --vision-results-dir was passed, so a
    # fresh vision run left the field absent -- and generate_scatter.py then
    # fell back to vision_chars, the verbosity axis this skill says cannot rank
    # a vision model. The run silently reproduced the exact failure the
    # grounded rubric exists to fix, and no default flow passes that flag.
    fixed, extra, superseded = vision, [], False
    if args.vision_results_dir:
        superseding = read_rows(args.vision_results_dir, "vision_bench")
        if superseding:
            # Models absent from the superseding dir keep the PRIMARY run's
            # vision score. That is not a fallback in the usual sense: a
            # two-machine sweep fixes the scorer mid-run, so the far machine's
            # vision CSVs were already produced by the corrected rubric and the
            # superseding dir only re-covers the machine that was re-run.
            fixed = superseding
            have = {r["model"] for r in fixed}
            extra = [r for r in vision if r["model"] not in have]
            superseded = True
    if fixed:
        for e in entries:
            m = e["name"]
            vals = [float(r["quality_score"]) for r in fixed
                    if r["model"] == m and not r.get("error")]
            if not vals:
                vals = [float(r["quality_score"]) for r in extra
                        if r["model"] == m and not r.get("error")]
            if vals:
                e["vision_quality"] = round(statistics.mean(vals), 2)
        print(f"  vision_quality: {len(fixed)} "
              f"{'superseded' if superseded else 'primary'} rows, "
              f"{len(extra)} kept from the primary dir")

    with open(args.out, "w") as f:
        json.dump(entries, f, indent=2)
    print(f"\nWrote {len(entries)} models -> {args.out}")

    if not args.no_reconcile:
        n_local, n_remote, n_deleted = reconcile(
            entries, args.llama_swap_config, args.registry)
        print(f"  reconciled: {n_local} declared here, {n_remote} remote-host, "
              f"{n_deleted} not loadable (marked deleted)")
        if n_deleted:
            for e in entries:
                if e.get("not_loadable"):
                    print(f"    deleted: {e['name']}")
        # Rewrite so the marks are persisted -- the first write predates the
        # reconciliation, and a config that looks clean on disk but renders
        # ghosts is exactly the bug this guards against.
        with open(args.out, "w") as f:
            json.dump(entries, f, indent=2)

    for e in entries:
        flag = "  !! GGUF path broken" if e.get("broken_paths") else ""
        if e.get("not_loadable"):
            flag += "  (deleted: not in any config)"
        print(f"  {e['name']:<22} spd={str(e['coding_spd']):>7} qual={str(e['quality']):>5} "
              f"{str(e['size_gb']):>5}GB {e['type']}{flag}")


if __name__ == "__main__":
    main()
