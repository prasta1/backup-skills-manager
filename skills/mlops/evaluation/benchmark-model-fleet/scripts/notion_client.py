#!/usr/bin/env python3
"""Shared Notion transport and local state for the benchmark skill.

Split out of push_to_notion.py so the sink and the view manager can both use it
without importing each other.

Auth is NOTION_API_KEY (environment or ~/.hermes/.env). Skill scripts run
headless -- in cron, from a terminal -- so there is no MCP session available and
the Notion MCP tools cannot be used here.
"""
import json
import os
import time
import urllib.error
import urllib.request

API = "https://api.notion.com/v1"
NOTION_VERSION = "2025-09-03"

# Notion's published limit is ~3 requests/second averaged.
_MIN_INTERVAL = 0.34

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
STATE_PATH = os.path.join(ROOT, "references", "notion.json")


def load_api_key():
    key = (os.environ.get("NOTION_API_KEY") or "").strip()
    if key:
        return key
    env = os.path.expanduser("~/.hermes/.env")
    if os.path.exists(env):
        for line in open(env):
            if line.startswith("NOTION_API_KEY="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise SystemExit("NOTION_API_KEY not set (environment or ~/.hermes/.env)")


class Notion:
    """Thin REST client.

    Surfaces Notion's error body verbatim: a bare 'HTTP 400' hides which property
    or field was actually rejected, and Notion's validation messages are the only
    documentation some of these endpoints have.
    """

    def __init__(self, key, verbose=False):
        self.key = key
        self.verbose = verbose
        self._last = 0.0

    def __call__(self, method, path, body=None, retries=4):
        url = path if path.startswith("http") else f"{API}{path}"
        data = json.dumps(body).encode() if body is not None else None
        for attempt in range(retries):
            gap = time.time() - self._last
            if gap < _MIN_INTERVAL:
                time.sleep(_MIN_INTERVAL - gap)
            req = urllib.request.Request(url, data=data, method=method)
            req.add_header("Authorization", f"Bearer {self.key}")
            req.add_header("Notion-Version", NOTION_VERSION)
            req.add_header("Content-Type", "application/json")
            try:
                with urllib.request.urlopen(req, timeout=30) as r:
                    self._last = time.time()
                    return json.loads(r.read() or b"{}")
            except urllib.error.HTTPError as e:
                self._last = time.time()
                detail = e.read().decode(errors="replace")
                if e.code == 429 and attempt < retries - 1:
                    wait = int(e.headers.get("Retry-After") or 1) + 1
                    print(f"    rate limited, waiting {wait}s")
                    time.sleep(wait)
                    continue
                if 500 <= e.code < 600 and attempt < retries - 1:
                    time.sleep(1.5 * (attempt + 1))
                    continue
                raise SystemExit(f"Notion {method} {path} -> HTTP {e.code}\n{detail}")
            except urllib.error.URLError as e:
                if attempt < retries - 1:
                    time.sleep(1.5 * (attempt + 1))
                    continue
                raise SystemExit(f"Notion {method} {path} -> {e.reason}")
        raise SystemExit("unreachable")


def rt(s):
    """rich_text / title payload for a string."""
    return [{"text": {"content": str(s)[:1900]}}]


# Old property name -> current name. Renames are issued AS renames on a live
# data source, so the property id survives and every view filter built on it
# keeps working. Shared here because both the sink and the view manager need to
# migrate their cached name->id maps when one lands.
RENAMES = {"Name": "Model", "Deleted": "Retired"}


def read_state():
    if os.path.exists(STATE_PATH):
        try:
            return json.load(open(STATE_PATH))
        except (OSError, ValueError):
            return {}
    return {}


def write_state(state):
    os.makedirs(os.path.dirname(STATE_PATH), exist_ok=True)
    with open(STATE_PATH, "w") as f:
        json.dump(state, f, indent=2)
        f.write("\n")
