---
name: system-administration-workflows
description: "macOS system administration, LaunchAgent management, port monitoring, git backup, file system operations, and backup repository management."
---

# System Administration Workflows

This skill covers workflows for managing system-level configurations and infrastructure in macOS environments, particularly for AI development setups. It consolidates macOS system administration tasks: LaunchAgent management, port and service monitoring, git repository cleanup, file system operations, backup repository management, and git backup troubleshooting.

## When to Use This Skill

Use this skill when:
- Managing system-level LaunchAgents and services
- Investigating port conflicts or occupied services
- Cleaning up stale configuration files or repository artifacts
- Working with git repositories in system backup contexts
- Managing macOS system services and configuration files
- Resolving macOS Finder alias / symlink issues
- Troubleshooting launchd-managed git backup authentication
- Deciding whether to consolidate or separate backup repositories

## Skill Inventory

| Skill | Purpose | Status |
|---|---|---|
| System Administration Workflows | Umbrella guide (this skill) | core |
| macOS File System Operations | Alias resolution, symlink management | absorbed |
| macos-git-backup-troubleshooting | launchd git backup credential auth fixes | absorbed |
| backup-repository-management | Managing multiple backup repos with different content types | absorbed |

## Key Workflows

### 1. LaunchAgent Management (absorbed from macos-git-backup-troubleshooting)
- Check currently running LaunchAgents
- Identify stale or misconfigured LaunchAgent plists
- Remove obsolete system services
- For git backup auth failures: switch from HTTPS to SSH protocol for remote URLs
- Verify gh CLI authentication

Procedure for git backup auth mismatch:
1. Check git remote URL: git remote -v
2. Check recent launchd logs
3. Test git operations manually
4. Fix: change remote from HTTPS to SSH protocol

Reference: references/macos-git-backup-troubleshooting.md

### 2. Port and Service Monitoring
- Identify occupied ports and associated processes
- Check service status for running components

### 3. Git Repository Cleanup
- Remove stale or obsolete repository files
- Manage tracked vs untracked configuration files

### 4. macOS File System Operations (absorbed from macos-file-system-operations)
Handle macOS-specific file system operations including alias resolution and symlink management.

Resolving Finder Aliases:
```bash
python3 -c "
import os, subprocess
path = '/path/to/alias'
script = 'tell application Finder to return POSIX path of (original item of (alias file path))'
result = subprocess.run(['osascript', '-e', script], capture_output=True, text=True)
print(result.stdout.strip())
"
```

Converting aliases to symlinks:
```bash
rm "/path/to/alias"
ln -s "/resolved/target/path" "/path/to/alias"
```

Reference: references/macos-file-system-operations.md

### 5. Backup Repository Management (absorbed from backup-repository-management)
Managing multiple backup repositories that serve different purposes or contain different content types.

When multiple repositories are appropriate:
- backup-hermes-macstudio / backup-hermes-macbook: per-host Hermes snapshots (config, skills, scripts, encrypted secrets bundle)

Decision framework:
1. Evaluate content types (per-host snapshots vs single shared repo)
2. Consider backup purpose (recovery vs audit/inspection)
3. Decide on consolidation (same system = combine; different purposes = keep separate)

Reference: references/backup-repository-management.md

## User Preferences to Respect

1. Concise responses: direct answers without fluff
2. Prose over bullet lists: natural language explanations
3. For once and for all solutions: complete fixes rather than incremental
4. System context awareness: understand the specific macOS AI infrastructure setup

## Common Pitfalls

1. Stale LaunchAgent references referenced but not installed
2. Repository confusion: separate git repos should not be tracked in main backup
3. Git ignore patterns: understand deny-all + allow-list pattern
4. HTTPS vs SSH credential mismatch: the remote is SSH (`github.com:prasta1/...`); a launchd job that can't reach the SSH agent fails while the same push works by hand. Verify the remote is SSH and the agent is reachable under launchd.
5. Force-pushing to change backup target
6. Consolidating different content types that serve distinct purposes

## Verification Steps

1. Confirm LaunchAgents are properly loaded via launchctl print
2. Validate port usage with lsof
3. Ensure git repository state is clean after changes
4. For git backup: verify remote uses SSH protocol
5. For file system: verify symlinks resolve

## References
- references/macos-git-backup-troubleshooting.md
- references/macos-file-system-operations.md
- references/backup-repository-management.md
- references/silent-accumulation-audit.md — dirs that grow silently on both hosts (composer snapshots, logs, caches, bench results); audit-before-act
