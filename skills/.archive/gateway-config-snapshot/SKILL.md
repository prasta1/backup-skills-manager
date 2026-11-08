---
name: gateway-config-snapshot
description: Snapshot gateway runtime config and detect config drift.
---

# Gateway Config Snapshot & Verification

## When to Use
Run before/after Hermes updates or troubleshooting provider fallback. Detects drift between config.yaml and the gateway runtime.

## Snapshot

```bash
cd /Users/macstudio/.hermes

# Config version
grep "_config_version" config.yaml

# Runtime environment of the gateway process
pgrep -f "hermes_cli.main gateway" | head -1 | xargs -I{} ps -E -p {} \
  | grep -oP '\w+=\S*' | sort > /tmp/gateway-runtime-env-$(date +%s).txt

# Verify .env matches config.yaml providers
python3 -c "
from pathlib import Path
import yaml
env = dict(line.split('=',1) for line in Path('/Users/macstudio/.hermes/.env').read_text().strip().split('\n') if '=' in line)
cfg = yaml.safe_load(Path('/Users/macstudio/.hermes/config.yaml').read_text())
print('.env keys:', sorted(env.keys()))
print('config.yaml providers:', sorted(cfg.get('providers',{}).keys()))
"

# Effective config
hermes config get model.default
hermes config get model.provider

# Uncommitted changes
git -C /Users/macstudio/.hermes status --short
```

## .env Integrity Guard
`gateway-launch.sh` now verifies `.env` checksum before sourcing:
```bash
ENV_HASH="cc5b1a1f8fb786c34d55a2ae714946251d238c72ed5d413cade650a27a8272e1"
ACTUAL_HASH=$(shasum -a 256 ~/.hermes/.env 2>/dev/null | awk '{print $1}')
if [ "$ACTUAL_HASH" != "$ENV_HASH" ]; then
  echo "WARNING: .env checksum mismatch!" >&2
fi
```
Check gateway logs after restart for the warning line if `.env` has been modified.
