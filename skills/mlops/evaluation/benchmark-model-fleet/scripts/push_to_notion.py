#!/usr/bin/env python3
"""Push fleet benchmark results into a single Notion database.

A benchmark run leaves a directory of ~40 flat CSVs plus a pile of PNGs and a
PDF. That is a fine archive and a hostile review surface: nothing sorts across
runs, and the answer ("which model should this box use") is spread over three
artifacts. This script collapses a run directory into one row per
(run x machine x family x model) and upserts those rows into one Notion table,
where they filter by run, sort by quality, and compare over time.

The CSVs stay on disk. They are the data layer the merge, the plots and the
ranked report all read; Notion is the review layer on top.

Runs headless on purpose -- auth is NOTION_API_KEY (environment or
~/.hermes/.env). A skill script has no MCP session, so it cannot use the Notion
MCP tools.

Aggregation mirrors generate_final_report.py so the table and the report cannot
disagree:
  speed   = mean of per-prompt median_tok_s over non-error rows (>0 only,
            because 0 tok/s means the call failed, not a slow model)
  quality = mean of quality_score over non-error rows (0.0 KEPT -- a genuine
            zero is a measurement, and averaging it away hides a bad model)
  frontier= pareto over (speed, quality) PER (machine, family), skipping
            deleted models -- the same `pareto()` the report uses

Two fidelity notes:
  * Rows record what THAT run measured, so vision quality is the run's own
    rubric score. `vision_quality` in model-config.json is a FLEET-view
    concept (a later run superseding a scorer fix) and importing it into a
    historical row would misdate it.
  * No frontier is computed for vision. Vision tok/s is unreliable by the
    skill's own measure (1.4-80.8 tok/s for one model across prompts), and a
    frontier drawn on an unreliable axis invites a false conclusion.

Usage:
    python3 scripts/push_to_notion.py --init                  # create the table once
    python3 scripts/push_to_notion.py --results-dir <dir>     # push one run
    python3 scripts/push_to_notion.py --all                   # backfill every run dir
    python3 scripts/push_to_notion.py --all --dry-run         # show, write nothing
    python3 scripts/push_to_notion.py --views-only            # reconcile views only

Every push also reconciles the Notion views (charts, KPIs) and, for a single-run
push, renders the per-machine frontier scatters and uploads them into Notion.
`--no-charts` skips that; `--all` skips it by default, because backfilling 18
runs would stack dozens of charts on the page.
"""
import argparse
import csv
import glob
import json
import os
import re
import shutil
import statistics
import sys
import time
from collections import OrderedDict, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import machines as M  # noqa: E402  (grouping key: the endpoint column)
import model_family as MF  # noqa: E402  (family from the id, arch from the GGUF)
import notion_views as V  # noqa: E402  (the native views + frontier charts)
import loadability as LOAD  # noqa: E402  (the one publish rule)
from notion_client import (Notion, RENAMES as CLIENT_RENAMES,  # noqa: E402
                           load_api_key, read_state, rt, write_state)

DEFAULT_RESULTS = os.path.expanduser("~/.hermes/benchmark_results")
FLEET_CONFIG = os.path.join(ROOT, "references", "model-config.json")
DB_TITLE = "Fleet Benchmark Results"

# The page the table lives under. Created by Patrick 2026-10-27.
DEFAULT_PARENT = "3f40efce-9aed-81d4-ac34-d23005151eec"

# Any <family>_bench_<YYYYMMDD>_<HHMMSS>[_<micros>].csv. Microseconds were added
# to stop two concurrent sweeps colliding, so every run before that carries only
# the seconds -- without the optional group, all of September is invisible.
CSV_RE = re.compile(
    r"^(?P<family>.+?)_bench_(?P<ts>\d{8}_\d{6})(?:_(?P<us>\d+))?\.csv$")

# Vision speed is not a trustworthy axis (see module docstring), so no frontier.
# CSV_RE strips the `_bench_` suffix, so family_of() returns "vision" -- the key
# here must match THAT, or the guard never fires and the table quietly marks a
# frontier on the axis the module docstring says cannot carry one.
NO_FRONTIER_FAMILIES = {"vision", "vision_bench"}

# Notion's published limit is ~3 requests/second averaged.
_MIN_INTERVAL = 0.34

