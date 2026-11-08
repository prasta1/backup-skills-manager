---
name: hermes-desktop-troubleshooting
description: "Diagnose Hermes desktop app initialization failures, startup errors, and connection issues — covering the Electron main process, backend spawning, remote gateway mode, identity file checks, and log analysis."
version: 1.0.0
author: Hermes Agent
metadata:
  hermes:
    tags: [debugging, hermes-agent, desktop, electron, gateway, startup]
    related_skills: [systematic-debugging, hermes-config-management, debugging-hermes-tui-commands]
---

# Hermes Desktop App Troubleshooting

> 2026-10-01 topology: the desktop app runs on the MacBook as a thin client to the Studio gateway. `desktop.log` and `bootstrap-installer.log` are on the MacBook (`ssh macbookpro`); `gateway.log`, `agent.log` and `dashboard.log` are on the Studio under `~/.hermes/logs/`. A `hermes` run on the MacBook re-seeds its `~/.hermes`; the shim there is `hermes-dev` with `HERMES_HOME=~/.hermes-dev`.

## Overview

The Hermes desktop app (`/Applications/Hermes.app`) is an Electron shell that can operate in two distinct modes:

1. **Local backend mode** — spawns a headless `hermes serve` Python process on the local machine as the backend.
2. **Remote gateway mode (thin client)** — connects to a remote Hermes gateway (e.g., on a Mac Studio over Tailscale), requiring only a browser-like auth session.

The user-facing error message is often a symptom, not the cause. The "agent init failed" error from the TUI gateway server wraps whatever the actual backend exception was. **Always check the logs first.**

## Always-on Rules (standing user preferences)

- **Inspect before acting.** When a user says "Inspect. Don't act." or indicates an investigation mode, run the full diagnostic sequence (read logs, check process state, verify file/state) but make NO changes — no restarts, no auth resets, no edits, no service restarts, no updates — until the user explicitly approves the fix. Label guesses as guesses; cite sources.
- **Don't assume the desktop mode.** Always verify `desktop.log` first to confirm remote vs local mode before interpreting errors.

## Log Hierarchy

Three log files to check, in priority order:

| Log | Path | What it tells you |
|-----|------|-------------------|
| **desktop.log** | `~/.hermes/logs/desktop.log` | Electron main process boot sequence — backend resolution, gateway liveness, session expiry. Start here. |
| **bootstrap-installer.log** | `~/.hermes/logs/bootstrap-installer.log` | Update/bootstrap process — installer errors, file seeding failures, version transitions. Check when the app recently updated. |
| **agent.log** | `~/.hermes/logs/agent.log` | Per-session agent interaction logs. Rarely the source of startup failures. |

The `errors.log` aggregates tool-level errors from running sessions and is not useful for desktop init diagnosis.

## Diagnostic Flow

### 1. Identify the mode

Read the desktop log to determine if the app is in local or remote mode:

```
# Remote mode (thin client to another machine):
[hermes] [boot] Connecting to remote Hermes backend at http://studio.taile85139.ts.net:9119
[hermes] [boot] Remote Hermes backend is ready

# Local mode:
[hermes] [boot] Spawning local backend: hermes serve --host 127.0.0.1 --port 0

# SSH mode (remote reached over an ssh control master, not HTTP):
[hermes] [boot] Resolving Hermes backend
[hermes] [ssh] opening control master to <user>@<host>:22
[hermes] [ssh-lifecycle] remote hermes version: Hermes Agent v...
```

**`Resolving Hermes backend` is ambiguous — it appears in BOTH local and SSH mode.** It is not a local-mode marker. Disambiguate by what follows: `Spawning local backend` means local, `[ssh] opening control master` means SSH. The stored mode is authoritative and readable as JSON:

```bash
cat ~/Library/Application\ Support/Hermes/connection.json
```

`"mode"` may be `"ssh"`, `"remote"` (HTTP gateway), or `"local"` — three distinct remote topologies with three different failure surfaces, so read it rather than inferring it from the log.

### 2A. Remote mode: check the gateway session

Remote mode requires a valid OAuth or token session with the remote gateway. **Before interpreting any "agent init failed" message as a file or identity error, confirm mode from `desktop.log`:** look for `Connecting to remote Hermes backend` (remote) vs `Spawning local backend` (local). Then check session state.

**New blocker pattern (update process):**
```
Desktop boot failed: Remote Hermes update process 46313 is still running; SSH startup is paused.
```
This is NOT an auth failure. A remote Hermes update process on the Studio (e.g., from `hermes-setup --update`) is still running and has locked the SSH startup sequence. Confirm by checking remote process state (`ssh studio 'ps aux | grep -i hermes-setup'`) before attempting any auth reset. Wait for or kill the stuck updater PID, then re-check.

