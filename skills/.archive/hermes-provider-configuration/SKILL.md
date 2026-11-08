---
name: hermes-provider-configuration
description: Configure Hermes AI providers and Mixture of Agents presets
version: 0.1.0
author: Hermes Agent
category: hermes
tags: [providers, configuration, moa]
---

# Hermes Provider Configuration

## Purpose
Configure AI providers in Hermes and set up Mixture of Agents (MoA) presets that leverage local and cloud models.

## Virtual Providers

### Mixture of Agents (moa)
MoA is a **virtual provider** with no external endpoint. It orchestrates multiple reference models and an aggregator model:

```yaml
moa:
  default_preset: default
  presets:
    default:
      reference_models:
        - provider: <provider-name>
          model: <model-id>
      aggregator:
        provider: <provider-name>
        model: <model-id>
```

When you select a MoA preset:
1. Reference models run in parallel (no tools, analysis only)
2. Aggregator runs with full Hermes context and tools
3. Aggregator synthesizes references into final response

### Configuration
**Important**: MoA presets use real provider credentials. Each slot resolves through `resolve_runtime_provider`:
- References route through their provider's actual endpoint
- Aggregator becomes the acting model for the session
- No recursive MoA presets allowed (blocked by design)

## Custom Providers

### Adding a Tailscale LM Studio endpoint
```yaml
providers:
  your-name:
    api_key: no-key-required      # or use key_env
    base_url: http://your-node.ts.net:1234/v1
    default_model: <model-id>
    name: <Display Name>
```

Use `hermes config set 'providers.<name>.name' '<Display Name>'` to rename (safer than editing config directly).

### Provider Resolution Priority
1. Named custom providers (`providers.<name>`)
2. Configured `model.base_url` / `model.provider`
3. Environment variables (`OPENROUTER_BASE_URL`, `CUSTOM_BASE_URL`)
4. Provider pools (for built-in providers with credentials)

## MoA Preset Patterns

### Local-model setup (cost-free)
Use small fast models for references, strongest for aggregator:

```yaml
moa:
  presets:
    reasoning:
      reference_models:
        - provider: lmstudio-studio
          model: microsoft/phi-4-mini-reasoning
        - provider: lmstudio-studio
          model: qwen/qwen3-vl-8b
      aggregator:
        provider: lmstudio-studio
        model: nousresearch/hermes-4-70b
      reference_temperature: 0.7
      aggregator_temperature: 0.4
```

### Hybrid setup (local refs, cloud aggregator)
```yaml
moa:
  presets:
    hybrid:
      reference_models:
        - provider: lmstudio-studio
          model: google/gemma-4-26b-a4b-qat
        - provider: lmstudio-studio
          model: mistralai/devstral-small-2-2512
      aggregator:
        provider: openrouter
        model: anthropic/claude-opus-4.8
```

## Verification
- Test provider: `hermes config show` → verify `providers:` section
- List MoA presets: `hermes moa list`
- Test preset: `/model <preset> --provider moa` then check `hermes status`

## Examples
See `templates/moa-preset-examples.yaml` for preset templates and `templates/coding-auxiliary-models.yaml` for coding-focused auxiliary model configs.

## Desktop Gateway Notes
- Desktop remote gateway uses `gateway.proxy_url`, NOT provider `base_url`
- OAuth gateway sessions expire; re-authenticate via Settings → Gateway
- Gateway binds to 127.0.0.1 by default; use `tailscale serve --bg 8642` to expose externally
- **User Preference Alignment**: The user prefers direct commands to execute without meta-commentary about why these steps are needed, and minimal explanation unless specifically requested

## References
- `references/provider-resolution-chain.md` — provider resolution priority order
- `references/tailscale-remote-setup.md` — Tailscale gateway setup for remote desktop clients
- `references/duplicate-provider-fix.md` — diagnose and fix duplicate providers in the menu

## Pitfalls
- Never set `provider: moa` as a reference/aggregator (blocked, creates infinite loop)
- Config edits to `~/.hermes/config.yaml` require `hermes config set` or restart
- `base_url: moa://local` is internal-only; references still need real endpoints
- A single failed reference doesn't abort the turn—it's included as error context
- **Avoid `hermes config set fallback_providers`** — YAML list serialization often becomes a string instead of proper list syntax. Edit the file directly or use a one-shot preset
- When configuring remote Tailscale backends from macOS client, use the exact model IDs returned by `/v1/models` endpoint (not abbreviated forms)
- **Do not duplicate providers in `moa.reference_models`** (lines like `- provider: openrouter` at top level vs inside `providers:` section). This causes the provider to appear twice in the provider picker menu. Use presets for model selection; top-level `reference_models` is redundant and deprecated