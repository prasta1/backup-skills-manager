#!/usr/bin/env python3
"""Upload all contacts from local markdown to Notion Customer Stakeholders database."""

import os
import subprocess, json, time, yaml
from pathlib import Path
from collections import defaultdict

# CONFIG - Update these IDs if databases change
def _notion_key():
    """Notion token: $NOTION_API_KEY, else the NOTION_API_KEY= line in ~/.hermes/.env."""
    if key := os.environ.get("NOTION_API_KEY"):
        return key
    for line in (Path.home() / ".hermes/.env").read_text().splitlines():
        if line.startswith("NOTION_API_KEY="):
            return line.split("=", 1)[1].strip()
    raise SystemExit("NOTION_API_KEY not found in env or ~/.hermes/.env")


API_KEY = _notion_key()
DATABASE_ID = "3a70efce-9aed-80fc-8a7d-d68e4f03de78"  # Customer Stakeholders database
CONTACTS_DATA_SOURCE_ID = "3a70efce-9aed-8024-966c-000b8ad90e4a"  # data source for queries

OPTION_ID_MAP = {
    "Motorola Solutions": "433700af-4437-4e3d-b377-b42153c285b8",
    "Poly / HP": "5f22f7c6-10ff-4a41-9dd5-9d3a16429bd1",
    "Nestlé Purina": "f06ab5ad-a800-4ae5-9f62-e8f16ec1af63",
    "Polar Electro": "562aca66-ce6b-450f-b389-31d593df883c",
    "CSEM": "dc267056-ea72-47e9-857c-1ece820ded1a",
    "Halma": "250b56ad-ba4d-4430-ad09-4bc6396346cd",
    "Tridonic": "7460712a-648f-4b8b-a77f-da01a7e2dc67",
    "Masco": "ae2fa619-6cc9-4113-a83b-e7c3be16c720",
    "Zwift": "26648c01-a400-46f7-8515-e3f651eeb11b",
    "Getac": "31dc43e4-42a3-45b1-8a89-ccd5626bf4b3",
    "Daikin": "3f4cb73b-3b93-46c4-856e-a1f8b3e397b6",
    "Replior": "62947dca-c025-448b-adae-2e9fe5f59185",
    "University of Jyväskylä": "35a472ce-04a4-470b-80fd-f798ded035d4",
    "JUMO": "341f6ae4-97a9-49e5-965e-d06d6dace373",
    "Sofar Ocean": "c97a186c-290e-4b03-9342-4a5f73aeec5f",
    "Halo Collar": "adf209fe-ff83-4601-b536-b82a6e5a16b0",
    "Globalsense": "b56e0bab-b86b-43ae-9f48-f5a49db06af8",
    "Küster Automotive": "3c8e7faa-2f23-4e6f-af20-ad5eb74933fd",
}
INFLUENCE = {"High":"ac515fca-d532-44e8-ab3b-71f88dd063e1","Medium":"bba95d74-c80f-4856-bf60-0887df171a84","Low":"c1f6ab8f-745a-4766-b549-72393192fb30"}
RELATIONSHIP = {"Ally":"c6b3173c-67cf-4bde-9c33-dc5b4aaba36e","Neutral":"e6b041f1-877d-4bf0-bc8e-f8356c747d30","Warm":"094085c6-0772-44d0-98c6-9dc596ef1226","Blocker":"59a06664-95cc-44e1-9846-e5034661850a","Marketing":"c0d2f591-84ad-4d65-9d04-983bd9ab52ba"}

REPO_ROOT = Path(__file__).parent.parent
CUSTOMERS_DIR = REPO_ROOT / "customers"
SLUG_MAP = {
    "motorola": "Motorola Solutions", "polar": "Polar Electro", "csem": "CSEM",
    "halma": "Halma", "university-of-jyvaskyla": "University of Jyväskylä",
    "tridonic": "Tridonic", "zwift": "Zwift", "poly": "Poly / HP",
    "sofar": "Sofar Ocean", "jumo": "JUMO", "kuester": "Küster Automotive",
    "getac": "Getac", "globalsense": "Globalsense", "halo-collar": "Halo Collar",
    "daikin": "Daikin", "masco": "Masco", "replior": "Replior",
    "nestle-purina": "Nestlé Purina",
}

def curl_create(payload):
    cmd = [
        "curl", "-s", "-X", "POST", "https://api.notion.com/v1/pages",
        "-H", f"Authorization: Bearer {API_KEY}",
        "-H", "Notion-Version: 2025-09-03",
        "-H", "Content-Type: application/json",
        "-d", json.dumps(payload)
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    return result.stdout, result.stderr, result.returncode

def main():
    # Load all contacts from markdown
    rows = []
    for path in sorted(CUSTOMERS_DIR.glob("*/index.md")):
        doc = path.read_text()
        if "---" not in doc:
            continue
        front = doc.split("---", 2)[1]
        try:
            data = yaml.safe_load(front)
        except Exception:
            continue
        if not data or not isinstance(data, dict):
            continue
        account = SLUG_MAP.get(path.parent.name, path.parent.name)
        for c in data.get("contacts") or []:
            rows.append({
                "account": account,
                "name": (c.get("name") or "").strip(),
                "role": (c.get("role") or "").strip(),
                "influence": (c.get("influence") or "Low").strip(),
                "relationship": (c.get("relationship_to_us") or "Neutral").strip(),
            })

    # Deduplicate
    seen = {}
    for r in rows:
        k = (r["account"], r["name"])
        if k not in seen:
            seen[k] = r
    rows = list(seen.values())
    print(f"Total unique contacts to upload: {len(rows)}")

    created = 0
    for i, r in enumerate(rows):
        acct_id = OPTION_ID_MAP.get(r["account"])
        inf_id = INFLUENCE.get(r["influence"])
        rel_id = RELATIONSHIP.get(r["relationship"])
        if not acct_id or not inf_id or not rel_id or not r["name"]:
            continue
        payload = {
            "parent": {"database_id": DATABASE_ID},
            "properties": {
                "Name": {"title": [{"text": {"content": r["name"]}}]},
                "Account": {"select": {"id": acct_id, "name": r["account"]}},
                "Role": {"rich_text": [{"text": {"content": r["role"]}}]},
                "Influence": {"select": {"id": inf_id, "name": r["influence"]}},
                "Relationship": {"select": {"id": rel_id, "name": r["relationship"]}},
            }
        }
        stdout, stderr, code = curl_create(payload)
        if code == 0 and '"object":"page"' in stdout:
            created += 1
        else:
            print(f"ERR {r['name']}: {stdout[:200]}")
        time.sleep(0.25)
        if (i + 1) % 50 == 0:
            print(f"  Progress: {i+1}/{len(rows)}, created={created}")

    print(f"\nDone. Created {created} contacts")

if __name__ == "__main__":
    main()