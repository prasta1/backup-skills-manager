# "This backend is running old code after an update" — the stale launchd dashboard

Symptom: Hermes Desktop shows *This backend is running old code after an update. Restart it to load
the new code.* (`apps/desktop/src/i18n/en_model_settings.ts` → `restartRequired`), and restarting the
app, the Desktop backend, or the gateway does not clear it.

## The offending process is the dashboard, not the app's backend

`/api/model/options` is refused by `_dashboard_code_skew_guard` (`hermes_cli/web_server_config.py`),
which compares the process's boot fingerprint (`gateway/code_skew.py::detect_code_skew`) against the
checkout on disk. On this stack that endpoint answers from the **launchd dashboard**
(`ai.hermes.dashboard` → `hermes dashboard --no-open`, 127.0.0.1:9119). The Desktop app's backend,
its SSH-isolated `serve`, and the messaging gateway are *different* processes with their own boot
fingerprints.

Identify the live process before believing any restart story:

```bash
launchctl list | grep ai.hermes.dashboard          # PID column is the launchd wrapper (osascript)
lsof -nP -iTCP:9119 -sTCP:LISTEN                   # the real server pid
ps eww -p <server_pid> | tr ' ' '\n' | grep HERMES_SERVE_HEADLESS
```

The *absence* of `HERMES_SERVE_HEADLESS` is what makes the refusal's advice read "restart this
Hermes process (`hermes dashboard --port <port>` …)" instead of "use Restart backend in Hermes
Desktop" (`_dashboard_skew_restart_hint`). That difference names which process logged it.

Live code identity, no auth needed:

```bash
curl -s http://127.0.0.1:9119/api/health        # {"ok":true,...,"commit":"<sha>",...}
git -C ~/.hermes/hermes-agent rev-parse HEAD    # must match
```

## Why a restart "doesn't work"

Three separate traps, hit together on 2026-11-06:

1. **The restart hits the wrong object.** Quitting the app, its "Restart backend", and
   `hermes gateway restart` all leave the launchd dashboard untouched.
2. **launchd races the update.** The plist is `KeepAlive{SuccessfulExit=false}`: the updater kills
   the dashboard, launchd respawns it within seconds, and the updater's own respawn then dies
   (`child exited during the first 1s (code 1)` — port 9119 already held). If a later step in the
   same run moves the branch tip (a wrapper rebasing a carried branch, as
   `~/.hermes/scripts/hermes-update-local.sh` does), the respawned process is booted on the
   *interim* code and is stale from that second on. Measured: dashboard up at 14:29:43, rebase
   finished 14:29:48. The dashboard's own log names the cause:
   `source-update completion failed: an update is still running`. `SuccessfulExit=false` also means
   a *clean* stop is never respawned, so it stays stale until something kicks it.
3. **A different message class gets conflated with it.** Install-state lines
   (`a source update could not be finished automatically (N attempts)`,
   `install out of sync (…)`) come from markers under `~/.hermes/installs/<id>/`
   (`source-completion-pending`, `source-completion-attempts`; retry cap in
   `hermes_cli/venv_sync.py`) and from `pm.check()`. **No restart clears those** — only a finished
   update tail (or `hermes pm install`) does. Do not keep restarting a process to silence a marker.

Related asymmetry: SSH-isolated Desktop backends *self-retire* on skew —
`hermes_cli.web_server_skew_exit` logs "retiring so its client respawns it on the new code" and
exits, so they recover by themselves. The launchd dashboard has no such path.

## Fix, then prove it

```bash
launchctl kickstart -k gui/$(id -u)/ai.hermes.dashboard
sleep 10
curl -s http://127.0.0.1:9119/api/health   # commit must equal the checkout HEAD
git -C ~/.hermes/hermes-agent rev-parse HEAD
```

Equal ⇒ the guard is satisfied and no new `GET /api/model/options refused` line should appear in
`logs/gui.log` / `logs/dashboard.error.log` after the restart timestamp.

## Pitfalls

- **A kickstart interrupts in-flight turns.** The dashboard hosts the Desktop's tui_gateway
  session, so a running chat turn ends as `status=interrupted`, the ws client disconnects
  (`code=1012`, service restart) and reconnects; the session is stored and resumes. Warn the user
  first, and check for running sessions.
- **Re-check after any update that rebases a branch.** The launchd race can land the dashboard stale
  again on the *same* run, so "restart the dashboard and verify" is a post-update step, not a
  one-time fix.
- `-15` in `launchctl list`'s status column right after a kickstart is the previous instance's
  SIGTERM, not a failure.
- Restarting the dashboard is not a fix for an owed build: if the update tail failed (e.g. a product
  build), the marker survives every restart and the same message returns.
