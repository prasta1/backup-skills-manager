---
name: macos-git-backup-troubleshooting
description: Troubleshoot launchd-managed git backups in macOS environments, particularly credential authentication issues between SSH and HTTPS
version: 0.1.0
author: Wren
platforms: [macos]
---

# macOS Git Backup Troubleshooting

Diagnosing and fixing launchd-managed git backups where authentication fails or
the push wedges. The live mechanism (verified 2026-10-23) is `~/.hermes/scripts/hermes-git-backup.sh`, run daily 03:30 by launchd `ai.hermes.git-backup` on the Studio (and a MacBook twin).

## How the backup actually works (today)

- **The repo IS `~/.hermes` itself.** The script does `cd "$H"` (H=`~/.hermes`)
  and commits/pushes that tree. There is NO separate `~/.hermes/backup-repo`
  directory — an older reference claimed one; it does not exist.
- **Remote:** `origin` = `github.com:prasta1/backup-hermes-macstudio.git`
  (SSH form). Push is `git push origin main`.
- **hermes-agent archival:** a second push, `git -C "$H/hermes-agent" push
  --force prasta1 HEAD:refs/backups/studio`, sends the hermes-agent checkout
  to the fork under a ref only this machine writes. `--force` is deliberate
  (single-writer, HEAD legitimately moves non-fast-forward).
- **Secrets:** `config.yaml`, `.env`, `auth.json` are untracked. Live
  credentials ride the push as `secrets.tar.gz.cms` — an openssl `cms
  -encrypt` bundle to `backup-cert.pem`. The private key is NOT on this
  machine (Bitwarden attachment only), so the box can write the backup but
  cannot read it back. Restore: `openssl cms -decrypt -inform DER -in
  secrets.tar.gz.cms -inkey studio-backup-key.pem | tar -xz -C ~`.
- **Alerts:** failures reach Discord via `hermes send -t discord:alert-infra`.
  A failed alert is logged, never fatal.
- **Structural guard:** >50 files or >15 deletions defers the push and alerts
  ("review and commit manually") — backups stay stopped until a human acts.
- **Secret guard:** `hermes-secret-scan.py` (the PYTHON scanner) runs pre-push
  and aborts on findings. The `.sh` variant is renamed `.broken-bsd-grep` —
  BSD grep lacks `-P`, so it silently reported CLEAN; never call it.

## Common Issue: GitHub Authentication Mismatch

When the backup runs via launchd it may fail with "Write access to repository
not granted" even though `gh` CLI auth looks fine.

### Root Cause
launchd jobs don't inherit the SSH-agent session an interactive shell has. If
the remote is HTTPS but the user authenticates via SSH (or vice versa), the
push fails under launchd while working by hand.

### Diagnosis
1. Check the remote URL:
   ```bash
   git -C ~/.hermes remote -v
   ```
   Expect `github.com:prasta1/backup-hermes-macstudio.git` (SSH).
2. Check the backup log:
   ```bash
   tail -f ~/.hermes/logs/git-backup.log
   ```
3. Test the push manually:
   ```bash
   cd ~/.hermes && git push origin main -v
   ```

### Fix: switch the remote to SSH
```bash
git -C ~/.hermes remote set-url origin git@github.com:prasta1/backup-hermes-macstudio.git
```

## Other failure modes (all alert to Discord)

- **"push rejected — fetching and rebasing"** — the remote moved ahead (web
  edit, another machine). The script auto-rebases and retries once; if that
  fails it alerts and stops. Fix by hand: `git -C ~/.hermes pull --rebase`
  then push.
- **"DEFERRED: structural change"** — >50 files or >15 deletions. A human
  must review and commit; backups stay stopped until then.
- **"BLOCKED: secret scan found findings"** — `hermes-secret-scan.py` found a
  secret. Fix the finding, then re-run the script.
- **"secrets bundle: ... not encrypted"** — `backup-cert.pem` missing or a
  listed secret path absent. Credentials are NOT backed up that run.
- **hermes-agent archival push warning** — the fork ref push failed; this
  machine's hermes-agent work is single-copy until it succeeds.

## When to Use This Skill
- Backup script fails with "Write access to repository not granted"
- Launchd jobs for git backups fail consistently with 403 errors
- GitHub CLI is configured with SSH but backup uses HTTPS
- The daily 03:30 push stops and an alert fires

## Additional Considerations
- Ensure `gh` CLI is authenticated (`gh auth status`).
- Verify the backup repo exists and the user has write permission.
- For launchd jobs, set env vars in the plist if the job needs them (the
  script reads `HERMES_HOME`, `HERMES_BIN`, `BACKUP_MAX_FILES`,
  `BACKUP_MAX_DELETES`).
- The MacBook has its own twin backup (`backup-hermes-macbook`) — same script
  shape, different remote. Diagnose per-host.
