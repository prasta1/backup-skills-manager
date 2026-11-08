---
name: hermes-configuration
description: "Comprehensive configuration and management of Hermes AI agent workflows"
version: 0.1.2
author: Hermes Agent + Teknium
license: MIT
tags: [hermes, configuration, local-models, inference, mlops]
---

# Hermes Configuration & Management

**Trigger:** Setting up and managing Hermes AI agent workflows, local model serving, and distributed inference patterns.

This skill covers the complete ecosystem of Hermes configuration including local model setup, provider management, and optimization strategies.

## Overview

This skill covers the complete ecosystem of Hermes configuration including local model setup, provider management, and optimization strategies.

## Local Model Configuration

### Profile-Specific Configuration

Hermes supports multiple named profiles, each with its own `config.yaml`. The default profile's config does NOT apply to other profiles.

**Before switching profiles, verify provider endpoints match your infrastructure:**

| Profile | Provider | Typical Issue |
|---------|----------|---------------|
| default | varies | Check if lmstudio points to correct host |
| cs-copilot, bd-copilot | lmstudio-studio | Often set to localhost, needs Tailscale hostname |
| diane | nous/openrouter | May not need local server changes |

**Apply Tailscale endpoint to all lmstudio profiles:**
```bash
hermes config set providers.lmstudio-studio.base_url http://studio.taile85139.ts.net:1234/v1
```

**Check active profile:**
```bash
hermes config get profile
ls ~/.hermes/profiles/  # list all profiles
```

**Pitfall:** Editing the default config while in a profile session has no effect. Changes must be applied to the profile that will use them.

### Ollama Integration

Hermes integrates with local Ollama instances for fast, offline inference. This setup allows users to leverage powerful local models while maintaining reliability.

#### Architecture

- **Local Ollama** (`localhost:11434`) - primary fast local inference
- **Tailscale Relay** (`studio.taile85139.ts.net:11434`) - fallback or distributed access

### Provider Naming

Each provider entry can have a custom display `name` field. This appears in status displays and model selection menus. To rename a provider to a specific display name (without changing the key):
```bash
hermes config set providers.<provider-key>.name "New Display Name"
```
The provider key (e.g., `lmstudio-studio`) remains the stable identifier; only the display name changes.

**Example:** Renaming the studio Tailscale endpoint:
```bash
hermes config set providers.lmstudio-studio.name "LMS: MacStudioUltra"
```

### Pitfall

**Config write restrictions:** Direct file edits to `~/.hermes/config.yaml` are blocked for security. Always use `hermes config set` for configuration changes, which validates and applies atomically.

### LM Studio Integration

For users running LM Studio on remote/headless machines, configure via Tailscale:

```yaml
providers:
  lmstudio-studio:
    base_url: http://studio.taile85139.ts.net:1234/v1
    api_key: no-key-required
    default_model: nousresearch/hermes-4-70b
    name: 'LMS: MacStudioUltra'
    request_timeout_seconds: 300
  lmstudio-local:
    api_key: no-key-required
    base_url: http://localhost:1234/v1
    name: 'LMS: MacBookLocal'
    default_model: google/gemma-4-26b-a4b-qat
```

### Pitfall

**Config write restrictions:** Direct file edits to `~/.hermes/config.yaml` are blocked for security. Always use `hermes config set` for configuration changes, which validates and applies atomically.

### Docker Networking Exception

**Important Note:** When running services like Honcho in Docker containers on Synology NAS (or other Linux hosts), `host.docker.internal` URLs only work in Docker Desktop environments. For native Docker, use explicit Tailscale IPs or hostnames:

```bash
# In .env files for Docker containers on Linux hosts:
DERIVER_MODEL_CONFIG__OVERRIDES__BASE_URL=http://100.89.133.43:1234/v1
EMBEDDING_MODEL_CONFIG__OVERRIDES__BASE_URL=http://100.89.133.43:1234/v1
DIALECTIC_LEVELS__minimal__MODEL_CONFIG__OVERRIDES__BASE_URL=http://100.89.133.43:1234/v1
```

