#!/usr/bin/env python3
"""Cross-sink diff: Notion table vs Grist table, key-for-key, field-for-field.

The Grist sink grades itself in `check()`, which proves it wrote what it meant
to. That is not the same as proving the two sinks AGREE. This reads both live
and diffs them, so a divergence in the shared transform would surface as rows
that differ between the destinations.

Read-only. Writes nothing to either side.
"""
import os
import sys

SKILL = os.path.expanduser(
    "~/.hermes/skills/mlops/evaluation/benchmark-model-fleet/scripts")
sys.path.insert(0, SKILL)

from grist_client import Grist, load_api_key as grist_key, read_state  # noqa: E402
from notion_client import Notion, load_api_key as notion_key  # noqa: E402
import grist_sink as GS  # noqa: E402

# Notion property name -> Grist column id
MAP = {
    "Model": "Model", "Run": "Run", "Run Dir": "Run_Dir",
    "Endpoint": "Endpoint", "Machine": "Machine", "Family": "Family",
    "Model Family": "Model_Family", "Base Architecture": "Base_Architecture",
    "Type": "Type", "Speed tok/s": "Speed_tok_s", "Quality": "Quality",
    "Chars": "Chars", "Size GB": "Size_GB", "tok/s per GB": "Efficiency",
    "Frontier": "Frontier", "Retired": "Retired", "Prompts": "Prompts",
    "Rows": "Rows", "Errors": "Errors", "Latest": "Latest",
}


def plain(prop):
    """Flatten one Notion property value to a scalar."""
    t = prop.get("type")
    if t == "title":
        return "".join(x.get("plain_text", "") for x in prop["title"]) or None
    if t == "rich_text":
        return "".join(x.get("plain_text", "") for x in prop["rich_text"]) or None
    if t == "select":
        return (prop.get("select") or {}).get("name")
    if t == "number":
        return prop.get("number")
    if t in ("checkbox",):
        return bool(prop.get(t))
    if t == "date":
        return (prop.get("date") or {}).get("start")
    return None


def read_notion():
    api = Notion(notion_key())
    st = GS.read_state()  # grist state; notion ids come from its own state
    from notion_client import read_state as notion_state
    ns = notion_state()
    ds = ns["data_source_id"]
    out, cursor = {}, None
    while True:
        body = {"page_size": 100}
        if cursor:
            body["start_cursor"] = cursor
        res = api("POST", f"/data_sources/{ds}/query", body)
        for page in res.get("results", []):
            props = page.get("properties", {})
            key = plain(props.get("Key", {}))
            if key:
                out[key] = {p: plain(props.get(p, {})) for p in MAP}
        if not res.get("has_more"):
            return out
        cursor = res.get("next_cursor")


def read_grist():
    st = read_state()
    g = Grist(grist_key())
    out = {}
    for r in g.records(st["doc_id"], st["table_id"]):
        f = r["fields"]
        key = f.get("Key")
        if key:
            out[key] = f
    return out


def same(a, b):
    if a is None and b is None:
        return True
    if isinstance(a, bool) or isinstance(b, bool):
        return bool(a) == bool(b)
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return abs(a - b) < 0.011
    return a == b


def main():
    n = read_notion()
    g = read_grist()
    print(f"Notion rows: {len(n)}")
    print(f"Grist  rows: {len(g)}")

    problems = []
    only_n = sorted(set(n) - set(g))
    only_g = sorted(set(g) - set(n))
    if only_n:
        problems.append(f"{len(only_n)} keys only in Notion, e.g. {only_n[:3]}")
    if only_g:
        problems.append(f"{len(only_g)} keys only in Grist, e.g. {only_g[:3]}")

    mismatches = {}
    for key in sorted(set(n) & set(g)):
        for np, gc in MAP.items():
            a, b = n[key].get(np), g[key].get(gc)
            # Notion's Date is an ISO string; Grist's is epoch seconds.
            if gc == "Date":
                b = GS.from_epoch(b)
            if not same(a, b):
                mismatches.setdefault(f"{np} -> {gc}", []).append(
                    (key, a, b))
    if mismatches:
        problems.append(f"{len(mismatches)} differing field(s)")
        for field, items in sorted(mismatches.items()):
            print(f"\n  {field}: {len(items)} row(s)")
            for key, a, b in items[:3]:
                print(f"     {key}\n       notion={a!r}\n       grist ={b!r}")

    if problems:
        print("\nCROSS-SINK DIFF: NOT CLEAN")
        for p in problems:
            print(f"  - {p}")
        return 1
    print("\nCROSS-SINK DIFF: CLEAN -- all "
          f"{len(n)} keys and {len(MAP)} fields agree across both sinks")
    return 0


if __name__ == "__main__":
    sys.exit(main())
