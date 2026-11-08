# Autonomous AI Agent Orchestration

**Absorbed from:** `autonomous-ai-agents` skill.

## Overview

Hermes provides support for orchestrating autonomous AI coding agents — Claude Code, OpenAI Codex, and OpenCode — via the terminal and process tools.

## Claude Code Integration

### Prerequisites
- Install: `npm install -g @anthropic-ai/claude-code`
- Auth: run `claude` once to log in

### Two Orchestration Modes

#### Mode 1: Print Mode (`-p`) - Non-Interactive (PREFERRED)

One-shot task, returns result, exits. No PTY needed.

```
terminal(command="claude -p 'Add error handling to all API calls in src/' --allowedTools 'Read,Edit' --max-turns 10", workdir="/path/to/project", timeout=120)
```

**When to use:** One-shot coding tasks, CI/CD automation, structured data extraction, piped input.

#### Mode 2: Interactive PTY via tmux

Full conversational REPL for multi-turn work.

```
terminal(command="tmux new-session -d -s claude-work -x 140 -y 40")
terminal(command="tmux send-keys -t claude-work 'cd /path/to/project && claude' Enter")
terminal(command="sleep 5 && tmux send-keys -t claude-work 'Refactor the auth module' Enter")
terminal(command="sleep 15 && tmux capture-pane -t claude-work -p -S -50")
terminal(command="tmux send-keys -t claude-work '/exit' Enter")
```

### Best Practices

1. Prefer print mode for automation — cleaner, structured output
2. Use Claude Max auth — `loggedIn: true` confirms authentication
3. SSH backend required — `HERMES_SSH_HOST` and `HERMES_SSH_USER` must be set
4. Use tmux for multi-turn interactive work
5. Always set `workdir`
6. Set `--max-turns` in print mode — prevents infinite loops
7. Look for the `❯` prompt — indicates Claude is waiting for input
8. Clean up tmux sessions when done

## OpenAI Codex Integration

### Prerequisites
- Codex installed: `npm install -g @openai/codex`
- OpenAI auth configured
- Must run inside a git repository
- Use `pty=true` in terminal calls

### One-Shot Tasks
```
terminal(command="codex exec 'Add dark mode toggle to settings'", workdir="~/project", pty=true)
```

For scratch work:
```
terminal(command="cd $(mktemp -d) && git init && codex exec 'Build a snake game in Python'", pty=true)
```

### Background Mode
```
terminal(command="codex exec --full-auto 'Refactor the auth module'", workdir="~/project", background=true, pty=true)
process(action="poll", session_id="<id>")
process(action="log", session_id="<id>")
process(action="submit", session_id="<id>", data="yes")
process(action="kill", session_id="<id>")
```

### Common Flags

| Flag | Effect |
|------|--------|
| `exec "prompt"` | One-shot execution |
| `--full-auto` | Auto-approves file changes |
| `--yolo` | No sandbox, no approvals |
| `--sandbox danger-full-access` | No Codex sandbox |

## OpenCode Integration

### Prerequisites
- Install: `npm i -g opencode-ai@latest`
- Auth: `opencode auth login` or set provider env vars

### One-Shot Tasks
```
terminal(command="opencode run 'Add retry logic to API calls'", workdir="~/project")
```

### Interactive Sessions
```
terminal(command="opencode", workdir="~/project", background=true, pty=true)
process(action="submit", session_id="<id>", data="Implement OAuth refresh flow")
process(action="poll", session_id="<id>")
process(action="write", session_id="<id>", data="\x03")
```

## Agent Comparison

| Feature | Claude Code | OpenAI Codex | OpenCode |
|---------|-------------|--------------|----------|
| Platform | Anthropic | OpenAI | Multi-provider |
| Interactive Mode | TUI with tmux | TUI | TUI |
| One-Shot Mode | Print mode (`-p`) | `exec` | `run` |
| Authentication | OAuth or API key | OAuth or API key | OAuth or API key |

## Herd Configuration Example

```yaml
model:
  default: qwen3.5:9b
  provider: custom:local-ollama
providers:
  local-ollama:
    base_url: http://localhost:11434/v1
```