### Troubleshooting Guide

- **Ollama not responding** → `ollama serve` or restart Ollama
- **Provider 404** → Pull model: `ollama pull <model>`
- **Tailscale blocked** → `tailscale up`
- **Changes not applying** → `/reset` (in session) or restart `hermes`

## Distributed Inference Patterns

### Distributed Inference Patterns

Hermes supports distributed inference patterns where primary heavy-lift models are hosted on a powerful remote machine (e.g. Mac Studio) while a local machine (e.g. MacBook) provides fast local fallback or lightweight auxiliary services.

#### Architecture: Heterogeneous Fallback
In a heterogeneous setup, models on the remote machine may have different architectures or even different versions than the local machine. 

**Optimal Strategy: Intentional Divergence**
Instead of mirroring everything, configure Hermes to use specialized models on each device:
- **Primary/Remote**: High-parameter models (70B+) for complex reasoning and heavy lifting.
- **Local/Fallback**: Faster, smaller models (8B-24B) that ensure continuity for chat and auxiliary tasks when the remote machine is unavailable.

**Pitfall: Model-Aware Fallover Limitation**
Hermes currently supports sequential fallback based on connection/availability (e.g., `fallback_to: local-tailscale`), but it does **not** support conditional model-aware routing (e.g., "if Studio model is a reasoning model, use this; else use that"). Users must manage model alignment via the configuration.

## Prompt Optimization Note

When running distributed inference setups (e.g., Mac Studio as primary with local fallback), the system prompt can grow significantly due to:
- Tool lists and guidance blocks being duplicated across all instances
- Memory/user profile blocks that get fully expanded in each prompt
- Context files like AGENTS.md being included in every session

To optimize token usage in distributed setups:
1. Use profile-specific configuration to reduce redundant tool inclusion
2. Implement system prompt compression for remote instances where token efficiency is critical
3. Consider centralized memory management to avoid full profile expansion in fallback instances

This is particularly relevant for performance-sensitive use cases where prompt size impacts latency or token costs.

#### Configuration Example

```yaml
# config.yaml snippet
providers:
  lmstudio-studio:
    base_url: http://studio.taile85139.ts.net:1234/v1
    default_model: nousresearch/hermes-4-70b
    fallback_to: lmstudio-local

  lmstudio-local:
    base_url: http://localhost:1234/v1
    default_model: google/gemma-4-26b-a4b-qat
```

### Configuration Backup and Cleanup

Hermes automatically creates backups of `config.yaml` when it saves changes. These backups are named with timestamps and include patterns like `.bak.<timestamp>`, `.corrupt.<timestamp>.bak`, or `.modelname.<timestamp>`.

While these backups serve as a safety net, they can accumulate over time. A typical cleanup involves:

1.  **Keeping the current `config.yaml`** (no suffix).
2.  **Retaining one most recent backup** (e.g., `.bak.20260703_170434`).
3.  **Deleting older `.bak`, `.corrupt`, or `.new` files** to prevent bloat.

For example, to clean up these files manually:
```bash
# Navigate to your .hermes directory
cd ~/.hermes

# List all config backups (including the current one)
ls config.yaml*

# Delete redundant backup files (keeping only the latest and the current)
rm config.yaml.bak.* config.yaml.corrupt.* config.yaml.new config.yaml.backup
```

### Automation Tip

You can set up a cron job or script to automate this cleanup periodically. This prevents long-term accumulation of configuration snapshots and keeps your Hermes directory clean.

For a manual solution, use the `execute_code` tool with a Python script to selectively delete files older than a specified threshold, retaining the current config and one backup.

This pattern is an example of Hermes using its own system to create redundant data for safety but lacking a built-in mechanism to prune it.

### User Preference Alignment

The user prefers "for once and for all" solutions over incremental fixes, which means they want to understand why something is working as designed rather than being treated as a bug. When troubleshooting configuration issues, they prefer direct commands to execute without meta-commentary about why these steps are needed.

### Pitfall: Configuration File Bloat

