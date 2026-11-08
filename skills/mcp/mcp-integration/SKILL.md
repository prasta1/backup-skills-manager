---
name: mcp-integration
description: "Complete MCP (Model Context Protocol) integration including server configuration, tool registration, and client usage"
version: 0.2.0
author: Hermes Agent + Teknium
license: MIT
tags: [mcp, integration, protocol, tools]
---

# MCP Integration Guide

**Trigger:** Setting up and using Model Context Protocol (MCP) integration for tool discovery and usage.

This skill provides comprehensive guidance for working with the Model Context Protocol (MCP) ecosystem, including server configuration, tool registration, and client usage patterns.

## Overview

The Model Context Protocol (MCP) enables tools to be discovered and used by LLMs through standardized interfaces. This skill covers MCP integration with both native and ad-hoc server configurations.

## MCP Client Usage

### Native MCP Integration

Hermes provides native MCP client capabilities:

```bash
# List available MCP servers
hermes mcp list

# Register a new MCP server 
hermes mcp add --name "<server-name>" --url "<server-url>"

# Configure MCP client settings (done automatically during add)
# hermes mcp config set --default-server "<server-name>"  # if needed

# Test connection to an MCP server
hermes mcp test "<server-name>"

# Discover tools from all configured servers
hermes mcp discover --all

# Execute a discovered tool
hermes mcp execute --tool "<tool-name>" --params "<params>"
```

### Ad-hoc MCP Server Interaction

Hermes provides `mcporter` CLI for direct MCP server interaction:

```bash
# List available tools from a server
mcporter list --server "http://localhost:8080"

# Configure MCP authentication
mcporter auth --server "http://localhost:8080" --token "your-token"

# Call MCP tools directly
mcporter call --server "http://localhost:8080" --tool "weather-api" --params "city=London"
```

## Server Configuration

### Setting up MCP Servers

Hermes supports various MCP server configurations. When using `hermes mcp add`, the configuration is automatically added to your profile's `config.yaml`:

```yaml
# MCP server configuration example (as added by hermes mcp add)
mcp:
  servers:
    - name: "amplitude-mcp"
      url: "https://mcp.amplitude.com/mcp"
      auth:
        type: "bearer"
        token: "your-amplitude-api-key-here"
    
    - name: "local-tools"
      url: "http://localhost:8080"
      auth:
        type: "bearer"
        token: "your-token-here"
    
    - name: "external-api"
      url: "https://api.example.com/mcp"
      auth:
        type: "oauth2"
        client_id: "your-client-id"
        client_secret: "your-secret"
```

#### Special Case: Amplitude MCP Authentication

The Amplitude MCP server at `https://mcp.amplitude.com/mcp` uses **OAuth 2.0 only** and does NOT accept raw API keys or secrets as Bearer tokens. Attempting to use them results in:

```
401 invalid_token: Token is not active
```

For Amplitude MCP, use `mcp-remote` to handle the OAuth flow:

```bash
# Correct way to add Amplitude MCP (uses mcp-remote for OAuth)
hermes mcp add amplitude --command npx --args mcp-remote https://mcp.amplitude.com/mcp
```

This will automatically handle the OAuth flow when first launched. The server will prompt for authentication via browser.

> **Note**: You must have `npx` available in your PATH (e.g., from Node.js) for this to work.

> **Note**: If you're in a headless environment (like a remote server or CI), the OAuth flow might not work properly. In such cases, you'll need to set up a local browser or use a headless browser solution like Puppeteer to complete the auth.

### Manual Configuration (Advanced)

If you need to manually edit the configuration:

```yaml
mcp:
  servers:
    - name: "<server-name>"
      url: "<server-url>"
      auth:
        type: "bearer"  # or "oauth2", "none", etc.
        token: "<your-token>"  # for bearer
        # or for oauth2:
        # client_id: "..."
        # client_secret: "..."
```

## When `hermes mcp login` blames the provider, verify before believing it

A failed `hermes mcp login` ends with a generic advisory that some providers (Google
Drive, Atlassian) lack automatic client registration and tells you to hand-create an
OAuth client. **That message is a fallback, not a diagnosis.** Do not go register a
client until you have checked the registration endpoint yourself:

```bash
curl -s https://<host>/.well-known/oauth-authorization-server | python3 -m json.tool   # registration_endpoint?
curl -s -X POST <registration_endpoint> -H 'Content-Type: application/json' \
  -d '{"client_name":"probe","redirect_uris":["http://127.0.0.1:8765/callback"],"grant_types":["authorization_code","refresh_token"],"response_types":["code"],"token_endpoint_auth_method":"none"}' -w '\nHTTP %{http_code}\n'
```

If that returns 201 with a `client_id`, dynamic registration works and the failure is
in the client's own OAuth path — not the provider. (Verified against
`huggingface.co/oauth/register`, which returns 201 for `none`, `client_secret_post`,
and even an empty `redirect_uris` array.)

