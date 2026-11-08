#!/usr/bin/env python3
"""Notion-native views for the fleet table, plus the frontier charts.

Two jobs:

1. **Views.** A declarative spec of chart/KPI views, reconciled after each push:
   create when the recorded view is gone, PATCH when it exists, and never touch a
   view this script never created.

   There is NO endpoint to list a database's views -- `GET /v1/databases/<id>/views`
   returns `invalid_request_url` -- so idempotency cannot come from enumerating
   them. It comes from `state["views"]`, a key -> view_id registry in
   references/notion.json. A recorded id that 404s on PATCH was deleted in the UI,
   so the view is recreated; that is the self-healing path.

2. **The frontier scatter.** Notion cannot draw a scatter plot, and the speed x
   quality frontier is this skill's central visual, so it is rendered per run and
   uploaded into Notion as an image block rather than left as a loose PNG. Blocks
   ARE listable, so idempotency here is a caption marker.

Wire shapes below were derived from the API's own validation errors and from
reading back views created through the MCP; several are not documented anywhere.
"""
import glob
import json
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import uuid

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from notion_client import RENAMES, rt, write_state  # noqa: E402

# Property ids harvested 2026-10-27. They are STABLE per data source (Quality is
# "g:\\i" whether read from a table view or a chart's y-axis), but they are opaque
# and regenerated if the database is, so resolve_property_ids() prefers a live
# read and only falls back to this map.
DEFAULT_PROPERTY_IDS = {
    "Model": "title",
    "Machine": "W~Vc",
    "Family": "\\oD_",
    "Run": "fKEY",
    "Date": "LTE\\",
    "Type": "h~wp",
    "Endpoint": "w;Qw",
    "Run Dir": "lCxJ",
    "Key": "Iz|t",
    "Speed tok/s": "rnkP",
    "Quality": "g:\\i",
    "Chars": "XxVh",
    "Size GB": "Bm~q",
    "tok/s per GB": "YmAT",
    "Prompts": "O{ea",
    "Rows": "\\m:_",
    "Errors": "jroH",
    "Frontier": "{zvz",
    "Retired": "GEuD",
}

# Caption prefix marking an image block this script owns. Re-pushing the same run
# must not stack a second copy of its charts on the page.
CAPTION_MARK = "◆"


def short_machine(name):
    """'Mac Studio M3 Ultra' -> 'Studio M3 Ultra'. Keeps speed charts readable
    without hardcoding the roster."""
    return name[4:] if name.startswith("Mac ") else name


def read_machine_names(api, data_source_id):
    """Machine names taken from the DATA SOURCE's own select options.

    Do NOT derive these from endpoints.json. The registry lists the Studio twice
    (local + tailnet) and the MBP twice (tailnet + loopback), and _host_label
    renders the same physical box as both 'Mac Studio M3 Ultra' and 'Mac Studio'.
    That produced two speed charts per machine -- one of them always empty. The
    select options are already deduped, because they were built from the machine
    each row actually ran on.
    """
    try:
        ds = api("GET", f"/data_sources/{data_source_id}")
    except SystemExit:
        return []
    opts = (((ds.get("properties") or {}).get("Machine") or {})
            .get("select") or {}).get("options") or []
    return [o["name"] for o in opts if o.get("name") and o["name"] != "unassigned"]


# ---------------------------------------------------------------------------
# property ids
# ---------------------------------------------------------------------------
def _harvest(view):
    """{property_name: property_id} from a view's configuration.

    A table view's configuration lists EVERY property with a visibility flag, not
    just the displayed ones, which makes any view a full id map.
    """
    cfg = view.get("configuration") or {}
    out = {}
    for p in cfg.get("properties") or []:
        if p.get("property_name") and p.get("property_id"):
            out[p["property_name"]] = p["property_id"]
    for axis in ("x_axis", "y_axis", "value"):
        a = cfg.get(axis) or {}
        if a.get("property_name") and a.get("property_id"):
            out[a["property_name"]] = a["property_id"]
    return out


class StaleIdCache(Exception):
    """Property ids are unknown and a dry run may not create the probe view."""


def _live_property_names(api, state):
    """Property NAMES on the data source, or None if unreadable."""
    try:
        ds = api("GET", f"/data_sources/{state['data_source_id']}")
    except SystemExit:
        return None
    return set((ds.get("properties") or {}).keys())