The `config.yaml` backup mechanism, while a safety feature, is not self-managing. It creates an increasing number of files over time (e.g., 23 `.bak` or `.corrupt` copies) unless actively pruned. This can lead to disk bloat and confusion about which file is the "real" configuration.

### Best Practice: Scheduled Cleanup

To manage this, users should periodically clean up these backup files. The cleanup process should:
1.  Identify the current `config.yaml`.
2.  Retain one recent backup (e.g., `.bak.20260703_170434`).
3.  Delete all other `.bak`, `.corrupt`, and `.new` files.

This ensures that the user's configuration is safe (via a recent backup) while avoiding unnecessary clutter.

### Troubleshooting Guide

- **Ollama not responding** → `ollama serve` or restart Ollama
- **Provider 404** → Pull model: `ollama pull <model>`
- **Tailscale blocked** → `tailscale up`
- **Changes not applying** → `/reset` (in session) or restart `hermes`

## Related Skills

- `hermes-agent` - General Hermes configuration and extension
- `llama-cpp` - GGUF model inference
- `hermes-agent-skill-authoring` - Skill authoring and documentation
- `hermes-profile-authentication` - Specific fix for multi-profile authentication issues

## Authentication Pitfall: Multi-Profile Session Isolation

When running Hermes in multi-profile mode with a gateway, desktop clients must properly authenticate to the gateway server. A common issue occurs when desktop applications attempt to connect to a remote Hermes gateway but send authentication headers that don't match what the gateway expects.

### Root Cause Analysis

The desktop app authenticates to gateways via two separate mechanisms:
1. **Local mode**: Desktop spawns its own per-profile backend processes, each getting a unique `HERMES_DASHBOARD_SESSION_TOKEN` 
2. **Remote mode**: Desktop connects to remote gateway using either:
   - Token auth: `X-Hermes-Session-Token` header (as used in desktop app's local mode)
   - OAuth auth: Session cookies + WebSocket ticket

However, the Hermes gateway API server (`api_server.py`) only validates `Authorization: Bearer ***` tokens (line 1245-1254), not the `X-Hermes-Session-Token` header, causing authentication rejections.

### Configuration Fix

To resolve this issue, see the dedicated `hermes-profile-authentication` skill which documents:

1. **Set an API server key** in the gateway's environment (`~/.hermes/.env`):
   ```bash
   echo "API_SERVER_KEY=your-secret-key-here" >> ~/.hermes/.env
   ```

2. **Configure the desktop client** to use token authentication when connecting to the remote gateway:
   - In Settings → Gateway, set the URL and provide the token via `X-Hermes-Session-Token` header format
   - Or set `HERMES_DESKTOP_REMOTE_URL` and `HERMES_DESKTOP_REMOTE_TOKEN` environment variables

### Example Desktop Configuration for Studio Gateway Connection

```bash
# Set environment variables for the desktop app to connect securely to Studio
export HERMES_DESKTOP_REMOTE_URL=http://studio.taile85139.ts.net:8642
export HERMES_DESKTOP_REMOTE_TOKEN=your-api-token-here
```

This ensures proper authentication and resolves the "Invalid API key" errors that occur when profile sessions merge incorrectly.

## References

- `references/photon-imessage-setup.md`
- `references/model-selection-strategies.md`
- `references/lmstudio-troubleshooting.md`
- `references/provider-organization.md`
- `references/profile-distributed-endpoints.md`
- `references/tailscale-relay-setup.md`
- `references/distributed-prompt-optimization.md`

1. Use the `cross_profile=true` parameter with file operation tools (write_file, patch, etc.)
2. Be aware that modifications will affect the target profile's future sessions
3. Verify you're targeting the correct profile path (e.g., `~/.hermes/profiles/profile-name/`)
4. Consider whether you should instead switch to that profile for the operation

Example:
```python
# Writing to another profile's hermes-configuration skill directory
write_file(
    path="/Users/macstudio/.hermes/profiles/default/skills/hermes-configuration/SKILL.md",
    content="# Skill content...",
    cross_profile=True  # Required when targeting non-active profile
)
```