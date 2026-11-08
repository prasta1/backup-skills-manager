# Provider resolution order (hermes_cli/runtime_provider.py)

1. **Named custom provider check** (`providers.<name>`)
   - Matches `custom:<name>` or display name
   - Uses `api`, `url`, or `base_url` from entry

2. **MoA short-circuit** (virtual endpoint)
   - Returns `moa://local` with no external call

3. **Azure Foundry** (explicit azure-foundry provider)

4. **Named custom runtime resolution** (`_resolve_named_custom_runtime`)
   - Handles `custom`, bare URLs, and custom provider lookup

5. **Explicit runtime** (`_resolve_explicit_runtime`)
   - Uses `model.base_url` from config when provider context matches

6. **Provider pool selection** (for built-in providers)
   - Only when `provider != openrouter` and credentials available

7. **OpenRouter fallback**
   - Default `https://openrouter.ai/api/v1` or `OPENROUTER_BASE_URL`

## Key insight: MoA presets resolve EACH slot through this same chain
- References call their provider's actual endpoint
- Aggregator becomes acting model for session
- No caching of resolved credentials (fresh per turn)