#!/usr/bin/env python3
"""Push fleet benchmark results into a Grist document (the second sink).

Same pipeline, second destination: the transform is IMPORTED from
push_to_notion.py rather than reimplemented, so the Notion table and the Grist
table are fed by one aggregation and cannot disagree. Only the sink half --
chema, payload shaping, transport -- is Grist-specific.

Why Grist:
  * Charts are available on every plan, including Free. Notion shows one chart
    on Free, which is what sent the benchmark review surface looking for a home.
  * A native Scatter Plot. Notion cannot draw one on ANY plan, which is why the
    frontier scatter currently has to be rendered in matplotlib and uploaded as
    an image.
  * PUT .../records takes {require, fields} -- declarative upsert -- so
    idempotency is the API's job instead of an emulated query-then-patch.

Rows are keyed identically to Notion (`run|machine|family|model`), so the two
tables can be diffed row-for-row.

Usage:
    python3 scripts/grist_sink.py --init              # create doc + table once
    python3 scripts/grist_sink.py --all --dry-run     # show, write nothing
    python3 scripts/grist_sink.py --all               # backfill every run dir
    python3 scripts/grist_sink.py --results-dir <dir>
    python3 scripts/grist_sink.py --check             # read back and verify

Auth: GRIST_API_KEY from the environment or ~/.hermes/.env.
"""
import argparse
import datetime
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import push_to_notion as P                     # noqa: E402  (the shared transform)
from grist_client import (Grist, load_api_key, read_state,  # noqa: E402
                          write_state)

DOC_NAME = "Fleet Benchmark Results"
TABLE_ID = "Results"
ORG_ID = 236614
WORKSPACE_ID = 250813          # "Home"
DEFAULT_PLACEHOLDER_COLS = ("A", "B", "C")
BATCH = 100

# Per-family tag colours (references/family-colors.json). Data, not code, so the
# palette can be corrected without touching the sink.
PALETTE_PATH = os.path.join(ROOT, "references", "family-colors.json")


def load_choice_palettes():
    """{column_id: {choice: {hex, text, provenance, source}}}."""
    try:
        with open(PALETTE_PATH) as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        return {}
    return {c: v for c, v in data.items()
            if not c.startswith("_") and isinstance(v, dict)}


CHOICE_PALETTES = load_choice_palettes()

# (column id, display label, Grist type). Ids carry no spaces or slashes; labels
# can, which is the whole reason the two are separate in Grist.
COLUMNS = [
    ("Key", "Key", "Text"),
    ("Model", "Model", "Text"),
    ("Run", "Run", "Text"),
    ("Run_Dir", "Run Dir", "Text"),
    ("Endpoint", "Endpoint", "Text"),
    ("Machine", "Machine", "Choice"),
    ("Family", "Family", "Choice"),
    ("Model_Family", "Model Family", "Choice"),
    ("Base_Architecture", "Base Architecture", "Choice"),
    ("Type", "Type", "Choice"),
    ("Date", "Date", "DateTime"),
    ("Speed_tok_s", "Speed tok/s", "Numeric"),
    ("Quality", "Quality", "Numeric"),
    ("Chars", "Chars", "Numeric"),
    ("Size_GB", "Size GB", "Numeric"),
    ("Efficiency", "tok/s per GB", "Numeric"),
    ("Frontier", "Frontier", "Bool"),
    ("Retired", "Retired", "Bool"),
    ("Latest", "Latest", "Bool"),
    ("Prompts", "Prompts", "Int"),
    ("Rows", "Rows", "Int"),
    ("Errors", "Errors", "Int"),
]
CHOICE_COLS = [c for c in COLUMNS if c[2] == "Choice"]
NUM_COLS = {
    "Speed_tok_s": "speed", "Quality": "quality", "Chars": "chars",
    "Size_GB": "size_gb", "Efficiency": "efficiency",
    "Prompts": "prompts", "Rows": "rows", "Errors": "errors",
}
CHOICE_FIELDS = {
    "Machine": "machine", "Family": "family", "Model_Family": "model_family",
    "Base_Architecture": "base_arch", "Type": "type",
}


# ---------------------------------------------------------------------------
# schema
# ---------------------------------------------------------------------------
def to_epoch(iso):
    """Grist DateTime columns store epoch seconds.

    run_date() yields a naive local 'YYYY-MM-DDTHH:MM:SS' built from the run's
    own clock, so it is interpreted as local time here rather than UTC -- the
    alternative would shift every September run by four hours.
    """
    if not iso:
        return None
    try:
        return int(datetime.datetime.strptime(
            iso, "%Y-%m-%dT%H:%M:%S").timestamp())
    except (ValueError, TypeError):
        return None


