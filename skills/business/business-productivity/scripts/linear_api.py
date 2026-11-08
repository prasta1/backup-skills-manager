#!/usr/bin/env python3
"""Zero-dependency Linear GraphQL CLI for Hermes cron jobs."""
import os, sys, json, urllib.request

ENDPOINT = "https://api.linear.app/graphql"
CONFIG_PATH = os.path.expanduser("~/.hermes/.env")

def load_env():
    if os.path.exists(CONFIG_PATH):
        for line in open(CONFIG_PATH):
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                k, v = line.split('=', 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"\''))

def get_token():
    load_env()
    token = os.environ.get("LINEAR_API_KEY")
    if not token:
        print("Error: LINEAR_API_KEY not set in environment or", CONFIG_PATH)
        sys.exit(1)
    return token

def gql(query, variables=None):
    token = get_token()
    payload = json.dumps({"query": query, "variables": variables or {}}).encode()
    req = urllib.request.Request(ENDPOINT, data=payload,
        headers={"Authorization": token, "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        print(f"HTTP {e.code}: {e.read().decode()}", file=sys.stderr)
        sys.exit(1)
    if data.get("errors"):
        for err in data["errors"]:
            print(f"GraphQL error: {err['message']}", file=sys.stderr)
        sys.exit(1)
    return data

def main():
    if len(sys.argv) < 2:
        print("Usage: linear_api.py <command> [args]")
        sys.exit(1)
    cmd = sys.argv[1]
    args = sys.argv[2:]

    if cmd == "whoami":
        r = gql("query { viewer { id name email } }")
        print(json.dumps(r["data"]["viewer"], indent=2))
    elif cmd == "list-teams":
        r = gql("query { teams { nodes { id name key } } }")
        for t in r["data"]["teams"]["nodes"]:
            print(f"{t['key']}  {t['name']}  {t['id']}")
    elif cmd == "list-issues":
        team = None
        for i, a in enumerate(args):
            if a == "--team" and i+1 < len(args): team = args[i+1]
        if team:
            q = "query($team: String!) { team(key: $team) { issues { nodes { identifier title state { name } } } } }"
            r = gql(q, {"team": team})
        else:
            r = gql("query { issues(first: 250) { nodes { identifier title state { name } } } }")
        issues = r["data"].get("team", {}).get("issues", {}).get("nodes", []) if team else r["data"]["issues"]["nodes"]
        for iss in issues:
            print(f"{iss['identifier']}  [{iss['state']['name']}]  {iss['title']}")
    elif cmd == "get-issue":
        identifier = args[0]
        r = gql(f'query {{ issue(identifier: "{identifier}") {{ title description state {{ name }} }} }}')
        iss = r["data"]["issue"]
        print(json.dumps(iss, indent=2))
    elif cmd == "raw":
        query = args[0]
        r = gql(query)
        print(json.dumps(r, indent=2))
    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)

if __name__ == "__main__":
    main()