def resolve_property_ids(api, state, dry=False):
    """{property_name: property_id} for this data source, cached in state.

    No endpoint lists a data source's property ids, and a BARE view exposes none
    either -- its configuration comes back as just {"type": "table"}. The move
    that works is a throwaway table view whose configuration names properties:
    the server then echoes back property_id/property_name for EVERY property on
    the data source, including ones the request never mentioned.

    Two things this has to survive, both of which bit during development:
      * a RENAME leaves a stale key, because the map is keyed by name;
      * a NEW column is invisible to a cache built before it existed, so the
        cache is checked against the live schema rather than trusted blindly.
    """
    cached = state.get("property_ids") or {}
    if cached:
        # The map is keyed by property NAME, so a rename leaves a stale key
        # behind and every lookup of the new name misses. The id is unchanged.
        for old, new in RENAMES.items():
            if old in cached and new not in cached:
                cached[new] = cached.pop(old)
        live = _live_property_names(api, state)
        if live is None or not (live - set(cached)):
            return cached
        missing = sorted(live - set(cached))
        if dry:
            # The probe creates and deletes a real view; a dry run must not.
            raise StaleIdCache(missing)
        print(f"    property-id cache is missing {len(missing)} new column(s) "
              f"({', '.join(missing)}); refreshing")
    ids = dict(DEFAULT_PROPERTY_IDS)
    ids.update(cached)
    if dry:
        return ids
    cfg = {"type": "table",
           "properties": [{"property_id": i, "visible": True}
                          for i in dict.fromkeys(ids.values())]}
    try:
        probe = api("POST", "/views", {
            "database_id": state["database_id"],
            "data_source_id": state["data_source_id"],
            "name": f"__property-probe__{uuid.uuid4().hex[:6]}",
            "type": "table", "configuration": cfg})
    except SystemExit as e:
        # The known ids are being rejected, which is the symptom of a recreated
        # database. Say so loudly -- a silent fallback here would produce views
        # filtering on properties that no longer exist.
        print(f"    property-id probe REJECTED: {str(e)[:160]}")
        print("    falling back to the shipped map; if this database was "
              "recreated its property ids differ and the charts will need "
              "re-bootstrapping (delete references/notion.json)")
        state["property_ids"] = ids
        write_state(state)
        return ids
    try:
        got = _harvest(api("GET", f"/views/{probe['id']}"))
    finally:
        try:
            api("DELETE", f"/views/{probe['id']}")
        except SystemExit:
            print("    warning: could not delete the property probe view")
    if len(got) >= len(DEFAULT_PROPERTY_IDS) - 1:
        # The probe only NAMES properties; deletions or renames since could mean
        # it lists fewer than we hold, so merge rather than replace.
        merged = dict(ids)
        merged.update(got)
        if len(merged) != len(ids):
            print(f"    property ids refreshed from the server ({len(merged)} properties)")
        ids = merged
    else:
        print(f"    probe returned {len(got)} properties; keeping the known map")
    state["property_ids"] = ids
    write_state(state)
    return ids


# ---------------------------------------------------------------------------
# view specs
# ---------------------------------------------------------------------------
def _and(*filters):
    """Compound filter as {"and": [...]}.

    NOT the {"type": "group", "operator": "and", "filters": [...]} shape the API
    RETURNS on read -- that form is rejected on write with a wall of
    'body.filter.or should be defined / body.filter.and should be defined...'.
    """
    filters = [f for f in filters if f]
    return filters[0] if len(filters) == 1 else {"and": list(filters)}


def _not_retired(ids):
    """Ids marked as still in service. The column is called `Retired` on the
    table; the pipeline field behind it is still `deleted` (see schema_properties
    in push_to_notion.py for why only the label moved)."""
    return {"property": ids["Retired"], "checkbox": {"does_not_equal": True}}


def _is_retired(ids):
    return {"property": ids["Retired"], "checkbox": {"equals": True}}


def _table_cols(ids, names):
    """configuration.properties for a table view, in display order.

    Only the listed properties are visible; a table created without this shows
    just the title. Property ids are required -- names are rejected."""
    return [{"property_id": ids[n], "visible": True} for n in names if n in ids]