Common failure patterns:

```
Desktop boot failed: Your remote gateway session has expired.
Open Settings → Gateway and click "Sign in" again
```

**Fix:** Open Hermes desktop → Settings → Gateway → re-authenticate.

If re-auth doesn't work:
- Verify the remote host is reachable: `nc -z -w3 <host> <port>`
- Check the remote gateway is alive: `curl -s http://<host>:<port>/api/status`
- The gateway writes session cookies (`hermes_session_at`, `hermes_session_rt`) into the Electron cookie store. Clearing these and re-signing-in is equivalent to "sign out and back in."
- On the remote host, check `~/.hermes/logs/gateway.log` or `~/.hermes/logs/dashboard.log` for auth errors.

### 2B. Remote mode: unreachable host

If the desktop log shows `net::ERR_NAME_NOT_RESOLVED` or timeout:
- Verify Tailscale/network connectivity to the remote host
- Check Tailscale status: `tailscale status`
- Verify the remote port is open: `nc -z -w3 <host> <port>`
- The remote gateway URL is stored in Electron's persisted state (not auth.json or config.yaml). It's set once during first-launch remote configuration and survives reinstalls.

### 2C. Local mode: backend spawn failure

Local mode spawns `hermes serve --host 127.0.0.1 --port 0`. Failures show as:
```
Timed out connecting to Hermes backend after 15000ms
```

**Troubleshoot:**
1. Verify the local Hermes CLI works: `hermes --version`
2. Try starting the backend manually: `hermes serve --host 127.0.0.1 --port 8642`
3. Check Python/environment issues in the venv: `~/.hermes/hermes-agent/venv/bin/python -c "import hermes_cli"`

### 2D. Remote mode: the remote install cannot execute

The desktop reports this when the remote is reachable but the SSH handshake fails:

```
Desktop boot failed: The remote Hermes install does not support --ssh-session-token-file and --ssh-owner-nonce. Update Hermes on the remote host to continue using Desktop SSH mode.
```

**Treat that sentence as an unverified hypothesis, not a finding.** It is the desktop's interpretation of a failed handshake, and a remote that cannot execute Python at all produces the identical message. Never recommend an update on the strength of that sentence alone — prove which case it is first.

Procedure:

1. **Check whether the flags exist in the remote source.** If they do, the version-mismatch theory is dead.
   ```bash
   ssh <host> 'grep -rn "ssh_session_token_file" --include="*.py" ~/.hermes/hermes-agent | head'
   ```
2. **Probe executability with a subcommand, never `--version`.** `hermes --version` short-circuits before module-level imports, so it reports healthy on a tree where every real invocation dies. `hermes serve --help` walks the import graph and is the honest test.
   ```bash
   ssh <host> 'hermes serve --help 2>&1 | head -20'
   ```
3. **On SyntaxError, suspect an abandoned merge before a dependency problem.** Unresolved conflict markers in a module imported at startup break every entry point, and the traceback names the *importer*, not the broken file — so the reported line looks innocent.
   ```bash
   ssh <host> 'cd ~/.hermes/hermes-agent && { [ -f .git/MERGE_HEAD ] && cat .git/MERGE_HEAD; grep -rlF "<<<<<<<" --include="*.py" . | head; }'
   ```
4. **Before offering `git merge --abort`, prove nothing is lost.** Count unstaged and untracked separately from staged. All-staged with 0 unstaged and 0 untracked means the tree holds only merge output, and abort returns it to `ORIG_HEAD`.
   ```bash
   ssh <host> 'cd ~/.hermes/hermes-agent && git status --porcelain | grep -cE "^.[MDARC]"; git status --porcelain | grep -c "^??"; git rev-parse --short ORIG_HEAD'
   ```
5. **Present it as a one-command fix and get approval.** An uncommitted merge has no work to lose and `ORIG_HEAD` names the exact pre-merge commit, so the fix is trivially reversible — but it is still a mutation of a production host, so stop and ask.

`scripts/probe-remote-install.sh` runs steps 1-5 in one shot against a given ssh host.

### 3. Identity file check ("agent init failed")

The "agent init failed: no such file or directory: soul.md" error comes from `tui_gateway/server.py` around line 1461. The wrapped exception is usually from `_ensure_default_soul_md` in `hermes_cli/config.py` during bootstrap.

**Identity file locations:**

| File | Path | Purpose |
|------|------|---------|
| SOUL.md | `~/.hermes/SOUL.md` | Agent persona — required for agent init |
| MEMORY.md | `~/.hermes/memories/MEMORY.md` | Cross-session durable memory |
| USER.md | `~/.hermes/memories/USER.md` | User profile (name, role, preferences) |

