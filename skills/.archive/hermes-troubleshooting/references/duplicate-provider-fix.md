# Duplicate Provider in Menu Fix

## Symptom
OpenRouter (or any provider) appears twice in the model/provider selection menu.

## Cause
The provider is declared in the `providers:` section AND referenced again in a top-level `moa.reference_models` block:

```yaml
providers:
  openrouter:
    name: OpenRouter
    ...

# This block is redundant if you use presets:
moa:
  reference_models:
    - provider: openrouter
      ...
```

## Fix
1. Delete the redundant `moa.reference_models` block (usually lines ~454-466)
2. Restart the gateway: `launchctl bootout gui/$(id -u)/ai.hermes.gateway && launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/ai.hermes.gateway.plist`

## Prevention
Use `moa.presets.<name>` for model selection; the old `reference_models` block at top-level is deprecated and only exists for legacy configs.