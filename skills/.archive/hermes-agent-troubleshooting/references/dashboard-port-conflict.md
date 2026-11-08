# Dashboard / Web UI Partial-Outage Example

## Observed State
- `127.0.0.1:3334` unreachable
- `ai.hermes.dashboard`: `job state: exited`, `last exit code: 1`
- `com.hermes.webui`: `job state: running`, pid alive

## Diagnostic Findings
- legacy dashboard backend still bound on `127.0.0.1:9119`
- `dashboard.error.log` repeatedly shows:
  - `address already in use` on `0.0.0.0:9119`
- `dashboard.log` repeatedly shows desktop build skip:
  - `Skipping web UI build (--skip-build); using dist at ...web_dist`

## Interpretation
This is a port/renderer split, not a total web UI failure.
`3334` can be dead while a backend and desktop UI stack remain active elsewhere.

## Corrective Approach
1. Do not restart `ai.hermes.dashboard` while another process owns `9119`.
2. Identify the live listener and UI path before changing services.
3. Re-check the user's intended dashboard URL after any service change.

## Recheck Pattern
```bash
curl -sS --max-time 6 http://127.0.0.1:3334/ -o /dev/null -w '%{http_code}\n'
launchctl list | grep -E 'ai.hermes.dashboard|com.hermes.webui'
lsof -i :9119 -sTCP:LISTEN -n -P 2>/dev/null || echo '__NO_LISTENER__'
ps -p <PID> -o pid,command
```