# Columns worth seeing in a table, chosen so the two classification axes sit
# next to each other and the numbers sit next to those.
TABLE_COLUMNS = ["Model", "Model Family", "Base Architecture", "Machine",
                 "Family", "Type", "Run", "Date", "Speed tok/s", "Quality",
                 "Size GB", "tok/s per GB", "Frontier", "Retired"]


def _select(ids, name, value):
    return {"property": ids[name], "select": {"equals": value}}


def build_specs(ids, machine_names):
    """The view set. Machine-specific speed charts are generated per registered
    machine, so adding a machine stays a registry change, not a code change."""
    specs = [{
        "key": "quality_by_model",
        "name": "Quality by Model",
        "type": "chart",
        "filter": _not_retired(ids),
        # Quality IS comparable across machines, so this one is deliberately
        # global. Speed is not -- see the per-machine charts below.
        "configuration": {
            "type": "chart", "chart_type": "bar",
            "x_axis": {"type": "title", "property_id": ids["Model"],
                       "group_by": "exact", "sort": {"type": "ascending"}},
            "y_axis": {"aggregator": "average", "property_id": ids["Quality"]},
            "sort": "y_descending", "color_theme": "blue", "height": "large",
        },
    }]

    for m in machine_names:
        if m == "unassigned":
            continue
        specs.append({
            "key": f"speed_{m}",
            "name": f"Speed by Model · {short_machine(m)}",
            "type": "chart",
            # Hard-filtered to ONE machine and ONE family. A speed chart spanning
            # machines ranks the hardware and reads as a model comparison; this
            # is the same rule the report and the plots follow.
            "filter": _and(_not_retired(ids),
                           _select(ids, "Machine", m),
                           _select(ids, "Family", "coding")),
            "configuration": {
                "type": "chart", "chart_type": "bar",
                "x_axis": {"type": "title", "property_id": ids["Model"],
                           "group_by": "exact", "sort": {"type": "ascending"}},
                "y_axis": {"aggregator": "average", "property_id": ids["Speed tok/s"]},
                "sort": "y_descending", "color_theme": "green", "height": "large",
            },
        })

    specs += [
        {
            "key": "family_mix",
            "name": "Family mix",
            "type": "chart",
            "configuration": {
                "type": "chart", "chart_type": "donut",
                "x_axis": {"type": "select", "property_id": ids["Family"],
                           "sort": {"type": "ascending"}},
                "y_axis": {"aggregator": "count"},
                "height": "medium",
            },
        },
        # Numbers count ROWS, not distinct models -- Notion has no count-distinct,
        # so these are named for what they actually measure.
        {
            "key": "kpi_rows",
            "name": "KPI · Result rows",
            "type": "chart",
            "configuration": {
                "type": "chart", "chart_type": "number",
                "value": {"aggregator": "count"}, "height": "small",
            },
        },
        {
            "key": "kpi_frontier",
            "name": "KPI · Frontier rows",
            "type": "chart",
            "filter": {"property": ids["Frontier"], "checkbox": {"equals": True}},
            "configuration": {
                "type": "chart", "chart_type": "number",
                "value": {"aggregator": "count"}, "height": "small",
            },
        },
        {
            "key": "kpi_disk",
            "name": "KPI · Disk GB (sized rows)",
            "type": "chart",
            "configuration": {
                "type": "chart", "chart_type": "number",
                "value": {"aggregator": "sum", "property_id": ids["Size GB"]},
                "height": "small",
            },
        },
        {
            "key": "quality_by_family",
            "name": "Quality by Model Family",
            "type": "chart",
            "filter": _not_retired(ids),
            # Grouped by the LINE, not by base architecture: this is the
            # at-a-glance "how does each family perform" chart, which is legible
            # at ~18 bars where Quality by Model has ~90.
            "configuration": {
                "type": "chart", "chart_type": "bar",
                "x_axis": {"type": "select", "property_id": ids["Model Family"],
                           "group_by": "exact", "sort": {"type": "ascending"}},
                "y_axis": {"aggregator": "average", "property_id": ids["Quality"]},
                "sort": "y_descending", "color_theme": "purple", "height": "large",
            },
        },
        {
            "key": "by_model_family",
            "name": "By Model Family",
            "type": "board",
            # A BOARD, because the API silently drops groupBy on a table: it
            # accepts the field and reads back null. Grouping a table is a
            # one-click UI action, so a table view is not worth faking here.
            "group_by": {"property": ids["Model Family"],
                         "propertyType": "select", "hideEmptyGroups": True,
                         "sort": {"type": "manual"}},
            "sorts": [{"property": ids["Quality"], "direction": "descending"}],
            "card_layout": "compact",
        },
        {
            "key": "latest_run",
            "name": "Latest run",
            "type": "table",
            "sorts": [{"property": ids["Date"], "direction": "descending"},
                      {"property": ids["Quality"], "direction": "descending"}],
            "configuration": {"type": "table",
                              "properties": _table_cols(ids, TABLE_COLUMNS)},
        },
        {
            "key": "frontier_only",
            "name": "Frontier only",
            "type": "table",
            "filter": {"property": ids["Frontier"], "checkbox": {"equals": True}},
            "sorts": [{"property": ids["Quality"], "direction": "descending"}],
            "configuration": {"type": "table",
                              "properties": _table_cols(ids, TABLE_COLUMNS)},
        },
    ]
    return specs


