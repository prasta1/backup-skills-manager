#!/usr/bin/env python3
"""Consolidate benchmark CSVs into ranked summary tables, PER MACHINE.

Reads individual run CSVs from the benchmark output directory and produces
ranked tables for coding speed, vision performance, and disk efficiency.
Coding and vision numbers come from the CSVs (never stale config values); the
model config supplies only size and deleted status.

Tables are grouped by the machine that produced them. A single combined
ranking across machines is not meaningful: tok/s is only comparable within
one box, so "151 tok/s beats 16 tok/s" is a statement about the hardware, not
the model. Each machine also serves a different roster.

Usage:
    python3 generate_final_report.py --results-dir ~/.hermes/benchmark_results
                                      --model-config references/model-config.json
    python3 generate_final_report.py --results-dir ... --combined   # one table
"""
import csv
import os
import json
import argparse
import glob
import sys
from datetime import datetime
from collections import defaultdict, OrderedDict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import machines as M

RULE = 98  # report width; matches the widest table


def load_csv(path):
    rows = []
    with open(path) as f:
        for row in csv.DictReader(f):
            rows.append(row)
    return rows


def pareto(points):
    """Return the names no other point beats on BOTH axes (higher is better).

    points: [(name, x, y)]. Walking from fastest to slowest, a model joins the
    frontier only if it scores higher than every faster model -- otherwise
    something quicker is at least as good, and it is beaten.
    """
    keep, best = [], float("-inf")
    for name, x, y in sorted(points, key=lambda p: (-p[1], -p[2])):
        if y > best:
            keep.append(name)
            best = y
    return keep


def bar(q, width=10):
    """Quality 0-1 as a fixed-width block bar, in eighths: 0.85 -> '████████▌ '."""
    eighths = round(max(0.0, min(1.0, q)) * width * 8)
    full, rem = divmod(eighths, 8)
    return ("█" * full + (" ▏▎▍▌▋▊▉"[rem] if rem else "")).ljust(width)