# ---------------------------------------------------------------------------
# The publish rule: only measurements of models some host can still load.
# ---------------------------------------------------------------------------
# Nothing is stored. `deleted` (surfaced as `Retired`) used to be computed at
# merge time and then frozen into each run's model-config.json, the fleet file
# and both sinks -- four copies frozen at different times, which disagreed: 12
# live rows described models no host could load and 10 of them were on a chart.
# Resolved once per process, because resolving it costs an ssh to the peer.
_LOADABLE = None


def loadable_predicate():
    """Cached `can some host still load this model` predicate."""
    global _LOADABLE
    if _LOADABLE is None:
        _LOADABLE = LOAD.resolver()
    return _LOADABLE


# The published row set as a file, in Patrick's own directory.
#
# Grist cannot ingest a CSV -- verified against the REST reference: the only
# import endpoint is `POST /workspaces/{id}/import`, which imports a .grist
# DOCUMENT, and the only table-write paths are the records/rows endpoints and
# /apply. A hosted doc also cannot see this filesystem. So this file is not the
# transport; it is the readable artifact, which is worth having anyway: the fleet
# becomes greppable and diffable with no API in the loop, and the sink is fed from
# the same list this writes, so the two cannot disagree.
CSV_OUT = os.path.expanduser("~/.hermes/outputs/fleet-benchmark/fleet-benchmark.csv")
CSV_COLUMNS = ["key", "run", "run_dir", "machine", "family", "model",
               "model_family", "base_arch", "type", "date", "speed", "quality",
               "chars", "size_gb", "efficiency", "frontier", "latest", "deleted",
               "prompts", "rows", "errors", "endpoint"]