# ---------------------------------------------------------------------------
# reconciliation
# ---------------------------------------------------------------------------
def reconcile_views(api, state, machine_names=None, dry=False, only=None):
    """Create/PATCH every spec. Returns [(action, name, view_id)].

    Only views recorded in state["views"] are ever PATCHed or recreated; a view
    Patrick made by hand is invisible to this and stays untouched.
    """
    try:
        ids = resolve_property_ids(api, state, dry=dry)
    except StaleIdCache as e:
        print(f"    property ids for {', '.join(e.args[0])} are not cached yet, and "
              f"a dry run cannot create the probe view that discovers them. "
              f"Run without --dry-run to refresh.")
        return []
    if machine_names is None:
        machine_names = read_machine_names(api, state["data_source_id"])
    specs = build_specs(ids, machine_names)
    reg = state.setdefault("views", {})
    results = []
    for spec in specs:
        if only and spec["key"] not in only:
            continue
        body = {
            "database_id": state["database_id"],
            "data_source_id": state["data_source_id"],
            "name": spec["name"],
            "type": spec["type"],
        }
        # groupBy / sorts / cardLayoutMode are VIEW-level fields, siblings of
        # `configuration`, not part of it -- a table's configuration only carries
        # its column list.
        for spec_key, wire_key in (("configuration", "configuration"),
                                   ("filter", "filter"), ("sorts", "sorts"),
                                   ("group_by", "groupBy"),
                                   ("card_layout", "cardLayoutMode")):
            if spec.get(spec_key):
                body[wire_key] = spec[spec_key]

        vid = reg.get(spec["key"])
        if dry:
            results.append(("would-update" if vid else "would-create",
                            spec["name"], vid))
            continue
        if vid:
            try:
                # A dashboard rejects `configuration` outright, and PATCH is where
                # that bites, so only send what the spec actually defines.
                api("PATCH", f"/views/{vid}",
                    {k: body[k] for k in ("name", "configuration", "filter",
                                          "sorts", "groupBy", "cardLayoutMode")
                     if k in body})
                results.append(("updated", spec["name"], vid))
                continue
            except SystemExit as e:
                if "HTTP 404" not in str(e):
                    raise
                # Deleted in the UI. Fall through and recreate it.
                print(f"    '{spec['name']}' is gone; recreating")
        created = api("POST", "/views", body)
        reg[spec["key"]] = created["id"]
        results.append(("created", spec["name"], created["id"]))
        write_state(state)
    return results


