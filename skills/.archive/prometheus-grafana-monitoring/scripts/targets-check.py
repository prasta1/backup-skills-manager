#!/usr/bin/env python3
"""Verify every Prometheus target's health via the API.

Run after any prometheus.yml change or exporter install. Prints one row per
active target: job, health, scrape URL. Every row should be 'up' after one
scrape interval; anything else needs fixing before moving on.

Usage: python3 targets-check.py [prometheus_base_url]   # default http://localhost:9090
"""
import json
import sys
import urllib.request

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:9090"

with urllib.request.urlopen(f"{BASE}/api/v1/targets") as r:
    d = json.load(r)

rows = []
bad = 0
for t in d["data"]["activeTargets"]:
    job = t["labels"].get("job", "?")
    health = t["health"]
    url = t["scrapeUrl"]
    err = t.get("lastError", "")
    rows.append((job, health, url, err))
    if health != "up":
        bad += 1

for job, health, url, err in sorted(rows):
    print(f"{job:22} {health:10} {url} {err}")
print(f"\n{len(rows) - bad}/{len(rows)} targets up")
raise SystemExit(1 if bad else 0)