def build_report(coding_rows, vision_rows, models, label):
    """Return the printable body for one machine (or the whole fleet)."""
    out = []
    w = out.append

    def meta_for(name):
        return next((mm for mm in models if mm["name"] == name), None)

    def gb_of(name):
        meta = meta_for(name)
        return meta.get("size_gb") if meta else None

    def size_of(name):
        gb = gb_of(name)
        return f"{gb} GB" if gb else "—"

    def status_of(name):
        # Only the exception is worth ink; a column of ACTIVE is noise.
        meta = meta_for(name)
        return "deleted" if meta and meta["deleted"] else ""

    # --- Coding ---
    coding_data = defaultdict(lambda: {"speeds": [], "quals": []})
    for r in coding_rows:
        if r.get("error"):
            continue  # failed call, not a genuine 0.0 score
        m = r["model"]
        if float(r.get("median_tok_s", 0)) > 0:
            coding_data[m]["speeds"].append(float(r["median_tok_s"]))
            coding_data[m]["quals"].append(float(r.get("quality_score", 0)))

    def mean(xs):
        return sum(xs) / len(xs) if xs else 0.0

    cod = {m: (mean(d["speeds"]), mean(d["quals"])) for m, d in coding_data.items()}
    ranked_coding = sorted(cod.items(), key=lambda kv: kv[1][0], reverse=True)
    live = [(m, s, q) for m, (s, q) in cod.items() if status_of(m) != "deleted"]
    frontier = pareto(live)

    # --- Verdict: the answer the sweep was run for, before the evidence ---
    # Coding quality is a deterministic pattern-match score; vision is ranked
    # by the rubric. Both are only comparable within this machine.
    if live:
        w("\n  VERDICT")
        w(f"  Coding frontier — {len(frontier)} of {len(live)} models; "
          "every other model is beaten on speed AND quality by one of these:")
        for m in sorted(frontier, key=lambda n: -cod[n][1]):
            s, q = cod[m]
            w(f"    ◆ {m:<30} {q:.2f} {bar(q)}  {s:>6.1f} tok/s  {size_of(m):>8}")
        effs = [(m, s / gb_of(m)) for m, s, _q in live if gb_of(m)]
        if effs:
            m, e = max(effs, key=lambda kv: kv[1])
            w(f"  Most speed per GB of disk:  {m}  ({e:.1f} tok/s/GB)")

    w("\n--- CODING PERFORMANCE (ranked by speed · ◆ = on the frontier) ---")
    w(f"{'Rank':>6} {'Model':<30} {'Speed':>7}  {'Quality':<15} {'Size':>8}")
    w("-" * 80)
    for i, (m, (spd, qual)) in enumerate(ranked_coding, 1):
        mark = "◆" if m in frontier else " "
        w(f"{mark:>2}{i:>4} {m:<30} {spd:>7.1f}  {qual:.2f} {bar(qual)} {size_of(m):>8}  {status_of(m)}".rstrip())
    if not ranked_coding:
        w("  (no coding results)")

    # --- Vision ---
    # Ranked by GROUNDED RUBRIC SCORE, not character count. A char count is a
    # proxy for verbosity: a model that pads or invents detail scores higher
    # than one that answers tersely and correctly. The rubric is the
    # measurement; chars are kept only as a diagnostic column.
    #
    # vision_quality comes from model-config.json (built by
    # build_model_config.py --vision-results-dir), which is where a scorer fix
    # gets applied. Ranking off the raw rows here would silently re-introduce
    # scores from a superseded run.
    vision_data = defaultdict(lambda: {"speeds": [], "chars": [], "inputs": [], "quals": []})
    for r in vision_rows:
        m = r["model"]
        if float(r.get("median_tok_s", 0)) > 0:
            vision_data[m]["speeds"].append(float(r["median_tok_s"]))
            vision_data[m]["chars"].append(int(r.get("quality_chars", 0)))
            vision_data[m]["inputs"].append(int(r.get("prompt_tokens", 0)))
            try:
                vision_data[m]["quals"].append(float(r.get("quality_score")))
            except (TypeError, ValueError):
                pass

    def _vq(m, data):
        meta = meta_for(m)
        if meta and meta.get("vision_quality") is not None:
            return meta["vision_quality"]
        return (sum(data["quals"]) / len(data["quals"])) if data["quals"] else None

    w("\n--- VISION PERFORMANCE (by grounded rubric score) ---")
    w(f"{'Rank':>6} {'Model':<30} {'Quality':<15} {'Speed':>7} {'Chars':>7} {'Input':>7} {'Size':>8}")
    w("-" * 98)
    # Sort on the rubric, then speed. Sorting on speed put ministral-3-3b first
    # at 97.5 tok/s on a 0.50 score -- the exact 'fast but wrong' result the
    # grounded rubric exists to expose.
    ranked_vision = sorted(
        vision_data.items(),
        key=lambda x: (_vq(x[0], x[1]) is not None,
                       _vq(x[0], x[1]) or 0,
                       sum(x[1]["speeds"]) / len(x[1]["speeds"])),
        reverse=True)
    for i, (m, data) in enumerate(ranked_vision, 1):
        spd = sum(data["speeds"]) / len(data["speeds"])
        ch = sum(data["chars"]) / len(data["chars"])
        ic = sum(data["inputs"]) / len(data["inputs"])
        q = _vq(m, data)
        qs = f"{q:.2f} {bar(q)}" if q is not None else f"{'—':<15}"
        w(f"{i:>6} {m:<30} {qs:<15} {spd:>7.1f} {ch:>7.0f} {ic:>7.0f} {size_of(m):>8}  {status_of(m)}".rstrip())
    if not ranked_vision:
        w("  (no vision results)")

    # --- Coding vs Vision ---
    w("\n--- CODING vs VISION SPEED ---")
    w(f"{'Model':<30} {'Coding tok/s':>14} {'Vision tok/s':>14} {'Size':>8}")
    w("-" * 72)
    all_names = sorted(set(coding_data) | set(vision_data),
                       key=lambda n: (sum(coding_data[n]["speeds"]) / len(coding_data[n]["speeds"])
                                      if coding_data.get(n) and coding_data[n]["speeds"] else 0),
                       reverse=True)
    for m in all_names:
        cd = coding_data.get(m)
        cspd = f"{sum(cd['speeds'])/len(cd['speeds']):.1f}" if cd and cd["speeds"] else "—"
        vd = vision_data.get(m)
        vstr = f"{sum(vd['speeds'])/len(vd['speeds']):.1f}" if vd and vd["speeds"] else "—"
        w(f"  {m:<30} {cspd:>14} {vstr:>14} {size_of(m):>8}")

    return "\n".join(out), len(ranked_coding)