**Prefer a Bearer header over OAuth in agent environments** when the server accepts a
static token. It skips DCR, the browser round-trip, and token refresh entirely, and it
reuses a credential you already hold. Read the token straight from its file into
`config.yaml` with a script so it never passes through the conversation, then verify
with `hermes mcp test <name>`. A parked server revives on the next config reconcile
without a gateway restart (`MCP server '<name>' revived - session healthy again after
parking` in `~/.hermes/logs/agent.log`).

## Wiring a Local stdio MCP Server (Hermes, verified path)

`hermes mcp add <name> --command <path> --args ... --env KEY=VALUE` is **interactive** (it asks
"Enable all N tools?" and a non-interactive shell answers nothing, so the add is **cancelled at
the prompt even though the connection succeeded**). Either answer the prompt in a real TTY, or
write the block into `~/.hermes/config.yaml` yourself under `mcp_servers:` and verify:

```yaml
mcp_servers:
  <name>:
    command: /absolute/path/to/server-binary   # never a bare name
    enabled: true
    env:
      <PROVIDER>_API_KEY: <value>              # secrets MUST live here
    timeout: 60
```

- **stdio servers get a sanitized env.** `_build_safe_env()` passes only `PATH`, `HOME`, `USER`,
  `LANG`, `LC_ALL`, `TERM`, `SHELL`, `TMPDIR`, `XDG_*`, names hydrated from a configured secret
  source, and the server's own `env:` block. Keys sitting in `os.environ` (e.g. everything in
  `~/.hermes/.env`) are **stripped**. `${VAR}` interpolation inside the block resolves through
  the secret scope, but a literal value is deterministic — use it unless the file is public.
- **Use an absolute command path.** A bare `npx`/`python` fails when the launcher PATH differs;
  install once (`npm i -g <pkg>`) and point at the binary rather than paying an `npx` cold start
  on every connect.
- **Rotating a key in an existing server's `env:` block needs a gateway restart.** The gateway
  caches the server env at spawn; killing the stdio subprocess is NOT enough — the gateway
  respawns it with the CACHED env, so the old key keeps flowing. `hermes gateway restart` from a
  separate shell (the gateway refuses to restart itself from inside; launchctl bootstrap/bootout
  is likewise blocked in-gateway). Verify via the process env or, better, a live tool call.
- **Verify, don't assume:** `hermes mcp list` (shows enabled + transport), `hermes mcp test <name>`
  (live connect, enumerates tools), `hermes tools list | grep <name>` (registered toolset).
  Config edits hot-reconcile in the running gateway — no restart:
  `gateway.run_profile_reconcile: MCP config changed (default): added=['<name>']` followed by
  `tools.mcp_tool: MCP server '<name>' (stdio): registered N tool(s)`.
- **New tools appear in the NEXT session, not the live one.** Tool schemas are frozen for the
  life of a conversation (prompt-cache invariant), so `tool_search` in the current chat will
  not see them. Start a new session to use them.
- **Raw handshake test** (no client needed) — proves transport + auth end to end:
  `(printf '%s\n' '<initialize json>' '<initialized notif>' '<tools/call json>'; sleep 4) | <server-binary>`
  and read the JSON-RPC replies off stdout. `Error: write EPIPE` on **stderr** is just the
  server noticing you closed stdin; harmless.
- `~/.hermes/config.yaml` and `~/.hermes/.env` are **not git-tracked** in the `~/.hermes` repo,
  so a key in `config.yaml` does not reach the backup remote. Back up `config.yaml` before
  editing anyway (it has no version history).

## MCP Protocol Features

### Tool Discovery

Hermes automates tool discovery:

```bash
# Discover tools from all configured servers
hermes mcp discover --all

# Filter tools by category (if supported by the server)
hermes mcp discover --category "analytics"
```

### Tool Execution

```bash
# Execute a discovered tool
hermes mcp execute --tool "<tool-name>" --params "<key=value,key2=value2>"

# Execute with context (if the tool supports it)
hermes mcp execute --tool "<tool-name>" --context "some context" --params "{}"
```

## Best Practices

### Security Considerations

- Use secure authentication for MCP servers (Bearer tokens, OAuth2)
- Validate tool capabilities before execution
- Implement proper access controls for sensitive tools
- Store API keys securely in your Hermes profile (they're encrypted in `.env`)

### Performance Optimization

- Cache tool metadata for faster discovery (Hermes does this automatically)
- Implement connection pooling for frequent server access
- Use appropriate timeout configurations

### Troubleshooting Tips

- If you get "401 Unauthorized", verify your authentication token is correct
- If a server isn't found after adding, check that it was added to the correct profile
- Use `hermes mcp list` to see configured servers and their status
- Check the Hermes logs for detailed connection error information

## Related Skills

- `mcporter` - MCP server management via mcporter CLI
- `native-mcp` - Native MCP client integration

## References

- `references/mcp-security-best-practices.md` - Authentication and security guidelines
- `templates/mcp-config.yaml` - Complete MCP configuration template
- `references/amplitude-mcp-setup.md` - Amplitude-specific MCP setup notes and OAuth handling