**Verification:**
```bash
ls -la ~/.hermes/SOUL.md ~/.hermes/memories/MEMORY.md ~/.hermes/memories/USER.md
wc -c ~/.hermes/SOUL.md
```

The bootstrap installer seeds a default SOUL.md on first run via `_ensure_default_soul_md()`. A `FileNotFoundError` during this step suggests the file was deleted or the HOME directory was recreated. Restore from a known-good backup or run `hermes update` to re-trigger the bootstrap.

The bootstrap log entry for this failure looks like:
```
2026-07-10T01:25:25.717155Z INFO bootstrap.log: FileNotFoundError: [Errno 2] No such file or directory: '/Users/prasta/.hermes/SOUL.md'
```

**Note:** "agent init failed" from the desktop does NOT imply a missing SOUL.md — it wraps *any* exception during agent initialization. Always check if the real problem is a gateway session expiry, which produces the same "agent init failed" message in the UI but for a completely different reason.

### 4. Profile backends

The desktop may also spawn per-profile backends (for names profiles like `cs-copilot`, `larp`, `diane`). Log entries like:
```
[hermes] Reaping idle profile backend "cs-copilot" (idle > 600s)
```

These are managed by the Electron main process. A profile backend that fails to initialize will surface as a timeout or error when the desktop tries to use that profile. Each profile gets its own `~/.hermes/profiles/<name>/` directory with its own SOUL.md, MEMORY.md, and skills.

### 5. Update loops

The desktop log may show rapid update-restart cycles:
```
[hermes] [updates] restart: Updating Hermes — this window will close...
[hermes] [updates] launched updater: /Users/prasta/.hermes/hermes-setup --update
```

This means the app is caught in an update cycle. Wait for it to complete, or if stuck:
1. Kill all Hermes processes
2. Run the updater manually: `~/.hermes/hermes-setup --update --target-app /Applications/Hermes.app`
3. Launch Hermes.app fresh

## Profile Dropdown Diagnostics

The Hermes desktop app shows a profile dropdown in the UI. If profiles shown don't match what `hermes profile list` returns locally, the app is probably in **remote mode** and the dropdown reflects the **remote dashboard's** profile list, not the local machine's.

### Check the mode

The desktop app's mode is stored in `~/Library/Application\ Support/Hermes/connection.json`:

```json
{
  "mode": "remote",                  // "remote" or "local"
  "remote": {
    "url": "http://studio.taile85139.ts.net:9119",  // remote dashboard URL
    "authMode": "oauth"              // "oauth" or "none"
  },
  "profiles": {}                     // per-profile overrides (usually empty)
}
```

- **`mode: "local"`** — profiles come from the local machine's `hermes profile list`
- **`mode: "remote"`** — profiles come from the remote dashboard (the Studio, another server, etc.)
- **`profiles: {}`** — no per-profile overrides; the dropdown populates from whatever the remote serves

Local vs remote mode is also visible in `~/.hermes/logs/desktop.log` — look for:
```
[hermes] [boot] Connecting to remote Hermes backend at http://...
```
vs
```
[hermes] [boot] Spawning local backend: hermes serve --host 127.0.0.1 --port 0
```

### Verify the remote dashboard's profile list

If reachable, curl the remote dashboard's profile API:

```bash
curl -s -H "Authorization: Bearer <token>" http://<remote>:9119/api/profiles
```

The response shape:
```json
{
  "profiles": [
    {"name": "default", "model": "...", "provider": "...", "skill_count": 130, ...},
    {"name": "bd-copilot", "model": "...", "provider": "...", ...}
  ]
}
```

To find the session token, inspect the dashboard page source:
```bash
curl -s http://<host>:9119/ | grep -o '__HERMES_SESSION_TOKEN__="[^"]*"'
```

The dashboard page also embeds:
- `__HERMES_AUTH_REQUIRED__=true|false` — whether the endpoint demands auth
- `__HERMES_DASHBOARD_EMBEDDED_CHAT__=true|false`
- `__HERMES_BASE_PATH__=""`

### Common mismatch scenarios

| Local `hermes profile list` shows | Desktop dropdown shows | Likely cause |
|---|---|---|
| 5 profiles | Different set or empty | Desktop is in remote mode; remote has different profiles |
| 5 profiles | Correct profiles but stale data | Remote dashboard cache needs a refresh |
| No profiles | Profiles exist | Desktop is on a different machine from expected |

### Refresh the dropdown

- **Remote mode**: the dropdown is live from the remote dashboard. Re-authenticate or restart the desktop app (`File → Quit`, relaunch).
- **Local mode**: if profiles were added/removed recently, the desktop app may need a restart. There's no on-demand profile refresh — quit and reopen.