def main():
    parser = argparse.ArgumentParser(description="Generate consolidated benchmark report")
    parser.add_argument("--results-dir", default=os.path.expanduser("~/.hermes/benchmark_results"))
    parser.add_argument("--model-config", required=False)
    parser.add_argument("--combined", action="store_true",
                        help="One ranking across all machines instead of a section "
                             "per machine. Faster to read, but tok/s is not "
                             "comparable across hardware.")
    parser.add_argument("--out", help="Write the report to this file as well as stdout")
    args = parser.parse_args()

    results_dir = args.results_dir

    # Load model metadata (size, deleted status only — numbers come from CSVs)
    config_path = args.model_config or os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "references", "model-config.json"
    )
    with open(config_path) as f:
        models = json.load(f)

    coding_rows, vision_rows = [], []
    for p in sorted(glob.glob(os.path.join(results_dir, "coding_bench_*.csv"))):
        coding_rows.extend(load_csv(p))
    for p in sorted(glob.glob(os.path.join(results_dir, "vision_bench_*.csv"))):
        vision_rows.extend(load_csv(p))

    registry = M.load_machines()
    chunks = []

    if args.combined:
        body, n = build_report(coding_rows, vision_rows, models, "all machines")
        chunks.append(("ALL MACHINES COMBINED", body))
    else:
        cg = M.group_rows(coding_rows, machines=registry)
        vg = M.group_rows(vision_rows, machines=registry)
        for name, _prefix in registry:
            pass  # registry order comes from group_rows
        # Emit one section per machine that has ANY result.
        for name in list(cg.keys()) + [k for k in vg.keys() if k not in cg]:
            c_rows = cg.get(name, [])
            v_rows = vg.get(name, [])
            if not c_rows and not v_rows:
                continue
            body, n = build_report(c_rows, v_rows, models, name)
            nc = len({r["model"] for r in c_rows if not r.get("error")})
            nv = len({r["model"] for r in v_rows})
            header = (f"{name.upper()}  ·  {nc} coding model{'s' * (nc != 1)}, "
                      f"{nv} vision model{'s' * (nv != 1)}")
            chunks.append((header, body))

    n_runs = (len(glob.glob(os.path.join(results_dir, "coding_bench_*.csv")))
              + len(glob.glob(os.path.join(results_dir, "vision_bench_*.csv"))))
    n_models = len({r["model"] for r in coding_rows + vision_rows})
    lines = ["━" * RULE,
             f"MODEL FLEET REPORT  ·  {datetime.now().strftime('%Y-%m-%d %H:%M')}",
             f"{n_models} models  ·  {n_runs} benchmark runs  ·  "
             f"{len(chunks)} section{'s' if len(chunks) != 1 else ''}",
             "━" * RULE]
    if not args.combined and len(chunks) > 1:
        lines.append("Rankings are PER MACHINE. tok/s is not comparable across hardware —")
        lines.append("compare quality within a machine, not speed across them.")
        lines.append("")

    def section(title):
        lines.append("")
        lines.append(f"━━ {title} ".ljust(RULE, "━"))

    for header, body in chunks:
        section(header)
        lines.append(body)

    # Cross-machine view: same MODEL on different boxes, which IS comparable.
    section("CROSS-MACHINE  ·  same weights, different silicon")
    lines.append(cross_machine(coding_rows, vision_rows, models, registry))

    lines.append("")
    lines.append("━" * RULE)
    text = "\n".join(lines)
    print(text)
    if args.out:
        with open(args.out, "w") as f:
            f.write(text + "\n")
        print(f"\nwritten to {args.out}")


