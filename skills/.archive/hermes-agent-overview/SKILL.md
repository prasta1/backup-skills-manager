---
name: hermes-agent-overview
description: Quick reference for Hermes Agent capabilities and usage.
version: 0.1.0
author: Hermes
platforms: [macos, linux, windows]
metadata.hermes.tags: [Hermes, Agent, Reference]
---

# Hermes Agent Overview
This skill provides a concise reference to Hermes Agent's capabilities, including tools, skills, memory, MCP, configuration, and delegation. It does not replace the official documentation but serves as a quick‑reference guide for applying Hermes features in dynamic scenarios. All interactions are performed through Hermes' built‑in tools.

## When to Use
- Recall available tools or toolsets
- Configure Hermes for a new provider, backend, or integration
- Learn how to create, load, or update skills
- Set up persistent memory or user preferences
- Delegate tasks to subagents or invoke MCP servers
- Set up cron jobs, voice mode, or browser automation

## Prerequisites
- Hermes Agent installed and accessible via the `hermes` CLI
- No additional installations required; all capabilities accessed via built‑in tools
- For provider setup, API keys may be needed in `~/.hermes/.env`

## How to Run
Invoke via the `skill_view` tool to load this skill, then follow the procedures outlined. Alternatively, use the slash command `/hermes-agent-overview` after installation.

## Quick Reference
- `hermes tools` – list available tools and toolsets
- `hermes model` – configure AI provider and model
- `hermes moa` – create/list/delete MoA presets
- `hermes gateway setup` – configure messaging platforms
- `hermes skills opt-in/out` – manage bundled skill seeding
- `hermes mcp` – manage MCP servers
- `hermes cronjob` – create/list/update/remove scheduled jobs
- `hermes config` – view/edit configuration
- `memory` tool – add/replace/remove memory entries (target `memory` or `user`)
- `skill_view` / `skill_manage` – inspect and modify skills
- `delegate_task` – spawn subagents for parallel work
- `web_search`, `web_extract` – web research
- `browser_navigate`, `browser_snapshot`, `browser_vision` – browser automation
- `terminal` – execute shell commands (with backend options)
- `read_file`, `write_file`, `patch` – file operations
- `vision_analyze`, `image_generate`, `text_to_speech` – multimodal I/O
- `todo`, `clarify`, `execute_code` – planning and code execution
- `session_search` – search conversation history
- `send_message` – deliver messages via configured gateways

## User preference: concise response style
The user prefers direct, concise responses with minimal fluff. They are frustrated by verbosity and want to see the final result quickly. When using skills like `plan`, `subagent-driven-development`, or any other that would normally generate extensive documentation, they expect the result to be trimmed to only what is actionable and relevant.

This preference has been observed in their feedback and communication style throughout the session. To align with this, whenever a skill produces a large or verbose output (e.g., detailed plans), ensure that the output reflects the user's preference by:
- Limiting explanations to what is directly relevant
- Focusing on executable steps rather than process descriptions
- Avoiding unnecessary meta-commentary or "I'm doing this because..." rationale unless specifically requested by the user

## Key principle: Final result first
The user has expressed a preference for "short, direct, actionable" responses and avoids over-explanation or unnecessary context. When providing results (especially in multi-step processes), always lead with the actual output or final result, not a procedural description of how you got there.

For example:
- Instead of "I will search for webui files, then analyze the structure, and finally report what I found" - lead with "Here are the webui files found: [list]"
- Instead of "I'll look at the server configuration and then explain how to access it" - lead with "WebUI is accessible at http://localhost:8787"

## Prompt size awareness
The user has noted that the system prompt in Hermes can grow to over 32k characters and includes duplicated content. They are concerned with reducing prompt size for efficiency, and want to see any system prompt trimming or deduplication efforts captured in the skill documentation. This is a critical optimization for performance-sensitive use cases.

## User Preference Alignment
The user explicitly said they prefer "for once and for all" solutions over incremental fixes, which means they want to understand why something is working as designed rather than being treated as a bug. They also prefer direct commands to execute without meta-commentary about why these steps are needed, and minimal explanation unless specifically requested.

## Procedure
1. **Explore tools**: use the `terminal` tool to run `hermes tools`.
2. **Configure/view settings**: use `terminal` to run `hermes config` (view) or `hermes config set KEY VALUE` (modify).
3. **Set up AI provider**: run `hermes model` via `terminal` and follow prompts; API keys go to `~/.hermes/.env`.
4. **Enable toolset for a chat session**: launch Hermes with `hermes chat --toolsets "web,terminal,file"` (example) via `terminal`.
5. **Load a skill for reference**: use the `skill_view` tool with the skill name (e.g., `skill_view(name='hermes-agent-overview')`).
6. **Create or update a skill**: use `skill_manage` with action `create` or `patch`, providing SKILL.md content.
7. **Delegate a task to a subagent**: use `delegate_task` with a clear `goal` and optional `context`.
8. **Set up a recurring job**: use `cronjob` with action `create`, providing `schedule` and `prompt`.
9. **Interact with memory**: use `memory` tool with actions `add`, `replace`, `remove` on target `memory` or `user`.
10. **Perform web research**: use `web_search` for queries, `web_extract` to pull page content.
11. **Automate browser tasks**: use `browser_navigate` to go to a URL, `browser_snapshot` to capture, `browser_vision` to ask about visuals.
12. **Generate images or speech**: use `image_generate` (text-to-image) or `text_to_speech` (text-to-audio).
13. **Execute code snippets**: use `execute_code` (or `terminal` with `background=true` for long-running).
14. **Manage tasks**: use `todo` to create, update, or check off items.
15. **Clarify ambiguous requests**: use `clarify` to ask the user a question.
16. **Send messages via configured gateways**: use `send_message` with `deliver` target.
17. **Search past conversations**: use `session_search` with query or session ID.
18. **Integrate external tools via MCP**: use `hermes mcp` to add/configure servers, then call MCP tools directly.
19. **Verify skill installation**: run `skill_view(name='hermes-agent-overview')` and confirm the returned content matches the SKILL.md frontmatter and sections.

## Pitfalls
- Tool availability depends on enabled toolsets; some tools (e.g., `browser_*`, `web_search`) require specific toolsets to be active.
- Configuration changes via `hermes config set` may require a restart of Hermes chats to take effect for certain settings (like model). The agent cannot edit `~/.hermes/config.yaml` directly — use the CLI commands or edit the file manually.
- MCP servers require their dependencies (Node.js, Python) installed on the host for stdio servers.
- Memory has strict character limits (MEMORY.md ~2.2k chars, USER.md ~1.3k chars); exceeding limits will cause the `memory` tool to return an error.
- Skill names must be unique lowercase hyphenated strings under 64 characters.
- When using `delegate_task`, subagents cannot access the parent's memory or ask clarifying questions; all needed context must be passed via the `context` field.
- Cron jobs run in isolated sessions; they cannot ask for clarification and must be self‑contained.
- Web search and extraction depend on the configured backend; some sites may block automated access.
- Image generation and text‑to‑speech rely on configured providers; missing API keys will cause errors.

## Verification
Run `skill_view(name='hermes-agent-overview')` via the `skill_view` tool and confirm the returned content matches the SKILL.md frontmatter and sections described above.