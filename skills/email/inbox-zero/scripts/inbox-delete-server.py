#!/usr/bin/env python3
"""Inbox action server — applies himalaya actions requested by the inbox-zero widget.

Receives message IDs from the widget and runs a himalaya command against Gmail.
Runs on the MacBook (loopback) because the Studio's application firewall drops
inbound traffic to a new Python process.

himalaya exits 0 even when it acted on nothing ("Successfully moved 0 message(s)",
"No message moved: no id matched in the source mailbox"), so the count it prints is
the only truth about what happened. We parse that count. We never report the number
we asked for as if it were the number that occurred.

Usage: python3 inbox-delete-server.py [--port 8644] [--token <tok>] [--host 127.0.0.1]
"""
import argparse, json, os, re, subprocess, sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

TOKEN = None
ACCOUNT = "personal"
MAX_BODY = 256 * 1024   # the payload is a list of ids; anything larger is abuse

# "Successfully moved 12 message(s) to the trash"  (delete)
# "1 message successfully moved"                    (archive/move)
MOVED_RE = re.compile(r"(\d+)\s+message", re.I)


def parse_count(stdout):
    """How many messages himalaya actually acted on, or None if it did not say.

    None is a real answer, not a failure: `flag add` prints no count at all.
    """
    m = MOVED_RE.search(stdout or "")
    if m:
        return int(m.group(1))
    if "no id matched" in (stdout or "").lower():
        return 0
    return None


def run_himalaya(ids, action):
    """Run a himalaya action on the given message IDs. action: delete | archive | read."""
    if not ids:
        return {"ok": True, "deleted": 0, "requested": 0, "confirmed": True,
                "detail": "no ids"}
    if action == "delete":
        cmd = ["himalaya", "message", "delete", "-a", ACCOUNT, "-m", "INBOX"]
        verb = "deleted"
    elif action == "archive":
        cmd = ["himalaya", "message", "move", "-a", ACCOUNT, "-f", "INBOX",
               "-t", "[Gmail]/All Mail"]
        verb = "archived"
    elif action == "read":
        cmd = ["himalaya", "flag", "add", "-a", ACCOUNT, "-m", "INBOX", "-f", "seen"]
        verb = "marked read"
    else:
        return {"ok": False, "deleted": 0, "requested": 0, "confirmed": True,
                "error": "unknown action: %s" % action}

    cmd += [str(i) for i in ids]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    except subprocess.TimeoutExpired:
        return {"ok": False, "deleted": 0, "requested": len(ids), "confirmed": True,
                "error": "himalaya timed out after 180s"}
    except Exception as e:
        return {"ok": False, "deleted": 0, "requested": len(ids), "confirmed": True,
                "error": str(e)}

    out = (r.stdout or "").strip()
    err = (r.stderr or "").strip()
    count = parse_count(out)
    confirmed = count is not None

    if r.returncode != 0:
        return {"ok": False, "deleted": 0, "requested": len(ids), "confirmed": True,
                "verb": verb,
                "error": err or out or ("himalaya exited %d" % r.returncode)}
    if confirmed and count == 0:
        # exit 0, but nothing was touched: the widget's ids are stale
        return {"ok": False, "deleted": 0, "requested": len(ids), "confirmed": True,
                "verb": verb,
                "error": "no ids matched in the mailbox — the widget is stale, rebuild it"}
    return {"ok": True, "deleted": count if confirmed else len(ids),
            "requested": len(ids), "confirmed": confirmed, "verb": verb,
            "detail": out or err}


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, obj):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self._send(200, {})

    def do_POST(self):
        auth = self.headers.get("Authorization", "")
        if TOKEN and auth != f"Bearer {TOKEN}":
            self._send(401, {"ok": False, "error": "unauthorized"})
            return
        try:
            length = int(self.headers.get("Content-Length", 0))
        except ValueError:
            self._send(400, {"ok": False, "error": "bad content-length"})
            return
        if length > MAX_BODY:
            self._send(413, {"ok": False, "error": "payload too large"})
            return
        try:
            payload = json.loads(self.rfile.read(length) or b"{}")
        except Exception:
            self._send(400, {"ok": False, "error": "bad json"})
            return
        ids = payload.get("ids", [])
        if not isinstance(ids, list) or not all(str(i).isdigit() for i in ids):
            self._send(400, {"ok": False, "error": "ids must be a list of numeric ids"})
            return
        action = payload.get("action", "delete")
        if action not in ("delete", "archive", "read"):
            self._send(400, {"ok": False, "error": f"unknown action: {action}"})
            return
        self._send(200, run_himalaya(ids, action))

    def log_message(self, format, *args):
        sys.stderr.write("[inbox-delete] %s\n" % (format % args))


def main():
    global TOKEN, ACCOUNT
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8644)
    ap.add_argument("--token", default=os.environ.get("INBOX_DELETE_TOKEN", ""))
    # loopback by default: the widget lives on this machine, nothing else needs in
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--account", default="personal",
                    help="himalaya account name (the MacBook's Gmail account is 'personal')")
    args = ap.parse_args()
    TOKEN = args.token
    ACCOUNT = args.account
    if not TOKEN:
        import secrets
        TOKEN = secrets.token_urlsafe(24)
        print(f"[inbox-delete] NO TOKEN SET — generated: {TOKEN}", flush=True)
    print(f"[inbox-delete] listening on {args.host}:{args.port} "
          f"account={ACCOUNT} token={'set' if TOKEN else 'NONE'}", flush=True)
    srv = ThreadingHTTPServer((args.host, args.port), Handler)
    srv.serve_forever()


if __name__ == "__main__":
    main()
