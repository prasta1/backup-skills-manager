#!/usr/bin/env python3
"""Declarative Grist charts for the fleet benchmark table.

The Grist equivalent of notion_views.py: a view SPEC is declared here and
reconciled on every run, so the charts are reproducible and script-owned rather
than hand-dragged and then lost.

The action API is undocumented for views, so everything below comes from
grist-core rather than from guesswork:

  GristDoc._addPage():
    ["CreateViewSection", tableRef, 0, type, columns, tableId]
       viewRef 0  -> create a NEW page
       returns       {tableRef, viewRef, sectionRef} in `retValues`

  ChartView.chartTypes: a chart section's AXES ARE ITS FIELD LIST, and the
  arity differs by type -- see CHART_FIELD_ARITY.

  ViewSectionRec: `this._savedFilters = recordSet(this, docModel.filters,
  "viewSectionRef")` and the section's row filter is built from THOSE rows.
  So filters live in `_grist_Filters {viewSectionRef, colRef, filter, pinned}`.
  `_grist_Views_section.filterSpec` also exists, but the client does not read it
  to filter the widget -- writing it is a silent no-op.

THREE traps, each of which failed silently before being found:

  1. A fresh chart section arrives with TWO DEFAULT FIELDS already on it (the
     table's first two columns). Re-point or remove them; appending yields four
     series.
  2. `read_views()` is a snapshot. A create/rename invalidates it, and adoption
     must record which page it consumed or every spec adopts the same one.
  3. Filters belong in `_grist_Filters`, NOT in `_grist_Views_section.filterSpec`.

Titles, page names and descriptions are all declared below and reconciled, so
a description can never drift from the chart it describes.

Usage:
    python3 scripts/grist_views.py --list      # what exists now
    python3 scripts/grist_views.py --dry-run   # show the plan
    python3 scripts/grist_views.py             # reconcile (idempotent)
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from grist_client import Grist, load_api_key, read_state, write_state  # noqa: E402

# Fields per chart type. Get this wrong and the chart renders EMPTY, silently:
# bar/line/area call basicPlot(series) which plots series.slice(1) against
# series[0]; scatter calls basicPlot(series.slice(1), {text: series[0].values})
# and so needs a LABEL field in front.
CHART_FIELD_ARITY = {
    "bar": 2, "line": 2, "area": 2,        # X, Y
    "scatter": 3,                          # LABEL, X, Y
    "pie": 2, "donut": 2,                  # labels, values
}

STUDIO = "Mac Studio M3 Ultra"
MACBOOK = "MacBook Pro M5"

# Every review chart is pinned to ONE task family, to the newest measurement of
# each model, and to live models. Three separate reasons, all found by reading
# the rendered chart rather than the config:
#
#   Family: speed, quality AND the frontier are only comparable within one task
#     family. `Frontier` is computed per (machine x family), so a chart that
#     mixes families superimposes several different frontiers on one axis -- and
#     it put unreliable vision speeds (1.4-80.8 tok/s for a single model) on a
#     speed axis. Mixing also broke the chart's own premise: the Studio
#     "Current fleet" chart drew 41 points for 22 models, one per family row
#     (ms-kat-coder-v2.5 plotted 4 times, ms-devstral-24b 4 times).
#   Latest: `Frontier` is computed over EVERY measurement ever taken, so the
#     frontier charts replayed five runs of the same model -- the Studio
#     frontier scatter drew 23 points for 8 models. Frontier + Latest is the
#     current frontier, which is what the fleet report's VERDICT block shows.
#   Retired: frontier charts carried no retirement filter, so pruned models
#     (ms-nuextract3, ms-gpt-oss-20b) sat on the keep list.
#
# `coding` is pinned for the speed charts because it is the canonical benchmark
# family and the only one with a row for every live model on both boxes. Pinning
# it also drops the three all-NULL vision rows and the known-bad 5.62 tok/s
# cold-start figure for ms-hermes-4.3-36b, which are other families.
def _filter(family="coding", **kw):
    """Compose a filter spec: one family, newest measurement, live models only."""
    out = {"Family": {"included": [family]},
           "Latest": {"included": [True]},
           "Retired": {"excluded": [True]}}
    out.update(kw)
    return out


VIEWS = [
    {
        "name": "Speed vs Quality",
        "title": "Frontier · Studio",
        "chart": "scatter",
        "fields": ["Model", "Speed_tok_s", "Quality"],     # LABEL, X, Y
        "filter": _filter(Frontier={"included": [True]}, Machine={"included": [STUDIO]}),
    },
    {
        "name": "Speed vs Quality (MacBook)",
        "title": "Frontier · MacBook",
        "chart": "scatter",
        "fields": ["Model", "Speed_tok_s", "Quality"],
        "filter": _filter(Frontier={"included": [True]}, Machine={"included": [MACBOOK]}),
    },
    {
        "name": "Quality by model",
        "title": "Quality (frontier)",
        "chart": "bar",
        "fields": ["Model", "Quality"],
        "filter": _filter(Frontier={"included": [True]}),
    },
    {
        "name": "Quality by model family",
        "title": "Quality by family (frontier)",
        "chart": "bar",
        "fields": ["Model_Family", "Quality"],
        "filter": _filter(Frontier={"included": [True]}),
    },
    {
        "name": "Speed by model (Studio)",
        "title": "Speed tok/s (frontier)",
        "chart": "bar",
        "fields": ["Model", "Speed_tok_s"],
        "filter": _filter(Frontier={"included": [True]}, Machine={"included": [STUDIO]}),
    },
    # "Present state" rather than "history": one point per model, newest
    # measurement only, live models only. This is the view that was impossible
    # before the Latest flag -- it is what an unfiltered chart was reaching for
    # and getting wrong (92% of rows are repeat measurements).
    {
        "name": "Current · Studio",
        "title": "Current fleet · Studio",
        "chart": "scatter",
        "fields": ["Model", "Speed_tok_s", "Quality"],
        "filter": _filter(Machine={"included": [STUDIO]}),
    },
    {
        "name": "Current · MacBook",
        "title": "Current fleet · MacBook",
        "chart": "scatter",
        "fields": ["Model", "Speed_tok_s", "Quality"],
        "filter": _filter(Machine={"included": [MACBOOK]}),
    },
    # The other two families get their own charts rather than sharing one: speed
    # and the frontier are per family, so they cannot be overlaid.
    {
        "name": "Tool calling · Studio",
        "title": "Tool calling · Studio",
        "chart": "scatter",
        "fields": ["Model", "Speed_tok_s", "Quality"],
        "filter": _filter(family="tool_calling", Machine={"included": [STUDIO]}),
    },
    {
        "name": "Tool calling · MacBook",
        "title": "Tool calling · MacBook",
        "chart": "scatter",
        "fields": ["Model", "Speed_tok_s", "Quality"],
        "filter": _filter(family="tool_calling", Machine={"included": [MACBOOK]}),
    },
    {
        "name": "Vision · Studio",
        "title": "Vision · Studio",
        "chart": "bar",
        "fields": ["Model", "Quality"],
        # Quality ONLY, deliberately: no vision row ever carries Frontier (the
        # pareto is suppressed for this family) and this skill's own rule is that
        # vision tok/s is not plottable -- 1.4 to 80.8 tok/s for one model across
        # prompts. Blank scores are excluded so the three unscored rows from the
        # bare `csvs` dir do not draw empty bars.
        "filter": _filter(family="vision", Quality={"excluded": [None]},
                          Machine={"included": [STUDIO]}),
    },
    {
        "name": "Vision · MacBook",
        "title": "Vision · MacBook",
        "chart": "bar",
        "fields": ["Model", "Quality"],
        "filter": _filter(family="vision", Quality={"excluded": [None]},
                          Machine={"included": [MACBOOK]}),
    },
]

# A fresh doc's raw-data page is called "Table1", which says nothing about what
# is in it. There is no API to delete a table, and this page is genuinely useful
# (it is the whole-history view), so it is renamed and described rather than
# hidden.
BASE_PAGE = "All results"

# One description per page: what question it answers and what it is filtered to.
# Reconciled on every run, like every other part of the view.
DESCRIPTIONS = {
    BASE_PAGE:
        "Every measurement ever pushed: one row per run x machine x family x "
        "model. Full history on purpose, so most rows are repeat measurements of "
        "the same model. Filter Latest for present state, Frontier for the "
        "tradeoff curve.",
    "Speed vs Quality":
        "Studio only, coding family only. The CURRENT frontier: Frontier and "
        "Latest true, retired models excluded, one point per model. Frontier is "
        "computed per machine and task family, so neither speed nor the "
        "frontier is comparable across families or across boxes.",
    "Speed vs Quality (MacBook)":
        "MacBook only, coding family only. The CURRENT frontier: Frontier and "
        "Latest true, retired models excluded, one point per model.",
    "Quality by model":
        "Current coding frontier models ranked by mean quality (mean of "
        "quality_score over non-error rows; a genuine zero counts). One bar per "
        "model: Frontier + Latest, retired excluded.",
    "Quality by model family":
        "Current coding frontier models' mean quality, grouped by model family "
        "(qwen, gemma, devstral, ...). The family is read from the model id.",
    "Speed by model (Studio)":
        "Studio only, coding family only. Current frontier models ranked by "
        "mean tokens/sec (per-prompt median). Per machine because tok/s "
        "measures the hardware as much as the model.",
    "Current · Studio":
        "Newest coding measurement of every live model on the Studio. Present "
        "state, not history: Latest = true, retired models excluded, one point "
        "per model. Other task families are not shown: speed, quality and the "
        "frontier are only comparable within one family.",
    "Current · MacBook":
        "Newest coding measurement of every live model on the MacBook. Present "
        "state, not history: Latest = true, retired models excluded, one point "
        "per model. Other task families are not shown.",
    "Tool calling · Studio":
        "Studio only, tool_calling family only. Latest measurement of every live "
        "model, one point per model. Separate from the coding charts on purpose: "
        "speed and quality are only comparable within one task family.",
    "Tool calling · MacBook":
        "MacBook only, tool_calling family only. Latest measurement of every live "
        "model, one point per model.",
    "Vision · Studio":
        "Studio only, vision family only. Grounded-rubric vision score by model, "
        "newest measurement, live models, ranked by quality. Quality only: no "
        "vision row carries Frontier, and this skill's own rule is that vision "
        "tok/s is not a plottable measurement. Rows with no score are excluded.",
    "Vision · MacBook":
        "MacBook only, vision family only. Grounded-rubric vision score by model, "
        "newest measurement, live models. Quality only, for the same reason: "
        "vision tok/s is not a plottable measurement.",
}


def sql(g, doc, query):
    res = g.call("GET", f"/docs/{doc}/sql", params={"q": query})
    return [r["fields"] for r in (res or {}).get("records", [])]


def col_ref_map(g, doc, table_ref):
    rows = sql(g, doc, "SELECT id, colId FROM _grist_Tables_column "
                       f"WHERE parentId = {table_ref}")
    return {r["colId"]: r["id"] for r in rows}


def table_ref(g, doc, table_id):
    for r in sql(g, doc, "SELECT id, tableId FROM _grist_Tables"):
        if r["tableId"] == table_id:
            return r["id"]
    raise SystemExit(f"table {table_id} not found in {doc}")


def section_fields(g, doc, section_ref):
    """LIVE field rows, in axis order. Never cached."""
    return sql(g, doc, "SELECT id, colRef FROM _grist_Views_section_field "
                       f"WHERE parentId = {section_ref} ORDER BY parentPos")


def section_filters(g, doc, section_ref):
    """LIVE filter rows -- the mechanism the client actually reads."""
    return sql(g, doc, "SELECT id, colRef, filter, pinned FROM _grist_Filters "
                       f"WHERE viewSectionRef = {section_ref}")


def read_views(g, doc):
    out = {}
    for v in sql(g, doc, "SELECT id, name FROM _grist_Views ORDER BY id"):
        out[v["name"]] = {"viewRef": v["id"], "sections": []}
    by_ref = {v["viewRef"]: name for name, v in out.items()}
    for s in sql(g, doc, "SELECT id, parentId, parentKey, title, chartType, "
                         "description, tableRef "
                         "FROM _grist_Views_section ORDER BY id"):
        page = by_ref.get(s["parentId"])
        if page is None:
            continue
        out[page]["sections"].append({
            "sectionRef": s["id"], "kind": s["parentKey"], "title": s["title"],
            "chartType": s["chartType"], "description": s["description"],
            "tableRef": s["tableRef"],
            "fields": [f["colRef"] for f in section_fields(g, doc, s["id"])],
            "filters": section_filters(g, doc, s["id"]),
        })
    return out


def chart_section(views, page):
    for s in (views.get(page) or {}).get("sections", []):
        if s["kind"] == "chart":
            return s
    return None


def unclaimed_chart_page(views, claimed, taken):
    """A chart page from an earlier probe, adopted rather than orphaned.

    `taken` is essential: `views` is a snapshot, so without it every spec would
    adopt the SAME page.
    """
    for name, entry in views.items():
        if name in claimed or name in taken:
            continue
        for s in entry["sections"]:
            if s["kind"] == "chart" and not s["chartType"]:
                return name
    return None


def plan_config(spec, refs, live_fields, live_filters):
    """(field_actions, filter_actions, notes) to make one section match its spec."""
    want_refs = [refs[c] for c in spec["fields"]]
    want_arity = CHART_FIELD_ARITY.get(spec["chart"])
    if want_arity and len(want_refs) != want_arity:
        raise SystemExit(
            f"{spec['name']}: chart type {spec['chart']!r} needs {want_arity} "
            f"fields (got {len(want_refs)}) -- a wrong arity renders EMPTY")

    notes = []
    live_ids = [f["id"] for f in live_fields]
    live_refs = [f["colRef"] for f in live_fields]
    if live_refs != want_refs:
        notes.append(f"fields {live_refs} -> {want_refs}")

    f_acts = []
    for i, col_ref in enumerate(want_refs):
        if i < len(live_ids):
            f_acts.append(["UpdateRecord", "_grist_Views_section_field",
                           live_ids[i], {"colRef": col_ref, "parentPos": i + 1}])
        else:
            f_acts.append(["AddRecord", "_grist_Views_section_field", None,
                           {"parentId": spec["sectionRef"], "parentPos": i + 1,
                            "colRef": col_ref}])
    for extra in live_ids[len(want_refs):]:
        f_acts.append(["RemoveRecord", "_grist_Views_section_field", extra])

    # Filters go in _grist_Filters, keyed by column ref.
    want_filters = {refs[c]: flt for c, flt in (spec.get("filter") or {}).items()}
    have = {f["colRef"]: f for f in live_filters}
    fl_acts = []
    for col_ref, flt in want_filters.items():
        blob = json.dumps(flt, sort_keys=True)
        row = have.pop(col_ref, None)
        if row is None:
            fl_acts.append(["AddRecord", "_grist_Filters", None,
                            {"viewSectionRef": spec["sectionRef"],
                             "colRef": col_ref, "filter": blob, "pinned": True}])
            notes.append(f"filter +colRef{col_ref} {blob}")
        elif row["filter"] != blob:
            fl_acts.append(["UpdateRecord", "_grist_Filters", row["id"],
                            {"filter": blob, "pinned": True}])
            notes.append(f"filter colRef{col_ref} -> {blob}")
    for stale in have.values():
        fl_acts.append(["RemoveRecord", "_grist_Filters", stale["id"]])
        notes.append(f"filter -colRef{stale['colRef']}")

    return f_acts, fl_acts, notes


def reconcile_base(g, doc, tref, dry=False):
    """Name and describe the whole-history view.

    A fresh doc ships this page as "Table1". Renaming it changes the page label
    only -- the underlying table id stays `Results`, so every record, chart
    binding and filter keeps working.
    """
    report = []
    views = read_views(g, doc)
    for name, entry in views.items():
        for s in entry["sections"]:
            if s["kind"] == "chart" or s.get("tableRef") != tref:
                continue
            if name != BASE_PAGE:
                report.append(("rename", BASE_PAGE,
                               f"page {name!r} -> {BASE_PAGE!r}"))
                if not dry:
                    g.call("POST", f"/docs/{doc}/apply",
                           [["UpdateRecord", "_grist_Views", entry["viewRef"],
                             {"name": BASE_PAGE}]])
            want = DESCRIPTIONS.get(BASE_PAGE, "")
            if (s.get("description") or "") != want:
                report.append(("update", BASE_PAGE, "description"))
                if not dry:
                    g.call("POST", f"/docs/{doc}/apply",
                           [["UpdateRecord", "_grist_Views_section",
                             s["sectionRef"], {"description": want}]])
            return report
    return report


def reconcile(g, doc, state, dry=False):
    tref = table_ref(g, doc, state["table_id"])
    refs = col_ref_map(g, doc, tref)
    views = read_views(g, doc)
    registry = state.setdefault("views", {})
    report = []
    claimed = {s["name"] for s in VIEWS}
    taken = set()

    for spec in VIEWS:
        page = spec["name"]
        section = chart_section(views, page)
        view_ref = (views.get(page) or {}).get("viewRef")
        # Snapshot state, so the dry run reports everything it would change.
        # A dry run that omits its own edits is how the inert filter hid.
        cur_title = (section or {}).get("title") or ""
        cur_desc = (section or {}).get("description") or ""

        # --- resolve the section: existing page -> adopt a probe page -> create
        if section is None:
            adopt = unclaimed_chart_page(views, claimed, taken)
            if adopt:
                taken.add(adopt)
                view_ref = views[adopt]["viewRef"]
                report.append(("adopt", page, f"page {adopt!r} -> {page!r}"))
                if dry:
                    continue
                g.call("POST", f"/docs/{doc}/apply",
                       [["UpdateRecord", "_grist_Views", view_ref,
                         {"name": page}]])
                adopted = chart_section(views, adopt)
                if adopted is None:
                    raise SystemExit(f"adopt target {adopt!r} lost its chart")
                section = {"sectionRef": adopted["sectionRef"]}
            else:
                report.append(("create", page, "new page + chart"))
                if dry:
                    continue
                ret = g.call("POST", f"/docs/{doc}/apply",
                             [["CreateViewSection", tref, 0, "chart",
                               None, None]])["retValues"][0]
                view_ref, section_ref = ret["viewRef"], ret["sectionRef"]
                g.call("POST", f"/docs/{doc}/apply",
                       [["UpdateRecord", "_grist_Views", view_ref,
                         {"name": page}]])
                section = {"sectionRef": section_ref}

        # Re-read AFTER create/adopt: a new section already carries two fields,
        # and the snapshot is stale the moment a page is renamed.
        live_fields = section_fields(g, doc, section["sectionRef"])
        live_filters = section_filters(g, doc, section["sectionRef"])
        spec = dict(spec, sectionRef=section["sectionRef"])

        want_desc = DESCRIPTIONS.get(page, "")
        if cur_title != spec["title"]:
            report.append(("update", page,
                           f"title {cur_title!r} -> {spec['title']!r}"))
        if cur_desc != want_desc:
            report.append(("update", page, "description"))

        f_acts, fl_acts, notes = plan_config(spec, refs, live_fields,
                                             live_filters)
        if not dry:
            acts = [["UpdateRecord", "_grist_Views_section",
                     section["sectionRef"],
                     {"chartType": spec["chart"], "title": spec["title"],
                      "description": DESCRIPTIONS.get(page, ""),
                      "options": json.dumps({}),
                      # Cleared on purpose: this column does NOT drive widget
                      # filtering (see module docstring). An earlier version
                      # wrote filters here and they were silently ignored, so a
                      # stale value left behind would mislead the next reader.
                      "filterSpec": "[]"}]]
            g.call("POST", f"/docs/{doc}/apply", acts + f_acts + fl_acts)
            registry[page] = {"viewRef": view_ref,
                              "sectionRef": section["sectionRef"]}
        for n in notes:
            report.append(("update", page, n))

    report.extend(reconcile_base(g, doc, tref, dry=dry))

    if not dry:
        write_state(state)
    return report


def verify(g, doc, state):
    views = read_views(g, doc)
    tref = table_ref(g, doc, state["table_id"])
    refs = col_ref_map(g, doc, tref)
    bad = []
    for spec in VIEWS:
        sec = chart_section(views, spec["name"])
        if not sec:
            bad.append(f"{spec['name']}: no chart section on that page")
            continue
        want = [refs[c] for c in spec["fields"]]
        if sec["fields"] != want:
            bad.append(f"{spec['name']}: fields {sec['fields']} != {want}")
        if sec["chartType"] != spec["chart"]:
            bad.append(f"{spec['name']}: chartType {sec['chartType']!r} "
                       f"!= {spec['chart']!r}")
        if not (sec.get("description") or "").strip():
            bad.append(f"{spec['name']}: section has no description")
        by_colref = {f["colRef"]: f["filter"] for f in sec["filters"]}
        for colid, flt in (spec.get("filter") or {}).items():
            got = by_colref.get(refs[colid])
            if got is None:
                bad.append(f"{spec['name']}: no _grist_Filters row for {colid}")
            elif json.loads(got) != flt:
                bad.append(f"{spec['name']}: filter {colid} {got} != {flt}")
    if BASE_PAGE not in views:
        bad.append(f"base page {BASE_PAGE!r} missing (is it still 'Table1'?)")
    else:
        for s in views[BASE_PAGE]["sections"]:
            if s["kind"] != "chart" and not (s.get("description") or "").strip():
                bad.append(f"the {BASE_PAGE!r} view has no description")
    if bad:
        print("  VIEW VERIFY FAILED:")
        for b in bad:
            print(f"    - {b}")
        return 1
    print(f"  VIEW VERIFY OK: {len(VIEWS)} charts + the {BASE_PAGE!r} view "
          f"match their specs")
    for spec in VIEWS:
        sec = chart_section(views, spec["name"])
        print(f"    {spec['name']:<27} {spec['chart']:<8} "
              f"{len(spec['fields'])} field(s), "
              f"{len(sec['filters'])} filter(s), described")
    return 0


def main():
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--list", action="store_true")
    args = ap.parse_args()

    state = read_state()
    doc = state.get("doc_id")
    if not doc:
        raise SystemExit("no Grist doc recorded; run grist_sink.py --init first")
    g = Grist(load_api_key())

    if args.list:
        for name, entry in read_views(g, doc).items():
            print(f"  page {name!r} (viewRef {entry['viewRef']})")
            for s in entry["sections"]:
                print(f"    section {s['sectionRef']} kind={s['kind']} "
                      f"chart={s['chartType']!r} title={s['title']!r} "
                      f"fields={s['fields']}")
                desc = (s.get("description") or "").strip()
                print(f"      description: {desc[:90] or '(none)'}"
                      f"{'...' if len(desc) > 90 else ''}")
                for f in s["filters"]:
                    print(f"      filter colRef={f['colRef']} "
                          f"pinned={f['pinned']} {f['filter']}")
        return 0

    report = reconcile(g, doc, state, dry=args.dry_run)
    label = "dry run" if args.dry_run else "reconciled"
    print(f"  {label} — {len(report)} change(s) across {len(VIEWS)} charts")
    for action, page, detail in report:
        print(f"    {action:<8} {page:<30} {detail}")
    if args.dry_run:
        return 0
    return verify(g, doc, state)


if __name__ == "__main__":
    sys.exit(main())
