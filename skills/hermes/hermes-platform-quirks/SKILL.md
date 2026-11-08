---
name: hermes-platform-quirks
description: Hermes Stack Pitfalls.
version: 1.1.0
license: MIT
author: Ionga (Hermes Curator)
tags: [hermes, operational, quirks, pitfall, workflow]
metadata:
  hermes:
    tags: [hermes, operational, quirks, pitfall, workflow]
---

# Hermes Platform Quirks

This skill captures non-obvious, high-cost, or failure-inducing operational constraints of the Hermes Agent on the Mac Studio. It is consulted when a workflow is unexpectedly halted or results in a non-standard error.

## Core Workflow Pitfalls

### Git Backup Deferral Gate
The automatic git backup script (`scripts/hermes-git-backup.sh`) includes a safety guard that automatically defers any backup run if a single change set (including deletions) exceeds 50 files or 15 deletions. Structural reorgs of the skills directory are a common trigger for this.
**Pitfall:** The system stops backing up until a human manually commits the structural changes. This is a safety measure to prevent accidental deletion/reorganization of critical history.

### Skill Resolution and Ambiguity
The skill resolver (`tools/skills_tool.py`) strictly enforces unique skill names. If two or more skills share the same name across different directories, the agent refuses to guess which one to load, returning an "Ambiguous skill name" error.
**Pitfall:** This refusal requires the user to explicitly load the skill using its full, categorized path (e.g., `category/skill-name`). Do not assume the system will auto-resolve name collisions.

### Skills Prompt Cache Invalidation
Renaming, moving, or altering the directory structure of a skill invalidates the disk-based skills prompt snapshot (`.skills_prompt_snapshot.json`).
**Pitfall:** The next session will require a full rebuild of the skill list, even if only one skill changed, due to the reliance on file paths for manifest integrity.

## Agentic Constraints & Performance
- **Prompt Overhead vs. Categorization:** While organizing skills into categories (e.g., `mlops/training/peft`) improves conversational legibility, these folders do not reduce the total number of skills loaded. All 264+ descriptions ship every turn. To reduce token overhead, focus on shorter descriptions, not deeper nesting.
- **External Dependency Fragility:** Many external tool APIs (e.g., Linear, Notion, AgentMail) rely on specific, internal MCP configurations. Failure to set the provider keys in the *server's* `config.yaml` block, rather than in the user's `.env` file, will cause connection errors.

- **launchd Test Copies:** When promoting a hand-run server to a KeepAlive LaunchAgent, kill the hand-started copy before `launchctl bootstrap`. Otherwise the launchd copy crash-loops on `EADDRINUSE` every 10s while the orphan keeps serving, and `launchctl list` shows exit 1 (ha-console, 2026-10-02: 2160 restarts).

## General Operational Principles

### Runtime Isolation and Workspace Drift
The production runtime (Mac Studio gateway) uses an isolated, managed installation of the code, which is a separate workspace copy and NOT the local `hermes-agent` checkout. This separation ensures production stability but causes issues where fixes applied to the checkout (e.g., TUI RPC method changes) are not immediately reflected in the live workspace.
**Pitfall:** Changes to the development checkout (MBP) must be explicitly synchronized or the managed workspace will retain the old, broken implementation (e.g., `r.describe()` instead of `r.description`). Do not assume the live production workspace is always current with the development branch.

### Update Synchronization Gate
The `hermes update` command will silently fail (a "no-op") if the development checkout (`~/.hermes/hermes-agent`) is not clean (i.e., has modified, unstaged files). The installation tool checks for a clean tree to ensure a predictable patch application; if dirty, it refuses to run to prevent overwriting local changes with potentially outdated upstream fixes.
If a tool can take action, it must take action. Do not describe what you would do; execute the command.
- **Action over Intent:** If a tool can take action, it must take action. Do not describe what you would do; execute the command.