def write_csv(rows, path=CSV_OUT):
    """Write the published rows to a CSV. Returns the path."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    ordered = sorted(rows, key=lambda r: (r["family"], r["machine"],
                                          -(r["speed"] or 0), r["model"]))
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CSV_COLUMNS, extrasaction="ignore")
        w.writeheader()
        w.writerows(ordered)
    return path


# ---------------------------------------------------------------------------
# Notion transport lives in notion_client.py
# ---------------------------------------------------------------------------
# load_api_key(), Notion, rt(), read_state() and write_state() moved there so
# this sink and notion_views.py share ONE copy of the transport rather than
# growing two definitions that can drift.


def props_for(row):
    """Notion property payload for one aggregated row.

    `row["deleted"]` is surfaced as the `Retired` column: the field keeps its
    pipeline name, only the label the user reads changed.
    """
    p = {
        "Model": {"title": rt(row["model"])},
        "Key": {"rich_text": rt(row["key"])},
        "Run": {"rich_text": rt(row["run"])},
        "Run Dir": {"rich_text": rt(row["run_dir"])},
        "Endpoint": {"rich_text": rt(row["endpoint"])},
        "Prompts": {"number": row["prompts"]},
        "Rows": {"number": row["rows"]},
        "Errors": {"number": row["errors"]},
        "Frontier": {"checkbox": bool(row["frontier"])},
        "Retired": {"checkbox": bool(row["deleted"])},
        "Latest": {"checkbox": bool(row.get("latest"))},
    }
    if row.get("machine"):
        p["Machine"] = {"select": {"name": row["machine"]}}
    if row.get("family"):
        p["Family"] = {"select": {"name": row["family"]}}
    if row.get("model_family"):
        p["Model Family"] = {"select": {"name": row["model_family"]}}
    if row.get("base_arch"):
        p["Base Architecture"] = {"select": {"name": row["base_arch"]}}
    if row.get("type"):
        p["Type"] = {"select": {"name": row["type"]}}
    if row.get("date"):
        p["Date"] = {"date": {"start": row["date"]}}
    for label, field in (("Speed tok/s", "speed"), ("Quality", "quality"),
                         ("Chars", "chars"), ("Size GB", "size_gb"),
                         ("tok/s per GB", "efficiency")):
        if row.get(field) is not None:
            p[label] = {"number": row[field]}
    return p


def schema_properties():
    """Column definitions keyed by FINAL name, minus the title.

    The title is not listed here because a database may hold exactly one, so on a
    fresh data source the default `Name` is RENAMED rather than re-added -- see
    RENAMES and init_database().

    `Retired` is the human-facing name for the flag the pipeline stores as
    `deleted`. The JSON field name is a persisted contract read by four scripts
    and by --carry-forward, so only the label changed; renaming the field would
    risk a half-migration in which retired models silently stop being marked.
    """
    return {
        "Key": {"rich_text": {}},
        "Run": {"rich_text": {}},
        "Run Dir": {"rich_text": {}},
        "Endpoint": {"rich_text": {}},
        "Machine": {"select": {}},
        "Family": {"select": {}},
        "Model Family": {"select": {}},
        "Base Architecture": {"select": {}},
        "Type": {"select": {}},
        "Date": {"date": {}},
        "Speed tok/s": {"number": {"format": "number"}},
        "Quality": {"number": {"format": "number"}},
        "Chars": {"number": {"format": "number"}},
        "Size GB": {"number": {"format": "number"}},
        "tok/s per GB": {"number": {"format": "number"}},
        "Frontier": {"checkbox": {}},
        "Retired": {"checkbox": {}},
        "Latest": {"checkbox": {}},
        "Prompts": {"number": {"format": "number"}},
        "Rows": {"number": {"format": "number"}},
        "Errors": {"number": {"format": "number"}},
    }


# Old name -> current name, shared with notion_views so both migrate their
# cached maps together.
RENAMES = CLIENT_RENAMES


def ensure_schema(api, state, dry=False):
    """Bring an existing table up to the current schema, idempotently.

    Adding columns and renaming one is otherwise a manual UI step that has to be
    repeated on every new database. Renames are issued as renames so the property
    id -- and therefore every chart filter built on it -- is preserved.
    """
    ds = api("GET", f"/data_sources/{state['data_source_id']}")
    have = set((ds.get("properties") or {}).keys())
    want = schema_properties()
    renames = {old: new for old, new in RENAMES.items()
               if old in have and new not in have}
    patch = {old: {"name": new} for old, new in renames.items()}
    for name, spec in want.items():
        if name in have or name in patch:
            continue
        # A rename INTO this name is already handled above; adding it as a new
        # property as well would collide with the rename in the same request.
        if name in renames.values():
            continue
        patch[name] = spec
    if not patch:
        return []
    if dry:
        return sorted(patch)
    api("PATCH", f"/data_sources/{state['data_source_id']}", {"properties": patch})
    # The cached id map is keyed by property NAME, so a renamed property leaves a
    # stale key behind. The id is unchanged; carry it to the new name.
    ids = state.get("property_ids") or {}
    for old, new in RENAMES.items():
        if old in ids and new not in ids:
            ids[new] = ids.pop(old)
    if ids:
        state["property_ids"] = ids
        write_state(state)
    return sorted(patch)


def init_database(api, parent_id):
    """Create the table and then its columns.

    Two calls, because they live on two different objects in the 2025-09-03 API:
    POST /v1/databases makes the container, and the COLUMNS belong to its data
    source. POST /v1/databases accepts a `properties` map and silently drops it,
    which does not fail here -- it fails later, as 'Model is not a property that
    exists' on every single row insert.
    """
    db = api("POST", "/databases", {
        "parent": {"type": "page_id", "page_id": parent_id},
        "title": rt(DB_TITLE),
    })
    ds = (db.get("data_sources") or [{}])[0].get("id") or db.get("id")
    # The default title ('Name') is RENAMED, not re-added: a database may hold
    # exactly one title property, so asking for a second one is rejected.
    want = dict(schema_properties())
    want["Name"] = {"name": RENAMES["Name"]}
    ds = api("PATCH", f"/data_sources/{ds}", {"properties": want})

    state = {
        "database_id": db.get("id"),
        "data_source_id": ds.get("id"),
        "parent_page_id": parent_id,
        "url": db.get("url"),
        "created": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    cols = sorted(ds.get("properties") or {})
    expect = len(schema_properties()) + 1        # + the title property
    if len(cols) != expect:
        raise SystemExit(f"schema incomplete: {len(cols)} columns, "
                         f"expected {expect}: {cols}")
    write_state(state)
    print(f"  created '{DB_TITLE}' with {len(cols)} columns")
    print(f"  database_id    {state['database_id']}")
    print(f"  data_source_id {state['data_source_id']}")
    if state.get("url"):
        print(f"  {state['url']}")
    return state


def existing_keys(api, data_source_id):
    """{Key: page_id} for every row already in the table. One paged read beats
    one filtered query per row (~600 rows x 1 query would be minutes)."""
    out, cursor = {}, None
    while True:
        body = {"page_size": 100}
        if cursor:
            body["start_cursor"] = cursor
        res = api("POST", f"/data_sources/{data_source_id}/query", body)
        for page in res.get("results", []):
            k = page.get("properties", {}).get("Key", {}).get("rich_text") or []
            if k:
                out["".join(x.get("plain_text", "") for x in k)] = page["id"]
        if not res.get("has_more"):
            return out
        cursor = res.get("next_cursor")


def prune(api, state, keep, dry=False):
    """Archive rows whose model no host can still load.

    Upsert alone cannot express the publish rule: a key that stops being published
    is simply never written again, so it would sit in the table forever. This
    table is meant to BE the fleet (see loadability.py), so a key outside the
    published set is archived. The run dirs are untouched, so a model that is
    declared again reappears on the very next push -- this is a filter on the
    review surface, not a deletion of history.
    """
    stale = {k: pid for k, pid in
             existing_keys(api, state["data_source_id"]).items() if k not in keep}
    if not stale:
        print("  prune: nothing stale")
        return 0
    for _k, pid in stale.items():
        if not dry:
            api("PATCH", f"/pages/{pid}", {"archived": True})
    print(f"  prune: {len(stale)} stale row(s) "
          + ("would be archived" if dry else "archived"))
    for k in sorted(stale)[:25]:
        print(f"    - {k}")
    if len(stale) > 25:
        print(f"    ... and {len(stale) - 25} more")
    return len(stale)


def create_row(api, state, row):
    """Create a page in the table. data_source_id is the 2025-09-03 form;
    database_id still works on older surfaces, so fall back rather than fail."""
    p = props_for(row)
    for parent in ({"type": "data_source_id", "data_source_id": state["data_source_id"]},
                   {"type": "database_id", "database_id": state["database_id"]}):
        try:
            api("POST", "/pages", {"parent": parent, "properties": p})
            return "created"
        except SystemExit as e:
            if "HTTP 400" not in str(e):
                raise
            last = e
    raise last


# ---------------------------------------------------------------------------
# aggregation
# ---------------------------------------------------------------------------
def read_csv(path):
    """Rows from one benchmark CSV. The headerless pre-fix format is skipped
    rather than misparsed -- model would come back as the first data cell."""
    with open(path) as f:
        if not f.readline().startswith("model,"):
            return []
        f.seek(0)
        return list(csv.DictReader(f))


def discover_runs(root):
    """Every directory under root that holds benchmark CSVs, as (run_id, path).

    Recursive: run dirs nest experiments (mbp-20261024/studio-toolcall/). A
    path component starting with '_' or '.' is an explicit archive/superseded
    marker (fleet/_superseded-mixed-pile) and is skipped -- those hold
    measurements that were replaced on purpose and would pollute the table.
    """
    runs = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if not d.startswith(("_", "."))]
        if not any(CSV_RE.match(fn) for fn in filenames):
            continue
        runs.append((os.path.relpath(dirpath, root), dirpath))
    return sorted(runs)


def run_date(dirpath):
    """Newest timestamp carried in the CSVs' own filenames, else the dir mtime.
    The filename is the run's real clock; a later copy would move the mtime."""
    stamps = []
    for fn in os.listdir(dirpath):
        m = CSV_RE.match(fn)
        if m:
            stamps.append(m.group("ts"))
    if stamps:
        t = max(stamps)
        return f"{t[0:4]}-{t[4:6]}-{t[6:8]}T{t[9:11]}:{t[11:13]}:{t[13:15]}"
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(os.path.getmtime(dirpath)))


