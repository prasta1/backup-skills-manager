---
name: Session Cleanup
version: 1.0.0
description: Complete session history removal in Hermes across multiple storage systems
---

# Session Cleanup

## Overview

Complete session history removal in Hermes requires understanding that there are multiple storage systems and different cleanup behaviors depending on the session source and UI.

## Storage Systems

Hermes uses multiple session storage mechanisms:
1. **SQLite Database** (`~/.hermes/state.db`) - Core session metadata storage
2. **Web UI Session Files** (`~/.hermes/webui/sessions/*.json`) - Individual session snapshots from the web UI
3. **Request Dump Files** (`~/.hermes/sessions/*.json`) - Temporary session dumps

## Prune Limitations

The `hermes sessions prune` command has specific limitations:
- Only deletes **ended** sessions (where `ended_at IS NOT NULL`)
- Does not clean web UI session JSON files
- Does not clean request dump files

## Complete Cleanup Process

To fully clear all session history:

1. **Archive active sessions first:**
   ```bash
   hermes sessions archive --source webui --yes
   hermes sessions archive --source telegram --yes
   hermes sessions archive --source cli --yes
   ```

2. **Prune ended sessions:**
   ```bash
   hermes sessions prune --older-than 0s --yes
   ```

3. **Manually remove JSON files:**
   ```bash
   rm -rf ~/.hermes/webui/sessions/*.json
   rm -rf ~/.hermes/sessions/request_dump_*.json
   ```

## Important Notes

- Sessions that are "active" (missing `ended_at` timestamp) cannot be pruned by the CLI
- The web UI maintains its own session files that are independent of the SQLite database
- Backups should be created before destructive operations

## Common Pitfall

Running `hermes sessions prune` alone will NOT remove sessions from the web UI or desktop app, as these use separate storage systems that are not cleaned by the prune command.