# Tolaria MCP PATH Fix

## Error Pattern
```text
===== [2026-07-31 06:55:27] starting MCP server 'tolaria' =====
env: node: No such file or directory
```

## Root Cause
Hermes configured `tolaria` as:
```yaml
mcp:
  servers:
    - name: tolaria
      command: /Applications/Tolaria.app/Contents/Resources/mcp-server/index.js
      args: []
      env: {}
```

This assumes:
1. `node` is on PATH in the MCP spawn environment
2. The JS file can be executed directly without an explicit interpreter

In practice, the MCP spawn environment does not include `~/.local/bin`, where
`node` is installed as a shim/symlink to `/opt/homebrew/bin/node`.

## Verification Commands
```bash
# Direct manual execution succeeds
/opt/homebrew/bin/node /Applications/Tolaria.app/Contents/Resources/mcp-server/index.js

# But Hermes `hermes mcp test` may still succeed if the test path is different
hermes mcp test tolaria

# The real launch uses the config command path, which fails without Node on PATH
grep -A4 'tolaria' ~/.hermes/config.yaml ~/.hermes/config.yaml 2>/dev/null | head -20
```

## Node Locations on This Machine
- `/opt/homebrew/bin/node` -> `/opt/homebrew/Cellar/node/26.5.0/bin/node`
- `/Users/macstudio/.local/bin/node` -> `/opt/homebrew/bin/node`
- NOT `/usr/local/bin/node`

## Fix Options
1. Use explicit Node invocation if Hermes config supports it.
2. Ensure PATH includes `/opt/homebrew/bin:/Users/macstudio/.local/bin` for the MCP spawn environment.
3. Use a wrapper script that sets PATH then `exec` the real runtime.

## Specific Case Applied
User pattern: Tolaria MCP server defined as direct JS command, local Node installed
via Homebrew at `/opt/homebrew/bin/node`, launch PATH missing `~/.local/bin`
and possibly `/opt/homebrew/bin`. Result: repeated restart loops in
`mcp-stderr.log` with healthy server lines interspersed, eventually steady
failures once PATH varied or launch hygiene changed.