---
name: hermes-backup
description: Manage focused git backups of Hermes config and skills.
---
# Hermes Backup Strategy

When backing up the Hermes environment to a remote repository (e.g., GitHub), follow a "Configuration-Only" principle. The goal is to capture the *definition* of the environment, not its *runtime state*.

## 0. Live Deployment (Two Environments)

There are two Hermes instances, each backed up to its own GitHub repo. **Per-machine repos, never a shared one** — each machine has its own `config.yaml`, independently-grown memories, and machine-specific provider/config state. A shared repo would force subdirectory or branch separation and risk one machine's push clobbering the other's divergent history. One machine = one restore unit.

| Machine | User | Repo | Shell | Schedule |
|---------|------|------|-------|----------|
| **Mac Studio** (always-on desktop) | `macstudio` | `prasta1/backup-hermes-macstudio` (HTTPS) | bash 3.2 | 03:30 daily |
| **MacBook Pro** (day-used laptop) | `prasta` | `prasta1/backup-hermes-macbook` (SSH) | zsh | 13:00 daily |

Both run a **launchd LaunchAgent** that calls a per-machine backup script daily, and both implement the same guarantees:

- **Pre-push secret guard.** `scripts/hermes-secret-scan.sh` runs on only the *staged* files (respects a file list arg) before any commit. If it flags a raw key/token, the push aborts. This is the hard blocker for the #1 pitfall (secret leakage).
- **Silent no-op.** Nothing changed → nothing happens (no commit, no log noise, no empty-push spam).
- **Self-healing push.** The MBP script pushes unconditionally, so a previously failed push is retried even on a day with no new commit. The Studio script also retries via its own push step.
- **Overlap guard (Studio).** A lock file bails if a prior run is somehow still active.

**Launchd agents:**
- Studio: `ai.hermes.git-backup` → `~/Library/LaunchAgents/ai.hermes.git-backup.plist` → `/bin/bash scripts/hermes-git-backup.sh`
- MBP: `com.prasta.hermes-git-backup` → `~/Library/LaunchAgents/com.prasta.hermes-git-backup.plist` → `/bin/zsh scripts/hermes-git-backup.sh`
- (MBP's agent was initially `com.prasta.hermes-git-backup` at 21:00; moved to 13:00 — see scheduling philosophy below.)

**Scheduling philosophy — match the machine's awake window, and it doesn't matter if it's not always-on:**
Both scripts are **idempotent and self-healing** (unconditional push + strict no-op silence), so a missed tick is harmless — the next run catches up any pending changes. That removes the pressure to pick a "perfect" time. The only real constraint is to fire during the window the machine is actually awake, because a sleeping machine simply skips its launchd tick:

- **Studio is always-on** → the dead of night (03:30) is an ideal quiet slot that never collides with interactive work.
- **MBP is a day-used laptop**, most likely closed/docked at night → 21:00 (its original slot) risked firing while asleep. Moved to 13:00 mid-workday when it's reliably on. Because pushes are unconditional, if it does miss one day the next run self-heals.

**bash-vs-zsh gotcha:** macOS ships **bash 3.2**, which has **no `mapfile`** (bash 4+ only). A script using `mapfile` (or `readarray`) fails silently-hard on 3.2. The Studio script therefore avoids it (`IFS=$'\n' read -r -d '' -a` instead); the MBP script uses **zsh** (default shell on modern macOS), which sidesteps the issue entirely and gives NUL-safe array splitting via `${(@0)...}`. `set -euo pipefail` is enabled in both.

**Deploying to the MBP over the tailnet:** `ssh macbook` (alias; `macbookpro` / `100.68.81.83`, user `prasta`, home `/Users/prasta`). The MBP's remote is SSH (`git@github.com:...`), the Studio's is HTTPS with the `osxkeychain` credential helper — both push non-interactively from launchd because auth is pre-solved (keychain / SSH agent), never a password prompt.

## 1. Core Scope
Only track files that define the persistent behavior of the Hermes agent:
- `.hermes/config.yaml` (The main configuration)
- `.hermes/memories/` (Persistent user and environment facts)
- `.hermes/skills/` (The procedural knowledge base)
- `.hermes/profiles/` (If specific profile configurations are needed)
- `README.md` (Project-level documentation)

## 2. Explicit Exclusions (The "Noise" Filter)
Never include the following in a backup repository. Ensure they are added to `.gitignore`:
- **Runtime State:** `.hermes/cache/`, `.hermes/sessions/`, `.hermes/logs/`, `.hermes/cron/`, `.hermes/state.db*`, `.hermes/response_store.db*`, `kanban.db*`, `gateway_state.json`, `gateway.lock`, `gateway.pid`
- **Package Manager Noise:** `node_modules/`, `venv/`, `.bundle/`, `.python-version`, `package-lock.json`
- **Temporary Files:** `.DS_Store`, `Thumbs.db`, `*.tmp`, `*.swp`
- **Secrets:** `.env`, `*.key`, `*.pem`, `auth.json`, `*.password` (Rotate keys if they must be in the repo, or use environment variables)
- **Heavy Artifacts:** `models/`, `data/`, `weights/`, `db.sqlite3` (unless specifically requested)

## 3. Handling Nested Repositories and Shared Skills (The Submodule/Symlink Trap)
Some skill directories may be submodules, symlinks, or global-shared paths. To prevent Git from treating them as dirty pointers and exploding the diff:
- **Inspect first:** check `git submodule status`, look for symlinks with `find skills -type l -ls`, and review `git status` before adding.
- **Preferred:** keep these directories out of the backup repo unless the user explicitly wants them tracked.
- **If restoration is required:** do not reintroduce submodule pointers blindly. If the source directory is a symlink, copy the real directory contents into place, then `git add` the restored tree. Replacing tracked directories with symlinks causes 100+ file churn and dirty submodule ghosts.
- **Cleanup path:** if a nested/symlinked directory is already causing churn, remove it from the index with `git rm --cached -r <path>` or `git rm --cached -- <path>` before replacing it with real content.

## 4. Standard Workflow
1. **Initialize:** `git init`
2. **Remote:** `git remote add origin <url>`
3. **Ignore:** Create a `.gitignore` that covers the "Noise" filter above.
4. **Select:** `git add .hermes/config.yaml .hermes/memories/ .hermes/skills/`
5. **Commit:** `git commit -m "Backup Hermes configuration and skills"`
6. **Push:** `git push -u origin main`

## 5. Pitfalls
- **Secret Leakage:** Always verify `.hermes/config.yaml` does not contain plain-text production keys before pushing.
- **Submodule Bloat:** If `git status` shows a directory as "modified content" but it's a nested repo, use `git rm --cached`.
- **Massive Commits:** If `git status` shows >1000 files, the Noise Filter was not applied correctly. Stop and check `.gitignore`.