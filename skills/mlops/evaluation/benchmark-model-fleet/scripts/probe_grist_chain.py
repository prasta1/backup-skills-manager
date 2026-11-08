#!/usr/bin/env python3
"""Probe the Grist primitive chain end to end, then clean up after itself.

Answers three things the sink's design depends on, none of which should be
assumed:
  1. Does POST /workspaces/{id}/docs + POST /docs/{id}/tables work as documented?
  2. Does a `Choice` column ACCEPT a value outside its declared choice list, or
     silently drop it? (Notion's equivalent trap dropped properties without
     erroring, and it went unnoticed until a read-back.)
  3. Is PUT .../records with `require` genuinely idempotent on re-run?

Creates a throwaway doc and deletes it at the end.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from grist_client import Grist, load_api_key  # noqa: E402

ORG_ID = 236614
WORKSPACE_ID = 250813
TABLE = "Probe"

CHOICES = ["Mac Studio M3 Ultra", "MacBook Pro M5", "unassigned"]


def main():
    g = Grist(load_api_key(), verbose=True)
    print("=== 1. create doc ===")
    doc = g.create_doc(WORKSPACE_ID, "schema-probe-tmp")
    print(f"doc id: {doc!r}  ({type(doc).__name__})")
    if not doc:
        return 1

    try:
        print("\n=== 2. tables in a fresh doc (expect none) ===")
        print("   ", g.tables(doc))

        print("\n=== 3. create table + columns in ONE call ===")
        g.add_table(doc, TABLE, [
            {"id": "Key", "fields": {"label": "Key", "type": "Text"}},
            {"id": "Machine", "fields": {
                "label": "Machine", "type": "Choice",
                "widgetOptions": json.dumps({"choices": CHOICES})}},
            {"id": "Speed", "fields": {"label": "Speed tok/s", "type": "Numeric"}},
            {"id": "Retired", "fields": {"type": "Bool"}},
        ])
        cols = g.columns(doc, TABLE)
        print("   columns created:")
        for c in cols:
            f = c.get("fields", {})
            print(f"     id={c['id']:<10} label={f.get('label')!r:<18} "
                  f"type={f.get('type')}")

        print("\n=== 4. THE QUESTION: write a Choice value NOT in the list ===")
        print(f"   declared choices: {CHOICES}")
        print("   writing Machine='GrowthTest' ...")
        g.upsert(doc, TABLE, [
            {"require": {"Key": "probe|growth"}, "fields": {
                "Key": "probe|growth", "Machine": "GrowthTest",
                "Speed": 12.5, "Retired": False}}])
        recs = g.records(doc, TABLE)
        got = recs[0]["fields"] if recs else {}
        print(f"   read back: {json.dumps(got, default=str)}")
        machine = got.get("Machine")
        if machine == "GrowthTest":
            print("   RESULT: ACCEPTED -- Grist auto-extends the choice list. "
                  "Choice is safe for columns that grow.")
        elif machine in (None, ""):
            print("   RESULT: DROPPED SILENTLY -- do NOT use Choice for "
                  "columns that grow. Use Text.")
        else:
            print(f"   RESULT: coerced/changed to {machine!r} -- investigate")

        col = [c for c in g.columns(doc, TABLE) if c["id"] == "Machine"][0]
        raw = col.get("fields", {}).get("widgetOptions")
        print(f"   column choices after write: "
              f"{(json.loads(raw).get('choices') if raw else None)}")

        print("\n=== 5. idempotency: same require, second upsert ===")
        g.upsert(doc, TABLE, [
            {"require": {"Key": "probe|growth"}, "fields": {
                "Key": "probe|growth", "Machine": "GrowthTest",
                "Speed": 99.0, "Retired": True}}])
        recs2 = g.records(doc, TABLE)
        print(f"   records now: {len(recs2)} (expect 1, not 2)")
        print(f"   fields now:  {json.dumps(recs2[0]['fields'], default=str)}")
        print(f"   Speed updated to 99.0? {recs2[0]['fields'].get('Speed') == 99.0}")

        print("\n=== 6. types round-trip (Bool / Numeric not stringified) ===")
        for k in ("Speed", "Retired"):
            v = recs2[0]["fields"].get(k)
            print(f"   {k:<10} {v!r:<10} ({type(v).__name__})")

    finally:
        print("\n=== 7. cleanup: delete the probe doc ===")
        try:
            g.delete_doc(doc)
            print("   deleted")
        except SystemExit as e:
            print(f"   cleanup failed: {e}")

    print("\n=== verify probe doc is gone from the workspace ===")
    ws = g.org_workspaces(ORG_ID)
    for w in ws if isinstance(ws, list) else []:
        if w.get("id") == WORKSPACE_ID:
            print("   Home docs now:", [d.get("name") for d in (w.get("docs") or [])])
    return 0


if __name__ == "__main__":
    sys.exit(main())
