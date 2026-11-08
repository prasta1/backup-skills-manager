# Desktop Init Failure — Reference Case

## Scenario

The desktop app showed "agent init failed no such file or directory soul.md" on startup. The user had a backup of SOUL.md, MEMORY.md, and USER.md from a July 10 identity backup.

## Initial Assumption

That SOUL.md was missing or corrupt, and needed restoring from backup.

## Actual Root Cause

The desktop was configured as a **remote gateway client** pointing at a Mac Studio (`studio.taile85139.ts.net:9119`). The remote gateway session had expired. The "agent init failed" message was a secondary symptom — the desktop never even started a local backend.

## Evidence Chain

### Step 1: File existence check
```
~/.hermes/SOUL.md — exists, 7002 bytes ✓
~/.hermes/memories/MEMORY.md — exists, 2199 bytes ✓
~/.hermes/memories/USER.md — exists, 4697 bytes ✓
```
All files were intact and the current MEMORY.md was actually *newer* than the backup.

### Step 2: Desktop log (the real diagnostic source)
```
[hermes] [boot] Connecting to remote Hermes backend at http://studio.taile85139.ts.net:9119
[hermes] [boot] Remote Hermes backend is ready
...
Desktop boot failed: Your remote gateway session has expired.
Open Settings → Gateway and click "Sign in" again.
```

### Step 3: Bootstrap log (secondary, older error)
```
2026-07-10T01:25:25.717155Z  INFO bootstrap.log: FileNotFoundError: [Errno 2]
  No such file or directory: '/Users/prasta/.hermes/SOUL.md'
```
This was a July 10 bootstrap failure during an update, not the current app runtime error. The file was restored since then.

### Step 4: Identity diff
```
SOUL.md — identical to backup
USER.md — identical to backup
MEMORY.md — newer than backup (had DGX Spark cleanup facts the backup didn't)
```

## Key Lessons

1. **desktop.log first, always.** The bootstrap-installer.log was from the update process, not the app runtime. They're different processes with different error states.
2. **Remote vs local mode.** The desktop can silently switch modes. The log says `Connecting to remote Hermes backend` — that's the first thing to check.
3. **"agent init failed" wraps everything.** In `tui_gateway/server.py:1461`, `_emit("error", sid, {"message": f"agent init failed: {e}"})` catches any exception during agent construction. The suffix after "agent init failed:" is the actual error.
4. **Gateway session expiry ≠ missing files.** A missing SOUL.md would prevent agent init on a *local* backend. On a remote client, the gateway never lets you start a session if your auth is expired.
5. **Network verification confirms reachability.** The Studio was reachable (13ms ping, ports 9119 and 1234 open), so the issue was purely the expired auth session, not network.

## Diagnosis Commands Used

```bash
# Check desktop log
tail -100 ~/.hermes/logs/desktop.log

# Verify identity files
ls -la ~/.hermes/SOUL.md ~/.hermes/memories/MEMORY.md ~/.hermes/memories/USER.md

# Diff against backup
diff ~/.hermes/SOUL.md ~/Downloads/hermes-identity.bak.20260710/SOUL.md

# Check remote host reachability
ping -c 2 -t 3 studio.taile85139.ts.net
nc -z -w3 studio.taile85139.ts.net 9119
nc -z -w3 studio.taile85139.ts.net 1234

# Check local CLI availability
which hermes && hermes --version

# Check auth.json for gateway config
python3 -c "import json; d=json.load(open('~/.hermes/auth.json')); print(json.dumps(d, indent=2))"

# Check gateway state
cat ~/.hermes/gateway_state.json

# Search for "agent init failed" in all logs (catch if hidden in other files)
grep -ri "agent init failed" ~/.hermes/logs/
```