def family_of(filename):
    m = CSV_RE.match(filename)
    return m.group("family") if m else None


def mean(xs):
    return round(statistics.mean(xs), 2) if xs else None


def pareto(points):
    """Names no other point beats on BOTH axes (higher is better). Same walk as
    generate_final_report.pareto: fastest -> slowest, a model joins only if it
    beats every faster model on quality."""
    keep, best = [], float("-inf")
    for name, _x, y in sorted(points, key=lambda p: (-p[1], -p[2])):
        if y > best:
            keep.append(name)
            best = y
    return keep


def run_configs(dirpath):
    """(sizes, deleted, types) for this run. The run's own model-config.json is
    written BY the run, so it is the right vintage; the fleet view is the
    fallback for a run predating the merge."""
    for path in (os.path.join(dirpath, "model-config.json"), FLEET_CONFIG):
        if not os.path.exists(path):
            continue
        try:
            entries = json.load(open(path))
        except (OSError, ValueError):
            continue
        sizes = {e["name"]: e.get("size_gb") for e in entries if e.get("name")}
        deleted = {e["name"]: bool(e.get("deleted") or e.get("not_loadable"))
                   for e in entries if e.get("name")}
        types = {e["name"]: e.get("type") for e in entries if e.get("name")}
        return sizes, deleted, types
    return {}, {}, {}


