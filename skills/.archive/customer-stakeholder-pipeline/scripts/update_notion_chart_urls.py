#!/usr/bin/env python3
"""Update Notion Customer Accounts Chart URL property with GitHub Pages URLs."""

import os
from pathlib import Path
import subprocess, json, time

# CONFIG
def _notion_key():
    """Notion token: $NOTION_API_KEY, else the NOTION_API_KEY= line in ~/.hermes/.env."""
    if key := os.environ.get("NOTION_API_KEY"):
        return key
    for line in (Path.home() / ".hermes/.env").read_text().splitlines():
        if line.startswith("NOTION_API_KEY="):
            return line.split("=", 1)[1].strip()
    raise SystemExit("NOTION_API_KEY not found in env or ~/.hermes/.env")


API_KEY = _notion_key()
ACCOUNTS_DB_ID = "3a70efce-9aed-80a1-b089-000b1fb5128f"  # Customer Accounts data source

# Map account names to chart filenames
CHART_MAP = {
    "Motorola Solutions": "motorola-stakeholder-map.html",
    "CSEM": "csem-stakeholder-map.html",
    "Polar Electro": "polar-stakeholder-map.html",
    "Halma": "halma-stakeholder-map.html",
    "Nestlé Purina": "nestle-purina-stakeholder-map.html",
    "Tridonic": "tridonic-stakeholder-map.html",
    "University of Jyväskylä": "university-of-jyvaskyla-stakeholder-map.html",
    "Globalsense": "globalsense-stakeholder-map.html",
    "Zwift": "zwift-stakeholder-map.html",
    "Poly / HP": "poly-stakeholder-map.html",
    "Küster Automotive": "kuester-stakeholder-map.html",
    "Halo Collar": "halo-collar-stakeholder-map.html",
    "Daikin": "daikin-stakeholder-map.html",
    "Sofar Ocean": "sofar-stakeholder-map.html",
    "Masco": "masco-stakeholder-map.html",
    "JUMO": "jumo-stakeholder-map.html",
    "Getac": "getac-stakeholder-map.html",
    "Replior": "replior-stakeholder-map.html",
}

# GitHub Pages base URL
BASE_URL = "https://prasta1.github.io/stakeholder-charts/"

def curl_patch(page_id, payload):
    cmd = [
        "curl", "-s", "-X", "PATCH", f"https://api.notion.com/v1/pages/{page_id}",
        "-H", f"Authorization: Bearer {API_KEY}",
        "-H", "Notion-Version: 2025-09-03",
        "-H", "Content-Type: application/json",
        "-d", json.dumps(payload)
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    return result.stdout, result.stderr, result.returncode

def main():
    # Query account rows
    cmd = [
        "curl", "-s", "-X", "POST", 
        "https://api.notion.com/v1/data_sources/3a70efce-9aed-80a1-b089-000b1fb5128f/query",
        "-H", f"Authorization: Bearer {API_KEY}",
        "-H", "Notion-Version: 2025-09-03",
        "-H", "Content-Type: application/json",
        "-d", '{"page_size": 100}'
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    accounts_resp = json.loads(result.stdout)

    updated = 0
    for p in accounts_resp.get("results", []):
        props = p.get("properties", {})
        acct_sel = props.get("Account", {}).get("select", {})
        acct_name = acct_sel.get("name", "") if acct_sel else ""
        chart_file = CHART_MAP.get(acct_name)
        if not chart_file:
            print(f"  No chart mapping for {acct_name}")
            continue
        chart_url = BASE_URL + chart_file
        payload = {"properties": {"Chart URL": {"url": chart_url}}}
        stdout, stderr, code = curl_patch(p["id"], payload)
        if code == 0 and '"object":"page"' in stdout:
            updated += 1
            print(f"  ✓ Updated {acct_name}")
        else:
            print(f"  ✗ Failed {acct_name}: {stdout[:200]}")
        time.sleep(0.2)

    print(f"\nUpdated {updated} account rows with chart URLs")

if __name__ == "__main__":
    main()