# Distributed Hermes Setup: Profile Endpoint Updates

## Context
When running Hermes client on one machine (MacBook) with backend on another (Mac Studio), all profiles using remote providers must have their `base_url` updated to the Tailscale hostname.

## Common Pitfall: Incomplete Profile Updates
Using `hermes config set` from within a profile session only updates that profile. Other profiles may retain stale localhost endpoints.

### Example Issue
User had profiles `cs-copilot`, `bd-copilot`, `larp`, and `diane`. Only `cs-copilot` and `bd-copilot` were updated to `studio.taile85139.ts.net:1234`. The `larp` profile still pointed to `localhost:1234` and used wrong model ID (`gemma-4-26b-a4b-it-qat-mlx` vs server's `google/gemma-4-26b-a4b-qat`).

## Remediation Script
```bash
# Apply Tailscale endpoint to all profiles using lmstudio-studio
for profile in ~/.hermes/profiles/*/config.yaml; do
  if grep -q "lmstudio-studio" "$profile"; then
    # Check if it has localhost instead of Tailscale
    if grep -q "localhost:1234" "$profile"; then
      echo "Fixing: $(dirname $profile | xargs basename)"
    fi
  fi
done

# Individual profile fix:
hermes config set providers.lmstudio-studio.base_url http://studio.taile85139.ts.net:1234/v1
hermes config set providers.lmstudio-studio.default_model google/gemma-4-26b-a4b-qat
```

## Verification
```bash
# Check all profile configs
for p in ~/.hermes/profiles/*; do
  echo "--- $p ---"
  grep -A2 "lmstudio-studio:" "$p/config.yaml" 2>/dev/null || echo "No lmstudio-studio"
done

# Test connectivity
curl -s http://studio.taile85139.ts.net:1234/v1/models | jq -r '.data[].id'
```

## Model ID Gotcha
LM Studio server returns model IDs in format `google/gemma-4-26b-a4b-qat` but configs may have variants like `gemma-4-26b-a4b-it-qat-mlx` (using mlx, different quantization). Always verify exact ID from `/v1/models` endpoint before setting `default_model`.

## Model Selection for Profile Roles
When fixing profiles, consider the profile's purpose:

| Profile Role | Recommended Model | Rationale |
|--------------|-----------------|-----------|
| General purpose | `google/gemma-4-26b-a4b-qat` | Balanced quality/speed |
| Coding/dev work | `mistralai/devstral-small-2-2512` | Efficient coding model, faster iteration |
| Heavy reasoning | `qwen/qwen3-coder-next` | Explicit coder model, better complex tasks |

The `larp` coding profile was updated to use `mistralai/devstral-small-2-2512` for performance.