def from_epoch(secs):
    if not isinstance(secs, (int, float)):
        return None
    return datetime.datetime.fromtimestamp(secs).strftime("%Y-%m-%dT%H:%M:%S")


def column_spec(col_id, label, ctype, choices=None):
    fields = {"label": label, "type": ctype}
    if ctype == "Choice":
        fields["widgetOptions"] = json.dumps({"choices": sorted(choices or [])})
    return {"id": col_id, "fields": fields}


def find_table(g, doc_id, table_id):
    for t in g.tables(doc_id):
        if t["id"] == table_id:
            return t
    return None


def init_doc(g, state, dry=False, name=DOC_NAME, workspace_id=WORKSPACE_ID):
    """Create the doc and table, idempotently.

    A 'fresh' Grist document is NOT empty: it ships with Table1 carrying three
    placeholder formula columns (A, B, C). There is no API to delete a table, so
    rather than create a sibling and leave an orphan, Table1 is RENAMED to
    Results and its placeholders removed. Placeholders are only removed if they
    still look like placeholders (formula columns with an empty formula) so this
    can never eat real data.
    """
    doc_id = state.get("doc_id")
    if doc_id:
        try:
            g.call("GET", f"/docs/{doc_id}")
            print(f"  reusing doc {doc_id}")
        except SystemExit:
            print(f"  recorded doc {doc_id} is gone -- creating a new one")
            doc_id = None

    if not doc_id:
        doc_id = g.create_doc(workspace_id, name)
        print(f"  created '{name}' -> {doc_id}")

    state.update({"doc_id": doc_id, "table_id": TABLE_ID,
                  "org_id": ORG_ID, "workspace_id": workspace_id,
                  "url": f"https://docs.getgrist.com/doc/{doc_id}"})

    tables = {t["id"] for t in g.tables(doc_id)}
    actions = []
    if TABLE_ID not in tables:
        if "Table1" in tables:
            if dry:
                actions.append("rename Table1 -> Results")
            else:
                g.call("PATCH", f"/docs/{doc_id}/tables",
                       {"tables": [{"id": "Table1",
                                    "fields": {"tableId": TABLE_ID}}]})
                actions.append("renamed Table1 -> Results")
        else:
            if dry:
                actions.append("create table Results")
            else:
                g.add_table(doc_id, TABLE_ID, [])
                actions.append("created table Results")

    if not dry:
        # Drop the default placeholders, but only the ones that are still blank
        # formula columns.
        for col in g.columns(doc_id, TABLE_ID):
            f = col.get("fields", {})
            if (col["id"] in DEFAULT_PLACEHOLDER_COLS and f.get("isFormula")
                    and not (f.get("formula") or "").strip()):
                g.call("DELETE",
                       f"/docs/{doc_id}/tables/{TABLE_ID}/columns/{col['id']}")
                actions.append(f"removed placeholder column {col['id']}")

    changed = ensure_schema(g, doc_id, dry=dry)
    actions.extend(f"added column {c}" for c in changed)
    if not dry:
        write_state(state)
    for a in actions:
        print(f"  {a}")
    if not actions:
        print("  already initialised, nothing to do")
    return state


def ensure_schema(g, doc_id, dry=False):
    """Add any missing columns. Existing columns are left untouched."""
    have = {c["id"] for c in g.columns(doc_id, TABLE_ID)}
    missing = [column_spec(cid, label, ctype)
               for cid, label, ctype in COLUMNS if cid not in have]
    if missing and not dry:
        g.add_columns(doc_id, TABLE_ID, missing)
    return [m["id"] for m in missing]