def cross_machine(coding_rows, vision_rows, models, registry):
    """Where the SAME model id was benchmarked on more than one machine.

    This is the one comparison the per-machine split hides: identical weights
    on different silicon, so a quality gap is the quantization or the runtime,
    not the model.
    """
    rows_by_machine = M.group_rows(coding_rows, machines=registry)
    vrows_by_machine = M.group_rows(vision_rows, machines=registry)
    qual = defaultdict(dict)
    spd = defaultdict(dict)
    # Two machines give the same weights DIFFERENT ids -- mb-devstral-24b and
    # ms-devstral-24b are one model on two boxes. Comparing raw ids finds no
    # overlap and the table comes back empty, which is exactly when it is most
    # interesting. Strip the registry prefix and match on what remains.
    #
    # load_machines() yields (url, (name, prefix)), so destructure BOTH parts.
    prefixes = [pfx for _url, (_nm, pfx) in registry]

    def bare(name):
        for pfx in prefixes:
            if name.startswith(pfx):
                return name[len(pfx):]
        return name

    for mname, rows in rows_by_machine.items():
        agg = defaultdict(list)
        for r in rows:
            if r.get("error"):
                continue
            agg[r["model"]].append(float(r["median_tok_s"]))
        for m, vals in agg.items():
            spd[bare(m)][mname] = sum(vals) / len(vals)
            qs = [float(r.get("quality_score", 0)) for r in rows
                  if r["model"] == m and not r.get("error")]
            if qs:
                qual[bare(m)][mname] = sum(qs) / len(qs)
    vq = defaultdict(lambda: defaultdict(list))
    for mname, rows in vrows_by_machine.items():
        for r in rows:
            try:
                vq[bare(r["model"])][mname].append(float(r.get("quality_score")))
            except (TypeError, ValueError):
                pass

    shared = sorted(m for m, d in spd.items() if len(d) > 1)
    if not shared:
        return "  (no model ids were benchmarked on more than one machine)"

    # Prefer the model's vision_quality from model-config.json. It may come from
    # a superseding re-run after a scorer fix; re-deriving from the raw rows
    # here would resurrect the superseded scores. Fall back to the row mean.
    def vis_for(bare_name, mname, full_ids):
        for mid in full_ids.get(bare_name, {}).get(mname, []):
            mm = next((x for x in models if x["name"] == mid), None)
            if mm and mm.get("vision_quality") is not None:
                return mm["vision_quality"]
        vals = vq.get(bare_name, {}).get(mname)
        return (sum(vals) / len(vals)) if vals else None

    full_ids = defaultdict(dict)
    for mname, rows in vrows_by_machine.items():
        for r in rows:
            full_ids[bare(r["model"])].setdefault(mname, [])
            if r["model"] not in full_ids[bare(r["model"])][mname]:
                full_ids[bare(r["model"])][mname].append(r["model"])

    out = [f"{'Model':<28} {'Machine':<22} {'tok/s':>8} {'Qual':>6} {'Vis':>6}",
           "-" * 74]
    for m in shared:
        for mname, s in sorted(spd[m].items(), key=lambda kv: -kv[1]):
            q = qual.get(m, {}).get(mname)
            v = vis_for(m, mname, full_ids)
            out.append(f"{m:<28} {mname:<22} {s:>8.1f} "
                       f"{(f'{q:.2f}' if q is not None else '—'):>6} "
                       f"{(f'{v:.2f}' if v is not None else '—'):>6}")
    return "\n".join(out)


if __name__ == "__main__":
    main()