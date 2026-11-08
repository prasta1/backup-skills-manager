---
name: macos-git-backup-troubleshooting
description: Troubleshoot launchd-managed git backups in macOS environments, particularly credential authentication issues between SSH and HTTPS
version: 0.1.0
author: Wren
platforms: [macos]
---

# macOS Git Backup Troubleshooting

This skill covers diagnosing and fixing launchd-managed git backups in macOS environments where authentication fails due to credential mismatch between HTTPS and SSH protocols.

## Common Issue: GitHub Authentication Mismatch

When a git backup script runs via launchd, it may fail with "Write access to repository not granted" errors even though the user is authenticated via `gh` CLI.

### Root Cause
The backup script typically uses HTTPS URLs for git operations, but the user's `gh` CLI is configured to use SSH credentials. When launched via launchd, git operations don't inherit the SSH-agent session that `gh` uses.

### Diagnosis
1. Check the git remote URL:
   ```bash
   cd /path/to/backup/repo
   git remote -v
   ```

2. Check recent launchd logs:
   ```bash
   tail -f /Users/macstudio/.paperclip-db-backup/launchd.log
   ```

3. Test git operations manually:
   ```bash
   cd /path/to/backup/repo
   git push -v origin master
   ```

### Fix: Switch from HTTPS to SSH
Change the git remote from HTTPS to SSH protocol:

```bash
git -C /Users/macstudio/.paperclip-db-backup remote set-url origin git@github.com:prasta1/backup-paperclip-db.git
```

This allows the backup script to use existing SSH credentials that are properly configured for the user's GitHub account.

## When to Use This Skill
- Backup scripts fail with "Write access to repository not granted"
- Launchd jobs for git backups fail consistently with 403 errors
- GitHub CLI is configured with SSH but backup uses HTTPS

## Additional Considerations
- Ensure `gh` CLI is properly authenticated via SSH (`gh auth status`)
- Verify the backup repository exists and user has write permissions
- For launchd jobs, consider setting proper environment variables in the plist if needed

## Handling Multiple Backup Repositories
When working with multiple backup repositories, consider their content types and purpose:
- `backup-paperclip-db` - Raw SQL dumps (plpgsql) for database snapshots
- `backup-paperclip` - Instance data (JS/JSON) for application state and configuration

In cases like this, the user should:
1. Evaluate whether both repositories serve different purposes (e.g., DB vs app instance)
2. If they do, keep them separate rather than consolidating into one
3. If consolidating is desired, handle the content type differences appropriately (e.g., separate directories or naming conventions)

The launch agent should target the appropriate repository based on content type and backup purpose.