def sync_choices(g, doc_id, rows, dry=False):
    """Extend each Choice column's list to cover the values actually present.

    A Choice column ACCEPTS an out-of-list value and stores it -- verified -- but
    it does not add it to the column's own choices. The value would render
    without its legend entry forever. So the sink unions what it is about to
    write into the declared list, which keeps the picker and the colours honest
    as new model families appear.
    """
    wanted = {}
    for cid, field in CHOICE_FIELDS.items():
        vals = {r.get(field) for r in rows if r.get(field)}
        if vals:
            wanted[cid] = vals
    if not wanted:
        return []

    changes = []
    payload = []
    for col in g.columns(doc_id, TABLE_ID):
        cid = col["id"]
        if cid not in wanted:
            continue
        f = col.get("fields", {})
        if f.get("type") != "Choice":
            continue
        raw = f.get("widgetOptions") or ""
        try:
            opts = json.loads(raw) if raw else {}
            if not isinstance(opts, dict):
                opts = {}
        except ValueError:
            opts = {}
        current = set(opts.get("choices") or [])
        add = wanted[cid] - current
        have_opts = opts.get("choiceOptions")
        have_opts = have_opts if isinstance(have_opts, dict) else {}

        # The tag colour rides in choiceOptions, one entry per choice. Reconciled
        # from the palette file, so correcting a colour is a data edit.
        pal = CHOICE_PALETTES.get(cid) or {}
        want_opts = {v: {"fillColor": pal[v]["hex"], "textColor": pal[v]["text"]}
                     for v in (current | add) if v in pal}
        opts_changed = any(have_opts.get(k) != v for k, v in want_opts.items())
        if not add and not opts_changed:
            continue
        if add:
            opts["choices"] = sorted(current | add)
            changes.append((cid, "choices", f"+{sorted(add)}"))
        if opts_changed and want_opts:
            merged = dict(have_opts)
            merged.update(want_opts)
            opts["choiceOptions"] = merged
            changes.append((cid, "colours", f"{len(want_opts)} tag(s)"))
        payload.append({"id": cid,
                        "fields": {"widgetOptions": json.dumps(opts)}})
    # One PATCH for every column: the endpoint takes an array, and a single
    # request cannot half-apply the way five sequential ones could.
    if payload and not dry:
        g.call("PATCH", f"/docs/{doc_id}/tables/{TABLE_ID}/columns",
               {"columns": payload})
    return changes


# ---------------------------------------------------------------------------
# payload
# ---------------------------------------------------------------------------
def fields_for(row):
    """Grist `fields` payload for one aggregated row.

    `row["deleted"]` is surfaced as `Retired`, mirroring the Notion column
    rename: the pipeline field keeps its name, only the label the user reads
    changed. None is used rather than "" so an unmeasured value is blank instead
    of an empty string masquerading as data.
    """
    f = {
        "Key": row["key"],
        "Model": row["model"],
        "Run": row["run"],
        "Run_Dir": row["run_dir"],
        "Endpoint": row.get("endpoint") or None,
        "Date": to_epoch(row.get("date")),
        "Frontier": bool(row["frontier"]),
        "Retired": bool(row["deleted"]),
        "Latest": bool(row.get("latest")),
    }
    for cid, field in CHOICE_FIELDS.items():
        f[cid] = row.get(field) or None
    for cid, field in NUM_COLS.items():
        v = row.get(field)
        f[cid] = v if isinstance(v, (int, float)) else None
    return f


def push(g, doc_id, rows, dry=False):
    records = [{"require": {"Key": r["key"]}, "fields": fields_for(r)}
               for r in rows]
    if dry:
        return 0
    written = 0
    for i in range(0, len(records), BATCH):
        chunk = records[i:i + BATCH]
        g.upsert(doc_id, TABLE_ID, chunk)
        written += len(chunk)
        print(f"    ... {written}/{len(records)}")
    return written


def prune(g, doc_id, keep, dry=False):
    """Remove records whose model no host can still load.

    Upsert cannot express the publish rule: a key that stops being published is
    never written again, so it would sit in the table forever. This table is meant
    to BE the fleet (see loadability.py), so a key outside the published set is
    removed. The run dirs are untouched, so a model declared again reappears on the
    very next push. Notion twin: `push_to_notion.prune()`.
    """
    stale = [(r["id"], (r.get("fields") or {}).get("Key"))
             for r in g.records(doc_id, TABLE_ID)
             if (r.get("fields") or {}).get("Key") not in keep]
    if not stale:
        print("  prune: nothing stale")
        return 0
    if not dry:
        g.call("POST", f"/docs/{doc_id}/apply",
               [["RemoveRecord", TABLE_ID, rid] for rid, _ in stale])
    print(f"  prune: {len(stale)} stale record(s) "
          + ("would be removed" if dry else "removed"))
    for _rid, k in sorted(stale, key=lambda t: t[1] or "")[:25]:
        print(f"    - {k}")
    if len(stale) > 25:
        print(f"    ... and {len(stale) - 25} more")
    return len(stale)


