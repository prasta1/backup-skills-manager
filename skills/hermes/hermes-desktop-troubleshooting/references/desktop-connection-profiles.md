# Profile Dropdown Mismatch — Reference Case

## Scenario

The user reported that the Hermes desktop app's profile dropdown didn't reflect the profiles accurately after consolidating profiles on the local machine.

## Initial Assumption

That the desktop app was reading stale/cached profile data locally and needed a refresh.

## Actual Root Cause

The desktop app was configured as a **remote gateway client** pointing at the Mac Studio (`studio.taile85139.ts.net:9119`). The profile dropdown was showing the **Studio's** profile list, not the local machine's. The user had 5 profiles locally (`default`, `bd-copilot`, `cs-copilot`, `diane`, `larp`) — those were present in the dropdown because the Studio's dashboard also had them. If the profiles had diverged (e.g., after consolidation only on one machine), the dropdown would show stale data.

## Evidence Chain

### Step 1: Connection mode check

The file `~/Library/Application Support/Hermes/connection.json` showed:

```json
{
  "mode": "remote",
  "remote": {
    "url": "http://studio.taile85139.ts.net:9119",
    "authMode": "oauth"
  },
  "profiles": {}
}
```

Key findings:
- `mode: "remote"` — not local. The desktop is a thin client.
- `remote.url` — points to the Studio's dashboard.
- `profiles: {}` — no per-profile overrides; all profiles come from the remote dashboard's API.

### Step 2: Local profile list vs remote profile list

Local (`hermes profile list`):
```
default         deepseek/deepseek-v4-flash    running
bd-copilot      gemma-4-26b-a4b-it-qat-mlx    stopped
cs-copilot      gemma-4-26b-a4b-it-qat-mlx    stopped
diane           gemma-4-26b-a4b-it-qat-mlx    stopped
larp            google/gemma-4-26b-a4b-qat     stopped
```

Remote dashboard API (`/api/profiles` with Bearer token):
Same 5 profiles, same models — they were in sync because profiles live on the shared filesystem (the Studio is the primary machine, the laptop connects remotely).

If the user had consolidated profiles on one machine but not the other (e.g., deleted `diane` locally but the Studio's `~/.hermes/profiles/diane/` still existed), the dropdown would keep showing the deleted profile.

### Step 3: Dashboard session token discovery

The dashboard page's `<script>` tag revealed:
```javascript
window.__HERMES_SESSION_TOKEN__="<desktop-token>"
window.__HERMES_AUTH_REQUIRED__=false
window.__HERMES_DASHBOARD_EMBEDDED_CHAT__=true
```

Even with `AUTH_REQUIRED=false` (loopback bind), the token is required for API calls:
```
> curl http://localhost:9119/api/profiles
{"detail":"Unauthorized"}

> curl -H "Authorization: Bearer <desktop-token>" http://localhost:9119/api/profiles
{"profiles": [...]}
```

### Step 4: Desktop log check

```
tail -100 ~/.hermes/logs/desktop.log | grep "\[boot\]"
```
Would show whether it's remote or local mode, confirming the connection.json finding.

## Key Lessons

1. **connection.json is the mode signal.** It's at `~/Library/Application Support/Hermes/connection.json` — not in `~/.hermes/`. Don't look there first.
2. **Profile dropdown = remote feed.** If the desktop is in remote mode, the dropdown is a live feed from the remote dashboard's `/api/profiles` endpoint. It's not cached locally.
3. **Profiles live on the remote machine.** The desktop is a thin client — it shows what the remote dashboard knows. Profile consolidation must happen on the machine running the dashboard (the Studio), not just on the laptop.
4. **Dashboard API needs the session token.** Even on localhost with no auth challenge, `/api/*` endpoints return 401 without a Bearer token. Extract it from the HTML page source.
5. **Restart to refresh.** There's no on-demand refresh trigger for the profile dropdown in the desktop app. Quit and relaunch.

## Diagnosis Commands Used

```bash
# Check connection mode
cat ~/Library/Application\ Support/Hermes/connection.json

# Check local profile list
hermes profile list

# Extract session token from dashboard
curl -s http://localhost:9119/ | grep -o '__HERMES_SESSION_TOKEN__="[^"]*"'

# Query the profiles API
TOKEN="<desktop-token>"
curl -s -H "Authorization: Bearer $TOKEN" http://localhost:9119/api/profiles | python3 -m json.tool

# Check desktop boot mode in logs
grep "\[boot\]" ~/.hermes/logs/desktop.log

# Check what profiles exist on disk
ls ~/.hermes/profiles/
```