## Dashboard Session Token

The Hermes dashboard's web page embeds a session token in the initial HTML payload. This token authenticates API calls to the dashboard backend (e.g., `/api/profiles`, `/api/sessions`).

**Discovery:** The token is in a `<script>` tag inside the dashboard page source at the root URL (`http://localhost:9119/` or remote equivalent):
```html
<script>
window.__HERMES_SESSION_TOKEN__="<base64-encoded-token>";
window.__HERMES_DASHBOARD_EMBEDDED_CHAT__=true;
window.__HERMES_BASE_PATH__="";
window.__HERMES_AUTH_REQUIRED__=false;
</script>
```

**Usage:** Pass as a Bearer token in API requests:
```bash
curl -s -H "Authorization: Bearer <token>" http://localhost:9119/api/profiles
```

**When `__HERMES_AUTH_REQUIRED__=false`** (local-only bind, 127.0.0.1), the token still works for API calls but unauthenticated requests to `/api/*` return `401 Unauthorized`. The token is always present in the page regardless of auth mode.

## References

See `references/desktop-init-diagnostics.md` for a session-specific walkthrough of a real init failure diagnosis.

See `references/desktop-connection-profiles.md` for a reference case on profile dropdown mismatches between local and remote dashboard profiles — including the connection.json discovery, dashboard session token extraction, and profile API endpoint pattern.

See `references/remote-install-unrunnable.md` for the decision procedure behind section 2D — telling a genuinely old remote apart from a broken one, and the merge-abort safety check.

See `references/stale-dashboard-after-update.md` for the "running old code after an update" message:
which process is actually stale (the launchd dashboard, not the app backend or gateway), the launchd
vs. update race that creates it, the marker messages that no restart can clear, and the kickstart +
`/api/health` verification that proves the fix.

Run `scripts/probe-remote-install.sh <ssh-host>` for a read-only health verdict on a remote Hermes install (version, real executability, merge state, conflict markers, abort safety, service liveness).

## Pitfalls

- **Don't trust the bootstrap-installer.log alone.** The bootstrap log is from the update/install process, not the desktop runtime. The desktop.log is the first place to look.
- **"agent init failed" is a wrapper.** The actual error is appended after the colon. Read the full message, not just the prefix.
- **SOUL.md exists ≠ correct.** If the file exists but is the legacy comment-only template (from an old install.sh), bootstrap will try to upgrade it. Verify content is the real Wren persona, not a scaffold.
- **auth.json does not store gateway URL.** The remote gateway URL is stored in `~/Library/Application Support/Hermes/connection.json` and also in Electron's Local Storage / IndexedDB. `connection.json` is the most accessible source — it's a plain JSON file you can `cat`. To change or clear the remote URL, use the desktop app's Settings → Gateway UI, or edit `connection.json` directly (restart the app after).
- **Desktop.log may mix old and new diagnostics.** A running desktop app appends to the same log file across launches and update cycles. Filter for "boot" to see only the most recent startup attempt.
- **Gateway session expiry is invisible in agent.log.** The agent never starts, so there's no session to log. Look only in desktop.log for this.
- **Don't assume local mode.** The desktop silently switches modes based on stored preference, and there are three remote topologies (ssh / http gateway / local) whose failure surfaces differ. `Resolving Hermes backend` shows up in both local and ssh mode, so read `connection.json` rather than inferring the mode from that line.
- **A live service does not mean a healthy host.** A gateway that loaded its code before a checkout broke keeps serving from memory while every fresh spawn on that host fails. Check liveness (`launchctl list`, `ps`) for "is it up", but probe the tree separately for "can it still run".
- **Thrashing is a retry storm, not a hang.** Diff consecutive `Resolving Hermes backend` timestamps; sub-5-second gaps mean the desktop is looping on a handshake that will never succeed. Restarting the app only resets the timer — fix the handshake cause.
- **Quote globs you pass through `ssh`.** `--include=*.py` is expanded by the *remote* shell, which aborts the whole command with "no matches found", so the grep never runs and you wrongly conclude the symbol is absent. Use `--include="*.py"`.
- **Read the updater's own log to see how previous runs ended.** On a custom branch, `hermes update` merges rather than resets and conflicts repeatedly; earlier runs may have backed out cleanly while the failing one left a merge in place. Distinguish "update keeps failing cleanly" from "update keeps leaving a broken tree" — only the second one takes the host down.
- **"A request to check the logs is not authorization to mutate a host."** When the user asks you to diagnose, run the full read-only sequence and report; reserve the fix for explicit approval, even when the fix is a single reversible git command.