# ---------------------------------------------------------------------------
# verification
# ---------------------------------------------------------------------------
def check(g, doc_id, rows):
    """Read the table back and compare against the rows we meant to write.

    A push that returns 200 is not evidence the data landed correctly. This
    re-reads every record and diffs it field by field, so a wrong date encoding
    or a dropped Choice value shows up here instead of in a chart later.
    """
    stored = {r["fields"].get("Key"): r["fields"]
              for r in g.records(doc_id, TABLE_ID)}
    print(f"  rows in Grist: {len(stored)}")
    print(f"  rows expected: {len(rows)}")

    problems = []
    missing = [r["key"] for r in rows if r["key"] not in stored]
    extra = [k for k in stored if k not in {r["key"] for r in rows}]
    if missing:
        problems.append(f"{len(missing)} rows missing, e.g. {missing[:3]}")
    if extra:
        problems.append(f"{len(extra)} unexpected rows, e.g. {extra[:3]}")

    mismatched = 0
    examples = []
    for r in rows:
        got = stored.get(r["key"])
        if got is None:
            continue
        exp = fields_for(r)
        for k, want in exp.items():
            have = got.get(k)
            if isinstance(want, float) or isinstance(have, float):
                same = (want is None and have is None) or (
                    isinstance(have, (int, float)) and isinstance(want, (int, float))
                    and abs(have - want) < 0.011)
            else:
                same = have == want
            if not same:
                mismatched += 1
                if len(examples) < 6:
                    examples.append(f"{r['key']}.{k}: want {want!r} got {have!r}")
    if mismatched:
        problems.append(f"{mismatched} field mismatches")
        for e in examples:
            print(f"    {e}")

    if problems:
        print("  VERIFY FAILED:")
        for p in problems:
            print(f"    - {p}")
        return 1
    print("  VERIFY OK: every row present, every field matches")
    return 0


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--init", action="store_true",
                    help="create the doc and table, then exit")
    ap.add_argument("--all", action="store_true",
                    help="backfill every run directory under --root")
    ap.add_argument("--results-dir", help="one run directory to push")
    ap.add_argument("--root", default=P.DEFAULT_RESULTS)
    ap.add_argument("--dry-run", action="store_true", help="write nothing")
    ap.add_argument("--check", action="store_true",
                    help="read back and diff against the source runs")
    ap.add_argument("--no-arch", action="store_true",
                    help="skip GGUF architecture resolution")
    args = ap.parse_args()

    state = read_state()
    g = Grist(load_api_key())

    if args.init:
        init_doc(g, state, dry=args.dry_run)
        return 0

    doc_id = state.get("doc_id")
    if not doc_id:
        raise SystemExit("No Grist doc recorded. Run --init first.")

    if args.check and not (args.all or args.results_dir):
        runs = P.discover_runs(args.root)
    elif args.all:
        runs = P.discover_runs(args.root)
    elif args.results_dir:
        d = os.path.abspath(os.path.expanduser(args.results_dir))
        rid = os.path.relpath(d, args.root)
        if rid.startswith(".."):
            rid = os.path.basename(d)
        runs = [(rid, d)]
    else:
        raise SystemExit("pass --init, --all, --results-dir, or --check")

    registry = P.M.load_machines()
    rows = []
    for rid, dirpath in runs:
        rows.extend(P.aggregate(rid, dirpath, registry))
    print(f"{len(runs)} run dirs -> {len(rows)} rows")

    if not args.no_arch:
        ids = sorted({r["model"] for r in rows})
        arches = P.MF.resolve_base_arch(ids)
        for r in rows:
            r["base_arch"] = arches.get(r["model"])
        print(f"  base architecture resolved for {len(arches)}/{len(ids)} models")

    P.mark_latest(rows)
    print(f"  latest flagged for {sum(1 for r in rows if r['latest'])} "
          f"(machine, family, model) triple(s)")

    if args.dry_run:
        print("\nschema changes:")
        for c in ensure_schema(g, doc_id, dry=True):
            print(f"  would add column {c}")
        print("\nchoice/colour changes:")
        for cid, kind, detail in sync_choices(g, doc_id, rows, dry=True):
            print(f"  {cid}: {kind} {detail}")
        print()
        P.show(rows[:8])
        prune(g, doc_id, {r["key"] for r in rows}, dry=True)
        print(f"\n(dry run: {len(rows)} rows would be upserted, nothing written)")
        return 0

    if args.check:
        return check(g, doc_id, rows)

    added = ensure_schema(g, doc_id)
    if added:
        print(f"  added columns: {', '.join(added)}")
    for cid, kind, detail in sync_choices(g, doc_id, rows):
        print(f"  {cid} {kind}: {detail}")

    print(f"  rows csv -> {P.write_csv(rows)}")
    print(f"\nupserting {len(rows)} rows -> {DOC_NAME}/{TABLE_ID}")
    n = push(g, doc_id, rows)
    print(f"  wrote {n} records")
    prune(g, doc_id, {r["key"] for r in rows})

    rc = check(g, doc_id, rows)
    print(f"\n  {state.get('url')}")
    return rc


if __name__ == "__main__":
    sys.exit(main())
