---
name: mnemosyne-memory-availability-fix
description: Fix mnemosyne memory provider unavailable in Hermes gateway.
---

# Fixing Mnemosyne Memory Provider "Not Available" in Hermes Gateway

## Root Cause
The `mnemosyne-hermes` and `mnemosyne-memory` packages were installed in a **uv-managed Python 3.13 environment** (`~/.local/share/uv/tools/mnemosyne-hermes/lib/python3.13/`), but the Hermes gateway runs in its own **Python 3.11 venv** (`~/.hermes/hermes-agent/venv/lib/python3.11/`). The plugin directory exists under `~/.hermes/plugins/`, so Hermes detects it as "installed" — but the venv Python can't import the mnemosyne core modules, so the provider reports "not available."

## Fix

### 1. Install packages into the gateway venv
```bash
/Users/macstudio/.hermes/hermes-agent/venv/bin/pip install mnemosyne-hermes==0.5.0
```
Pin to `0.5.0` to match the plugin version in `~/.hermes/plugins/mnemosyne/plugin.yaml`.

### 2. Verify imports resolve
```bash
/Users/macstudio/.hermes/hermes-agent/venv/bin/python -c "
from mnemosyne.batch_tool import validate_batch_operations
from mnemosyne.hermes_config import read_hermes_config_key
from mnemosyne.integrations.hermes_persona_prompt import HermesPersonaPromptMixin
from mnemosyne.core.beam import BeamMemory
from mnemosyne.core.triples import add_triple, query_triples
print('All imports OK')
"
```

### 3. Restart the gateway
```bash
pgrep -f "hermes_cli.main gateway"  # get PID
kill -TERM <PID>                    # launchd restarts via KeepAlive
sleep 8
/Users/macstudio/.hermes/hermes-agent/venv/bin/hermes memory status
```

## Notes
- The standalone `mnemosyne` CLI at `~/.local/bin/mnemosyne` still works (separate Python 3.13 shebang). Keep both installs coexisting.
- Idempotent — re-running pip install confirms "already satisfied."