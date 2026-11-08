#!/usr/bin/env python3
"""Grist REST transport + local state, shared by every Grist-facing script.

Mirrors the role notion_client.py plays for the Notion sink: ONE copy of the
transport, so grist_sink.py (and anything that follows it) cannot drift.

Auth is GRIST_API_KEY, read from the environment or ~/.hermes/.env. A skill
script has no MCP session, so it cannot use the Grist MCP server -- same reason
the Notion sink reads NOTION_API_KEY rather than calling Notion MCP tools.

Two things about Grist's API worth knowing before reading the code:

  * Tables and columns are addressed by COLUMN ID, not by display label. The
    label ("Speed tok/s") can carry spaces and slashes; the id
    ("speed_tok_s") cannot. Records are written by id.
  * Idempotent upsert is BUILT IN: PUT .../records takes
    {"require": {...}, "fields": {...}} and matches on `require`. That is the
    primitive Notion made us emulate with a query-then-patch dance.
"""
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

HOST = "https://docs.getgrist.com"
API = HOST + "/api"

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
STATE_PATH = os.path.join(ROOT, "references", "grist.json")

# Grist meters API calls. Far gentler than Notion's 3/s, but a backfill of a few
# hundred rows is still worth pacing rather than hammering.
_MIN_INTERVAL = 0.12
_RETRY_STATUS = {429, 500, 502, 503, 504}
_MAX_RETRIES = 5


def _parse_env_file(path):
    """KEY=VALUE lines from a .env, ignoring comments and surrounding quotes."""
    out = {}
    try:
        with open(path) as fh:
            for line in fh:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                out[k.strip()] = v.strip().strip('"').strip("'")
    except OSError:
        pass
    return out


def load_api_key():
    """GRIST_API_KEY from the environment, else ~/.hermes/.env.

    An empty value is refused loudly: a blank key would otherwise surface as a
    bare 401 three calls deep, which reads like a permissions problem instead of
    a missing paste.
    """
    key = (os.environ.get("GRIST_API_KEY") or "").strip()
    if not key:
        for candidate in (os.path.expanduser("~/.hermes/.env"),
                          os.path.join(ROOT, ".env")):
            key = (_parse_env_file(candidate).get("GRIST_API_KEY") or "").strip()
            if key:
                break
    if not key:
        raise SystemExit(
            "GRIST_API_KEY is empty. Put it in ~/.hermes/.env as\n"
            "    GRIST_API_KEY=<token>\n"
            "(no quotes, no trailing comment), or export it.")
    if any(c in key for c in "\"' \t\r\n"):
        raise SystemExit("GRIST_API_KEY contains a quote/space -- paste it bare.")
    return key


def read_state():
    try:
        with open(STATE_PATH) as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {}


def write_state(state):
    os.makedirs(os.path.dirname(STATE_PATH), exist_ok=True)
    tmp = STATE_PATH + ".tmp"
    with open(tmp, "w") as fh:
        json.dump(state, fh, indent=2, sort_keys=True)
        fh.write("\n")
    os.replace(tmp, STATE_PATH)


class Grist:
    """Minimal Grist API client.

    Raises SystemExit on a non-2xx so a caller can catch-and-report, matching
    notion_client.Notion's behaviour.
    """

    def __init__(self, api_key, host=HOST, verbose=False):
        self.key = api_key
        self.host = host.rstrip("/")
        self.base = self.host + "/api"
        self.verbose = verbose
        self._last = 0.0

    def _throttle(self):
        gap = time.time() - self._last
        if gap < _MIN_INTERVAL:
            time.sleep(_MIN_INTERVAL - gap)
        self._last = time.time()

    def call(self, method, path, body=None, params=None, raw=False):
        url = self.base + path
        if params:
            url += "?" + urllib.parse.urlencode(params)
        data = None
        if body is not None:
            data = json.dumps(body).encode()
        headers = {"Authorization": "Bearer " + self.key,
                   "Accept": "application/json"}
        if data:
            headers["Content-Type"] = "application/json"

        last = None
        for attempt in range(_MAX_RETRIES):
            self._throttle()
            req = urllib.request.Request(url, data=data, headers=headers,
                                         method=method)
            try:
                with urllib.request.urlopen(req, timeout=60) as resp:
                    payload = resp.read().decode("utf-8", "replace")
                    if raw:
                        return payload
                    return json.loads(payload) if payload.strip() else None
            except urllib.error.HTTPError as e:
                detail = e.read().decode("utf-8", "replace")[:500]
                last = f"HTTP {e.code} on {method} {path}: {detail}"
                if e.code in _RETRY_STATUS and attempt < _MAX_RETRIES - 1:
                    time.sleep(min(2 ** attempt, 8))
                    continue
                raise SystemExit(last)
            except Exception as e:  # noqa: BLE001  (transport-level)
                last = f"{type(e).__name__} on {method} {path}: {e}"
                if attempt < _MAX_RETRIES - 1:
                    time.sleep(min(2 ** attempt, 8))
                    continue
                raise SystemExit(last)
        raise SystemExit(last or "request failed")

    # -- convenience -------------------------------------------------------
    def org_workspaces(self, org_id):
        return self.call("GET", f"/orgs/{org_id}/workspaces")

    def create_doc(self, workspace_id, name, is_pinned=False):
        """POST /workspaces/{id}/docs returns the doc id as a bare JSON string."""
        res = self.call("POST", f"/workspaces/{workspace_id}/docs",
                        {"name": name, "isPinned": is_pinned})
        return res if isinstance(res, str) else (res or {}).get("id")

    def tables(self, doc_id):
        res = self.call("GET", f"/docs/{doc_id}/tables")
        return (res or {}).get("tables", [])

    def columns(self, doc_id, table_id):
        res = self.call("GET", f"/docs/{doc_id}/tables/{table_id}/columns")
        return (res or {}).get("columns", [])

    def add_table(self, doc_id, table_id, columns):
        return self.call("POST", f"/docs/{doc_id}/tables",
                         {"tables": [{"id": table_id, "columns": columns}]})

    def add_columns(self, doc_id, table_id, columns):
        if not columns:
            return None
        return self.call("POST", f"/docs/{doc_id}/tables/{table_id}/columns",
                         {"columns": columns})

    def records(self, doc_id, table_id, limit=None):
        res = self.call("GET", f"/docs/{doc_id}/tables/{table_id}/records")
        recs = (res or {}).get("records", [])
        return recs[:limit] if limit else recs

    def upsert(self, doc_id, table_id, records, noparse=False):
        """PUT .../records with require+fields: add-or-update, keyed on require."""
        body = {"records": records}
        params = {"noparse": "true"} if noparse else None
        return self.call("PUT", f"/docs/{doc_id}/tables/{table_id}/records",
                         body, params=params)

    def delete_doc(self, doc_id):
        return self.call("DELETE", f"/docs/{doc_id}")


def slug(text):
    """Grist column/table id: identifiers only, no spaces or punctuation."""
    s = re.sub(r"[^0-9A-Za-z_]+", "_", (text or "").strip()).strip("_")
    if not s or s[0].isdigit():
        s = "c_" + s
    return s


if __name__ == "__main__":
    # Tiny self-check: prove the key authenticates before anything is written.
    g = Grist(load_api_key())
    orgs = g.call("GET", "/orgs")
    print(f"auth ok -- {len(orgs)} org(s):")
    for o in orgs:
        print(f"   id={o['id']:<8} name={o['name']:<12} domain={o.get('domain')} "
              f"access={o.get('access')}")
    sys.exit(0)