# ---------------------------------------------------------------------------
# frontier charts -> image blocks
# ---------------------------------------------------------------------------
def frontier_images(run_dir, timeout=300):
    """Render the coding scatters for one run into a scratch dir.

    Returns [(path, caption)] for the PER-MACHINE charts, because the combined
    one deliberately has no frontier drawn on it. Everything is written to a
    temp dir that the caller removes -- the point is that no chart is left lying
    beside the CSVs.
    """
    merged = os.path.join(run_dir, "model-config.json")
    if not os.path.exists(merged):
        print(f"    no model-config.json in {run_dir} -- skipping charts "
              f"(the merge has to run first)")
        return [], None
    out = tempfile.mkdtemp(prefix="notion-charts-")
    cmd = [sys.executable, os.path.join(HERE, "generate_scatter.py"),
           "--results-dir", run_dir, "--model-config", merged,
           "--output-dir", out, "--no-pdf", "--per-machine"]
    try:
        proc = subprocess.run(cmd, stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT, timeout=timeout)
    except (OSError, subprocess.SubprocessError) as e:
        shutil.rmtree(out, ignore_errors=True)
        print(f"    chart render failed ({e}) -- skipping")
        return [], None
    if proc.returncode != 0:
        shutil.rmtree(out, ignore_errors=True)
        tail = (proc.stdout or b"").decode(errors="replace").strip().splitlines()
        print(f"    chart render exited {proc.returncode} -- skipping. Last output:")
        for line in tail[-6:]:
            print(f"      {line}")
        return [], None

    pngs = [p for p in glob.glob(os.path.join(out, "scatter_coding*.png"))
            if "efficiency" not in os.path.basename(p)]
    per_machine = [p for p in sorted(pngs)
                   if os.path.basename(p) != "scatter_coding.png"]
    items = []
    for p in (per_machine or [p for p in pngs
                              if os.path.basename(p) == "scatter_coding.png"]):
        suffix = os.path.basename(p)[len("scatter_coding"):-len(".png")]
        label = suffix.strip("_").replace("_", " ") or "all machines"
        items.append((p, label))
    return items, out


def page_captions(api, page_id):
    """Set of captions already on a page's image blocks. Blocks ARE listable, so
    this is how re-pushing a run avoids stacking duplicate charts."""
    found, cursor = set(), None
    while True:
        path = f"/blocks/{page_id}/children?page_size=100"
        if cursor:
            path += f"&start_cursor={cursor}"
        try:
            res = api("GET", path)
        except SystemExit:
            return found
        for b in res.get("results", []):
            img = (b.get("image") or {})
            for c in (img.get("caption") or []):
                if c.get("plain_text"):
                    found.add(c["plain_text"])
        if not res.get("has_more"):
            return found
        cursor = res.get("next_cursor")


def _multipart(fields, filename, data, ctype="image/png"):
    """multipart/form-data body. Notion's /send endpoint rejects a raw PUT --
    it wants a file part named 'file', and answers 400 'invalid status of
    pending' if you get it wrong, which reads like a state problem."""
    b = "----hermes" + uuid.uuid4().hex
    body = b""
    for k, v in fields.items():
        body += (f"--{b}\r\nContent-Disposition: form-data; name=\"{k}\"\r\n\r\n"
                 f"{v}\r\n").encode()
    body += (f"--{b}\r\nContent-Disposition: form-data; name=\"file\"; "
             f"filename=\"{filename}\"\r\nContent-Type: {ctype}\r\n\r\n").encode()
    body += data + f"\r\n--{b}--\r\n".encode()
    return body, f"multipart/form-data; boundary={b}"


def upload_images(api, state, items, run_id, dry=False):
    """Upload each rendered chart and append it to the parent page.

    Caption carries the run id so a re-push is a no-op instead of a duplicate.
    """
    page = state.get("parent_page_id")
    if not page:
        print("    no parent page recorded -- skipping chart upload")
        return 0, 0
    have = set() if dry else page_captions(api, page)
    added = skipped = 0
    for path, label in items:
        caption = f"{CAPTION_MARK} {run_id} · {label}"
        if caption in have:
            skipped += 1
            continue
        if dry:
            print(f"    would upload {os.path.basename(path)} as '{caption}'")
            added += 1
            continue
        data = open(path, "rb").read()
        up = api("POST", "/file_uploads",
                 {"filename": os.path.basename(path), "content_type": "image/png"})
        body, ctype = _multipart({}, os.path.basename(path), data)
        req = urllib.request.Request(up["upload_url"], data=body, method="POST")
        req.add_header("Authorization", f"Bearer {api.key}")
        req.add_header("Notion-Version", "2025-09-03")
        req.add_header("Content-Type", ctype)
        with urllib.request.urlopen(req, timeout=120) as r:
            status = json.loads(r.read()).get("status")
        if status != "uploaded":
            print(f"    upload of {os.path.basename(path)} returned {status}")
            continue
        api("PATCH", f"/blocks/{page}/children", {"children": [{
            "object": "block", "type": "image",
            "image": {"type": "file_upload", "file_upload": {"id": up["id"]},
                      "caption": [{"type": "text", "text": {"content": caption}}]},
        }]})
        added += 1
    return added, skipped
