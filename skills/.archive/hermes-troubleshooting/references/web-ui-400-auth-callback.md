# Web UI 400 Auth Callback vs. Live Dashboard

## Session Signal
- User report: “the hermex application is hutting a 400”
- Actual `127.0.0.1:8787/` response: `HTTP/1.1 302 Found` with `Location: login?next=/`
- `dashboard-auth.log` contains: `login_failure` with `reason: missing_pkce_cookie` from Studio IP `100.89.133.43`
- Code path: `hermes_cli/dashboard_auth/routes.py` `/auth/callback` returns HTTP 400 when `hermes_session_pkce` cookie is absent

## Port/Process Map Observed
- `127.0.0.1:8787` — Hermes web UI / desktop backend, healthy, redirects to login when unauthenticated
- `127.0.0.1:9119` — legacy dashboard backend, may be down or conflicted; callback failure here still generates `missing_pkce_cookie` 400
- Desktop Hermes app can hit dashboard callback path independently of `8787`

## Diagnostic Commands
```bash
# Live UI check
curl -sS --max-time 5 http://127.0.0.1:8787/ -D - -o /dev/null | head -20

# Auth callback failures
grep -E 'missing_pkce_cookie|login_failure|login_success' ~/.hermes/logs/dashboard-auth.log | tail -20

# Listeners
lsof -i :8787 -sTCP:LISTEN -n -P
lsof -i :9119 -sTCP:LISTEN -n -P
```

## Lesson
- “400” without path/context is ambiguous on Hermes because there are multiple auth surfaces.
- Always verify the actual listener and response before treating a single user report as total web UI outage.
- “Hermes app hitting 400” may mean desktop/dashboard OAuth callback, not the currently running web UI on `8787`.