def aggregate(run_id, dirpath, registry, loadable=None):
    """One row per (machine, family, model) for this run dir.

    Only models some host can still load get a row at all -- that IS the publish
    rule (see loadability.py). A pruned model keeps its CSVs on disk and comes
    back automatically if it is ever declared again, so this is a filter on the
    review surface, not a deletion of history.
    """
    sizes, deleted, types = run_configs(dirpath)
    loadable = loadable or loadable_predicate()
    date = run_date(dirpath)
    by_family = defaultdict(list)          # family -> rows
    for path in sorted(glob.glob(os.path.join(dirpath, "*_bench_*.csv"))):
        fam = family_of(os.path.basename(path))
        if fam:
            by_family[fam].extend(read_csv(path))

    rows = []
    for fam, fam_rows in sorted(by_family.items()):
        # machine comes from the endpoint column the CSVs carry (measured
        # fact), falling back to the id prefix -- load_machines yields
        # (url, (name, prefix)), so both halves must be destructured.
        buckets = defaultdict(list)
        for r in fam_rows:
            name = r.get("model")
            if not name or not loadable(name):
                continue
            mach = (M.machine_for_endpoint(r.get("endpoint"), registry)
                    or M.machine_for_model(name, registry) or "unassigned")
            buckets[(mach, name)].append(r)

        agg = {}
        for (mach, name), rs in buckets.items():
            ok = [r for r in rs if not r.get("error")]
            speeds = [float(r["median_tok_s"]) for r in ok
                      if _f(r.get("median_tok_s")) and float(r["median_tok_s"]) > 0]
            quals = [float(r["quality_score"]) for r in ok
                     if _f(r.get("quality_score"))]
            chars = [float(r["quality_chars"]) for r in ok
                     if _f(r.get("quality_chars"))]
            endpoints = [r.get("endpoint") for r in rs if r.get("endpoint")]
            speed, quality = mean(speeds), mean(quals)
            gb = sizes.get(name)
            agg[(mach, name)] = {
                "model": name, "machine": mach, "family": fam,
                "run": run_id, "run_dir": os.path.basename(dirpath) or run_id,
                "date": date, "endpoint": endpoints[0] if endpoints else "",
                "type": types.get(name),
                "speed": speed, "quality": quality, "chars": mean(chars),
                "size_gb": gb,
                "efficiency": (round(speed / gb, 2) if speed and gb else None),
                # Always False, and the field stays only because the column does:
                # publication itself is now gated on loadability, so every row in
                # the table is loadable by construction. There is no second axis
                # left to store, and the views' filters on it are a no-op guard.
                "deleted": False,
                "prompts": len({r.get("prompt_name") for r in rs
                                if r.get("prompt_name")}),
                "rows": len(rs),
                "errors": len([r for r in rs if r.get("error")]),
                "key": f"{run_id}|{mach}|{fam}|{name}",
                "frontier": False,
                # Family is a pure function of the id. The architecture is not
                # -- it comes from the GGUF and is resolved for the whole batch
                # in main(), because reading it costs ssh/SMB I/O.
                "model_family": MF.model_family(name),
                "base_arch": None,
                # Set for the whole batch in main() -- see mark_latest().
                "latest": False,
            }

        # Frontier per (machine, family) among loadable models -- a fleet-wide
        # frontier would rank the hardware instead of the models.
        if fam not in NO_FRONTIER_FAMILIES:
            for mach in {m for m, _ in agg}:
                live = [(n, a["speed"], a["quality"]) for (m, n), a in agg.items()
                        if m == mach and not a["deleted"]
                        and a["speed"] and a["quality"] is not None]
                for n in pareto(live):
                    agg[(mach, n)]["frontier"] = True
        rows.extend(agg.values())
    return sorted(rows, key=lambda r: (r["family"], r["machine"], -(r["speed"] or 0)))


