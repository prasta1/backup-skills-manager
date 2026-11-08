---
name: autonomous-ai-agents
description: "Comprehensive orchestration and management of autonomous AI coding agents"
version: 1.0.0
author: Hermes Agent + Teknium
license: MIT
tags: [coding-agent, autonomous, claude, codex, opencode, agent-orchestration]
---

# Autonomous AI Agents - Hermes Orchestration Guide

This skill provides comprehensive guidance for orchestrating autonomous AI coding agents including Claude Code, OpenAI Codex, and OpenCode via the Hermes terminal and process tools.

## Overview

Hermes provides extensive support for various autonomous AI coding agents that can be used to implement features, refactor code, review pull requests, and automate software development tasks.

## Claude Code Integration

### Prerequisites
- Install: `npm install -g @anthropic-ai/claude-code`
- Auth: run `claude` once to log in (browser OAuth for Pro/Max, or set `ANTHROPIC_API_KEY`)
- Console auth: `claude auth login --console` for API key billing
- Check status: `claude auth status` (JSON) or `claude auth status --text` (human-readable)

### Two Orchestration Modes

#### Mode 1: Print Mode (`-p`) - Non-Interactive (PREFERRED for most tasks)
Print mode runs a one-shot task, returns the result, and exits. No PTY needed.

```
terminal(command="claude -p 'Add error handling to all API calls in src/' --allowedTools 'Read,Edit' --max-turns 10", workdir="/path/to/project", timeout=120)
```

**When to use print mode:**
- One-shot coding tasks (fix a bug, add a feature, refactor)
- CI/CD automation and scripting
- Structured data extraction with `--json-schema`
- Piped input processing (`cat file | claude -p "analyze this"`)
- Any task where you don't need multi-turn conversation

#### Mode 2: Interactive PTY via tmux - Multi-Turn Sessions
Interactive mode gives you a full conversational REPL where you can send follow-up prompts, use slash commands, and watch Claude work in real time.

```
# Start a tmux session
terminal(command="tmux new-session -d -s claude-work -x 140 -y 40")

# Launch Claude Code inside it
terminal(command="tmux send-keys -t claude-work 'cd /path/to/project && claude' Enter")

# Wait for startup, then send your task
# (after ~3-5 seconds for the welcome screen)
terminal(command="sleep 5 && tmux send-keys -t claude-work 'Refactor the auth module to use JWT tokens' Enter")

# Monitor progress by capturing the pane
terminal(command="sleep 15 && tmux capture-pane -t claude-work -p -S -50")

# Send follow-up tasks
terminal(command="tmux send-keys -t claude-work 'Now add unit tests for the new JWT code' Enter")

# Exit when done
terminal(command="tmux send-keys -t claude-work '/exit' Enter")
```

### Configuration and Best Practices
1. Prefer print mode (`-p`) for single tasks - cleaner, no dialog handling, structured output
2. Use Claude Max auth - `loggedIn: true` confirms authentication via claude.ai (no rate limits)
3. SSH backend required - `HERMES_SSH_HOST` and `HERMES_SSH_USER` must be set for terminal tool execution
4. Use tmux for multi-turn interactive work - the only reliable way to orchestrate the TUI
5. Always set `workdir` - keep Claude focused on the right project directory
6. Set `--max-turns` in print mode - prevents infinite loops and runaway costs
7. Monitor tmux sessions - use `tmux capture-pane -t <session> -p -S -50` to check progress
8. Look for the `❯` prompt - indicates Claude is waiting for input (done or asking a question)
9. Clean up tmux sessions - kill them when done to avoid resource leaks
10. Report results - after completion, summarize what Claude did and what changed (no padding)

## OpenAI Codex Integration

### Prerequisites
- Codex installed: `npm install -g @openai/codex`
- OpenAI auth configured: either `OPENAI_API_KEY` or Codex OAuth credentials from the Codex CLI login flow
- Must run inside a git repository - Codex refuses to run outside one
- Use `pty=true` in terminal calls - Codex is an interactive terminal app

### One-Shot Tasks
```
terminal(command="codex exec 'Add dark mode toggle to settings'", workdir="~/project", pty=true)
```

For scratch work (Codex needs a git repo):
```
terminal(command="cd $(mktemp -d) && git init && codex exec 'Build a snake game in Python'", pty=true)
```

### Background Mode (Long Tasks)
```
# Start in background with PTY
terminal(command="codex exec --full-auto 'Refactor the auth module'", workdir="~/project", background=true, pty=true)
# Returns session_id

# Monitor progress
process(action="poll", session_id="<id>")
process(action="log", session_id="<id>")

# Send input if Codex asks a question
process(action="submit", session_id="<id>", data="yes")

# Kill if needed
process(action="kill", session_id="<id>")
```

### Common Flags
| Flag | Effect |
|------|--------|
| `exec "prompt"` | One-shot execution, exits when done |
| `--full-auto` | Sandboxed but auto-approves file changes in workspace |
| `--yolo` | No sandbox, no approvals (fastest, most dangerous) |
| `--sandbox danger-full-access` | No Codex sandbox; useful when the host service context breaks bubblewrap |

## OpenCode Integration

### Prerequisites
- OpenCode installed: `npm i -g opencode-ai@latest` or `brew install anomalyco/tap/opencode`
- Auth configured: `opencode auth login` or set provider env vars (OPENROUTER_API_KEY, etc.)
- Verify: `opencode auth list` should show at least one provider
- Git repository for code tasks (recommended)
- `pty=true` for interactive TUI sessions

### One-Shot Tasks
Use `opencode run` for bounded, non-interactive tasks:
```
terminal(command="opencode run 'Add retry logic to API calls and update tests'", workdir="~/project")
```

