---
name: backup-repository-management
description: Managing multiple backup repositories with different content types and purposes
version: 0.1.0
author: Wren
platforms: [macos, linux]
---

# Backup Repository Management

This skill covers managing multiple backup repositories that serve different purposes or contain different content types.

## When Multiple Repositories Are Appropriate

In some backup scenarios, you may have multiple repositories:
- `backup-hermes-macstudio` - Studio host snapshot (config, skills, scripts, encrypted secrets bundle)
- `backup-hermes-macbook` - MacBook host snapshot

These should be kept separate when they serve different backup purposes.

## Decision Framework for Repository Management

1. **Evaluate content types**: 
   - Database backups (SQL dumps) vs application instance data (JSON/JS configs)
   - Different retention policies or storage requirements

2. **Consider backup purpose**:
   - Is one for recovery, one for audit/inspection?
   - Do they serve different teams or systems?

3. **Decide on consolidation**:
   - If both are for the same system, consider combining with proper naming/structure
   - If they're fundamentally different (DB vs app state), keep separate

## Example Workflow

```bash
# Check current repository status
cd /path/to/backup/repo
git remote -v

# If you have different content types:
# - backup-hermes-macstudio: Studio host snapshot
# - backup-hermes-macbook: MacBook host snapshot

# Only change target when appropriate for content type
git remote set-url origin git@github.com:prasta1/backup-hermes-macstudio.git  # For Studio backups
```

## Common Pitfalls

- **Force-pushing to change a backup target**: Avoid rewriting history of repositories that are actively being used for backups
- **Consolidating different content types**: Keep separate if they serve distinct purposes (e.g., DB vs app config)
- **Overlooking different retention needs**: Database backups may need more frequent rotation than application state

## When to Use This Skill

- You're setting up or managing multiple backup repositories
- You need to decide whether to consolidate or keep separate repositories
- You're working with backup scripts that push to GitHub repos