def mark_latest(rows):
    """Flag the newest measurement per (machine, family, model).

    The table keeps EVERY run on purpose -- that is how a model is tracked over
    time -- but that is exactly what makes "what is current" invisible: 219 rows
    are only 54 distinct model ids, and one id appears in 12 runs.

    `latest` marks the row a review surface should show when it wants present
    state rather than history. Split by family because a model's coding and
    vision measurements are not comparable. Newest by the run's own date, ties
    broken by run id so the answer is deterministic rather than dependent on
    filesystem walk order.
    """
    newest = {}
    for r in rows:
        r["latest"] = False
        key = (r["machine"], r["family"], r["model"])
        cur = newest.get(key)
        if cur is None or (r["date"], r["run"]) > (cur["date"], cur["run"]):
            newest[key] = r
    for r in newest.values():
        r["latest"] = True
    return rows


def _f(v):
    try:
        float(v)
        return True
    except (TypeError, ValueError):
        return False


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------
def push(api, state, rows, dry=False, quiet=False):
    known = {} if dry else existing_keys(api, state["data_source_id"])
    created = updated = failed = 0
    for row in rows:
        if dry:
            continue
        try:
            if row["key"] in known:
                api("PATCH", f"/pages/{known[row['key']]}",
                    {"properties": props_for(row)})
                updated += 1
            else:
                create_row(api, state, row)
                created += 1
        except SystemExit as e:
            failed += 1
            print(f"    FAILED {row['key']}: {str(e)[:200]}", file=sys.stderr)
        if not quiet and (created + updated) % 50 == 0 and (created + updated):
            print(f"    ... {created + updated}/{len(rows)}")
    return created, updated, failed


