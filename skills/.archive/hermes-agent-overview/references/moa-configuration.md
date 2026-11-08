# MoA Configuration Reference

## For Local LM Studio Setups

When configuring Mixture of Agents with local models, use:
- **References**: Fast small models (3-8B) for quick perspectives
- **Aggregator**: Strongest available model (26B+) for synthesis
- **Timeouts**: Increase `request_timeout_seconds` (300s recommended for 70B models)

## YAML Structure

```yaml
moa:
  presets:
    <preset-name>:
      reference_models:
        - provider: <provider-slug>
          model: <model-id>
      aggregator:
        provider: <provider-slug>
        model: <model-id>
      reference_temperature: 0.6-0.8
      aggregator_temperature: 0.3-0.5
      max_tokens: 8192
      enabled: true
```

## Command Reference

- `hermes moa list` — view presets
- `hermes moa configure <name>` — create/update preset (interactive)
- `hermes moa delete <name>` — remove preset
- `/model <preset> --provider moa` — activate preset in session
- `/moa <prompt>` — one-shot with default preset

## Multi-Provider Example

Mix reference sources:
```yaml
reference_models:
  - provider: lmstudio-studio    # local
    model: microsoft/phi-4-mini-reasoning
  - provider: openrouter       # cloud fallback
    model: deepseek/deepseek-v4-pro
```

If a reference fails, MoA continues with available models.