Attach context files with `-f`:
```
terminal(command="opencode run 'Review this config for security issues' -f config.yaml -f .env.example", workdir="~/project")
```

Show model thinking with `--thinking`:
```
terminal(command="opencode run 'Debug why tests fail in CI' --thinking", workdir="~/project")
```

Force a specific model:
```
terminal(command="opencode run 'Refactor auth module' --model openrouter/anthropic/claude-sonnet-4", workdir="~/project")
```

### Interactive Sessions (Background)
For iterative work requiring multiple exchanges, start the TUI in background:
```
terminal(command="opencode", workdir="~/project", background=true, pty=true)
# Returns session_id

# Send a prompt
process(action="submit", session_id="<id>", data="Implement OAuth refresh flow and add tests")

# Monitor progress
process(action="poll", session_id="<id>")
process(action="log", session_id="<id>")

# Send follow-up input
process(action="submit", session_id="<id>", data="Now add error handling for token expiry")

# Exit cleanly - Ctrl+C
process(action="write", session_id="<id>", data="\x03")
# Or just kill the process
process(action="kill", session_id="<id>")
```

### Configuration and Best Practices
1. Prefer `opencode run` for one-shot automation - it's simpler and doesn't need pty.
2. Use interactive background mode only when iteration is needed.
3. Always scope OpenCode sessions to a single repo/workdir.
4. For long tasks, provide progress updates from `process` logs.
5. Report concrete outcomes (files changed, tests, remaining risks).
6. Exit interactive sessions with Ctrl+C or kill, never `/exit`.

## Agent Comparison and Use Cases

### Claude Code vs Codex vs OpenCode

| Feature | Claude Code | OpenAI Codex | OpenCode |
|---------|-------------|--------------|----------|
| Platform | Anthropic | OpenAI | Multi-provider |
| Interactive Mode | TUI with tmux orchestration | TUI | TUI |
| One-Shot Mode | Print mode (`-p`) | `exec` command | `run` command |
| Model Support | Claude models | GPT models | Multiple providers |
| Authentication | OAuth or API key | OAuth or API key | OAuth or API key |
| Use Case | Complex reasoning, structured output | Fast implementation, scratch work | Multi-provider flexibility |

## Configuration Examples

### Herd Configuration
```
# Example configuration for Claude Code
model:
  default: qwen3.5:9b
  provider: custom:local-ollama
  context_length: 200000

providers:
  local-ollama:
    base_url: http://localhost:11434/v1
    default_model: qwen3.5:9b
    request_timeout_seconds: 300

  local-tailscale:
    base_url: http://studio.taile85139.ts.net:11434/v1
    default_model: qwen3-coder:30b
    request_timeout_seconds: 300
```

## Best Practices

1. **Prefer print mode for automation** - Cleaner, no dialog handling, structured output
2. **Use appropriate tools for task complexity** - Simple tasks with Claude Code print mode, complex iterative work with TUI
3. **Always scope sessions to specific directories** - Prevents cross-contamination and confusion
4. **Monitor long-running tasks** - Use process monitoring for background operations
5. **Clean up resources** - Kill tmux sessions and processes when done
6. **Document task outcomes** - Summarize what each agent did for user clarity


## Merge Conflict Reconciliation (absorbed from merge-reconciler)

Resolve a git merge conflict between two AGENTS' branches as an impartial third party. Agents resolving conflicts against a peer's work reliably overwrite the peer or abandon their own change — they lack the peer's context and are biased toward their own side. This subsection is the fix: a neutral reconciler that receives both diffs plus both sides' stated intents and produces a merged result.

### When to Use
- Two agent branches/worktrees collide during a parallel campaign
- `git merge` or `git rebase` halts on conflicts between two agents' work
- Do NOT use for conflicts within a single agent's own work, or for trivial lockfile conflicts

### Quick Reference

| Hunk class | Definition | Resolution |
|---|---|---|
| disjoint-intent | Different goals, can coexist | Combine both |
| same-question-different-answer | Both sides answered one design question differently | Pick ONE per stated intents |
| superseded | One side's premise no longer holds after the other's change | Keep the surviving side; note why |

### Procedure
1. **Gather both sides** — `git status`, `git merge-base`, `git diff` for each side. Collect intent from PR bodies, commit messages, or kanban completion summaries.
2. **Classify every conflicted hunk** — assign each `<<<<<<<` block one class from the table above.
3. **Resolve under the impartiality contract** — disjoint-intent: merge both; same-question: pick per stated intents; superseded: keep surviving side. Touch ONLY conflicted regions. `git add` each resolved file.
4. **Verify** — Run build/tests; both intents must be demonstrably present.
5. **Hand back** — Produce a completion summary naming every hunk decision.

**Full reference:** `references/merge-reconciler.md`


## Issue-to-PR Workflow (absorbed from github-issue-to-pr)

**When to use:** "Fix issue #123 and open a PR", "Implement this GitHub feature request", "Take this bug from issue to green CI"

This workflow uses autonomous agents to carry a GitHub issue to a verified PR with honest CI state. The procedure:
1. Read the live issue body AND full thread (comments carry live state)
2. Sweep for existing/duplicate PRs with keyword variants
3. Validate premise against current code + design intent (git log -p -S)
4. Define acceptance criteria and risk
5. Implement the smallest complete change — fix the class, not just one call site
6. Prove the regression test bites (sabotage run: revert fix, test fails, restore fix)
7. Run quality gates, open PR immediately (PR dispatches CI)
8. Shepherd CI honestly — report from live evidence only

**Full reference:** `references/github-issue-to-pr.md`

## References

- `references/claude-auth.md` - Claude authentication best practices and configuration
- `templates/agent-config.yaml` - Example configurations for different agents