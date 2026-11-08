---
name: hermes-env-config
description: Standard setup for the Mac Studio/hermes stack.
---
# Hermes Environment & Stack Configuration

This skill captures established procedures, environmental rules, and user preferences for the Hermes stack and its environment.

## 🧭 Core Context
**The "Here" Rule**: When referring to "here" in conversation, default to the **Mac Studio** (`ms-*` host). This is the only machine running the full Hermes Gateway. The MacBook is strictly a thin client for local inference and development.

**Model IDs**: Always use host-prefixed IDs (`ms-*` for Studio, `macbook-*` for MBP).

## ⚙️ Development Workflows & Pitfalls

**Remote Dev (llama-dash)**
For remote access to the `llama-dash` dev dashboard, the server must bind all interfaces and explicitly whitelist Tailscale hostnames.

*   **Pitfall:** Failure to set `host: true` and `allowedHosts` in `vite.config.ts` results in the dev server being unreachable remotely, throwing "Blocked request" errors.
*   **Procedure**: Ensure `vite.config.ts` includes:
    ```typescript
    server: {
        host: true,
        allowedHosts: ['studio.taile85139.ts.net', 'localhost'],
    }
    ```

**Agent Patch Management**
The `hermes-agent` repository's `local` branch accumulates private, unmerged patches (~78 commits ahead of `origin/main`). `hermes update` performs a non-destructive merge.

## References
- `here_definition.md`
- `llama_dash/remote_dev_setup.md`