def show(rows):
    print(f"  {len(rows)} rows")
    for r in rows:
        spd = f"{r['speed']:.1f}" if r["speed"] else "—"
        q = f"{r['quality']:.2f}" if r["quality"] is not None else "—"
        flags = ("◆" if r["frontier"] else "") + (" deleted" if r["deleted"] else "")
        print(f"    {r['run']:<30} {r['machine']:<20} {r['family']:<12} "
              f"{r['model']:<30} {(r['model_family'] or '—'):<10} "
              f"{(r['base_arch'] or '—'):<12} {spd:>7} {q:>5}  {flags}".rstrip())


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--results-dir", help="one run directory to push")
    ap.add_argument("--all", action="store_true",
                    help="backfill every run directory under --root")
    ap.add_argument("--root", default=DEFAULT_RESULTS,
                    help=f"benchmark results root (default {DEFAULT_RESULTS})")
    ap.add_argument("--init", action="store_true",
                    help="create the Notion database, then exit")
    ap.add_argument("--parent", default=None,
                    help="parent page id for --init (defaults to the saved one)")
    ap.add_argument("--dry-run", action="store_true", help="print rows, write nothing")
    ap.add_argument("--views-only", action="store_true",
                    help="reconcile the Notion views and exit; pushes no rows")
    ap.add_argument("--no-charts", action="store_true",
                    help="skip rendering and uploading the frontier scatters")
    ap.add_argument("--no-arch", action="store_true",
                    help="skip reading base architecture from the GGUFs (no ssh "
                         "to the MacBook; those rows are left unverified)")
    ap.add_argument("--charts", action="store_true",
                    help="also render/upload frontier scatters on --all (off by "
                         "default there: 18 runs would stack dozens of images)")
    args = ap.parse_args()

    state = read_state()
    if args.init:
        parent = args.parent or state.get("parent_page_id") or DEFAULT_PARENT
        print(f"Creating '{DB_TITLE}' under page {parent}")
        init_database(Notion(load_api_key()), parent)
        return 0

    if not state.get("data_source_id"):
        raise SystemExit("No Notion database recorded. Run with --init first.")

    # The per-machine speed charts come from the table's own Machine select
    # options (see notion_views.read_machine_names) -- NOT from endpoints.json,
    # which lists each box twice and would double every speed chart.
    if args.views_only:
        api = Notion(load_api_key())
        changed = ensure_schema(api, state, dry=args.dry_run)
        if changed:
            print(f"schema: {', '.join(changed)}")
        print("views:")
        for action, name, _vid in V.reconcile_views(api, state,
                                                    dry=args.dry_run):
            print(f"  {action:<14} {name}")
        return 0

    if args.all:
        runs = discover_runs(args.root)
    elif args.results_dir:
        d = os.path.abspath(os.path.expanduser(args.results_dir))
        rid = os.path.relpath(d, args.root)
        # A run dir outside the root would otherwise be labelled with a
        # ../.. chain -- use its own name instead.
        if rid.startswith(".."):
            rid = os.path.basename(d)
        runs = [(rid, d)]
    else:
        raise SystemExit("pass --results-dir <dir>, --all, or --init")

    if not runs:
        raise SystemExit(f"no run directories with benchmark CSVs under {args.root}")

    registry = M.load_machines()
    all_rows = []
    print(f"{len(runs)} run director{'ies' if len(runs) != 1 else 'y'}")
    for run_id, dirpath in runs:
        rows = aggregate(run_id, dirpath, registry)
        print(f"  {run_id:<44} {len(rows):>3} rows")
        all_rows.extend(rows)

    # Base architecture comes from each model's own GGUF, so it is resolved once
    # for the whole batch -- cached, and the MacBook half is read over ssh.
    ids = sorted({r["model"] for r in all_rows})
    if not args.no_arch:
        arches = MF.resolve_base_arch(ids)
        for r in all_rows:
            r["base_arch"] = arches.get(r["model"])
        unverified = len(ids) - len(arches)
        print(f"  base architecture verified for {len(arches)}/{len(ids)} models"
              + (f"; {unverified} unverified (no GGUF reachable -- retired, or "
                 f"an MLX/oMLX run that never had one)" if unverified else ""))
    # Batch-level, like the architecture: one run dir cannot know what the
    # newest measurement of a model is.
    mark_latest(all_rows)
    print(f"  latest flagged for {sum(1 for r in all_rows if r['latest'])} "
          f"(machine, family, model) triple(s)")

    unclassified = sorted({i for i in ids if not MF.model_family(i)})
    if unclassified:
        print(f"  no model family matched: {', '.join(unclassified)}")

    if args.dry_run:
        show(all_rows)
        api = Notion(load_api_key())
        prune(api, state, {r["key"] for r in all_rows}, dry=True)
        print("\nviews:")
        for action, name, _vid in V.reconcile_views(api, state, dry=True):
            print(f"  {action:<14} {name}")
        return 0

    api = Notion(load_api_key())
    changed = ensure_schema(api, state)
    if changed:
        print(f"schema: added/renamed {', '.join(changed)}")
    print(f"  rows csv -> {write_csv(all_rows)}")
    print(f"\npushing {len(all_rows)} rows -> {DB_TITLE}")
    created, updated, failed = push(api, state, all_rows)
    print(f"  created {created}, updated {updated}, failed {failed}")
    if failed:
        return 1
    prune(api, state, {r["key"] for r in all_rows})

    print("\nviews:")
    for action, name, _vid in V.reconcile_views(api, state):
        print(f"  {action:<14} {name}")

    want_charts = not args.no_charts and (len(runs) == 1 or args.charts)
    if want_charts:
        run_id, dirpath = runs[0]
        items, scratch = V.frontier_images(dirpath)
        try:
            if items:
                added, skipped = V.upload_images(api, state, items, run_id)
                print(f"\nfrontier charts: {added} uploaded, "
                      f"{skipped} already on the page")
        finally:
            # The render is scratch: the whole point is that no chart is left
            # sitting beside the CSVs.
            if scratch:
                shutil.rmtree(scratch, ignore_errors=True)

    print(f"\n  {state.get('url')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
